"""Lecture de tableurs simples (csv, xlsx, ods) et écriture ODS/xlsx, sans dépendance externe."""

from __future__ import annotations

import csv
import io
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

from .db import normaliser

LIGNES_MAX = 2000
COLONNES_MAX = 60


class ErreurTableur(Exception):
    pass


# ------------------------------------------------------------------- lecture

def lire(chemin) -> list[list[str]]:
    chemin = Path(chemin)
    ext = chemin.suffix.lower()
    try:
        if ext in (".csv", ".txt", ".tsv"):
            lignes = _lire_csv(chemin)
        elif ext in (".xlsx", ".xlsm"):
            lignes = _lire_xlsx(chemin)
        elif ext == ".ods":
            lignes = _lire_ods(chemin)
        else:
            raise ErreurTableur(f"Format non pris en charge : {ext or 'inconnu'}")
    except (zipfile.BadZipFile, ET.ParseError, KeyError, UnicodeError) as e:
        raise ErreurTableur(f"Fichier illisible : {e}") from e
    # Nettoyage : espaces, lignes vides, colonnes vides en fin de ligne.
    propres = []
    for ligne in lignes[:LIGNES_MAX]:
        ligne = [" ".join(str(c).split()) for c in ligne[:COLONNES_MAX]]
        while ligne and not ligne[-1]:
            ligne.pop()
        if any(ligne):
            propres.append(ligne)
    return propres


def _lire_csv(chemin: Path):
    brut = chemin.read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            texte = brut.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    echantillon = texte[:4096]
    try:
        dialecte = csv.Sniffer().sniff(echantillon, delimiters=";,\t")
    except csv.Error:
        class dialecte(csv.excel):
            delimiter = ";" if echantillon.count(";") >= echantillon.count(",") else ","
    return [list(r) for r in csv.reader(io.StringIO(texte), dialecte)]


_NS_X = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NS_PR = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def _col_index(ref: str) -> int:
    lettres = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for ch in lettres:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _xlsx_texte(el) -> str:
    return "".join(t.text or "" for t in el.iter(f"{{{_NS_X['m']}}}t"))


def _lire_xlsx(chemin: Path):
    with zipfile.ZipFile(chemin) as z:
        partages = []
        if "xl/sharedStrings.xml" in z.namelist():
            racine = ET.fromstring(z.read("xl/sharedStrings.xml"))
            partages = [_xlsx_texte(si) for si in racine.findall("m:si", _NS_X)]
        classeur = ET.fromstring(z.read("xl/workbook.xml"))
        feuille = classeur.find("m:sheets/m:sheet", _NS_X)
        rid = feuille.get(f"{{{_NS_R}}}id")
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        cible = next(r.get("Target") for r in rels.iter(f"{_NS_PR}Relationship") if r.get("Id") == rid)
        cible = cible.lstrip("/")
        if not cible.startswith("xl/"):
            cible = "xl/" + cible
        racine = ET.fromstring(z.read(cible))
    lignes = []
    for row in racine.iter(f"{{{_NS_X['m']}}}row"):
        cellules: dict[int, str] = {}
        for i, c in enumerate(row.findall("m:c", _NS_X)):
            idx = _col_index(c.get("r")) if c.get("r") else i
            if idx >= COLONNES_MAX:
                continue
            t = c.get("t")
            v = c.find("m:v", _NS_X)
            if t == "s" and v is not None:
                val = partages[int(v.text)]
            elif t == "inlineStr":
                val = _xlsx_texte(c)
            elif v is not None and v.text is not None:
                val = v.text
                if t not in ("str", "b", "e"):
                    val = _nombre_propre(val)
            else:
                val = ""
            cellules[idx] = val
        if cellules:
            ligne = [""] * (max(cellules) + 1)
            for k, val in cellules.items():
                ligne[k] = val
            lignes.append(ligne)
        if len(lignes) >= LIGNES_MAX:
            break
    return lignes


def _nombre_propre(val: str) -> str:
    try:
        f = float(val)
    except ValueError:
        return val
    return str(int(f)) if f.is_integer() else repr(round(f, 6))


_NS_O = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
}


