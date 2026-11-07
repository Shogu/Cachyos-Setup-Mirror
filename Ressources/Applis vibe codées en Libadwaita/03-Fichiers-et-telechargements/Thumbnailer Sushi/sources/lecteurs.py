# SPDX-License-Identifier: GPL-2.0-or-later
"""Lecteurs de texte des documents et présentations bureautiques.

Partagé par convertir.py (aperçu Sushi) et vignette.py (miniatures).
Tout est lu en flux et borné : pas de DOM complet, nombre de blocs limité.

Un document devient une liste de blocs :
    ('titre' | 'h1' | 'h2' | 'h3' | 'p' | 'puce', texte)
    ('ligne', [cellule, …])            ligne de tableau
    ('image', (type_mime, octets))     première image seulement
Une présentation devient une liste de diapositives :
    {'titre': texte, 'lignes': [(niveau, texte), …]}
"""

import os
import re
import zipfile

try:
    import ole
except Exception:                 # module absent ou illisible (droits) : seuls
    ole = None                    # les .doc perdent leur aperçu, pas le reste

MAX_BLOCS = 400
MAX_DIAPOS = 60
MAX_LIGNES_DIAPO = 40
TAILLE_MAX_IMAGE = 4 * 1024**2

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
P = '{http://schemas.openxmlformats.org/presentationml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
REL = '{http://schemas.openxmlformats.org/package/2006/relationships}'
TEXT = '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'
TABLE = '{urn:oasis:names:tc:opendocument:xmlns:table:1.0}'
DRAW = '{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}'
XLINK = '{http://www.w3.org/1999/xlink}'
PRES = '{urn:oasis:names:tc:opendocument:xmlns:presentation:1.0}'
OFFICE = '{urn:oasis:names:tc:opendocument:xmlns:office:1.0}'
STYLE = '{urn:oasis:names:tc:opendocument:xmlns:style:1.0}'
FO = '{urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0}'

TYPES_IMAGE = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}


def iterparse(flux, events=('end',)):
    """iterparse refusant DTD et entités (fichiers XML « à plat » non fiables)."""
    try:
        from defusedxml.ElementTree import iterparse as sur
        return sur(flux, events=events, forbid_dtd=True)
    except ImportError:
        import xml.etree.ElementTree as ET
        return ET.iterparse(flux, events=events)


# --- Formats -----------------------------------------------------------------

FORMATS = {
    # extension : (famille, lecteur)
    '.docx': ('document', 'docx'), '.docm': ('document', 'docx'),
    '.dotx': ('document', 'docx'), '.dotm': ('document', 'docx'),
    '.odt': ('document', 'odt'), '.ott': ('document', 'odt'),
    '.fodt': ('document', 'fodt'),
    '.rtf': ('document', 'rtf'),
    '.doc': ('document', 'doc'),           # Word 97-2003 (conteneur OLE2)
    '.md': ('document', 'md'), '.markdown': ('document', 'md'), '.mkd': ('document', 'md'),
    '.xlsx': ('tableur', 'xlsx'), '.xlsm': ('tableur', 'xlsx'),
    '.xltx': ('tableur', 'xlsx'), '.xltm': ('tableur', 'xlsx'),
    '.ods': ('tableur', 'ods'), '.ots': ('tableur', 'ods'),
    '.fods': ('tableur', 'fods'),
    '.pptx': ('presentation', 'pptx'), '.pptm': ('presentation', 'pptx'),
    '.potx': ('presentation', 'pptx'), '.ppsx': ('presentation', 'pptx'),
    '.odp': ('presentation', 'odp'), '.otp': ('presentation', 'odp'),
    '.fodp': ('presentation', 'fodp'),
}

FORMATS_EXT_CONNUES = {ext.lstrip('.') for ext in FORMATS}
FORMATS_ZIP = {'docx', 'odt', 'xlsx', 'ods', 'pptx', 'odp'}


