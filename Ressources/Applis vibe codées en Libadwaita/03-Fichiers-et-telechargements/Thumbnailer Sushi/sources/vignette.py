#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Générateur de miniatures GNOME : documents, PDF, présentations, tableurs,
texte brut et code.

Usage (appelé par Nautilus via sushi-thumbnailer-docs-extra.thumbnailer) :
    vignette.py -s <taille> <entrée> <sortie.png>

Chaque famille a son rendu, choisi par l'utilisateur sur maquettes :
  - document (DOCX, ODT, RTF, MD, DOC) et PDF : fiche — bandeau du format,
    titre (2 lignes au plus), puis 4 intertitres au plus ; sans titres, le
    début du texte en gras puis un paragraphe en gris ;
  - présentation (PPTX, ODP…) : fiche — bandeau orange, titre, titres des
    diapositives numérotés ;
  - tableur (XLSX, ODS…) : grille des premières cellules sous un bandeau vert ;
  - texte brut : bandeau gris, première ligne en titre, puis quelques lignes ;
  - code : fond sombre façon terminal, bandeau du langage.
Les miniatures enregistrées dans les fichiers (LibreOffice) sont ignorées,
pour que toutes les miniatures aient le même style.

Deux formes de page, mesurées sur l'icône Adwaita text-x-generic.svg (page
88 × 112 dans une grille de 128, soit 11:14 ; rayon 8) :
  - **page aux 4 coins arrondis**, quand le paquet partenaire
    nautilus-vignettes-arrondies-sushi est installé : image carrée et
    transparente où la page occupe exactement la place de celle des icônes
    Adwaita. Le paquet partenaire retire le damier et le cadre que Nautilus
    peint sous toute miniature ; sans lui, la transparence ferait apparaître
    ce damier ;
  - **page rectangulaire opaque** sinon : la page 11:14 seule, d'un bord à
    l'autre, sans aucun pixel transparent.

Polices : Adwaita Sans et Adwaita Mono (dépendance adwaita-fonts) ; si elles
manquaient quand même, la police sans empattement du système prend le relais.