def _ods_texte(cell) -> str:
    morceaux = []
    for p in cell.findall("text:p", _NS_O):
        bouts = []
        for el in p.iter():
            if el.tag == f"{{{_NS_O['text']}}}s":
                bouts.append(" " * int(el.get(f"{{{_NS_O['text']}}}c", "1")))
            if el.text and el.tag != f"{{{_NS_O['text']}}}s":
                bouts.append(el.text)
            if el is not p and el.tail:
                bouts.append(el.tail)
        morceaux.append("".join(bouts))
    return "\n".join(morceaux)


def _lire_ods(chemin: Path):
    with zipfile.ZipFile(chemin) as z:
        racine = ET.fromstring(z.read("content.xml"))
    table = racine.find(".//table:table", _NS_O)
    if table is None:
        return []
    T = _NS_O["table"]
    O = _NS_O["office"]
    lignes = []
    for row in table.iter(f"{{{T}}}table-row"):
        rep_l = min(int(row.get(f"{{{T}}}number-rows-repeated", "1")), 50)
        ligne = []
        for cell in row:
            if cell.tag not in (f"{{{T}}}table-cell", f"{{{T}}}covered-table-cell"):
                continue
            rep_c = int(cell.get(f"{{{T}}}number-columns-repeated", "1"))
            vtype = cell.get(f"{{{O}}}value-type")
            if vtype in ("float", "percentage", "currency"):
                val = _nombre_propre(cell.get(f"{{{O}}}value", ""))
            else:
                val = _ods_texte(cell)
            if not val and len(ligne) + rep_c > COLONNES_MAX:
                break
            ligne.extend([val] * min(rep_c, COLONNES_MAX))
        if any(ligne):
            lignes.extend([list(ligne) for _ in range(rep_l)])
        elif lignes:
            lignes.append([])
        if len(lignes) >= LIGNES_MAX:
            break
    return lignes


# ------------------------------------------------------------------ analyse

_MOTS_NOM = ("nom", "eleve", "élève", "nom eleve", "nom de famille")
_MOTS_PRENOM = ("prenom", "prénom")
_MOTS_MOY = ("moy", "moyenne", "moyenne generale", "moy. gen", "moy gen", "mg")


def parser_moyenne(val: str):
    v = (val or "").strip().replace(",", ".").replace(" ", "")
    m = re.match(r"^-?\d+(\.\d+)?", v)
    if not m:
        return None
    f = float(m.group(0))
    return f if 0 <= f <= 20 else None


def separer_nom_prenom(texte: str) -> tuple[str, str]:
    """« DUPONT Marie-Claire » -> (DUPONT, Marie-Claire). Les mots en capitales forment le nom."""
    mots = texte.split()
    if not mots:
        return "", ""
    if "," in texte:
        nom, _, prenom = texte.partition(",")
        return nom.strip(), prenom.strip()
    nom = []
    for m in mots:
        lettres = [c for c in m if c.isalpha()]
        if lettres and all(c.isupper() for c in lettres):
            nom.append(m)
        else:
            break
    if not nom:
        return mots[0], " ".join(mots[1:])
    if len(nom) == len(mots):
        return " ".join(mots[:-1]) if len(mots) > 1 else mots[0], (mots[-1] if len(mots) > 1 else "")
    return " ".join(nom), " ".join(mots[len(nom):])


def _ressemble(cellule: str, mots) -> bool:
    c = normaliser(cellule).replace(".", " ").replace("_", " ")
    c = " ".join(c.split())
    return any(c == m or c.startswith(m + " ") for m in (normaliser(x) for x in mots))


def analyser(lignes: list[list[str]]) -> dict:
    """Détecte la ligne d'en-tête et les colonnes nom / prénom / moyenne."""
    res = {"entete": None, "nom": None, "prenom": None, "moyenne": None, "colonnes": []}
    if not lignes:
        return res
    largeur = max(len(l) for l in lignes)
    for i, ligne in enumerate(lignes[:10]):
        idx_nom = next((j for j, c in enumerate(ligne) if _ressemble(c, _MOTS_NOM)), None)
        idx_pre = next((j for j, c in enumerate(ligne) if _ressemble(c, _MOTS_PRENOM)), None)
        if idx_nom is not None or idx_pre is not None:
            res["entete"] = i
            res["nom"] = idx_nom if idx_nom is not None else idx_pre
            res["prenom"] = idx_pre if idx_pre is not None and idx_pre != res["nom"] else None
            res["moyenne"] = next((j for j, c in enumerate(ligne) if _ressemble(c, _MOTS_MOY)), None)
            break
    donnees = lignes[(res["entete"] + 1) if res["entete"] is not None else 0:]
    if res["nom"] is None:
        res["nom"] = 0
    if res["moyenne"] is None:
        # Première colonne dont la majorité des valeurs sont des notes sur 20.
        for j in range(largeur):
            if j in (res["nom"], res["prenom"]):
                continue
            vals = [l[j] for l in donnees if j < len(l) and l[j]]
            if vals and sum(parser_moyenne(v) is not None for v in vals) >= 0.7 * len(vals):
                res["moyenne"] = j
                break
    entete = lignes[res["entete"]] if res["entete"] is not None else []
    res["colonnes"] = [
        (entete[j] if j < len(entete) and entete[j] else f"Colonne {_lettre(j)}")
        for j in range(largeur)
    ]
    return res