def format_de(chemin):
    """(famille, lecteur) d'après l'extension, ou d'après le contenu si elle
    est absente ou inconnue. None si le format n'est pas reconnu."""
    ext = os.path.splitext(chemin)[1].lower()
    if ext in FORMATS:
        return FORMATS[ext]
    try:
        with open(chemin, 'rb') as f:
            debut = f.read(8)
        if debut.startswith(b'{\\rtf'):
            return FORMATS['.rtf']
        if ole is not None and debut == ole.MAGIC:
            # Conteneur OLE2 : Word (.doc) plutôt qu'Excel (.xls) ou
            # PowerPoint (.ppt), reconnaissables à leurs flux.
            with open(chemin, 'rb') as f:
                noms = {e['nom'] for e in ole.Conteneur(f.read()).entrees}
            if 'WordDocument' in noms:
                return FORMATS['.doc']
        if debut.startswith(b'PK'):
            with zipfile.ZipFile(chemin) as z:
                noms = set(z.namelist())
                if 'word/document.xml' in noms:
                    return FORMATS['.docx']
                if 'xl/workbook.xml' in noms:
                    return FORMATS['.xlsx']
                if 'ppt/presentation.xml' in noms:
                    return FORMATS['.pptx']
                if 'mimetype' in noms:
                    mt = z.read('mimetype').decode('ascii', 'replace')
                    for cle, ext2 in (('text', '.odt'), ('spreadsheet', '.ods'),
                                      ('presentation', '.odp')):
                        if f'opendocument.{cle}' in mt:
                            return FORMATS[ext2]
    except (OSError, ValueError, zipfile.BadZipFile):
        pass
    return None


# --- Images ------------------------------------------------------------------

def _image(archive, nom):
    type_mime = TYPES_IMAGE.get(os.path.splitext(nom)[1].lower())
    if not type_mime:
        return None
    try:
        info = archive.getinfo(nom)
        if info.file_size > TAILLE_MAX_IMAGE:
            return None
        return (type_mime, archive.read(nom))
    except KeyError:
        return None


# --- DOCX ----------------------------------------------------------------------

def _titre_par_mise_en_forme(p, texte, premier):
    """Titre tapé « à la main » : paragraphe court entièrement en gras, ou
    écrit en grand. Renvoie 'titre', 'h1', 'h2' ou None."""
    if len(texte) > 140:
        return None
    runs = [r for r in p.iter(W + 'r') if ''.join(t.text or '' for t in r.iter(W + 't')).strip()]
    if not runs:
        return None
    def gras(r):
        b = r.find(f'{W}rPr/{W}b')
        return b is not None and b.get(W + 'val', 'true') not in ('0', 'false')
    tailles = []
    for r in runs:
        sz = r.find(f'{W}rPr/{W}sz')
        if sz is not None and (sz.get(W + 'val') or '').isdigit():
            tailles.append(int(sz.get(W + 'val')) / 2)    # demi-points → points
    taille = min(tailles) if len(tailles) == len(runs) else 0
    tout_gras = all(gras(r) for r in runs)
    if taille >= 15 or (premier and tout_gras and taille >= 13):
        return 'titre' if premier else 'h1'
    if taille >= 13 or tout_gras:
        return 'titre' if premier and taille >= 13 else 'h2'
    return None


def blocs_docx(chemin, avec_image=True):
    archive = zipfile.ZipFile(chemin)
    cibles = {}
    if avec_image:
        try:
            with archive.open('word/_rels/document.xml.rels') as f:
                for _, el in iterparse(f):
                    if el.tag == REL + 'Relationship':
                        cibles[el.get('Id')] = 'word/' + el.get('Target', '').lstrip('/').removeprefix('word/')
        except KeyError:
            pass
    blocs, profondeur_tableau, image_vue = [], 0, not avec_image
    with archive.open('word/document.xml') as f:
        for evenement, el in iterparse(f, events=('start', 'end')):
            if el.tag == W + 'tbl':
                profondeur_tableau += 1 if evenement == 'start' else -1
                continue
            if evenement != 'end':
                continue
            if el.tag == A + 'blip' and not image_vue:
                image = _image(archive, cibles.get(el.get(R + 'embed'), ''))
                if image:
                    blocs.append(('image', image))
                    image_vue = True
            elif el.tag == W + 'p' and profondeur_tableau == 0:
                texte = ''.join((t.text or '') if t.tag == W + 't' else ' '
                                for t in el.iter() if t.tag in (W + 't', W + 'tab')).strip()
                if texte:
                    style = el.find(f'{W}pPr/{W}pStyle')
                    bas = ((style.get(W + 'val') if style is not None else '') or '').lower()
                    est_liste = el.find(f'{W}pPr/{W}numPr') is not None or bas.startswith(('list', 'liste'))
                    if bas in ('title', 'titre'):
                        genre = 'titre'
                    elif bas.startswith(('heading', 'titre')) and bas[-1:].isdigit():
                        genre = 'h' + str(min(3, int(bas[-1])))
                    elif est_liste:
                        genre = 'puce'
                    else:
                        genre = _titre_par_mise_en_forme(el, texte, not blocs) or 'p'
                    blocs.append((genre, texte))
                el.clear()
            elif el.tag == W + 'tr' and profondeur_tableau == 1:
                cellules = [''.join(t.text or '' for t in tc.iter(W + 't')).strip()
                            for tc in el.findall(W + 'tc')]
                if any(cellules):
                    blocs.append(('ligne', cellules))
                el.clear()
            if len(blocs) >= MAX_BLOCS:
                break
    return blocs