Fonctionne dans le bac à sable des miniatures GNOME (bwrap : /usr en lecture
seule, pas de réseau, pas de /etc/fonts). Codes de sortie : 0 succès, 1 échec.
"""

import os
import re
import signal
import sys
import zipfile

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)

# Le bac à sable ne monte pas /etc/fonts : on fournit notre configuration
# fontconfig (sous /usr), à définir AVANT de charger Pango.
_conf = os.path.join(ICI, 'fonts.conf')
if os.path.exists(_conf) and not os.path.exists('/etc/fonts/fonts.conf'):
    os.environ['FONTCONFIG_FILE'] = _conf

import lecteurs  # noqa: E402

DELAI_MAX_S = 8
TAILLE_MAX = 40 * 1024**2
TAILLE_MAX_PDF = 200 * 1024**2        # poppler ne lit que les pages demandées
TAILLE_LUE_TEXTE = 64 * 1024          # début du fichier lu pour le texte et le code
# Adwaita d'abord (dépendance adwaita-fonts) ; si elle manquait quand même,
# fontconfig prend la police sans empattement du système plutôt que de ne rien
# dessiner. (Pas la police du document : souvent absente, ou Calibri, Times…
# chacune différente, et le style des vignettes ne serait plus uniforme.)
POLICE = 'Adwaita Sans, Cantarell, Noto Sans, sans-serif'
POLICE_MONO = 'Adwaita Mono, Source Code Pro, DejaVu Sans Mono, monospace'
ENCRE = (0.14, 0.12, 0.19)        # texte courant
NOIR = (0.03, 0.03, 0.05)          # titres
GRIS = (0.36, 0.35, 0.39)          # texte secondaire
BLANC = (1.0, 1.0, 1.0)
# Fond de la page rectangulaire (sans le paquet partenaire) : #deddda, qui la
# détache du volet clair comme du sombre.
PAGE = (0.87059, 0.86667, 0.85490)

# Présence du paquet partenaire (fichier visible dans le bac à sable : /usr y
# est monté en lecture seule).
MARQUE_ARRONDI = '/usr/share/nautilus-vignettes-arrondies-sushi/nautilus.css'


def coins_arrondis():
    forcer = os.environ.get('VIGNETTE_ARRONDI')       # essais hors session
    if forcer in ('0', '1'):
        return forcer == '1'
    return os.path.exists(MARQUE_ARRONDI)


def _teinte(hexa):
    """(r, g, b) entre 0 et 1, depuis '#rrggbb'."""
    return tuple(int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5))


# Teintes reprises telles quelles de la palette libadwaita
# (src/stylesheet/_palette.scss et _colors.scss de GNOME/libadwaita) : chaque
# bandeau est donc un `accent_bg_color` officiel, prévu pour du texte blanc.
LA = {
    'blue-3': _teinte('#3584e4'),      # aussi --accent-blue
    'blue-4': _teinte('#1c71d8'),
    'blue-5': _teinte('#1a5fb4'),
    'green-5': _teinte('#26a269'),
    'orange-4': _teinte('#e66100'),
    'orange-5': _teinte('#c64600'),
    'red-4': _teinte('#c01c28'),
    'purple-3': _teinte('#9141ac'),    # aussi --accent-purple
    'purple-4': _teinte('#813d9c'),
    'purple-5': _teinte('#613583'),
    'brown-3': _teinte('#986a44'),
    'light-2': _teinte('#f6f5f4'),     # fond de page des icônes Adwaita
    'light-3': _teinte('#deddda'),
    'dark-1': _teinte('#77767b'),
    'dark-2': _teinte('#5e5c64'),
    'dark-3': _teinte('#3d3846'),      # page du code : assez claire pour que
                                       # les coins se voient sur un volet sombre
    'dark-4': _teinte('#241f31'),
    'teal': _teinte('#2190a4'),        # --accent-teal
    'vert': _teinte('#3a944a'),        # --accent-green
    'jaune': _teinte('#c88800'),       # --accent-yellow
    'orange': _teinte('#ed5b00'),      # --accent-orange
    'rouge': _teinte('#e62d42'),       # --accent-red
    'rose': _teinte('#d56199'),        # --accent-pink
    'ardoise': _teinte('#6f8396'),     # --accent-slate
}

COULEURS = {
    # documents
    'docx': LA['blue-4'],          # bleu Word
    'doc': LA['blue-4'],           # bleu Word 97-2003 (ancien .doc)
    'odt': LA['blue-3'],           # bleu Writer
    'fodt': LA['blue-3'],
    'rtf': LA['purple-3'],         # violet
    'md': LA['teal'],              # sarcelle markdown
    # présentations
    'pptx': LA['orange-4'],        # orange PowerPoint
    'odp': LA['orange'],           # orange Impress
    'fodp': LA['orange'],
    # tableurs
    'xlsx': LA['vert'],            # vert Excel
    'ods': LA['green-5'],          # vert Calc
    'fods': LA['green-5'],
    # texte et code
    'texte': LA['ardoise'],        # ardoise (texte brut)
    'code': LA['dark-2'],          # repli pour un langage inconnu
}


def _table_couleurs(groupes):
    table = {}
    for teinte, extensions in groupes:
        for ext in extensions.split():
            table[ext] = teinte
    return table


# Une teinte par famille de langage : les extensions restent reconnaissables et
# le bandeau ne se confond plus avec celui des documents.
COULEURS_CODE = _table_couleurs([
    (LA['vert'], 'sh bash zsh fish'),                          # --accent-green
    (LA['blue-3'], 'py pyw'),                                  # --accent-blue
    (LA['jaune'], 'js mjs cjs ts jsx tsx json jsonc'),         # --accent-yellow
    (LA['ardoise'], 'c h cc cpp cxx hpp hh'),                  # --accent-slate
    (LA['brown-3'], 'rs'),                                     # rouille Rust
    (LA['teal'], 'go sql'),                                    # --accent-teal
    (LA['rouge'], 'java kt kts scala'),                        # --accent-red
    (LA['blue-4'], 'cs'),                                      # bleu C#
    (LA['orange'], 'swift'),                                   # --accent-orange
    (LA['red-4'], 'rb'),                                       # rouge Ruby
    (LA['purple-5'], 'pl pm'),                                 # violet foncé Perl
    (LA['purple-4'], 'lua'),                                   # violet Lua
    (LA['purple-3'], 'php'),                                   # --accent-purple
    (LA['blue-5'], 'css scss sass less'),                      # bleu foncé styles
    (LA['orange-5'], 'html htm'),                              # orange foncé HTML
    (LA['blue-3'], 'xml ui blp vala'),                         # --accent-blue
    (LA['rose'], 'yaml yml'),                                  # --accent-pink
    (LA['dark-2'], 'toml ini conf cfg'),                       # gris config
    (LA['green-5'], 'diff patch'),                             # vert correctif
    (LA['dark-1'], 'vim el nix cmake mk meson install '        # gris outillage
                   'r jl dart hs ml'),
    (LA['dark-1'], 'log out err journal'),                     # journaux : gris
    (LA['green-5'], 'csv tsv'),                                # colonnes : vert Calc
    (LA['teal'], 'tex latex bib'),                             # composition
    (LA['purple-4'], 'po pot'),                                # traduction
    (LA['purple-5'], 'dot gv puml plantuml'),                  # schémas en texte
    (LA['dark-2'], 'desktop service socket timer env '         # configuration
                   'properties reg rc'),
])

# Texte rédigé : couleur du bandeau, par famille
COULEURS_TEXTE = {
    'txt': LA['ardoise'], 'text': LA['ardoise'], 'me': LA['ardoise'],
    'nfo': LA['ardoise'],
    'rst': LA['teal'], 'org': LA['teal'], 'adoc': LA['teal'], 'asc': LA['teal'],
    'srt': LA['rose'], 'vtt': LA['rose'], 'sub': LA['rose'], 'ass': LA['rose'],
}


def couleur_texte(ext=''):
    return COULEURS_TEXTE.get((ext or '').lower(), COULEURS['texte'])

# Langage déduit du shebang ou du nom du fichier (pas d'extension à lire).
COULEURS_LANGAGES = {
    'SH': COULEURS_CODE['sh'], 'ZSH': COULEURS_CODE['zsh'],
    'FISH': COULEURS_CODE['fish'], 'SCRIPT': COULEURS_CODE['sh'],
    'PY': COULEURS_CODE['py'], 'JS': COULEURS_CODE['js'],
    'PL': COULEURS_CODE['pl'], 'RB': COULEURS_CODE['rb'],
    'LUA': COULEURS_CODE['lua'], 'PHP': COULEURS_CODE['php'],
    'PKGBUILD': COULEURS_CODE['vim'], 'MAKEFILE': COULEURS_CODE['vim'],
    'MESON': COULEURS_CODE['vim'], 'CMAKE': COULEURS_CODE['vim'],
    'SRCINFO': COULEURS_CODE['vim'], 'DOCKERFILE': COULEURS_CODE['vim'],
}


def couleur_code(etiquette, ext=''):
    return (COULEURS_CODE.get((ext or '').lower())
            or COULEURS_LANGAGES.get((etiquette or '').upper())
            or COULEURS['code'])


def melange(couleur, autre=BLANC, part=0.5):
    """Rapproche une couleur du blanc (part = 0 → couleur, 1 → blanc)."""
    return tuple(c * (1 - part) + a * part for c, a in zip(couleur, autre))


def assombrir(couleur, facteur=0.75):
    return tuple(c * facteur for c in couleur)

# --- Texte brut et code : reconnaissance ------------------------------------

EXTENSIONS_CODE = {
    'sh', 'bash', 'zsh', 'fish', 'py', 'pyw', 'js', 'mjs', 'cjs', 'ts', 'jsx', 'tsx',
    'c', 'h', 'cc', 'cpp', 'cxx', 'hpp', 'hh', 'rs', 'go', 'java', 'kt', 'kts', 'cs',
    'swift', 'rb', 'pl', 'pm', 'lua', 'php', 'css', 'scss', 'sass', 'less', 'html', 'htm',
    'xml', 'json', 'jsonc', 'yaml', 'yml', 'toml', 'ini', 'conf', 'cfg', 'vala', 'blp',
    'ui', 'sql', 'diff', 'patch', 'vim', 'el', 'r', 'jl', 'dart', 'scala', 'hs', 'ml',
    'nix', 'cmake', 'mk', 'meson', 'install',
    'log', 'out', 'err', 'journal',                       # journaux
    'csv', 'tsv',                                         # données en colonnes
    'tex', 'latex', 'bib',                                # composition
    'desktop', 'service', 'socket', 'timer', 'env',       # configuration
    'properties', 'reg', 'rc',
    'po', 'pot',                                          # traduction
    'dot', 'gv', 'puml', 'plantuml',                      # schémas en texte
}

# Texte rédigé : feuille claire et prose, plutôt que grille monospace.
EXTENSIONS_TEXTE = {
    'txt', 'text', 'me', 'rst', 'org', 'adoc', 'asc', 'nfo',
    'srt', 'vtt', 'sub', 'ass',
}
# Fichiers texte sans extension, désignés par leur nom entier
NOMS_TEXTE = {'readme': 'README', 'licence': 'LICENCE', 'license': 'LICENSE',
              'copying': 'COPYING', 'changelog': 'CHANGELOG', 'news': 'NEWS',
              'authors': 'AUTHORS', 'todo': 'TODO', 'contributors': 'CONTRIBUTORS'}
NOMS_CODE = {'pkgbuild': 'PKGBUILD', 'makefile': 'MAKEFILE', 'meson.build': 'MESON',
             'cmakelists.txt': 'CMAKE', 'dockerfile': 'DOCKERFILE', '.srcinfo': 'SRCINFO'}
INTERPRETES = {'bash': 'SH', 'sh': 'SH', 'zsh': 'ZSH', 'fish': 'FISH', 'dash': 'SH',
               'python': 'PY', 'python3': 'PY', 'node': 'JS', 'perl': 'PL', 'ruby': 'RB',
               'lua': 'LUA', 'php': 'PHP', 'gjs': 'JS'}
# Langages où « # » ouvre une directive, pas un commentaire
DIESE_NON_COMMENTAIRE = {'c', 'h', 'cc', 'cpp', 'cxx', 'hpp', 'hh', 'cs', 'md'}


def lire_debut_texte(chemin):
    """Début du fichier décodé, ou None s'il ne ressemble pas à du texte."""
    with open(chemin, 'rb') as f:
        octets = f.read(TAILLE_LUE_TEXTE)
    if b'\0' in octets:
        return None
    try:
        texte = octets.decode('utf-8')
    except UnicodeDecodeError as e:
        if e.start >= len(octets) - 4:        # caractère coupé en fin de lecture
            texte = octets[:e.start].decode('utf-8', 'replace')
        else:
            texte = octets.decode('latin-1')
    texte = texte.lstrip('﻿').replace('\r\n', '\n').replace('\r', '\n')
    return ''.join(c for c in texte if c in '\n\t' or c.isprintable())