def _lettre(j: int) -> str:
    s = ""
    j += 1
    while j:
        j, r = divmod(j - 1, 26)
        s = chr(65 + r) + s
    return s


def extraire(lignes, entete, col_nom, col_prenom=None, col_moyenne=None):
    """-> [(nom, prenom, moyenne|None)]"""
    res = []
    for ligne in lignes[(entete + 1) if entete is not None else 0:]:
        def cell(j):
            return ligne[j].strip() if j is not None and j < len(ligne) else ""
        nom = cell(col_nom)
        if col_prenom is None:
            nom, prenom = separer_nom_prenom(nom)
        else:
            prenom = cell(col_prenom)
        if not nom and not prenom:
            continue
        if normaliser(nom) in ("moyenne", "moyenne classe", "total", "moyenne de la classe"):
            continue
        res.append((nom, prenom, parser_moyenne(cell(col_moyenne)) if col_moyenne is not None else None))
    return res


# ------------------------------------------------- commentaires de collègues

_MOTS_DISCIPLINE = ("discipline", "matiere", "specialite", "cours", "module", "enseignement")
_MOTS_COMMENTAIRE = ("commentaire", "commentaires", "appreciation", "bilan", "remarque",
                     "remarques", "avis", "observation", "observations", "texte")
_MOTS_NOTE = ("note", "moyenne", "moy", "note matiere", "note discipline")

# « Mathématiques (moyenne) », « Maths - note », « Anglais : commentaire »
_QUALIFICATIF = re.compile(
    r"[\s\-–—:/(]+(moyennes?|notes?|moy\.?|commentaires?|appr[ée]ciations?|avis|remarques?|"
    r"observations?|textes?)\s*\)?\s*$", re.IGNORECASE)


def base_colonne(entete: str) -> tuple[str, str]:
    """« Mathématiques (moyenne) » -> (« Mathématiques », « moyenne »)."""
    texte = (entete or "").strip()
    m = _QUALIFICATIF.search(texte)
    if m:
        mot = normaliser(m.group(1))
        genre = "moyenne" if mot.startswith(("moy", "note")) else "commentaire"
        return texte[:m.start()].strip() or texte, genre
    return texte, ""


def analyser_commentaires(lignes: list[list[str]]) -> dict:
    """Détecte un fichier de commentaires/moyennes par discipline.

    Deux dispositions sont reconnues :
    - longue : une ligne par élève et par discipline, avec des colonnes
      « discipline » et « commentaire » et/ou « moyenne » ;
    - large : une colonne par discipline (éventuellement « Discipline (moyenne) »
      et « Discipline (commentaire) »).
    """
    res = analyser(lignes)
    res.update({"format": None, "discipline": None, "commentaire": None,
                "moyenne_discipline": None, "disciplines": []})
    if res["entete"] is None and not lignes:
        return res
    entete = lignes[res["entete"]] if res["entete"] is not None else []
    idx_disc = next((j for j, c in enumerate(entete) if _ressemble(c, _MOTS_DISCIPLINE)), None)
    idx_com = next((j for j, c in enumerate(entete) if _ressemble(c, _MOTS_COMMENTAIRE)), None)
    idx_note = next((j for j, c in enumerate(entete) if _ressemble(c, _MOTS_NOTE)), None)
    if idx_disc is not None and (idx_com is not None or idx_note is not None):
        res.update({"format": "long", "discipline": idx_disc, "commentaire": idx_com,
                    "moyenne_discipline": idx_note})
        return res

    # Disposition large : une colonne par discipline.
    donnees = lignes[(res["entete"] + 1) if res["entete"] is not None else 0:]
    exclues = {res["nom"], res["prenom"]}
    # Une colonne numérique n'est une « moyenne générale » que si son titre le dit ;
    # sinon c'est la colonne de notes d'une discipline.
    if res["moyenne"] is not None and res["moyenne"] < len(entete) \
            and _ressemble(entete[res["moyenne"]], _MOTS_MOY):
        exclues.add(res["moyenne"])
    disciplines: dict[str, dict] = {}
    ordre: list[str] = []
    for j in range(len(entete)):
        if j in exclues:
            continue
        titre = (entete[j] or "").strip()
        if not titre:
            continue
        vals = [(l[j] or "").strip() for l in donnees if j < len(l) and (l[j] or "").strip()]
        if not vals:
            continue
        base, genre = base_colonne(titre)
        notes = sum(parser_moyenne(v) is not None for v in vals)
        if not genre:
            genre = "moyenne" if notes >= 0.7 * len(vals) else "commentaire"
        if base not in disciplines:
            disciplines[base] = {}
            ordre.append(base)
        disciplines[base][genre] = j
    if ordre:
        res["format"] = "large"
        res["disciplines"] = [(base, disciplines[base]) for base in ordre]
    return res