# --- ODT / OTT / FODT --------------------------------------------------------

def texte_odf(el):
    morceaux = []

    def parcourir(e):
        if e.tag == TEXT + 's':
            morceaux.append(' ' * int(e.get(TEXT + 'c', '1')))
        elif e.tag in (TEXT + 'tab', TEXT + 'line-break'):
            morceaux.append(' ')
        elif e.tag in (TEXT + 'note', OFFICE + 'annotation'):
            return
        elif e.text:
            morceaux.append(e.text)
        for enfant in e:
            parcourir(enfant)
            if enfant.tail:
                morceaux.append(enfant.tail)
    parcourir(el)
    return re.sub(r'\s+', ' ', ''.join(morceaux)).strip()


def _titre_odf(p, texte, styles, premier):
    """Titre ODF tapé « à la main » (gras ou grande taille), comme pour le DOCX."""
    if len(texte) > 140:
        return None
    gras, taille = styles.get(p.get(TEXT + 'style-name'), (False, 0))
    spans = [sp for sp in p.iter(TEXT + 'span') if texte_odf(sp)]
    if spans and not gras:
        props = [styles.get(sp.get(TEXT + 'style-name'), (False, 0)) for sp in spans]
        couvert = sum(len(texte_odf(sp)) for sp in spans) >= len(texte) - 2
        if couvert and all(g for g, _ in props):
            gras = True
        if couvert and props:
            taille = max(taille, min(t for _, t in props))
    if taille >= 15 or (premier and gras and taille >= 13):
        return 'titre' if premier else 'h1'
    if taille >= 13 or gras:
        return 'titre' if premier and taille >= 13 else 'h2'
    return None


def blocs_odf(flux, archive=None):
    """flux : content.xml (ODT/OTT) ou le fichier .fodt lui-même."""
    blocs, profondeur_tableau, profondeur_liste, image_vue = [], 0, 0, archive is None
    styles = {}      # styles automatiques : nom → (gras, taille en points)
    for evenement, el in iterparse(flux, events=('start', 'end')):
        if el.tag == STYLE + 'style' and evenement == 'end':
            props = el.find(STYLE + 'text-properties')
            if props is not None:
                taille = props.get(FO + 'font-size', '')
                styles[el.get(STYLE + 'name')] = (
                    props.get(FO + 'font-weight') == 'bold',
                    float(taille[:-2]) if taille.endswith('pt') and taille[:-2].replace('.', '', 1).isdigit() else 0)
            continue
        if el.tag == TABLE + 'table':
            profondeur_tableau += 1 if evenement == 'start' else -1
            continue
        if el.tag == TEXT + 'list-item':
            profondeur_liste += 1 if evenement == 'start' else -1
            continue
        if evenement != 'end':
            continue
        if el.tag == DRAW + 'image' and not image_vue:
            href = (el.get(XLINK + 'href') or '').removeprefix('./')
            image = _image(archive, href) if href else None
            if image:
                blocs.append(('image', image))
                image_vue = True
        elif el.tag in (TEXT + 'h', TEXT + 'p') and profondeur_tableau == 0:
            texte = texte_odf(el)
            if texte:
                if el.tag == TEXT + 'h':
                    genre = 'h' + str(min(3, int(el.get(TEXT + 'outline-level', '1') or 1)))
                elif el.get(TEXT + 'style-name', '') in ('Title', 'Titre'):
                    genre = 'titre'
                elif profondeur_liste:
                    genre = 'puce'
                else:
                    genre = _titre_odf(el, texte, styles, not blocs) or 'p'
                blocs.append((genre, texte))
            el.clear()
        elif el.tag == TABLE + 'table-row' and profondeur_tableau == 1:
            cellules = [texte_odf(c) for c in el
                        if c.tag in (TABLE + 'table-cell', TABLE + 'covered-table-cell')]
            if any(cellules):
                blocs.append(('ligne', cellules))
            el.clear()
        if len(blocs) >= MAX_BLOCS:
            break
    return blocs


