"""Moteur PDF : un seul fil de travail possède tous les documents PyMuPDF.

PyMuPDF n'est pas sûr entre fils sur un même document : toute opération
(ouverture, conversion, rendu, enregistrement) passe donc par `soumettre`,
qui l'exécute dans le fil du moteur, puis rappelle l'interface dans le fil
principal (GLib.idle_add). L'interface ne touche jamais PyMuPDF.

La même fonction `page_unique` sert à l'aperçu ET à l'enregistrement :
la grille montre exactement ce qui sera écrit.
"""

from __future__ import annotations

import functools
import itertools
import os
import queue
import tempfile
import threading
import traceback
from collections import OrderedDict

import pymupdf

from . import conversion
from .modele import EFFACER, ROGNER, SUPPRIMER, TEXTE, Page

pymupdf.TOOLS.mupdf_display_errors(False)
pymupdf.TOOLS.mupdf_display_warnings(False)

# Priorités (plus petit = plus urgent) ; les miniatures sont triées par rang
URGENT = (0, 0)
NORMAL = (10, 0)

# Source réservée au document d'aperçu, hors de la numérotation des fichiers.
APERCU = -1


def priorite_miniature(rang: int):
    return (20, rang)


class MotDePasseRequis(Exception):
    pass


class MotDePasseIncorrect(Exception):
    pass


def _idle(fonction, *args):
    from gi.repository import GLib

    def appel():
        fonction(*args)
        return False
    GLib.idle_add(appel)