def extraire_commentaires(lignes, analyse) -> list[tuple]:
    """-> [(nom, prenom, discipline, moyenne|None, commentaire)]"""
    entete = analyse["entete"]
    debut = (entete + 1) if entete is not None else 0
    res: list[tuple] = []
    for ligne in lignes[debut:]:
        def cell(j):
            if j is None or j >= len(ligne):
                return ""
            return (ligne[j] or "").strip()

        nom = cell(analyse["nom"])
        if analyse["prenom"] is None:
            nom, prenom = separer_nom_prenom(nom)
        else:
            prenom = cell(analyse["prenom"])
        if not nom and not prenom:
            continue
        if normaliser(nom) in ("moyenne", "moyenne classe", "total", "moyenne de la classe"):
            continue
        if analyse["format"] == "long":
            res.append((nom, prenom, cell(analyse["discipline"]),
                        parser_moyenne(cell(analyse["moyenne_discipline"])),
                        cell(analyse["commentaire"])))
        elif analyse["format"] == "large":
            for base, colonnes in analyse["disciplines"]:
                note = parser_moyenne(cell(colonnes.get("moyenne"))) \
                    if "moyenne" in colonnes else None
                commentaire = cell(colonnes.get("commentaire")) if "commentaire" in colonnes else ""
                if note is None and not commentaire:
                    continue
                res.append((nom, prenom, base, note, commentaire))
    return res


# ----------------------------------------------------------------- écriture