def famille_texte(chemin, texte):
    """(famille, étiquette, ext) d'un fichier texte. Le bandeau porte toujours
    l'extension réelle du fichier ; à défaut son nom, puis « TXT ». Toute
    extension inconnue est traitée comme du texte technique (grille monospace) :
    c'est le cas le plus fréquent, et cela garde l'alignement du contenu."""
    nom = os.path.basename(chemin)
    # GNOME copie le fichier sous un nom technique en gardant l'extension
    ext = os.path.splitext(nom)[1].lstrip('.').lower()
    if nom.lower() in NOMS_CODE:
        return 'code', NOMS_CODE[nom.lower()], ''
    if nom.lower() in NOMS_TEXTE:
        return 'texte', NOMS_TEXTE[nom.lower()], ''
    if ext in EXTENSIONS_CODE:
        return 'code', ext.upper(), ext
    premiere = texte.split('\n', 1)[0]
    if premiere.startswith('#!'):
        mots = premiere[2:].replace('/usr/bin/env', ' ').split()
        interprete = os.path.basename(mots[0]) if mots else ''
        interprete = interprete.rstrip('0123456789.') or interprete
        return 'code', INTERPRETES.get(interprete, 'SCRIPT'), ''
    if 'pkgname=' in texte[:2000] and 'pkgver=' in texte[:4000]:
        return 'code', 'PKGBUILD', ''
    if ext in EXTENSIONS_TEXTE:
        return 'texte', ext.upper(), ext
    if ext:
        return 'code', ext.upper(), ext
    return 'texte', 'TXT', ''


COULEURS['pdf'] = LA['red-4']          # rouge PDF


# --- Outils de dessin --------------------------------------------------------

def _pango():
    import gi
    gi.require_version('Pango', '1.0')
    gi.require_version('PangoCairo', '1.0')
    from gi.repository import Pango, PangoCairo
    return Pango, PangoCairo


def verifier_polices(mono=False):
    """Signale (sans échouer) une police Adwaita absente : le repli prend le relais."""
    _, PangoCairo = _pango()
    familles = {f.get_name() for f in PangoCairo.FontMap.get_default().list_families()}
    for voulue in ('Adwaita Sans', 'Adwaita Mono' if mono else None):
        if voulue and voulue not in familles:
            print(f'{voulue} introuvable : police de repli du système.', file=sys.stderr)