class Moteur:
    def __init__(self, planifier=_idle):
        self._planifier = planifier
        self._file = queue.PriorityQueue()
        self._seq = itertools.count()
        self.docs: dict[int, pymupdf.Document] = {}
        self._cache: OrderedDict = OrderedDict()   # cle_contenu → Document
        self._cache_max = 40
        self._fil = threading.Thread(target=self._boucle, name="moteur-maquette",
                                     daemon=True)
        self._fil.start()

    # ------------------------------------------------------------ file
    def soumettre(self, fonction, *args, priorite=NORMAL, rappel=None,
                  erreur=None, voulu=None):
        """Exécute fonction(*args) dans le fil du moteur.

        rappel(résultat) / erreur(exception) sont appelés dans le fil
        principal. voulu() (facultatif) est consulté juste avant le travail :
        s'il renvoie False, le travail est abandonné (miniature périmée).
        """
        self._file.put((priorite, next(self._seq), fonction, args, rappel,
                        erreur, voulu))

    def _boucle(self):
        while True:
            _, _, fonction, args, rappel, erreur, voulu = self._file.get()
            if voulu is not None:
                try:
                    if not voulu():
                        continue
                except Exception:
                    continue
            try:
                resultat = fonction(*args)
            except Exception as e:
                if not isinstance(e, (MotDePasseRequis, MotDePasseIncorrect,
                                      conversion.ErreurConversion)):
                    traceback.print_exc()
                if erreur:
                    self._planifier(erreur, e)
                continue
            if rappel:
                self._planifier(rappel, resultat)

    # ------------------------------------------------------- ouverture
    @staticmethod
    def _infos_pages(doc):
        infos = []
        for p in doc:
            r = p.rect
            rot = p.rotation % 360
            l, h = (r.height, r.width) if rot in (90, 270) else (r.width, r.height)
            infos.append((round(l, 3), round(h, 3), rot))
        return infos

    def ouvrir(self, id_source, chemin, genre, reglages, mot_de_passe=None):
        """→ liste [(l, h, rotation)] des pages ; garde le document."""
        if genre == "pdf":
            try:
                doc = pymupdf.open(chemin)
            except Exception as e:
                raise conversion.ErreurConversion(
                    f"« {os.path.basename(chemin)} » n'est pas un PDF lisible.") from e
            if doc.needs_pass:
                if mot_de_passe is None:
                    raise MotDePasseRequis(chemin)
                if not doc.authenticate(mot_de_passe):
                    raise MotDePasseIncorrect(chemin)
            if not doc.is_pdf:
                doc = pymupdf.open("pdf", doc.convert_to_pdf())
        elif genre == "image":
            doc = conversion.image_vers_pdf(
                chemin, reglages["images_marges"],
                reglages["images_mode"] == "pleine", reglages["images_orientation_auto"])
        elif genre == "bureautique":
            raise conversion.ErreurConversion(
                f"« {os.path.basename(chemin)} » doit d'abord être exporté en PDF "
                "depuis son éditeur, puis déposé ici.")
        else:
            raise conversion.ErreurConversion(
                f"Format non pris en charge : « {os.path.basename(chemin)} ».")
        if doc.page_count == 0:
            raise conversion.ErreurConversion(
                f"« {os.path.basename(chemin)} » ne contient aucune page.")
        self.docs[id_source] = doc
        return self._infos_pages(doc)

    def liberer(self, ids):
        for i in ids:
            doc = self.docs.pop(i, None)
            if doc is not None:
                doc.close()
        for cle in [c for c in self._cache if c[0] in ids]:
            self._cache.pop(cle).close()

    # ------------------------------------------- construction d'une page
    def page_unique(self, page: Page) -> pymupdf.Document:
        """Document d'une seule page, opérations de zone appliquées,
        rotation 0. La rotation finale est posée par l'appelant."""
        cle = page.cle_contenu()
        doc = self._cache.get(cle)
        if doc is not None:
            self._cache.move_to_end(cle)
            return doc
        if page.blanche:
            doc = pymupdf.open()
            doc.new_page(width=page.blanche[0], height=page.blanche[1])
        else:
            doc = pymupdf.open()
            doc.insert_pdf(self.docs[page.source], from_page=page.index,
                           to_page=page.index)
            doc[0].set_rotation(0)
        for op in page.ops:
            doc = _appliquer(doc, op)
        self._cache[cle] = doc
        while len(self._cache) > self._cache_max:
            self._cache.popitem(last=False)[1].close()
        return doc

    def rotation_origine(self, page: Page) -> int:
        if page.blanche:
            return 0
        return self.docs[page.source][page.index].rotation % 360

    # ------------------------------------------------------------ rendu
    def rendre(self, page: Page, largeur_px: int, hauteur_px: int):
        """→ (largeur, hauteur, pas, octets RGB) tenant dans la boîte donnée."""
        rot = (self.rotation_origine(page) + page.rotation) % 360
        if page.brute:
            pg = self.docs[page.source][page.index]
            extra = page.rotation
        else:
            pg = self.page_unique(page)[0]
            extra = rot
        r = pg.rect   # rect affiché avec la rotation propre de pg
        l, h = (r.height, r.width) if extra in (90, 270) else (r.width, r.height)
        zoom = max(0.02, min(largeur_px / l, hauteur_px / h))
        pix = pg.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom).prerotate(extra),
                            alpha=False, annots=True)
        return pix.width, pix.height, pix.stride, bytes(pix.samples)

    # ----------------------------------------------------- enregistrement
    def construire(self, pages: list[Page], reglages: dict, sources_meta: dict):
        sortie = pymupdf.open()
        i = 0
        while i < len(pages):
            pg = pages[i]
            if pg.brute:
                # pages brutes consécutives d'une même source : un seul bloc
                j = i
                while (j + 1 < len(pages) and pages[j + 1].brute
                       and pages[j + 1].source == pg.source
                       and pages[j + 1].index == pages[j].index + 1):
                    j += 1
                debut = sortie.page_count
                sortie.insert_pdf(self.docs[pg.source], from_page=pg.index,
                                  to_page=pages[j].index)
                for k in range(i, j + 1):
                    if pages[k].rotation:
                        p = sortie[debut + k - i]
                        p.set_rotation((p.rotation + pages[k].rotation) % 360)
                i = j + 1
            else:
                rot = (self.rotation_origine(pg) + pg.rotation) % 360
                sortie.insert_pdf(self.page_unique(pg))
                sortie[-1].set_rotation(rot)
                i += 1

        if reglages.get("effacer_metadonnees"):
            sortie.set_metadata({})
            sortie.del_xml_metadata()
        else:
            meta = {}
            for pg in pages:
                if sources_meta.get(pg.source) == "pdf":
                    meta = dict(self.docs[pg.source].metadata or {})
                    break
            garde = {k: meta.get(k, "") for k in ("title", "author", "subject", "keywords")}
            garde["creator"] = "Maquette"
            garde["producer"] = ""
            sortie.set_metadata(garde)
        return sortie

    def construire_apercu(self, pages, reglages, sources_meta):
        """Construit le document final et le garde sous APERCU, pour le montrer.

        Même chemin que l'enregistrement, imposition comprise : l'aperçu
        montre donc le fichier tel qu'il sera écrit.
        """
        self.liberer([APERCU])
        sortie = self.construire(pages, reglages, sources_meta)
        if reglages.get("imposition", "fidele") != "fidele":
            sortie = imposer(sortie, reglages["imposition"])
        self.docs[APERCU] = sortie
        return self._infos_pages(sortie)

    def enregistrer(self, pages, chemin, reglages, sources_meta):
        """Écrit dans un fichier temporaire du même dossier puis le renomme :
        l'ancien fichier n'est remplacé qu'une fois le nouveau complet."""
        sortie = self.construire(pages, reglages, sources_meta)
        if reglages.get("imposition", "fidele") != "fidele":
            sortie = imposer(sortie, reglages["imposition"])
        if reglages.get("compresser", True):
            if reglages.get("reduire_images"):
                dpi = int(reglages.get("dpi_images", 150))
                try:
                    sortie.rewrite_images(dpi_threshold=int(dpi * 1.3), dpi_target=dpi,
                                          quality=82, bitonal=False)
                except Exception:
                    traceback.print_exc()
            options = dict(garbage=4, deflate=True, deflate_images=True,
                           deflate_fonts=True, clean=True, use_objstms=1)
        else:
            options = dict(garbage=1)
        dossier = os.path.dirname(os.path.abspath(chemin))
        fd, tmp = tempfile.mkstemp(dir=dossier, prefix=".maquette-", suffix=".pdf")
        os.close(fd)
        try:
            sortie.save(tmp, **options)
            sortie.close()
            try:
                mode = os.stat(chemin).st_mode & 0o777
            except OSError:
                mode = 0o666 & ~_umask()
            os.chmod(tmp, mode)
            os.replace(tmp, chemin)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        return os.path.getsize(chemin)