def ecrire_ods(chemin, feuilles: list[tuple[str, list[list]]], largeurs_cm: list[float] | None = None):
    """feuilles : [(nom, lignes)] ; la première ligne de chaque feuille est l'en-tête.
    Les nombres (int/float) sont écrits comme valeurs numériques."""
    largeurs_cm = largeurs_cm or []
    styles_col = []
    for i, w in enumerate(largeurs_cm):
        styles_col.append(
            f'<style:style style:name="co{i}" style:family="table-column">'
            f'<style:table-column-properties style:column-width="{w}cm"/></style:style>')
    corps = []
    for nom, lignes in feuilles:
        nom = escape(nom[:31], {'"': "&quot;"})
        corps.append(f'<table:table table:name="{nom}">')
        ncol = max((len(l) for l in lignes), default=0)
        for j in range(ncol):
            st = f"co{j}" if j < len(largeurs_cm) else f"co{len(largeurs_cm) - 1}" if largeurs_cm else None
            attr = f' table:style-name="{st}"' if st else ""
            corps.append(f'<table:table-column{attr} table:default-cell-style-name="ce1"/>')
        for i, ligne in enumerate(lignes):
            corps.append("<table:table-row>")
            for val in ligne:
                style = "ce0" if i == 0 else "ce1"
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    corps.append(f'<table:table-cell table:style-name="{style}" office:value-type="float" '
                                 f'office:value="{val}"><text:p>{str(val).replace(".", ",")}</text:p>'
                                 f'</table:table-cell>')
                elif val is None or val == "":
                    corps.append(f'<table:table-cell table:style-name="{style}"/>')
                else:
                    paras = "".join(f"<text:p>{escape(p)}</text:p>" for p in str(val).split("\n"))
                    corps.append(f'<table:table-cell table:style-name="{style}" office:value-type="string">'
                                 f'{paras}</table:table-cell>')
            corps.append("</table:table-row>")
        corps.append("</table:table>")
    contenu = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
        'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
        'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
        'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
        'xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" office:version="1.3">'
        '<office:automatic-styles>' + "".join(styles_col) +
        '<style:style style:name="ce0" style:family="table-cell">'
        '<style:table-cell-properties fo:background-color="#deddda" fo:wrap-option="wrap" '
        'style:vertical-align="middle"/><style:text-properties fo:font-weight="bold"/></style:style>'
        '<style:style style:name="ce1" style:family="table-cell">'
        '<style:table-cell-properties fo:wrap-option="wrap" style:vertical-align="top"/></style:style>'
        '</office:automatic-styles><office:body><office:spreadsheet>' + "".join(corps) +
        '</office:spreadsheet></office:body></office:document-content>'
    )
    manifeste = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" '
        'manifest:version="1.3">'
        '<manifest:file-entry manifest:full-path="/" manifest:version="1.3" '
        'manifest:media-type="application/vnd.oasis.opendocument.spreadsheet"/>'
        '<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>'
        '</manifest:manifest>'
    )
    with zipfile.ZipFile(chemin, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/vnd.oasis.opendocument.spreadsheet",
                   compress_type=zipfile.ZIP_STORED)
        z.writestr("content.xml", contenu, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("META-INF/manifest.xml", manifeste, compress_type=zipfile.ZIP_DEFLATED)


# --------------------------------------------------------------------- xlsx
# Écriture d'un classeur xlsx minimal (OpenXML) : chaînes en ligne, une feuille
# par entrée, en-tête en gras, colonnes dimensionnées, retour à la ligne activé.

_XLSX_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_XLSX_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_XLSX_PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
_XLSX_CT = "http://schemas.openxmlformats.org/package/2006/content-types"


def _xlsx_nom_feuille(nom: str, utilises: set) -> str:
    nom = re.sub(r"[\[\]:*?/\\]", "-", (nom or "Feuille").strip())[:31] or "Feuille"
    base, i = nom, 2
    while nom in utilises:
        suffixe = f" ({i})"
        nom = base[:31 - len(suffixe)] + suffixe
        i += 1
    utilises.add(nom)
    return nom


def _xlsx_echapper(texte: str) -> str:
    return escape(texte, {'"': "&quot;"})


def ecrire_xlsx(chemin, feuilles: list[tuple[str, list[list]]], largeurs_cm: list[float] | None = None):
    """feuilles : [(nom, lignes)] ; la première ligne de chaque feuille est l'en-tête.
    Les nombres sont écrits comme valeurs numériques, le reste comme texte."""
    largeurs_cm = list(largeurs_cm or [])
    utilises: set = set()
    noms = [_xlsx_nom_feuille(nom, utilises) for nom, _ in feuilles]

    def feuille(lignes):
        ncol = max((len(l) for l in lignes), default=0)
        cols = ""
        if largeurs_cm and ncol:
            morceaux = []
            for j in range(ncol):
                cm = largeurs_cm[j] if j < len(largeurs_cm) else largeurs_cm[-1]
                morceaux.append(f'<col min="{j + 1}" max="{j + 1}" '
                                f'width="{max(8, round(cm * 5, 1))}" customWidth="1"/>')
            cols = f"<cols>{''.join(morceaux)}</cols>"
        rangs = []
        for i, ligne in enumerate(lignes, start=1):
            style = 1 if i == 1 else 2
            cellules = []
            for j, val in enumerate(ligne):
                ref = f"{_lettre(j)}{i}"
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    cellules.append(f'<c r="{ref}" s="{style}"><v>{val}</v></c>')
                elif val is None or val == "":
                    cellules.append(f'<c r="{ref}" s="{style}"/>')
                else:
                    txt = _xlsx_echapper(str(val))
                    cellules.append(f'<c r="{ref}" s="{style}" t="inlineStr">'
                                    f'<is><t xml:space="preserve">{txt}</t></is></c>')
            rangs.append(f'<row r="{i}">{"".join(cellules)}</row>')
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                f'<worksheet xmlns="{_XLSX_NS}">{cols}<sheetData>{"".join(rangs)}</sheetData></worksheet>')

    def classeur():
        feuilles_xml = "".join(
            f'<sheet name="{_xlsx_echapper(noms[i])}" sheetId="{i + 1}" r:id="rId{i + 1}"/>'
            for i in range(len(noms)))
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                f'<workbook xmlns="{_XLSX_NS}" xmlns:r="{_XLSX_REL}">'
                f'<sheets>{feuilles_xml}</sheets></workbook>')

    def rels_classeur():
        rels = "".join(
            f'<Relationship Id="rId{i + 1}" Type="{_XLSX_REL}/worksheet" '
            f'Target="worksheets/sheet{i + 1}.xml"/>' for i in range(len(noms)))
        rels += f'<Relationship Id="rIdStyles" Type="{_XLSX_REL}/styles" Target="styles.xml"/>'
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                f'<Relationships xmlns="{_XLSX_PKG}">{rels}</Relationships>')

    def types_contenu():
        overrides = "".join(
            f'<Override PartName="/xl/worksheets/sheet{i + 1}.xml" ContentType="application/'
            'vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for i in range(len(noms)))
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                f'<Types xmlns="{_XLSX_CT}">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.'
                'relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-'
                'officedocument.spreadsheetml.sheet.main+xml"/>'
                f'{overrides}'
                '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-'
                'officedocument.spreadsheetml.styles+xml"/></Types>')

    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              f'<styleSheet xmlns="{_XLSX_NS}">'
              '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
              '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
              '<fills count="3"><fill><patternFill patternType="none"/></fill>'
              '<fill><patternFill patternType="gray125"/></fill>'
              '<fill><patternFill patternType="solid"><fgColor rgb="FFDEDDDA"/>'
              '<bgColor indexed="64"/></patternFill></fill></fills>'
              '<borders count="1"><border/></borders>'
              '<cellStyleXfs count="1"><xf/></cellStyleXfs>'
              '<cellXfs count="3"><xf xfId="0"/>'
              '<xf xfId="0" fontId="1" fillId="2" applyFont="1" applyFill="1" applyAlignment="1">'
              '<alignment wrapText="1" vertical="center"/></xf>'
              '<xf xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>'
              '</cellXfs></styleSheet>')

    rels_racine = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   f'<Relationships xmlns="{_XLSX_PKG}">'
                   f'<Relationship Id="rId1" Type="{_XLSX_REL}/officeDocument" Target="xl/workbook.xml"/>'
                   '</Relationships>')

    with zipfile.ZipFile(chemin, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types_contenu())
        z.writestr("_rels/.rels", rels_racine)
        z.writestr("xl/workbook.xml", classeur())
        z.writestr("xl/_rels/workbook.xml.rels", rels_classeur())
        z.writestr("xl/styles.xml", styles)
        for i, (_nom, lignes) in enumerate(feuilles):
            z.writestr(f"xl/worksheets/sheet{i + 1}.xml", feuille(lignes))