def _insecable(chaine):
    """Espaces normalisées ; espace insécable avant « : ; ! ? » » et après
    « « » (typographie française) : « ARGUMENTATION : » ne se coupe pas là."""
    chaine = ' '.join(chaine.split())
    chaine = re.sub(r' (?=[:;!?»])', '\u00a0', chaine)
    return re.sub(r'(?<=«) ', '\u00a0', chaine)


_GRAISSES = {False: 'NORMAL', True: 'BOLD', 'medium': 'MEDIUM', 'semi': 'SEMIBOLD'}


def _texte(cr, chaine, x, y, largeur, corps, gras=False, couleur=ENCRE,
           alignement=None, une_ligne=False, police_famille=POLICE, lignes=None,
           centre=None, ajuster=False):
    """Écrit un paragraphe ; renvoie sa hauteur (points de la page virtuelle).

    `gras` : False, True (gras), 'medium' ou 'semi'. Avec `centre`, le
    paragraphe est centré verticalement dans une bande de cette hauteur.
    Avec `ajuster`, le corps est réduit (jusqu'à 72 %) pour que le mot le plus
    long tienne sur une ligne : un titre n'est jamais coupé en plein mot."""
    Pango, PangoCairo = _pango()
    mise = PangoCairo.create_layout(cr)
    police = Pango.FontDescription.from_string(f'{police_famille} {corps}')
    police.set_weight(getattr(Pango.Weight, _GRAISSES[gras]))
    mise.set_font_description(police)
    if ajuster and chaine.split():
        mise.set_text(max(_insecable(chaine).split(' '), key=len), -1)
        _, mot = mise.get_extents()
        largeur_mot = mot.width / Pango.SCALE
        if largeur_mot > largeur * 0.97:          # marge : l'arrondi ferait couper
            police.set_size(int(police.get_size() * max(0.72, largeur * 0.97 / largeur_mot)))
            mise.set_font_description(police)
    mise.set_width(int(max(1, largeur) * Pango.SCALE))
    mise.set_wrap(Pango.WrapMode.WORD_CHAR)
    mise.set_ellipsize(Pango.EllipsizeMode.END)
    # Pas de trait d'union inventé au milieu d'un mot (« ARGUMENT-ATION »)
    attributs = Pango.AttrList()
    attributs.insert(Pango.attr_insert_hyphens_new(False))
    mise.set_attributes(attributs)
    if une_ligne:
        mise.set_height(0)            # une seule ligne, coupée par « … »
    elif lignes:
        mise.set_height(-lignes)      # valeur négative : nombre de lignes maximal
    if alignement == 'droite':
        mise.set_alignment(Pango.Alignment.RIGHT)
    mise.set_text(_insecable(chaine[:1500]), -1)
    _, logique = mise.get_extents()
    hauteur = logique.height / Pango.SCALE
    if centre is not None:
        y += max(0.0, (centre - hauteur) / 2)
    cr.set_source_rgb(*couleur)
    cr.move_to(x, y)
    PangoCairo.show_layout(cr, mise)
    return hauteur


