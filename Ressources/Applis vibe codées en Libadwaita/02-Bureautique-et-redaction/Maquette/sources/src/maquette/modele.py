"""Modèle du document en cours : pages, sources, géométrie.

Rien ici ne touche PyMuPDF ni GTK : ce sont des données pures, immuables,
pour que l'historique (annuler/rétablir) se résume à garder des tuples.

Repères géométriques
--------------------
- Les dimensions sont en points PDF (1/72 de pouce).
- « Non tourné » : la page telle qu'elle est dessinée, avant son /Rotate.
- Les opérations de zone (effacer, supprimer un passage, rogner) sont
  exprimées dans l'espace non tourné de la page *intermédiaire*, c'est-à-dire
  la page obtenue après les opérations précédentes, origine en haut à gauche.
- La rotation affichée = rotation d'origine de la page + rotation ajoutée.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field, replace

_uid = itertools.count(1)
_sid = itertools.count(1)


def nouvel_uid() -> int:
    return next(_uid)


def nouvel_id_source() -> int:
    return next(_sid)


# ---------------------------------------------------------------- opérations

# Les trois issues du recadrage, et la pose de texte.
EFFACER = "effacer"        # la zone est vidée, la page garde son format
SUPPRIMER = "supprimer"    # la bande est retirée, la suite de la page remonte
ROGNER = "rogner"          # on ne garde que la zone, la page s'y réduit
TEXTE = "texte"            # bloc de texte posé sur la page

# Libellés des trois issues, pour l'interface et les messages.
ISSUES_RECADRAGE = (
    (ROGNER, "Garder cette zone",
     "La page est réduite à la zone tracée ; tout le reste est retiré du fichier."),
    (EFFACER, "Vider cette zone",
     "La zone est vidée et devient blanche ; la page garde son format."),
    (SUPPRIMER, "Retirer cette zone et réduire la page",
     "La bande est retirée et la suite de la page remonte pour combler le vide."),
)


@dataclass(frozen=True)
class Op:
    genre: str
    x0: float
    y0: float
    x1: float
    y1: float
    # SUPPRIMER : axe de la bande retirée ('y' : bande horizontale, la suite
    # remonte ; 'x' : bande verticale, la suite se décale vers la gauche).
    axe: str = "y"
    # ROGNER : True = la page garde son format, seule la zone reste visible.
    garder_format: bool = False
    # TEXTE : contenu posé dans le rectangle, et sa mise en forme.
    contenu: str = ""
    taille: float = 12.0
    couleur: str = "#000000"

    @property
    def largeur(self) -> float:
        return self.x1 - self.x0

    @property
    def hauteur(self) -> float:
        return self.y1 - self.y0


# --------------------------------------------------------------------- pages

@dataclass(frozen=True)
class Page:
    uid: int
    source: int | None          # id de la source ; None = page blanche
    index: int = 0              # numéro de page dans la source
    rotation: int = 0           # rotation ajoutée : 0, 90, 180, 270
    ops: tuple = ()             # tuple d'Op, appliquées dans l'ordre
    blanche: tuple | None = None  # (largeur, hauteur) d'une page blanche

    @property
    def brute(self) -> bool:
        """Page source sans opération de zone (la rotation est à part)."""
        return self.source is not None and not self.ops

    @property
    def modifiee(self) -> bool:
        return bool(self.rotation or self.ops or self.blanche)

    def cle_contenu(self):
        """Ce qui détermine le dessin de la page, rotation ajoutée exclue."""
        return (self.source, self.index, self.ops, self.blanche)

    def cle_rendu(self):
        return (self.cle_contenu(), self.rotation)

    def copie(self, **changements) -> "Page":
        """Copie avec un nouvel uid (page dupliquée ou réinsérée)."""
        changements.setdefault("uid", nouvel_uid())
        return replace(self, **changements)


@dataclass
class Source:
    """Un fichier ouvert ou converti. Le document PyMuPDF vit dans le moteur."""
    id: int
    nom: str                     # nom affiché (nom du fichier)
    chemin: str                  # fichier d'origine choisi par l'utilisateur
    genre: str                   # 'pdf' | 'image' | 'document'
    pages: list = field(default_factory=list)   # [(l, h, rotation_origine)]
    couleur: int = 0

    @property
    def convertie(self) -> bool:
        return self.genre != "pdf"


# ---------------------------------------------------------------- géométrie

def base(page: Page, sources: dict) -> tuple[float, float, int]:
    """(largeur, hauteur) non tournées et rotation d'origine."""
    if page.blanche:
        return page.blanche[0], page.blanche[1], 0
    return sources[page.source].pages[page.index]


