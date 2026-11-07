"""Calculs sans interface : texte des appréciations, répartition des suivis PFMP."""

from __future__ import annotations

from fractions import Fraction

# ----------------------------------------------------------------- appréciations

SEPARATEURS = [", ", " : ", " – ", " "]


def prefixe(prenom: str, separateur: str = ", ") -> str:
    prenom = (prenom or "").strip()
    return f"{prenom}{separateur}" if prenom else ""


def developper(phrase: str, prenom: str, nom: str = "") -> str:
    """Remplace {prénom} (ou {prenom}) et {nom} dans une phrase de la banque."""
    for var in ("{prénom}", "{prenom}", "{Prénom}", "{Prenom}"):
        phrase = phrase.replace(var, prenom)
    return phrase.replace("{nom}", nom).replace("{NOM}", nom.upper())


def ajuster_insertion(avant: str, phrase: str, prenom: str = "") -> str:
    """Adapte une phrase insérée au texte qui précède le curseur :
    - après « Léa, » ou juste après le prénom seul (« Léa ») la majuscule initiale
      passe en minuscule (sauf nom propre) : « Léa très bon trimestre » ;
    - une espace est ajoutée si le texte précédent n'en finit pas par une."""
    s = phrase.strip()
    if not s:
        return ""
    fin = avant.rstrip(" ")
    apres_prenom = bool(prenom) and fin.strip() == prenom.strip()
    if ((fin.endswith(",") or apres_prenom) and len(s) > 1 and s[0].isupper() and s[1].islower()
            and not (prenom and s.startswith(prenom))):
        s = s[0].lower() + s[1:]
    if avant and not avant.endswith((" ", "\n", "\t")):
        s = " " + s
    return s


def valeur_sans_prefixe_seul(texte: str, pref: str) -> str:
    """Un texte réduit au préfixe automatique (« Léa, ») compte comme vide."""
    if pref and texte.strip() == pref.strip():
        return ""
    return texte


# --------------------------------------------------------------- répartition

def en_fraction(heures) -> Fraction:
    return Fraction(str(heures)) if heures else Fraction(0)


def repartir(heures: dict, nb_eleves: int) -> dict:
    """{cle: heures} -> {cle: Fraction} ; élèves suivis = heures ÷ total × nb_eleves.
    Calcul exact (fractions), sans arrondi."""
    h = {k: en_fraction(v) for k, v in heures.items() if v and v > 0}
    total = sum(h.values(), Fraction(0))
    if total == 0:
        return {k: Fraction(0) for k in h}
    return {k: v / total * nb_eleves for k, v in h.items()}


def une_decimale(f: Fraction) -> str:
    """Valeur à une décimale, arrondie au plus proche (demi vers le haut), virgule française."""
    dixiemes = (f * 10 + Fraction(1, 2)).__floor__()
    ent, dec = divmod(dixiemes, 10)
    return f"{ent},{dec}"


def format_quota(f: Fraction) -> str:
    """« 8 », « 4,5 » (valeurs exactes) ou « 14/3 ≈ 4,7 » (fraction exacte et valeur approchée)."""
    if f.denominator == 1:
        return str(f.numerator)
    if (f * 10).denominator == 1:
        return une_decimale(f)
    return f"{f.numerator}/{f.denominator} ≈ {une_decimale(f)}"


def format_heures(h) -> str:
    if h is None:
        return "—"
    s = f"{float(h):g}".replace(".", ",")
    return f"{s} h"