def _umask():
    m = os.umask(0)
    os.umask(m)
    return m


# ------------------------------------------------- opérations vectorielles

def _copie(doc):
    d = pymupdf.open()
    d.insert_pdf(doc)
    return d


def _retirer(doc, zones, blanc=False):
    """Retire réellement le contenu (texte, traits, pixels) des zones."""
    p = doc[0]
    o = p.rect.tl
    n = 0
    for z in zones:
        z = pymupdf.Rect(z) + (o.x, o.y, o.x, o.y)
        z = z & p.rect
        if z.is_empty or z.width < 0.5 or z.height < 0.5:
            continue
        p.add_redact_annot(z, fill=(1, 1, 1) if blanc else None)
        n += 1
    if n:
        p.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_PIXELS,
                           graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
                           text=pymupdf.PDF_REDACT_TEXT_REMOVE)
    return doc


def _hors(l, h, x0, y0, x1, y1):
    """Les (au plus) 4 rectangles de la page l×h situés hors de la zone."""
    return [(0, 0, l, y0), (0, y1, l, h), (0, y0, x0, y1), (x1, y0, l, y1)]


# Polices Unicode courantes sous GNOME ; la base 14 du PDF ne couvre que le
# latin-1 et perdrait les tirets cadratins et les guillemets typographiques.
POLICES = (
    "/usr/share/fonts/cantarell/Cantarell-Regular.otf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/TTF/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
)
NOM_POLICE = "maquette-texte"