def blocs_odt(chemin, avec_image=True):
    archive = zipfile.ZipFile(chemin)
    with archive.open('content.xml') as f:
        return blocs_odf(f, archive if avec_image else None)


def blocs_fodt(chemin, avec_image=True):
    with open(chemin, 'rb') as f:
        return blocs_odf(f, None)


# --- RTF -----------------------------------------------------------------------

_JETONS_RTF = re.compile(
    rb"\\([a-zA-Z]{1,32})(-?\d{1,10})? ?|\\'([0-9a-fA-F]{2})|\\(.)|([{}])|([^\\{}\r\n]+)|[\r\n]+",
    re.S)
_DESTINATIONS_IGNOREES = {
    b'fonttbl', b'colortbl', b'stylesheet', b'info', b'object', b'header', b'footer',
    b'headerl', b'headerr', b'headerf', b'footerl', b'footerr', b'footerf', b'footnote',
    b'fldinst', b'themedata', b'colorschememapping', b'latentstyles', b'datastore',
    b'xmlnstbl', b'listtable', b'listoverridetable', b'rsidtbl', b'generator',
    b'mmathPr', b'bkmkstart', b'bkmkend', b'pgdsctbl', b'filetbl', b'revtbl',
    b'nonshppict', b'annotation', b'atnid', b'atnauthor', b'comment',
}


