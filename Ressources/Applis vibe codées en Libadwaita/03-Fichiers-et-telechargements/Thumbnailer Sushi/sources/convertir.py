#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Convertisseur utilisé par le plugin Sushi « sushi-thumbnailer-docs-extra ».

Usage :
    convertir.py document <fichier>
        Documents (ODT, OTT, FODT, DOCX, DOCM, DOTX, DOTM, RTF, Markdown) et présentations
        (ODP, OTP, FODP, PPTX, PPTM, POTX, PPSX) : écrit sur la sortie standard
        une page HTML autonome (images intégrées en data: URI), affichée par le
        plugin avec WebKit.
    convertir.py tableur <fichier>
        Tableurs (ODS, OTS, FODS, XLSX, XLSM, XLTX, XLTM) :
        Écrit sur la sortie standard le contenu des feuilles en JSON
        (valeurs calculées, jamais les formules).

Codes de sortie : 0 succès, 2 usage, 3 fichier trop gros, 4 délai dépassé,
5 format non pris en charge, 6 échec de lecture ou de conversion.
Les messages d'erreur, en français, sont écrits sur la sortie d'erreur.
"""

import base64
import datetime
import json
import mimetypes
import os
import re
import signal
import sys
import zipfile

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, 'vendor'))  # mammoth et cobble embarqués
sys.path.insert(0, ICI)
import lecteurs  # noqa: E402

# --- Limites -----------------------------------------------------------------

DELAI_MAX_S = 25                      # le plugin coupe de son côté à 30 s
TAILLE_MAX_DOCUMENT = 40 * 1024**2    # taille du fichier sur le disque
TAILLE_MAX_TABLEUR = 25 * 1024**2
TAILLE_MAX_DECOMPRESSEE = 300 * 1024**2   # protection contre les « bombes zip »
MAX_FEUILLES = 30
MAX_LIGNES = 2000                     # par feuille
MAX_COLONNES = 60                     # par feuille
MAX_REPETITIONS = 10000               # lignes/colonnes répétées dans un ODS
COMPTER_FORMULES_SANS_VALEUR = True   # désactivé par le générateur de miniatures

E_USAGE, E_TROP_GROS, E_DELAI, E_FORMAT, E_ECHEC = 2, 3, 4, 5, 6


class Erreur(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _delai_depasse(signum, frame):
    raise Erreur(E_DELAI, f"Délai dépassé ({DELAI_MAX_S} s) : fichier trop complexe pour l'aperçu.")


def verifier_fichier(chemin, taille_max, zip_attendu=True):
    try:
        taille = os.path.getsize(chemin)
    except OSError as e:
        raise Erreur(E_ECHEC, f"Fichier illisible : {e.strerror}.")
    if taille > taille_max:
        raise Erreur(E_TROP_GROS,
                     f"Fichier trop gros pour l'aperçu ({taille / 1024**2:.0f} Mo, "
                     f"maximum {taille_max // 1024**2} Mo).")
    if not zip_attendu:
        return
    try:
        with zipfile.ZipFile(chemin) as z:
            total = sum(i.file_size for i in z.infolist())
    except zipfile.BadZipFile:
        raise Erreur(E_ECHEC, "Fichier endommagé ou qui n'est pas un document Office/OpenDocument.")
    if total > TAILLE_MAX_DECOMPRESSEE:
        raise Erreur(E_TROP_GROS, "Contenu décompressé trop volumineux pour l'aperçu.")


def extension(chemin):
    return os.path.splitext(chemin)[1].lower()


# --- Documents texte → HTML ---------------------------------------------------

CSS_APERCU = """
:root { color-scheme: light dark; }
html { background: #ebebed; }
@media (prefers-color-scheme: dark) { html { background: #222226; } }
/* odfpy pose « * { background-color: white } » : sans ce fond transparent,
   le body recouvre le fond du volet et l'on ne voit plus ni l'arrondi ni
   l'ombre de la feuille (elle est blanche sur blanc). */
body { margin: 0; padding: 20px 16px; background: transparent; }
/* La « feuille » reste blanche : les documents sont écrits pour du papier.
   Rayon 12 px et ombre discrète : la norme des cartes Adwaita. */
.page { box-sizing: border-box; max-width: 21cm; margin: 0 auto;
        padding: clamp(20px, 6vw, 2.2cm); background: #fff; color: #241f31;
        border-radius: 12px; box-shadow: 0 1px 2px rgba(0,0,0,.12), 0 0 0 1px rgba(0,0,0,.04);
        font-size: 11pt; line-height: 1.5; overflow-wrap: break-word; }
/* Adwaita Sans pour tout le document, y compris les styles apportés par le
   fichier (odfpy, mammoth) : l'aperçu garde la typographie de GNOME. */
.page, .page * { font-family: "Adwaita Sans", Cantarell, "Noto Sans", "DejaVu Sans", sans-serif !important; }
.page code, .page pre, .page kbd, .page samp,
.page code *, .page pre * { font-family: "Adwaita Mono", "Source Code Pro", "DejaVu Sans Mono", monospace !important; }
.page h1, .page h2, .page h3, .page h4, .page h5, .page h6 { line-height: 1.2; margin: 1.1em 0 0.45em; color: #000; }
.page h1 { font-size: 1.75em; } .page h2 { font-size: 1.4em; } .page h3 { font-size: 1.18em; }
.page h4, .page h5, .page h6 { font-size: 1em; }
.page > :first-child { margin-top: 0; }
.page p { margin: 0 0 0.55em; }
.page ul, .page ol { margin: 0 0 0.6em; padding-left: 1.6em; }
.page li { margin: 0.12em 0; }
.page table { border-collapse: collapse; margin: 0.6em 0 0.9em; max-width: 100%; }
.page td, .page th { border: 1px solid #c0bfbc; padding: 0.25em 0.5em; vertical-align: top; }
.page th { background: #f6f5f4; font-weight: bold; }
.page td p, .page th p { margin: 0; }
.page img { max-width: 100%; height: auto; }
.page a { color: #1c71d8; }
.page blockquote { margin: 0.6em 0 0.6em 1em; padding-left: 0.8em; border-left: 3px solid #deddda; }
"""

# Aucun script, aucune ressource extérieure : seules les images intégrées
# (data:) et les styles de la page sont autorisés. Un document piégé ne peut
# ni contacter un serveur ni lire un fichier local.
CSP = ("default-src 'none'; img-src data:; style-src 'unsafe-inline'; "
       "font-src data:; form-action 'none'; base-uri 'none'")


def html_depuis_docx(chemin):
    import mammoth
    with open(chemin, 'rb') as f:
        # Les images sont intégrées en data: URI par défaut.
        styles = "\n".join([
            "p[style-name='Title'] => h1.titre:fresh",
            "p[style-name='Titre'] => h1.titre:fresh",
            "p[style-name='Subtitle'] => p.sous-titre:fresh",
            "p[style-name='Sous-titre'] => p.sous-titre:fresh",
        ])
        resultat = mammoth.convert_to_html(f, style_map=styles)
    return resultat.value, ''


def html_depuis_odt(chemin):
    from odf.odf2xhtml import ODF2XHTML

    archive = zipfile.ZipFile(chemin)

    class Convertisseur(ODF2XHTML):
        def rewritelink(self, href):
            # Images internes (Pictures/…) → data: URI ; liens externes ignorés.
            nom = href[2:] if href.startswith('./') else href
            try:
                donnees = archive.read(nom)
            except KeyError:
                return ''
            type_mime = mimetypes.guess_type(nom)[0] or 'application/octet-stream'
            return f"data:{type_mime};base64,{base64.b64encode(donnees).decode()}"

    conv = Convertisseur(generate_css=True, embedable=True)
    corps = conv.odf2xhtml(chemin)
    try:
        css = conv.css()
    except Exception:
        css = ''
    # odfpy fixe parfois une taille de page ou des marges : on garde les nôtres.
    css = re.sub(r'@page[^{]*\{[^}]*\}', '', css)
    return corps, css


TAILLE_MAX_MARKDOWN = 5 * 1024**2
TAILLE_MAX_IMAGE_MD = 4 * 1024**2
TAILLE_MAX_IMAGES_MD = 20 * 1024**2
TYPES_IMAGE_MD = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                  '.gif': 'image/gif', '.webp': 'image/webp', '.svg': 'image/svg+xml'}


def html_depuis_md(chemin):
    """Markdown → HTML (python-markdown). Les images locales situées dans le
    dossier du fichier (ou ses sous-dossiers) sont intégrées en data: URI ;
    les autres (distantes, hors dossier, trop grosses) sont remplacées par
    leur texte alternatif."""
    import html as html_mod
    import urllib.parse
    import markdown
    with open(chemin, 'rb') as f:
        texte = f.read().decode('utf-8', 'replace')
    corps = markdown.markdown(texte, extensions=['tables', 'fenced_code', 'sane_lists'],
                              output_format='html')
    dossier = os.path.realpath(os.path.dirname(os.path.abspath(chemin)))
    budget = [TAILLE_MAX_IMAGES_MD]

    def remplacer(m):
        balise = m.group(0)
        src = re.search(r'\ssrc="([^"]*)"', balise)
        alt = re.search(r'\salt="([^"]*)"', balise)
        alt = alt.group(1) if alt else ''
        bloquee = f'<span class="image-bloquee">Image non affichée{" : " + alt if alt else ""}</span>'
        if not src:
            return bloquee
        cible = html_mod.unescape(src.group(1))
        if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', cible) or cible.startswith('//'):
            return bloquee                         # distante (http, file…) : jamais chargée
        cible = urllib.parse.unquote(cible.split('#')[0].split('?')[0])
        vrai = os.path.realpath(os.path.join(dossier, cible))
        type_mime = TYPES_IMAGE_MD.get(os.path.splitext(vrai)[1].lower())
        if (not type_mime or not vrai.startswith(dossier + os.sep) or not os.path.isfile(vrai)):
            return bloquee
        taille = os.path.getsize(vrai)
        if taille > TAILLE_MAX_IMAGE_MD or taille > budget[0]:
            return bloquee
        budget[0] -= taille
        with open(vrai, 'rb') as f:
            donnees = base64.b64encode(f.read()).decode()
        return (f'<img alt="{html_mod.escape(alt)}" src="data:{type_mime};base64,{donnees}">')

    corps = re.sub(r'<img\b[^>]*>', remplacer, corps)
    return corps, ''


CSS_MARKDOWN = """
.page code, .page pre { font-size: .9em; }
.page :not(pre) > code { background: #f2f1ef; padding: .1em .3em; border-radius: 4px; }
.page pre { background: #f6f5f4; padding: .8em 1em; border-radius: 6px; overflow-x: auto;
            line-height: 1.4; white-space: pre-wrap; }
.page hr { border: none; border-top: 1px solid #deddda; margin: 1.2em 0; }
.page .image-bloquee { display: inline-block; padding: .2em .6em; border: 1px dashed #c0bfbc;
                       border-radius: 4px; color: #77767b; font-size: .85em; }
"""


def _echapper(t):
    import html
    return html.escape(t, quote=True)


def html_depuis_blocs(blocs):
    """Blocs de lecteurs.py → HTML simple (RTF, FODT)."""
    morceaux, liste, tableau = [], False, False
    for genre, valeur in blocs:
        if genre != 'puce' and liste:
            morceaux.append('</ul>')
            liste = False
        if genre != 'ligne' and tableau:
            morceaux.append('</table>')
            tableau = False
        if genre == 'image':
            mime, octets = valeur
            morceaux.append(f'<p><img alt="" src="data:{mime};base64,'
                            f'{base64.b64encode(octets).decode()}"></p>')
        elif genre == 'ligne':
            if not tableau:
                morceaux.append('<table>')
                tableau = True
            morceaux.append('<tr>' + ''.join(f'<td>{_echapper(c)}</td>' for c in valeur) + '</tr>')
        elif genre == 'puce':
            if not liste:
                morceaux.append('<ul>')
                liste = True
            morceaux.append(f'<li>{_echapper(valeur)}</li>')
        elif genre == 'code':
            morceaux.append(f'<pre><code>{_echapper(valeur)}</code></pre>')
        else:
            balise = {'titre': 'h1', 'h1': 'h1', 'h2': 'h2', 'h3': 'h3'}.get(genre, 'p')
            morceaux.append(f'<{balise}>{_echapper(valeur)}</{balise}>')
    morceaux.append('</ul>' if liste else '')
    morceaux.append('</table>' if tableau else '')
    return ''.join(morceaux)


CSS_DIAPOS = """
.diapos { max-width: 960px; margin: 0 auto; display: flex; flex-direction: column; gap: 22px; }
.diapo { position: relative; aspect-ratio: 16 / 9; box-sizing: border-box; overflow: hidden;
         padding: 4.5% 6%; background: #fff; color: #241f31; border-radius: 12px;
         box-shadow: 0 1px 2px rgba(0,0,0,.12), 0 0 0 1px rgba(0,0,0,.04);
         font-size: clamp(11px, 2.1vw, 19px); line-height: 1.35; }
.diapo, .diapo * { font-family: "Adwaita Sans", Cantarell, "Noto Sans", "DejaVu Sans", sans-serif !important; }
.diapo h2 { margin: 0 0 .7em; font-size: 1.75em; line-height: 1.15; color: #000; }
.diapo ul { margin: 0; padding-left: 1.3em; }
.diapo li { margin: .25em 0; }
.diapo li.n1 { margin-left: 1.4em; font-size: .92em; }
.diapo li.n2 { margin-left: 2.8em; font-size: .86em; }
.diapo .numero { position: absolute; right: 1.2em; bottom: .8em; font-size: .7em; color: #77767b; }
.diapo .sous-titre { margin: -.3em 0 .8em; font-size: 1.15em; color: #5e5c64; }
.vide { color: #77767b; font-style: italic; }
"""


def html_depuis_diapos(diapos):
    if not diapos:
        return '<div class="diapos"><p class="vide">Présentation vide.</p></div>'
    cartes = []
    for i, d in enumerate(diapos, 1):
        sous_titres = ''.join(f'<p class="sous-titre">{_echapper(t)}</p>'
                              for niveau, t in d['lignes'] if niveau < 0)
        lignes = ''.join(f'<li class="n{min(niveau, 2)}">{_echapper(t)}</li>'
                         for niveau, t in d['lignes'] if niveau >= 0)
        cartes.append('<section class="diapo">'
                      + (f'<h2>{_echapper(d["titre"])}</h2>' if d['titre'] else '')
                      + sous_titres
                      + (f'<ul>{lignes}</ul>' if lignes else '')
                      + f'<span class="numero">{i} / {len(diapos)}</span></section>')
    return '<div class="diapos">' + ''.join(cartes) + '</div>'


def _page(corps, css_doc='', css_plus='', classe='page'):
    return ('<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">'
            f'<meta http-equiv="Content-Security-Policy" content="{CSP}">'
            '<meta name="viewport" content="width=device-width">'
            f'<style>{css_doc}</style><style>{CSS_APERCU}{css_plus}</style></head>'
            f'<body><article class="{classe}">{corps}</article></body></html>')


def convertir_document(entree):
    fmt = lecteurs.format_de(entree)
    if fmt is None or fmt[0] == 'tableur':
        ext = extension(entree)
        raise Erreur(E_FORMAT, f"Format non pris en charge pour l'aperçu : « {ext or 'sans extension'} ».")
    famille, lecteur = fmt
    verifier_fichier(entree, TAILLE_MAX_DOCUMENT, lecteur in lecteurs.FORMATS_ZIP)
    try:
        if famille == 'presentation':
            diapos = lecteurs.LECTEURS_PRESENTATION[lecteur](entree)
            return _page(html_depuis_diapos(diapos), css_plus=CSS_DIAPOS, classe='presentation')
        corps, css_plus = None, ''
        if lecteur == 'md':
            css_plus = CSS_MARKDOWN
            if os.path.getsize(entree) > TAILLE_MAX_MARKDOWN:
                raise Erreur(E_TROP_GROS, "Fichier Markdown trop gros pour l'aperçu.")
            try:
                corps, css_doc = html_depuis_md(entree)
            except ImportError:
                corps = None                       # python-markdown absent : lecture simple
        if lecteur in ('docx', 'odt'):
            # Rendu riche (mammoth / odfpy) ; s'il échoue sur un fichier un peu
            # abîmé, on se rabat sur notre lecture simple du texte.
            try:
                corps, css_doc = (html_depuis_docx if lecteur == 'docx' else html_depuis_odt)(entree)
            except Exception:
                corps = None
        if corps is None:
            corps, css_doc = html_depuis_blocs(lecteurs.LECTEURS_DOCUMENT[lecteur](entree)), ''
    except Erreur:
        raise
    except Exception as e:
        raise Erreur(E_ECHEC, f"Lecture du document impossible ({type(e).__name__} : {e}).")
    return _page(corps, css_doc, css_plus)


# --- Tableurs → JSON ---------------------------------------------------------
# Chaque cellule est une chaîne (texte) ou {"n": "…"} (nombre, date, booléen :
# aligné à droite par le plugin). Les lignes sont des listes de cellules.

def _nombre_fr(valeur, decimales=None, separateur_milliers=False):
    if decimales is None:
        if float(valeur).is_integer() and abs(valeur) < 1e15:
            texte = str(int(valeur))
        else:
            texte = f"{valeur:.10g}"
    else:
        texte = f"{valeur:.{decimales}f}"
    if separateur_milliers and 'e' not in texte:
        entier, _, frac = texte.partition('.')
        signe = '-' if entier.startswith('-') else ''
        entier = entier.lstrip('-')
        groupes = []
        while len(entier) > 3:
            groupes.insert(0, entier[-3:])
            entier = entier[:-3]
        groupes.insert(0, entier)
        texte = signe + ' '.join(groupes) + ('.' + frac if frac else '')
    return texte.replace('.', ',')


def _formater_xlsx(valeur, fmt):
    if valeur is None:
        return ''
    if isinstance(valeur, str):
        return valeur
    if isinstance(valeur, bool):
        return {'n': 'VRAI' if valeur else 'FAUX'}
    if isinstance(valeur, datetime.datetime):
        if valeur.time() == datetime.time(0) and 'h' not in (fmt or '').lower():
            return {'n': valeur.strftime('%d/%m/%Y')}
        return {'n': valeur.strftime('%d/%m/%Y %H:%M')}
    if isinstance(valeur, datetime.date):
        return {'n': valeur.strftime('%d/%m/%Y')}
    if isinstance(valeur, datetime.time):
        return {'n': valeur.strftime('%H:%M')}
    if isinstance(valeur, datetime.timedelta):
        return {'n': str(valeur)}
    if isinstance(valeur, (int, float)):
        fmt = fmt or 'General'
        section = fmt.split(';')[0]
        m = re.search(r'0\.(0+)', section)
        if m:
            decimales = len(m.group(1))
        elif '0' in section:
            decimales = 0          # « 0 », « #,##0 », « 0% »…
        else:
            decimales = None       # « General » : nombre tel quel
        milliers = '#,##' in section or '# ##' in section
        if '%' in section:
            d = decimales if decimales is not None else 0
            return {'n': _nombre_fr(valeur * 100, d) + ' %'}
        texte = _nombre_fr(valeur, decimales, milliers)
        if '€' in section:
            texte += ' €'
        return {'n': texte}
    return str(valeur)


def _cellules_formules_sans_valeur(archive, chemin_feuille):
    """Compte les cellules <c> ayant une formule <f> mais pas de valeur <v>
    (fichier généré par un programme et jamais recalculé par un tableur)."""
    import xml.etree.ElementTree as ET
    ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    n = 0
    try:
        with archive.open(chemin_feuille) as f:
            for _, el in ET.iterparse(f, events=('end',)):
                if el.tag == ns + 'c':
                    if el.find(ns + 'f') is not None:
                        v = el.find(ns + 'v')
                        if v is None or (v.text or '') == '':
                            n += 1
                    el.clear()
                elif el.tag == ns + 'row':
                    el.clear()
    except Exception:
        return 0
    return n


def lire_xlsx(chemin):
    import openpyxl
    # data_only=True : valeurs calculées enregistrées dans le fichier, pas les formules.
    classeur = openpyxl.load_workbook(chemin, read_only=True, data_only=True)
    archive = zipfile.ZipFile(chemin)
    feuilles = []
    try:
        for i, ws in enumerate(classeur.worksheets):
            if i >= MAX_FEUILLES:
                break
            lignes = []
            tronquee = False
            for r, ligne in enumerate(ws.iter_rows(max_col=MAX_COLONNES + 1)):
                if r >= MAX_LIGNES:
                    tronquee = True
                    break
                cellules = []
                for c, cell in enumerate(ligne):
                    if c >= MAX_COLONNES:
                        if getattr(cell, 'value', None) not in (None, ''):
                            tronquee = True
                        break
                    cellules.append(_formater_xlsx(getattr(cell, 'value', None),
                                                   getattr(cell, 'number_format', None)))
                lignes.append(cellules)
            sans_valeur = 0
            chemin_xml = getattr(ws, '_worksheet_path', None) or getattr(ws, 'path', None)
            if chemin_xml and COMPTER_FORMULES_SANS_VALEUR:
                sans_valeur = _cellules_formules_sans_valeur(archive, chemin_xml.lstrip('/'))
            feuilles.append(_nettoyer({'nom': ws.title, 'lignes': lignes,
                                       'tronquee': tronquee,
                                       'formules_sans_valeur': sans_valeur}))
        return {'feuilles': feuilles,
                'feuilles_omises': max(0, len(classeur.worksheets) - MAX_FEUILLES)}
    finally:
        classeur.close()


def lire_ods(chemin, a_plat=False):
    """Lecture en flux de content.xml (pas de DOM complet en mémoire).
    Le texte affiché de chaque cellule (text:p) est déjà formaté par le tableur
    et contient la valeur calculée des formules."""
    import xml.etree.ElementTree as ET
    TABLE = '{urn:oasis:names:tc:opendocument:xmlns:table:1.0}'
    TEXT = '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'
    OFFICE = '{urn:oasis:names:tc:opendocument:xmlns:office:1.0}'
    NUMERIQUES = {'float', 'percentage', 'currency', 'date', 'time', 'boolean'}

    def texte_de(el):
        morceaux = []
        def parcourir(e):
            if e.tag == TEXT + 's':
                morceaux.append(' ' * int(e.get(TEXT + 'c', '1')))
            elif e.tag == TEXT + 'tab':
                morceaux.append('\t')
            elif e.tag == TEXT + 'line-break':
                morceaux.append('\n')
            elif e.text:
                morceaux.append(e.text)
            for enfant in e:
                parcourir(enfant)
                if enfant.tail:
                    morceaux.append(enfant.tail)
        paragraphes = []
        for p in el.iter(TEXT + 'p'):
            morceaux = []
            parcourir(p)
            paragraphes.append(''.join(morceaux))
        return '\n'.join(paragraphes)

    feuilles = []
    feuilles_omises = 0
    feuille = None
    profondeur_table = 0

    flux = open(chemin, 'rb') if a_plat else zipfile.ZipFile(chemin).open('content.xml')
    with flux as f:
        for evenement, el in lecteurs.iterparse(f, events=('start', 'end')):
            if evenement == 'start':
                if el.tag == TABLE + 'table':
                    profondeur_table += 1
                    if profondeur_table == 1:
                        if len(feuilles) >= MAX_FEUILLES:
                            feuilles_omises += 1
                            feuille = None
                        else:
                            feuille = {'nom': el.get(TABLE + 'name', f'Feuille {len(feuilles) + 1}'),
                                       'lignes': [], 'tronquee': False,
                                       'formules_sans_valeur': 0, '_vides': 0}
                continue

            # --- événements « end » ---
            if el.tag == TABLE + 'table':
                profondeur_table -= 1
                if profondeur_table == 0:
                    if feuille is not None:
                        feuille.pop('_vides')
                        feuilles.append(_nettoyer(feuille))
                    feuille = None
                    el.clear()
            elif el.tag == TABLE + 'table-row' and profondeur_table == 1 and feuille is not None:
                cellules = []
                cellules_vides_en_attente = 0
                for cell in el:
                    if cell.tag not in (TABLE + 'table-cell', TABLE + 'covered-table-cell'):
                        continue
                    rep = min(int(cell.get(TABLE + 'number-columns-repeated', '1')), MAX_REPETITIONS)
                    texte = texte_de(cell)
                    type_valeur = cell.get(OFFICE + 'value-type')
                    if texte == '' and type_valeur is None:
                        cellules_vides_en_attente += rep
                        continue
                    if cellules_vides_en_attente:
                        cellules.extend([''] * cellules_vides_en_attente)
                        cellules_vides_en_attente = 0
                    valeur = {'n': texte} if type_valeur in NUMERIQUES else texte
                    cellules.extend([valeur] * rep)
                if len(cellules) > MAX_COLONNES:
                    cellules = cellules[:MAX_COLONNES]
                    feuille['tronquee'] = True
                rep_lignes = min(int(el.get(TABLE + 'number-rows-repeated', '1')), MAX_REPETITIONS)
                if not cellules:
                    feuille['_vides'] += rep_lignes     # matérialisées seulement si du contenu suit
                else:
                    a_ajouter = [[]] * feuille['_vides'] + [cellules] * rep_lignes
                    feuille['_vides'] = 0
                    place = MAX_LIGNES - len(feuille['lignes'])
                    if len(a_ajouter) > place:
                        feuille['tronquee'] = True
                    feuille['lignes'].extend(a_ajouter[:max(0, place)])
                el.clear()

    return {'feuilles': feuilles, 'feuilles_omises': feuilles_omises}


def _nettoyer(feuille):
    """Retire les lignes et colonnes vides en fin de feuille."""
    lignes = [list(l) for l in feuille['lignes']]
    while lignes and not any(c not in ('', None) for c in lignes[-1]):
        lignes.pop()
    largeur = 0
    for l in lignes:
        while l and l[-1] in ('', None):
            l.pop()
        largeur = max(largeur, len(l))
    feuille['lignes'] = lignes
    feuille['colonnes'] = largeur
    return feuille


def lire_tableur(entree):
    fmt = lecteurs.format_de(entree)
    if fmt is None or fmt[0] != 'tableur':
        ext = extension(entree)
        raise Erreur(E_FORMAT, f"Format non pris en charge pour l'aperçu : « {ext or 'sans extension'} ».")
    lecteur = fmt[1]
    verifier_fichier(entree, TAILLE_MAX_TABLEUR, lecteur in lecteurs.FORMATS_ZIP)
    try:
        if lecteur == 'xlsx':
            return lire_xlsx(entree)
        return lire_ods(entree, a_plat=(lecteur == 'fods'))
    except Erreur:
        raise
    except Exception as e:
        raise Erreur(E_ECHEC, f"Lecture du tableur impossible ({type(e).__name__} : {e}).")


# --- Point d'entrée ----------------------------------------------------------

def main(argv):
    signal.signal(signal.SIGALRM, _delai_depasse)
    signal.alarm(DELAI_MAX_S)
    try:
        if len(argv) == 3 and argv[1] == 'document':
            sys.stdout.write(convertir_document(argv[2]))
        elif len(argv) == 3 and argv[1] == 'tableur':
            json.dump(lire_tableur(argv[2]), sys.stdout, ensure_ascii=False, separators=(',', ':'))
        else:
            print("Usage : convertir.py document <fichier>\n"
                  "        convertir.py tableur <fichier>", file=sys.stderr)
            return E_USAGE
    except Erreur as e:
        print(str(e), file=sys.stderr)
        return e.code
    except MemoryError:
        print("Mémoire insuffisante pour l'aperçu de ce fichier.", file=sys.stderr)
        return E_TROP_GROS
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