class Toile:
    """La page de la miniature, en points virtuels (VL de large).

    Géométrie de la page Adwaita (text-x-generic.svg, grille de 128) : page
    88 × 112 posée en (20, 8), coins de rayon 8, fond #f6f5f4. En paysage
    (tableurs), la même page couchée.

    - Avec le paquet partenaire : image carrée, ARGB, page aux coins arrondis ;
      la page a la taille exacte de celle des icônes dans Nautilus.
    - Sans lui : la page seule en 11:14, opaque (RGB24, sans canal alpha).

    Rendu direct à la taille demandée par Nautilus (512 px sur un écran HiDPI) :
    aucun rééchantillonnage de notre côté, GTK réduit ensuite l'image avec des
    mipmaps."""

    COURT, LONG = 88.0, 112.0          # page Adwaita, grille de 128
    RAYON = 8.0
    BANDEAU_GRILLE = 14.0              # hauteur du bandeau, grille de 128

    def __init__(self, taille, portrait=True, VL=176.0, fond=None, mono=False):
        import cairo
        verifier_polices(mono)
        self.arrondi = coins_arrondis()
        self.taille = taille
        if self.arrondi:
            k = taille / 128.0
            l = h = taille
            if portrait:
                px, py, pw, ph = 20 * k, 8 * k, self.COURT * k, self.LONG * k
            else:
                px, py, pw, ph = 8 * k, 20 * k, self.LONG * k, self.COURT * k
            fmt = cairo.FORMAT_ARGB32
            fond = fond or LA['light-2']
        else:
            court = max(1, round(taille * self.COURT / self.LONG))
            l, h = (court, taille) if portrait else (taille, court)
            px, py, pw, ph = 0.0, 0.0, float(l), float(h)
            fmt = cairo.FORMAT_RGB24
            fond = fond or PAGE
        self.l, self.h = l, h
        self.VL = VL
        unite = pw / VL                                  # pixels par point
        self.VH = ph / unite
        cote_court = min(pw, ph)
        grille = cote_court / self.COURT                 # pixels par unité de grille
        self.u = grille / unite                          # points par unité de grille
        self.f = self.BANDEAU_GRILLE * self.u / 28.0     # 1 en portrait
        self.BANDEAU = self.BANDEAU_GRILLE * self.u
        if self.arrondi:
            self.BANDEAU = 17.0 * self.u                 # coins arrondis seuls
        self.marge = 13.0 * self.f
        self.fond = fond
        self.utile = VL - 2 * self.marge

        self.surface = cairo.ImageSurface(fmt, l, h)
        cr = self.cr = cairo.Context(self.surface)
        options = cairo.FontOptions()
        options.set_antialias(cairo.ANTIALIAS_GRAY)
        options.set_hint_style(cairo.HINT_STYLE_NONE)
        options.set_hint_metrics(cairo.HINT_METRICS_OFF)
        cr.set_font_options(options)
        cr.translate(px, py)
        cr.scale(unite, unite)
        if self.arrondi:
            self._chemin_page()
            cr.clip()
        cr.set_source_rgb(*fond)
        cr.paint()

    def _chemin_page(self):
        import math
        cr, W, H = self.cr, self.VL, self.VH
        r = self.RAYON * self.u
        cr.new_path()
        cr.move_to(r, 0)
        cr.arc(W - r, r, r, -math.pi / 2, 0)
        cr.arc(W - r, H - r, r, 0, math.pi / 2)
        cr.arc(r, H - r, r, math.pi / 2, math.pi)
        cr.arc(r, r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

    def bandeau(self, etiquette, couleur):
        cr = self.cr
        cr.set_source_rgb(*couleur)
        cr.rectangle(0, 0, self.VL, self.BANDEAU)
        cr.fill()
        _texte(cr, etiquette, self.marge, 0, self.VL * 0.5, 12.5 * self.f, True, BLANC,
               une_ligne=True, centre=self.BANDEAU)

    def enregistrer(self, sortie):
        self.surface.flush()
        self.surface.write_to_png(sortie)


def _repere(cr, x, y, couleur, f=1.0):
    cr.set_source_rgb(*couleur)
    cr.rectangle(x, y + 3.2 * f, 2.6 * f, 8.6 * f)
    cr.fill()


# --- Document (et PDF) : fiche ----------------------------------------------

TITRES = ('titre', 'h1', 'h2', 'h3')
MAX_PLAN = 4


def dessiner_document(blocs, taille, sortie, etiquette='DOC', lecteur='docx'):
    t = Toile(taille)
    couleur = COULEURS.get(lecteur, COULEURS['docx'])
    t.bandeau(etiquette, couleur)
    cr, marge = t.cr, t.marge
    utile = t.VL - 2 * marge
    bas = t.VH - marge
    y = t.BANDEAU + 12

    titre = next((v for g, v in blocs if g == 'titre'), None) or \
        next((v for g, v in blocs if g in TITRES), None)
    plan = [v for g, v in blocs if g in ('h1', 'h2', 'h3') and v != titre]
    texte = [v for g, v in blocs if g in ('p', 'puce') and v != titre]
    image = next((v for g, v in blocs if g == 'surface'), None)
    if image is None:
        image = next((surface_image(v) for g, v in blocs if g == 'image'), None)

    if titre is None and texte:
        # Document sans aucun titre : le début du texte en gras, en accroche.
        y += _texte(cr, texte[0], marge, y, t.utile, 12.5, True, NOIR, lignes=2,
                    ajuster=True) + 8
        texte = texte[1:]
    elif titre:
        y += _texte(cr, titre, marge, y, t.utile, 14.5, True, NOIR, lignes=2,
                    ajuster=True) + 9

    # Titre, plan, image : le texte courant n'apparaît que s'il n'y a ni plan
    # ni image, pour que la page ne soit pas vide.
    if plan:
        for intertitre in plan[:2 if image is not None else MAX_PLAN]:
            if y > bas - 14:
                break
            _repere(cr, marge, y, couleur)
            y += _texte(cr, intertitre, marge + 8, y, utile - 8, 10.8, 'medium', ENCRE,
                        une_ligne=True) + 5
    if image is not None and bas - y >= 40:
        _dessiner_image(t, image, marge, y + 3, utile, min(bas - y - 3, utile * 0.8))
    elif not plan:
        for paragraphe in texte[:2]:
            reste = bas - y
            if reste < 14:
                break
            y += _texte(cr, paragraphe, marge, y, utile, 10.3, False, GRIS,
                        lignes=max(1, min(2, int(reste // 14)))) + 6
    t.enregistrer(sortie)


# --- Images --------------------------------------------------------------------

IMAGE_MIN_PX = 48                       # en dessous : logo, puce, filet → ignoré


def surface_image(donnee):
    """Surface cairo d'une image (type MIME, octets) d'un document ; None si
    elle est illisible (EMF, WMF…) ou trop petite. Décodage par GdkPixbuf."""
    import io
    import cairo
    try:
        import gi
        gi.require_version('GdkPixbuf', '2.0')
        from gi.repository import GdkPixbuf
        _, octets = donnee
        chargeur = GdkPixbuf.PixbufLoader()
        chargeur.write(octets)
        chargeur.close()
        pixbuf = chargeur.get_pixbuf()
        l, h = pixbuf.get_width(), pixbuf.get_height()
        if min(l, h) < IMAGE_MIN_PX:
            return None
        k = min(1.0, 640 / max(l, h))      # inutile de garder plus de pixels
        if k < 1:
            pixbuf = pixbuf.scale_simple(max(1, round(l * k)), max(1, round(h * k)),
                                         GdkPixbuf.InterpType.BILINEAR)
        ok, png = pixbuf.save_to_bufferv('png', [], [])
        return cairo.ImageSurface.create_from_png(io.BytesIO(png)) if ok else None
    except Exception:
        return None


def _dessiner_image(t, surface, x, y, largeur, hauteur):
    """L'image remplit le cadre (recadrée au centre), coins arrondis."""
    import cairo
    import math
    cr = t.cr
    l, h = surface.get_width(), surface.get_height()
    if l < 1 or h < 1:
        return
    # Cadre aux proportions de l'image, sans dépasser la place disponible
    if l / h > largeur / hauteur:
        hauteur = max(hauteur * 0.55, min(hauteur, largeur * h / l))
    k = max(largeur / l, hauteur / h)
    r = 4 * t.f
    cr.save()
    cr.new_sub_path()
    cr.arc(x + largeur - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + largeur - r, y + hauteur - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + hauteur - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()
    cr.clip()
    cr.translate(x + (largeur - l * k) / 2, y + (hauteur - h * k) / 2)
    cr.scale(k, k)
    motif = cairo.SurfacePattern(surface)
    motif.set_filter(cairo.FILTER_GOOD)
    cr.set_source(motif)
    cr.paint()
    cr.restore()


# --- PDF ------------------------------------------------------------------------

_GRAS_PDF = re.compile(r'bold|black|heavy|semibold|demibold|[-,]b(d|old)?$', re.I)
_TITRES_BIDON = re.compile(r'^(microsoft (word|powerpoint)\b|untitled|sans titre|document\d*$|'
                           r'titre$|title$)|\.(docx?|odt|rtf|pdf|pptx?|indd|tex|dvi|ps)$', re.I)
PAGES_PDF = 3


def _poppler():
    import gi
    gi.require_version('Poppler', '0.18')
    from gi.repository import Poppler
    return Poppler


def ouvrir_pdf(chemin):
    from gi.repository import GLib
    return _poppler().Document.new_from_file(GLib.filename_to_uri(os.path.abspath(chemin)), None)


def _signets(doc):
    """Titres des signets de premier niveau (ou ceux sous l'unique signet racine)."""
    Poppler = _poppler()
    try:
        it = Poppler.IndexIter.new(doc)
    except TypeError:                     # aucun signet
        return []

    def niveau(iterateur):
        titres = []
        while True:
            action = iterateur.get_action()
            titre = (getattr(action.any, 'title', None) or '').strip() if action else ''
            titres.append((titre, iterateur.get_child()))
            if not iterateur.next() or len(titres) > 30:
                return titres
    racine = niveau(it)
    if len(racine) == 1 and racine[0][1] is not None:
        return [t for t, _ in niveau(racine[0][1]) if t]
    return [t for t, _ in racine if t]


def _lignes_pdf(doc):
    """[(texte, taille, gras, page)] des premières pages ; '' = rupture."""
    lignes = []
    for n in range(min(PAGES_PDF, doc.get_n_pages())):
        page = doc.get_page(n)
        texte = page.get_text() or ''
        if not texte.strip():
            continue
        tailles = [0.0] * len(texte)
        gras = [False] * len(texte)
        for a in page.get_text_attributes() or []:
            g = bool(_GRAS_PDF.search((a.font_name or '').split('+')[-1]))
            for i in range(max(0, a.start_index), min(a.end_index + 1, len(texte))):
                tailles[i], gras[i] = a.font_size, g
        debut = 0
        for brut in texte.split('\n'):
            fin = debut + len(brut)
            ligne = ' '.join(brut.split())
            if ligne:
                idx = [i for i in range(debut, fin) if not texte[i].isspace()]
                compte = {}
                for i in idx:
                    compte[round(tailles[i], 1)] = compte.get(round(tailles[i], 1), 0) + 1
                taille = max(compte, key=compte.get) if compte else 0.0
                part_gras = sum(gras[i] for i in idx) / max(1, len(idx))
                lignes.append((ligne, taille, part_gras > 0.9, n))
            else:
                lignes.append(('', 0.0, False, n))
            debut = fin + 1
        lignes.append(('', 0.0, False, n))
    return lignes


def blocs_pdf(chemin):
    """Blocs (genre, texte) d'un PDF, comme ceux des documents ; [] si le PDF
    n'a pas de texte (scan)."""
    doc = ouvrir_pdf(chemin)
    lignes = _lignes_pdf(doc)
    pleines = [l for l in lignes if l[0]]
    if not pleines:
        return doc, []
    # Corps du texte : la taille la plus fréquente des lignes non grasses (les
    # intertitres, en gras, peuvent compter plus de caractères qu'un texte court)
    poids = {}
    for texte, taille, gras, _ in [l for l in pleines if not l[2]] or pleines:
        poids[taille] = poids.get(taille, 0) + len(texte)
    corps = max(poids, key=poids.get)

    # Titre : le plus grand texte de la 1re page, s'il dépasse nettement le corps
    premiere = [l for l in pleines if l[3] == pleines[0][3]]
    plus_grand = max(l[1] for l in premiere)
    titre, lignes_titre = None, set()
    if plus_grand >= corps * 1.25:
        morceaux, en_cours = [], False
        for i, (texte, taille, _, page) in enumerate(lignes):
            if page != pleines[0][3]:
                break
            if texte and abs(taille - plus_grand) < 0.6:
                morceaux.append(texte)
                lignes_titre.add(i)
                en_cours = True
            elif en_cours and texte:
                break
        titre = ' '.join(morceaux)
    if not titre:
        meta = ' '.join((doc.get_title() or '').split())
        if len(meta) >= 3 and not _TITRES_BIDON.search(meta):
            titre = meta

    # Plan : les signets, sinon les lignes plus grandes que le corps ou en gras
    plan = [s for s in _signets(doc) if s != titre]
    if not plan:
        for i, (texte, taille, gras, _) in enumerate(lignes):
            if not texte or i in lignes_titre or len(texte) > 90:
                continue
            if taille >= corps * 1.12 or (gras and taille >= corps * 0.95
                                          and not texte.endswith(('.', ','))):
                if texte != titre and texte not in plan:
                    plan.append(texte)
            if len(plan) >= 8:
                break

    # Paragraphes : lignes du corps de texte, recollées
    paragraphes, courant = [], []
    for i, (texte, taille, gras, _) in enumerate(lignes):
        corps_de_texte = texte and i not in lignes_titre and abs(taille - corps) < 0.6 \
            and texte not in plan and not texte.isdigit()
        if corps_de_texte:
            if courant and courant[-1].endswith('-'):
                courant[-1] = courant[-1][:-1] + texte
            else:
                courant.append(texte)
            if texte.endswith(('.', '!', '?', ':')):
                paragraphes.append(' '.join(courant))
                courant = []
        elif courant:
            paragraphes.append(' '.join(courant))
            courant = []
        if len(paragraphes) >= 4:
            break
    if courant:
        paragraphes.append(' '.join(courant))

    blocs = ([('titre', titre)] if titre else []) + [('h1', p) for p in plan] \
        + [('p', p) for p in paragraphes]
    image = _image_pdf(doc)
    if image is not None:
        blocs.append(('surface', image))
    return doc, blocs


def _image_pdf(doc):
    """La plus grande image des premières pages (2 % de la page au moins)."""
    meilleure, aire_max = None, 0.0
    for n in range(min(PAGES_PDF, doc.get_n_pages())):
        page = doc.get_page(n)
        lp, hp = page.get_size()
        for m in page.get_image_mapping() or []:
            a = m.area
            aire = abs((a.x2 - a.x1) * (a.y2 - a.y1))
            if aire > aire_max and aire >= 0.02 * lp * hp:
                try:
                    surface = page.get_image(m.image_id)
                except Exception:
                    continue
                if surface is not None and min(surface.get_width(),
                                               surface.get_height()) >= IMAGE_MIN_PX:
                    meilleure, aire_max = surface, aire
        if meilleure is not None:
            break
    return meilleure


def dessiner_pdf_image(doc, taille, sortie):
    """PDF sans texte (scan) : la première page, sous le bandeau."""
    t = Toile(taille)
    page = doc.get_page(0)
    lp, hp = page.get_size()
    cr = t.cr
    cr.save()
    cr.rectangle(0, t.BANDEAU, t.VL, t.VH - t.BANDEAU)
    cr.clip()
    echelle = t.VL / lp
    cr.translate(0, t.BANDEAU)
    cr.scale(echelle, echelle)
    cr.set_source_rgb(1, 1, 1)
    cr.paint()
    page.render(cr)
    cr.restore()
    t.bandeau('PDF', COULEURS['pdf'])
    t.enregistrer(sortie)


# --- Présentation : fiche -------------------------------------------------------

def dessiner_presentation(diapos, taille, sortie, etiquette='PPTX', lecteur='pptx'):
    t = Toile(taille)
    couleur = COULEURS.get(lecteur, COULEURS['pptx'])
    t.bandeau(etiquette, couleur)
    cr, marge = t.cr, t.marge
    utile = t.VL - 2 * marge
    y = t.BANDEAU + 12
    titres = [(d['titre'] or next((l for _, l in d['lignes']), '')).strip() for d in diapos]
    if titres and titres[0]:
        y += _texte(cr, titres[0], marge, y, t.utile, 14.5, True, NOIR, lignes=2,
                    ajuster=True) + 9
    montres = 0
    for numero, titre in enumerate(titres[1:], 2):
        if y > t.VH - marge - 14 or montres >= MAX_PLAN:
            break
        if not titre:
            continue
        _texte(cr, str(numero), marge, y, 14, 10.8, True, couleur, une_ligne=True)
        y += _texte(cr, titre, marge + 14, y, utile - 14, 10.8, 'medium', ENCRE,
                    une_ligne=True) + 5
        montres += 1
    t.enregistrer(sortie)


# --- Tableur : grille sous un bandeau ----------------------------------------

def dessiner_tableur(feuille, taille, sortie, etiquette='XLSX', lecteur='xlsx'):
    t = Toile(taille, portrait=False, VL=280.0)
    cr, f = t.cr, t.f
    couleur = COULEURS.get(lecteur, COULEURS['xlsx'])
    t.bandeau(etiquette, couleur)

    lignes = feuille['lignes']
    nb_col = max(1, min(feuille['colonnes'], 8))
    texte = lambda c: (c['n'] if isinstance(c, dict) else c) or ''
    corps = 9.4 * f
    largeurs = []
    for j in range(nb_col):
        plus_long = max([len(texte(l[j])) for l in lignes[:20] if j < len(l)] + [3])
        largeurs.append(min(26.0 * corps / 2.2, (8.0 + 0.62 * corps * plus_long)))

    haut = t.BANDEAU
    entete, haut_ligne, x0 = 1.55 * corps, 1.75 * corps, 2.3 * corps
    bas = t.VH - (t.u * 3 if t.arrondi else 4)
    encre_entete = assombrir(couleur, 0.70)
    cr.set_source_rgb(*melange(couleur, BLANC, 0.86))
    cr.rectangle(0, haut, t.VL, entete)
    cr.fill()
    cr.set_source_rgb(*melange(couleur, BLANC, 0.84))
    cr.rectangle(0, haut, x0, bas - haut)
    cr.fill()

    x = x0
    for j in range(nb_col):
        _texte(cr, chr(65 + j), x + 3, haut, largeurs[j] - 6, 0.85 * corps,
               couleur=encre_entete, une_ligne=True, centre=entete)
        x += largeurs[j]
    y = haut + entete
    for i, ligne in enumerate(lignes):
        if y > bas - haut_ligne:
            break
        _texte(cr, str(i + 1), 0, y, x0 - 3, 0.85 * corps, couleur=encre_entete,
               alignement='droite', une_ligne=True, centre=haut_ligne)
        x = x0
        for j in range(nb_col):
            if x > t.VL:
                break
            if j < len(ligne) and texte(ligne[j]):
                c = ligne[j]
                _texte(cr, texte(c), x + 3, y, largeurs[j] - 6, corps,
                       gras=True if i == 0 else False,
                       alignement='droite' if isinstance(c, dict) else None,
                       une_ligne=True, centre=haut_ligne)
            x += largeurs[j]
        y += haut_ligne

    cr.set_source_rgba(0, 0, 0, 0.14)
    cr.set_line_width(0.7 * f)
    gy = haut + entete
    while gy < bas:
        cr.move_to(0, gy)
        cr.line_to(t.VL, gy)
        gy += haut_ligne
    gx = x0
    for l in [0] + largeurs:
        gx += l
        if gx > t.VL:
            break
        cr.move_to(gx, haut)
        cr.line_to(gx, bas)
    cr.stroke()
    t.enregistrer(sortie)


# --- Texte brut : fiche -------------------------------------------------------

def dessiner_texte(texte, taille, sortie, etiquette='TXT', couleur=None):
    t = Toile(taille)
    t.bandeau(etiquette, couleur or COULEURS['texte'])
    cr, marge = t.cr, t.marge
    utile = t.VL - 2 * marge
    lignes = [' '.join(l.split()) for l in texte.split('\n')]
    while lignes and not lignes[0]:
        lignes.pop(0)
    y = t.BANDEAU + 12
    if lignes:
        y += _texte(cr, lignes.pop(0), marge, y, t.utile, 14, True, NOIR, lignes=2,
                    ajuster=True) + 8
    vide, montrees = False, 0
    for ligne in lignes:
        if y > t.VH - marge - 13 or montrees >= 5:
            break
        if not ligne:
            if not vide:
                y += 4                     # une ligne vide = petit espace
            vide = True
            continue
        vide = False
        y += _texte(cr, ligne, marge, y, utile, 10.3, False, ENCRE, une_ligne=True) + 4
        montrees += 1
    t.enregistrer(sortie)


# --- Code : fond sombre ---------------------------------------------------------

def dessiner_code(texte, taille, sortie, etiquette, ext=''):
    t = Toile(taille, fond=LA['dark-3'], mono=True)
    t.bandeau(etiquette, couleur_code(etiquette, ext))
    cr = t.cr
    commentaires = ('//', '--', '/*', '* ', '<!--', ';')
    if ext not in DIESE_NON_COMMENTAIRE:
        commentaires = commentaires + ('#',)
    y = t.BANDEAU + 8
    marge = t.marge
    for ligne in texte.split('\n'):
        if y > t.VH - marge - 4:
            break
        ligne = ligne.rstrip().replace('\t', '    ')
        if ligne:
            vert = ligne.lstrip().startswith(commentaires)
            _texte(cr, ligne, marge, y, t.VL - 2 * marge, 8.8,
                   couleur=(0.56, 0.76, 0.50) if vert else (0.88, 0.89, 0.86),
                   une_ligne=True, police_famille=POLICE_MONO)
        y += 11.6
    t.enregistrer(sortie)


# --- Point d'entrée ----------------------------------------------------------

def _delai(signum, frame):
    raise TimeoutError


def _etiquette(entree, lecteur):
    ext = os.path.splitext(entree)[1].lstrip('.').upper()
    etiquette = ext if ext and ext.lower() in lecteurs.FORMATS_EXT_CONNUES else lecteur.upper()
    return 'MD' if etiquette in ('MARKDOWN', 'MKD') else etiquette


def _est_pdf(entree):
    with open(entree, 'rb') as f:
        return b'%PDF-' in f.read(1024)


def main(argv):
    if len(argv) != 5 or argv[1] != '-s':
        print('Usage : vignette.py -s <taille> <entrée> <sortie.png>', file=sys.stderr)
        return 1
    taille = max(32, min(1024, int(argv[2])))
    entree, sortie = argv[3], argv[4]
    signal.signal(signal.SIGALRM, _delai)
    signal.alarm(DELAI_MAX_S)
    try:
        if _est_pdf(entree):
            if os.path.getsize(entree) > TAILLE_MAX_PDF:
                return 1
            doc, blocs = blocs_pdf(entree)
            if blocs:
                dessiner_document(blocs, taille, sortie, 'PDF', 'pdf')
            else:
                dessiner_pdf_image(doc, taille, sortie)
            return 0
        if os.path.getsize(entree) > TAILLE_MAX:
            return 1
        fmt = lecteurs.format_de(entree)
        if fmt is None:
            texte = lire_debut_texte(entree)
            if texte is None or not texte.strip():
                print('Format non reconnu.', file=sys.stderr)
                return 1
            famille, etiquette, ext = famille_texte(entree, texte)
            if famille == 'code':
                dessiner_code(texte, taille, sortie, etiquette, ext)
            else:
                dessiner_texte(texte, taille, sortie, etiquette, couleur_texte(ext))
            return 0

        famille, lecteur = fmt
        if lecteur in lecteurs.FORMATS_ZIP:
            with zipfile.ZipFile(entree) as archive:
                if sum(i.file_size for i in archive.infolist()) > 300 * 1024**2:
                    return 1
        etiquette = _etiquette(entree, lecteur)
        if famille == 'document':
            blocs = lecteurs.LECTEURS_DOCUMENT[lecteur](entree, avec_image=True)
            dessiner_document(blocs, taille, sortie, etiquette, lecteur)
        elif famille == 'presentation':
            diapos = lecteurs.LECTEURS_PRESENTATION[lecteur](entree)
            dessiner_presentation(diapos, taille, sortie, etiquette, lecteur)
        else:
            import convertir
            convertir.MAX_FEUILLES, convertir.MAX_LIGNES, convertir.MAX_COLONNES = 30, 40, 12
            convertir.COMPTER_FORMULES_SANS_VALEUR = False
            donnees = convertir.lire_tableur(entree)
            if not donnees['feuilles']:
                return 1
            dessiner_tableur(donnees['feuilles'][0], taille, sortie, etiquette, lecteur)
        return 0
    except TimeoutError:
        print('Délai dépassé.', file=sys.stderr)
    except Exception as e:
        print(f'Miniature impossible : {type(e).__name__} : {e}', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