def blocs_rtf(chemin, avec_image=True):
    with open(chemin, 'rb') as f:
        donnees = f.read()
    if not donnees.startswith(b'{\\rtf'):
        raise ValueError("ce fichier n'est pas un RTF")

    blocs = []
    pile = []
    etat = {'ignorer': False, 'uc': 1, 'pict': False, 'puce': False}
    codage = 'cp1252'
    para = {'texte': [], 'taille': 24, 'gras': False, 'niveau': None, 'puce': False}
    a_sauter = 0                     # caractères de repli après \uN
    image = {'hex': [], 'type': None}
    image_vue = not avec_image
    cellules = []

    def ajouter(t):
        nonlocal a_sauter
        if a_sauter:
            n = min(a_sauter, len(t))
            t, a_sauter = t[n:], a_sauter - n
        if t and not etat['ignorer'] and not etat['pict']:
            para['texte'].append(t)

    def fin_paragraphe(type_fin='par'):
        texte = re.sub(r'\s+', ' ', ''.join(para['texte'])).strip()
        para['texte'] = []
        if type_fin == 'cell':
            cellules.append(texte)
            return
        if type_fin == 'row':
            if any(cellules):
                blocs.append(('ligne', list(cellules)))
            cellules.clear()
            return
        if not texte:
            return
        if para['niveau'] is not None:
            genre = 'h' + str(min(3, para['niveau'] + 1))
        elif para['puce']:
            genre = 'puce'
        elif para['taille'] >= 36 and len(texte) < 120:
            genre = 'titre'
        elif para['taille'] >= 30 and len(texte) < 120:
            genre = 'h1'
        elif para['gras'] and len(texte) < 100:
            genre = 'h3'
        else:
            genre = 'p'
        blocs.append((genre, texte))

    premiere_dest = False
    for m in _JETONS_RTF.finditer(donnees):
        if len(blocs) >= MAX_BLOCS:
            break
        mot, param, hexa, symbole, accolade, texte = m.groups()
        if accolade == b'{':
            pile.append(dict(etat))
            premiere_dest = True
            continue
        if accolade == b'}':
            if etat['pict'] and not image_vue and image['type'] and image['hex']:
                try:
                    blocs.append(('image', (image['type'], bytes.fromhex(''.join(image['hex'])))))
                    image_vue = True
                except ValueError:
                    pass
            image['hex'], image['type'] = [], None
            if pile:
                etat = pile.pop()
            premiere_dest = False
            continue
        debut_groupe, premiere_dest = premiere_dest, False
        if mot is not None:
            if etat['ignorer'] and mot not in (b'pict',):
                continue                     # contenu d'un groupe ignoré
            if mot in _DESTINATIONS_IGNOREES or (mot in (b'pntext', b'listtext')):
                if mot in (b'pntext', b'listtext'):
                    para['puce'] = True
                etat['ignorer'] = True
            elif mot == b'pict':
                etat['pict'] = True
            elif etat['pict']:
                if mot == b'pngblip':
                    image['type'] = 'image/png'
                elif mot == b'jpegblip':
                    image['type'] = 'image/jpeg'
            elif mot == b'ansicpg' and param:
                codage = 'cp' + param.decode()
            elif mot in (b'par', b'sect'):
                fin_paragraphe()
            elif mot == b'line':
                ajouter(' ')
            elif mot == b'tab':
                ajouter(' ')
            elif mot == b'cell':
                fin_paragraphe('cell')
            elif mot == b'row':
                fin_paragraphe('row')
            elif mot == b'pard':
                para.update(taille=24, gras=False, niveau=None, puce=False)
            elif mot == b'fs' and param:
                para['taille'] = max(para['taille'], int(param)) if para['texte'] else int(param)
            elif mot == b'b':
                if not para['texte']:
                    para['gras'] = param != b'0'
            elif mot == b'outlinelevel' and param:
                para['niveau'] = int(param)
            elif mot == b'uc' and param:
                etat['uc'] = int(param)
            elif mot == b'u' and param:
                n = int(param)
                ajouter(chr(n + 65536 if n < 0 else n))
                a_sauter = etat['uc']
            elif mot in (b'emdash',):
                ajouter('—')
            elif mot in (b'endash',):
                ajouter('–')
            elif mot in (b'lquote', b'rquote'):
                ajouter('’')
            elif mot in (b'ldblquote', b'rdblquote'):
                ajouter('"')
            elif mot == b'bullet':
                ajouter('•')
        elif symbole is not None:
            if symbole == b'*' and debut_groupe is False:
                etat['ignorer'] = True
            elif symbole == b'*':
                etat['ignorer'] = True
            elif symbole in (b'\\', b'{', b'}'):
                ajouter(symbole.decode())
            elif symbole == b'~':
                ajouter('\u00a0')
            elif symbole == b'\n' or symbole == b'\r':
                fin_paragraphe()
        elif hexa is not None:
            if etat['pict']:
                continue
            ajouter(bytes.fromhex(hexa.decode()).decode(codage, 'replace'))
        elif texte is not None:
            if etat['pict']:
                if not image_vue and len(image['hex']) < TAILLE_MAX_IMAGE // 512:
                    image['hex'].append(texte.decode('ascii', 'ignore'))
                continue
            ajouter(texte.decode(codage, 'replace'))
    fin_paragraphe()
    return blocs


# --- PPTX ----------------------------------------------------------------------