def taille_intermediaire(page: Page, sources: dict, jusqua: int | None = None):
    """Taille non tournée après les opérations (ou les `jusqua` premières)."""
    l, h, _ = base(page, sources)
    ops = page.ops if jusqua is None else page.ops[:jusqua]
    for op in ops:
        if op.genre == TEXTE:
            continue
        if op.genre == SUPPRIMER:
            if op.axe == "y":
                h -= op.hauteur
            else:
                l -= op.largeur
        elif op.genre == ROGNER and not op.garder_format:
            l, h = op.largeur, op.hauteur
    return max(l, 1.0), max(h, 1.0)


def rotation_totale(page: Page, sources: dict) -> int:
    return (base(page, sources)[2] + page.rotation) % 360


def taille_affichee(page: Page, sources: dict):
    l, h = taille_intermediaire(page, sources)
    if rotation_totale(page, sources) in (90, 270):
        return h, l
    return l, h


def vers_non_tourne(u: float, v: float, l: float, h: float, r: int):
    """Point affiché (u, v) → point non tourné (x, y).

    l, h : taille non tournée ; r : rotation totale (sens horaire, comme
    /Rotate). Vérifié contre Page.rotation_matrix de PyMuPDF dans les tests.
    """
    if r == 90:
        return v, h - u
    if r == 180:
        return l - u, h - v
    if r == 270:
        return l - v, u
    return u, v


def zone_depuis_affichage(page: Page, sources: dict, genre: str,
                          fu0, fv0, fu1, fv1, garder_format=False, **mise_en_forme) -> Op | None:
    """Rectangle tracé à l'écran (fractions 0..1 de la page affichée) → Op."""
    l, h = taille_intermediaire(page, sources)
    r = rotation_totale(page, sources)
    dl, dh = (h, l) if r in (90, 270) else (l, h)
    fu0, fu1 = sorted((min(max(fu0, 0.0), 1.0), min(max(fu1, 0.0), 1.0)))
    fv0, fv1 = sorted((min(max(fv0, 0.0), 1.0), min(max(fv1, 0.0), 1.0)))
    if genre == SUPPRIMER:          # bande horizontale à l'écran, toute largeur
        fu0, fu1 = 0.0, 1.0
    a = vers_non_tourne(fu0 * dl, fv0 * dh, l, h, r)
    b = vers_non_tourne(fu1 * dl, fv1 * dh, l, h, r)
    x0, x1 = sorted((a[0], b[0]))
    y0, y1 = sorted((a[1], b[1]))
    axe = "y" if r in (0, 180) else "x"
    if genre == SUPPRIMER:
        if axe == "y":
            x0, x1 = 0.0, l
            if y1 - y0 >= h - 2:
                return None
        else:
            y0, y1 = 0.0, h
            if x1 - x0 >= l - 2:
                return None
    if x1 - x0 < 2 or y1 - y0 < 2:
        return None
    return Op(genre, round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2),
              axe=axe, garder_format=garder_format, **mise_en_forme)


# ------------------------------------------------------------ formats papier

A4 = (595.28, 841.89)
A3 = (841.89, 1190.55)

FORMATS_BLANCS = {
    "a4-portrait": A4,
    "a4-paysage": (A4[1], A4[0]),
    "a3-portrait": A3,
    "a3-paysage": (A3[1], A3[0]),
}