# ------------------------------------------------------- export de toutes les données

def _nom_fichier(annee: str, theme: str) -> str:
    return f"Livret {annee} - {theme}.xlsx"


def exporter_donnees(base, annee_id, dossier) -> list[Path]:
    """Écrit un jeu de classeurs xlsx séparés, un par thème. -> [chemins]"""
    from .db import CONVENTION, RECHERCHE, libelle_periode

    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    annee = base.annee(annee_id)["libelle"]
    classes = {c["id"]: c for c in base.classes(annee_id)}
    faits: list[Path] = []

    def ecrire(theme, lignes, largeurs):
        chemin = dossier / _nom_fichier(annee, theme)
        ecrire_xlsx(chemin, [(theme, lignes)], largeurs)
        faits.append(chemin)

    # Classes
    lignes = [["Classe", "Découpage", "Élèves", "Matières"]]
    for c in classes.values():
        lignes.append([c["nom"], "3 trimestres" if c["decoupage"] == "T" else "2 semestres",
                       len(base.eleves(c["id"])), len(base.matieres(c["id"]))])
    ecrire("Classes", lignes, [24, 14, 8, 10])

    # Élèves
    lignes = [["Classe", "Nom", "Prénom"]]
    for e in base.eleves_annee(annee_id):
        lignes.append([e["classe_nom"], e["nom"], e["prenom"]])
    ecrire("Élèves", lignes, [24, 20, 20])

    # Matières
    lignes = [["Classe", "Ordre", "Matière"]]
    for cid, c in classes.items():
        for m in base.matieres(cid):
            lignes.append([c["nom"], m["ordre"] + 1, m["nom"]])
    ecrire("Matières", lignes, [24, 8, 28])

    # Appréciations
    lignes = [["Classe", "Élève", "Période", "Matière", "Appréciation", "Terminé", "Moyenne"]]
    for e in base.eleves_annee(annee_id):
        c = classes.get(e["classe_id"])
        if c is None:
            continue
        mats = {m["id"]: m["nom"] for m in base.matieres(c["id"])}
        for (mid, periode), a in sorted(base.appreciations_eleve(e["id"]).items(),
                                        key=lambda kv: (kv[0][1], kv[0][0])):
            lignes.append([c["nom"], f"{e['nom']} {e['prenom']}".strip(),
                           libelle_periode(c["decoupage"], periode, True), mats.get(mid, ""),
                           a["texte"], "oui" if a["termine"] else "non",
                           a["moyenne"] if a["moyenne"] is not None else ""])
    ecrire("Appréciations", lignes, [18, 22, 14, 22, 60, 8, 9])

    # Bilans
    lignes = [["Classe", "Élève", "Période", "Bilan", "Terminé", "Moyenne", "Décision",
               "Note de décision"]]
    for e in base.eleves_annee(annee_id):
        c = classes.get(e["classe_id"])
        if c is None:
            continue
        for periode, b in sorted(base.bilans_eleve(e["id"]).items()):
            lignes.append([c["nom"], f"{e['nom']} {e['prenom']}".strip(),
                           libelle_periode(c["decoupage"], periode, True), b["texte"],
                           "oui" if b["termine"] else "non",
                           b["moyenne"] if b["moyenne"] is not None else "",
                           b["decision"] or "", b["decision_note"] or ""])
    ecrire("Bilans", lignes, [18, 22, 14, 60, 8, 9, 22, 30])

    # PFMP
    lignes = [["Classe", "Élève", "PFMP", "Recherche", "Convention", "Entreprise", "Adresse",
               "Téléphone", "Tuteur", "Prof référent", "Visite le"]]
    for numero in (1, 2):
        pid = base.pfmp_id(annee_id, numero)
        for s in base.stages(annee_id, pid):
            lignes.append([s["classe_nom"], f"{s['nom']} {s['prenom']}".strip(), f"PFMP {numero}",
                           RECHERCHE.get(s["recherche"], s["recherche"]),
                           CONVENTION[s["convention"]] if 0 <= s["convention"] < len(CONVENTION) else "",
                           s["entreprise"], s["adresse"], s["telephone"], s["tuteur"],
                           s["enseignant_nom"], s["visite_le"]])
    ecrire("PFMP", lignes, [16, 22, 8, 12, 20, 26, 34, 16, 22, 22, 14])

    # Visites attribuées
    lignes = [["Prof référent", "Classe", "Élève", "Entreprise", "Adresse", "Téléphone", "Tuteur",
               "PFMP", "Visite le"]]
    for numero in (1, 2):
        pid = base.pfmp_id(annee_id, numero)
        for s in base.stages(annee_id, pid):
            if not s["enseignant_id"]:
                continue
            lignes.append([s["enseignant_nom"], s["classe_nom"], f"{s['nom']} {s['prenom']}".strip(),
                           s["entreprise"], s["adresse"], s["telephone"], s["tuteur"],
                           f"PFMP {numero}", s["visite_le"]])
    ecrire("Visites", lignes, [22, 16, 22, 26, 34, 16, 22, 8, 14])

    # Professeurs et heures
    ens = base.enseignants(annee_id)
    noms_classes = [c["nom"] for c in classes.values()]
    lignes = [["Professeur", *noms_classes, "Total"]]
    for e in ens:
        heures = base.heures_enseignant(e["id"])
        ligne = [e["nom"]]
        total = 0.0
        for cid, c in classes.items():
            h = heures.get(cid, 0) or 0
            total += h
            ligne.append(h or "")
        ligne.append(total or "")
        lignes.append(ligne)
    ecrire("Professeurs", lignes, [24, *([12] * len(noms_classes)), 10])

    # Carnet d'entreprises
    lignes = [["Entreprise", "Adresse", "Téléphone", "Tuteur"]]
    for r in base.carnet():
        lignes.append([r["nom"], r["adresse"], r["telephone"], r["tuteur"]])
    ecrire("Entreprises", lignes, [28, 36, 18, 24])

    return faits