def diapos_pptx(chemin):
    archive = zipfile.ZipFile(chemin)
    cibles = {}
    with archive.open('ppt/_rels/presentation.xml.rels') as f:
        for _, el in iterparse(f):
            if el.tag == REL + 'Relationship':
                cible = el.get('Target', '')
                cibles[el.get('Id')] = cible.lstrip('/') if cible.startswith('/') else 'ppt/' + cible
    ordre = []
    with archive.open('ppt/presentation.xml') as f:
        for _, el in iterparse(f):
            if el.tag == P + 'sldId':
                ordre.append(cibles.get(el.get(R + 'id')))
    diapos = []
    for nom in ordre[:MAX_DIAPOS]:
        if not nom:
            continue
        titre, lignes = '', []
        try:
            with archive.open(nom) as f:
                for _, el in iterparse(f):
                    if el.tag != P + 'sp':
                        continue
                    ph = el.find(f'{P}nvSpPr/{P}nvPr/{P}ph')
                    genre = ph.get('type', 'body') if ph is not None else 'autre'
                    paragraphes = []
                    for p in el.iter(A + 'p'):
                        t = ''.join(x.text or '' for x in p.iter(A + 't')).strip()
                        if t:
                            ppr = p.find(A + 'pPr')
                            niveau = int(ppr.get('lvl', '0')) if ppr is not None else 0
                            paragraphes.append((niveau, t))
                    if genre in ('title', 'ctrTitle') and not titre:
                        titre = ' '.join(t for _, t in paragraphes)
                    elif genre == 'subTitle':
                        lignes.extend((-1, t) for _, t in paragraphes)   # -1 : sous-titre
                    else:
                        lignes.extend(paragraphes)
                    el.clear()
        except KeyError:
            continue
        if not titre and lignes:
            titre = lignes.pop(0)[1]
        diapos.append({'titre': titre, 'lignes': lignes[:MAX_LIGNES_DIAPO]})
    return diapos


# --- ODP / OTP / FODP ----------------------------------------------------------

def diapos_odf(flux):
    diapos, diapo = [], None
    profondeur_liste = 0
    for evenement, el in iterparse(flux, events=('start', 'end')):
        if el.tag == DRAW + 'page':
            if evenement == 'start':
                diapo = {'titre': '', 'lignes': []}
            else:
                if diapo is not None:
                    if not diapo['titre'] and diapo['lignes']:
                        diapo['titre'] = diapo['lignes'].pop(0)[1]
                    diapos.append(diapo)
                diapo = None
                el.clear()
                if len(diapos) >= MAX_DIAPOS:
                    break
            continue
        if el.tag == TEXT + 'list':
            profondeur_liste += 1 if evenement == 'start' else -1
            continue
        if evenement != 'end' or diapo is None:
            continue
        if el.tag == DRAW + 'frame':
            classe = el.get(PRES + 'class', '')
            if classe in ('notes', 'page-number', 'date-time', 'footer', 'header'):
                continue
            if el.find(f'.//{PRES}notes') is not None:
                continue
            textes = []

            def parcourir(e, profondeur):
                for enfant in e:
                    if enfant.tag in (TEXT + 'p', TEXT + 'h'):
                        t = texte_odf(enfant)
                        if t:
                            textes.append((max(0, profondeur - 1), t))
                    else:
                        parcourir(enfant, profondeur + (enfant.tag == TEXT + 'list'))
            parcourir(el, 0)
            if classe == 'title' and not diapo['titre'] and textes:
                diapo['titre'] = ' '.join(t for _, t in textes)
            elif classe == 'subtitle':
                diapo['lignes'].extend((-1, t) for _, t in textes)
            else:
                diapo['lignes'].extend(textes)
            el.clear()
        elif el.tag == PRES + 'notes':
            el.clear()
    for d in diapos:
        d['lignes'] = d['lignes'][:MAX_LIGNES_DIAPO]
    return diapos


def diapos_odp(chemin):
    with zipfile.ZipFile(chemin).open('content.xml') as f:
        return diapos_odf(f)


def diapos_fodp(chemin):
    with open(chemin, 'rb') as f:
        return diapos_odf(f)