@functools.cache
def fichier_police() -> str | None:
    return next((c for c in POLICES if os.path.exists(c)), None)


def _couleur(hexa: str):
    hexa = hexa.lstrip("#")
    return tuple(int(hexa[i:i + 2], 16) / 255 for i in (0, 2, 4))


MARGE_BAS = 18          # pt gardés sous un cadre de texte agrandi
CORPS_MINIMUM = 5       # pt


def _poser_texte(doc, op):
    """Écrit le texte dans son cadre.

    Le corps demandé est respecté tant que possible : le cadre est d'abord
    agrandi vers le bas de la page, et seul un texte qui déborde encore fait
    réduire le corps. Les essais ont lieu sur une page jetable, car
    insert_textbox dessine aussi la partie qui déborde : un essai raté sur la
    vraie page y laisserait un calque de texte coupé.
    """
    p = doc[0]
    o = p.rect.tl
    couleur = _couleur(op.couleur)
    fichier = fichier_police()
    nom = NOM_POLICE if fichier else "helv"
    if fichier:
        p.insert_font(fontname=nom, fontfile=fichier)

    tracee = pymupdf.Rect(op.x0, op.y0, op.x1, op.y1) + (o.x, o.y, o.x, o.y)
    agrandie = pymupdf.Rect(tracee.x0, tracee.y0, tracee.x1,
                            max(tracee.y1, p.rect.y1 - MARGE_BAS))

    brouillon = pymupdf.open()
    essai = brouillon.new_page(width=p.rect.width, height=p.rect.height)
    if fichier:
        essai.insert_font(fontname=nom, fontfile=fichier)

    def tient(zone, taille):
        return essai.insert_textbox(zone, op.contenu, fontsize=taille, fontname=nom,
                                    fontfile=fichier, render_mode=3,
                                    align=pymupdf.TEXT_ALIGN_LEFT) >= 0

    zone, corps = agrandie, CORPS_MINIMUM
    if tient(tracee, op.taille):
        zone, corps = tracee, op.taille
    else:
        taille = op.taille
        while taille >= CORPS_MINIMUM:
            if tient(agrandie, taille):
                corps = taille
                break
            taille -= 0.5
    brouillon.close()

    p.insert_textbox(zone, op.contenu, fontsize=corps, fontname=nom, fontfile=fichier,
                     color=couleur, align=pymupdf.TEXT_ALIGN_LEFT)
    return doc


def _appliquer(doc, op):
    if op.genre == TEXTE:
        return _poser_texte(doc, op)
    p = doc[0]
    l, h = p.rect.width, p.rect.height
    o = p.rect.tl
    if op.genre == EFFACER:
        return _retirer(doc, [(op.x0, op.y0, op.x1, op.y1)], blanc=True)

    if op.genre == ROGNER:
        x0, y0 = max(0, op.x0), max(0, op.y0)
        x1, y1 = min(l, op.x1), min(h, op.y1)
        if op.garder_format:
            return _retirer(doc, _hors(l, h, x0, y0, x1, y1), blanc=True)
        masque = _retirer(_copie(doc), _hors(l, h, x0, y0, x1, y1))
        nouveau = pymupdf.open()
        np_ = nouveau.new_page(width=x1 - x0, height=y1 - y0)
        np_.show_pdf_page(np_.rect, masque, 0,
                          clip=pymupdf.Rect(x0, y0, x1, y1) + (o.x, o.y, o.x, o.y))
        return nouveau

    if op.genre == SUPPRIMER:
        nouveau = pymupdf.open()
        if op.axe == "y":
            a, b = max(0, op.y0), min(h, op.y1)
            np_ = nouveau.new_page(width=l, height=h - (b - a))
            if a > 0.5:
                haut = _retirer(_copie(doc), [(0, a, l, h)])
                np_.show_pdf_page(pymupdf.Rect(0, 0, l, a), haut, 0,
                                  clip=pymupdf.Rect(0, 0, l, a) + (o.x, o.y, o.x, o.y))
            if h - b > 0.5:
                bas = _retirer(_copie(doc), [(0, 0, l, b)])
                np_.show_pdf_page(pymupdf.Rect(0, a, l, h - (b - a)), bas, 0,
                                  clip=pymupdf.Rect(0, b, l, h) + (o.x, o.y, o.x, o.y))
        else:
            a, b = max(0, op.x0), min(l, op.x1)
            np_ = nouveau.new_page(width=l - (b - a), height=h)
            if a > 0.5:
                gauche = _retirer(_copie(doc), [(a, 0, l, h)])
                np_.show_pdf_page(pymupdf.Rect(0, 0, a, h), gauche, 0,
                                  clip=pymupdf.Rect(0, 0, a, h) + (o.x, o.y, o.x, o.y))
            if l - b > 0.5:
                droite = _retirer(_copie(doc), [(0, 0, b, h)])
                np_.show_pdf_page(pymupdf.Rect(a, 0, l - (b - a), h), droite, 0,
                                  clip=pymupdf.Rect(b, 0, l, h) + (o.x, o.y, o.x, o.y))
        return nouveau
    raise ValueError(op.genre)


# ------------------------------------------------------- brochures et livrets

# Feuille d'impression de chaque disposition, en paysage.
FEUILLES = {
    "brochure-a5": (841.89, 595.28),    # A4 paysage : deux A5 côte à côte
    "livret-a4": (1190.55, 841.89),     # A3 paysage : deux A4 côte à côte
}


def ordre_livret(nombre: int) -> list[tuple[int | None, int | None]]:
    """Faces d'un cahier agrafé au centre : [(gauche, droite), …].

    Les pages sont complétées par des blanches jusqu'au multiple de 4, puis
    appariées pour que le pliage au centre rétablisse l'ordre de lecture.
    """
    total = (nombre + 3) // 4 * 4
    faces = []
    for i in range(total // 4):
        a, b, c, d = total - 1 - 2 * i, 2 * i, 2 * i + 1, total - 2 - 2 * i
        faces.append((a if a < nombre else None, b if b < nombre else None))
        faces.append((c if c < nombre else None, d if d < nombre else None))
    return faces


def imposer(doc: pymupdf.Document, mode: str) -> pymupdf.Document:
    """Place deux pages par face, dans l'ordre d'impression recto verso."""
    largeur, hauteur = FEUILLES[mode]
    sortie = pymupdf.open()
    moities = (pymupdf.Rect(0, 0, largeur / 2, hauteur),
               pymupdf.Rect(largeur / 2, 0, largeur, hauteur))
    for face in ordre_livret(doc.page_count):
        feuille = sortie.new_page(width=largeur, height=hauteur)
        for moitie, numero in zip(moities, face):
            if numero is None:
                continue
            source = doc[numero]
            r = source.rect
            sl, sh = (r.height, r.width) if source.rotation in (90, 270) else (r.width, r.height)
            echelle = min(moitie.width / sl, moitie.height / sh)
            l, h = sl * echelle, sh * echelle
            cible = pymupdf.Rect(0, 0, l, h) + (moitie.x0 + (moitie.width - l) / 2,
                                                (hauteur - h) / 2,
                                                moitie.x0 + (moitie.width - l) / 2,
                                                (hauteur - h) / 2)
            feuille.show_pdf_page(cible, doc, numero, rotate=source.rotation)
    doc.close()
    return sortie