def blocs_md(chemin, avec_image=True):
    """Lecture simple du Markdown pour les miniatures (titres, puces, tableaux,
    paragraphes). Les images ne sont pas reprises : seul le .md est accessible
    dans le bac à sable des miniatures."""
    with open(chemin, 'rb') as f:
        texte = f.read(512 * 1024).decode('utf-8', 'replace')
    blocs, paragraphe, dans_code = [], [], False

    def finir():
        if paragraphe:
            blocs.append(('p', ' '.join(paragraphe)))
            paragraphe.clear()

    def nettoyer(t):
        t = re.sub(r'!\[([^\]]*)\]\([^)]*\)', r'\1', t)          # images → texte alternatif
        t = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', t)           # liens → texte
        t = re.sub(r'(\*\*|__|\*|_|`)', '', t)                     # emphase, code
        t = re.sub(r'<script\b.*?</script>|<[^>]+>', '', t, flags=re.S | re.I)   # HTML brut
        return t.strip()

    for ligne in texte.splitlines():
        brute = ligne.rstrip()
        if brute.lstrip().startswith(('```', '~~~')):
            finir()
            dans_code = not dans_code
            continue
        if dans_code:
            if brute.strip():
                blocs.append(('code', brute))
            continue
        m = re.match(r'^(#{1,6})\s+(.*?)\s*#*$', brute)
        if m:
            finir()
            niveau = len(m.group(1))
            genre = 'titre' if niveau == 1 and not any(g == 'titre' for g, _ in blocs) else 'h' + str(min(3, niveau))
            blocs.append((genre, nettoyer(m.group(2))))
        elif re.match(r'^\s*([-*+]|\d+[.)])\s+', brute):
            finir()
            blocs.append(('puce', nettoyer(re.sub(r'^\s*([-*+]|\d+[.)])\s+(\[[ xX]\]\s+)?', '', brute))))
        elif brute.lstrip().startswith('|'):
            finir()
            cellules = [nettoyer(c) for c in brute.strip().strip('|').split('|')]
            if not all(re.fullmatch(r':?-{2,}:?', c.replace(' ', '')) for c in cellules if c):
                blocs.append(('ligne', cellules))
        elif re.match(r'^\s*(---+|\*\*\*+|___+)\s*$', brute) or not brute.strip():
            finir()
        else:
            paragraphe.append(nettoyer(brute.lstrip('> ')))
        if len(blocs) >= MAX_BLOCS:
            break
    finir()
    return blocs


_PUCE_DOC = re.compile(r'^[-*\u2022\u00b7\u25cf\u25aa\u2013\u2014]\s+')
_CARACTERES_GARDES = '\n\t'


def _blocs_texte_doc(texte):
    """Texte d'un .doc → blocs. Le format ne donne pas la mise en forme
    (elle passe par des feuilles de style séparées) : on se contente de
    repérer les puces et une première ligne courte comme titre."""
    # Contrôles propres au format : \\r fin de paragraphe, \\x07 fin de cellule,
    # \\x0b et \\x0c sauts de ligne/page, \\x1e trait d'union conditionnel.
    texte = (texte.replace('\r', '\n').replace('\x07', '\t')
                  .replace('\x0b', '\n').replace('\x0c', '\n')
                  .replace('\x1e', '-').replace('\u00a0', ' '))
    texte = ''.join(c for c in texte if c >= ' ' or c in _CARACTERES_GARDES)
    blocs = []
    for ligne in texte.split('\n'):
        ligne = re.sub(r'[ \t]+', ' ', ligne).strip()
        if not ligne:
            continue
        if blocs and _PUCE_DOC.match(ligne):
            blocs.append(('puce', _PUCE_DOC.sub('', ligne)))
        elif not blocs and len(ligne) < 120:
            blocs.append(('titre', ligne))
        else:
            blocs.append(('p', ligne))
        if len(blocs) >= MAX_BLOCS:
            break
    return blocs


def blocs_doc(chemin, avec_image=True):
    """Word 97-2003 (.doc) : conteneur OLE2 dont on extrait la piece table.

    Beaucoup de fichiers .doc sont en réalité du RTF (ou du simple texte)
    renommés : ces deux cas sont traités au passage."""
    with open(chemin, 'rb') as f:
        donnees = f.read()
    if donnees.startswith(b'{\\rtf'):
        return blocs_rtf(chemin, avec_image)
    if ole is None:
        raise ValueError('lecteur .doc indisponible : module « ole » absent ou illisible')
    if donnees[:8] != ole.MAGIC:
        if b'\x00' in donnees[:8192]:
            raise ValueError("fichier binaire non reconnu : ce n'est pas un .doc Word")
        return _blocs_texte_doc(donnees.decode('utf-8', 'replace'))
    return _blocs_texte_doc(ole.texte_doc(donnees))


LECTEURS_DOCUMENT = {'docx': blocs_docx, 'odt': blocs_odt, 'fodt': blocs_fodt,
                     'rtf': blocs_rtf, 'md': blocs_md, 'doc': blocs_doc}
LECTEURS_PRESENTATION = {'pptx': diapos_pptx, 'odp': diapos_odp, 'fodp': diapos_fodp}
