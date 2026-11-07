"""Distances entre l'établissement et les lieux de stage (à vol d'oiseau).

Les adresses sont localisées à la demande par Nominatim (OpenStreetMap), puis
gardées dans la table « geocache » de la base : une adresse n'est demandée
qu'une fois. Seules des adresses d'entreprises et celle de l'établissement
quittent la machine, jamais un nom d'élève. Ce module ne dépend pas de GTK ;
la partie réseau (localiser) est appelée depuis un fil d'exécution séparé et
ne touche pas à la base, qui reste dans le fil principal.
"""

from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request

from .db import maintenant, normaliser

URL = "https://nominatim.openstreetmap.org/search"
AGENT = "Livret/1.1 (application de bureau GNOME, usage personnel)"
DELAI = 1.1  # Nominatim : au plus une requête par seconde
REGLAGE_ETABLISSEMENT = "adresse_etablissement"


def cle(adresse: str) -> str:
    return " ".join(normaliser(adresse).split())


def haversine(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distance en km entre deux points (lat, lon), à vol d'oiseau."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def localiser(adresse: str, ouvrir=urllib.request.urlopen, pays="fr"):
    """(lat, lon) de l'adresse, None si introuvable. Lève OSError si le réseau échoue."""
    requete = urllib.request.Request(
        f"{URL}?{urllib.parse.urlencode({'q': adresse, 'format': 'jsonv2', 'limit': 1, 'countrycodes': pays})}",
        headers={"User-Agent": AGENT, "Accept-Language": "fr"})
    with ouvrir(requete, timeout=15) as rep:
        donnees = json.loads(rep.read().decode("utf-8"))
    if not donnees:
        return None
    return float(donnees[0]["lat"]), float(donnees[0]["lon"])


def localiser_tout(adresses, ouvrir=urllib.request.urlopen, attendre=time.sleep, signaler=None):
    """{adresse: (lat, lon) | None} ; s'arrête à la première panne réseau
    (renvoie alors aussi l'erreur)."""
    res, erreur = {}, None
    for i, a in enumerate(adresses):
        if i:
            attendre(DELAI)
        try:
            res[a] = localiser(a, ouvrir)
        except (OSError, ValueError, KeyError) as e:
            erreur = e
            break
        if signaler:
            signaler(i + 1, len(adresses))
    return res, erreur


# ------------------------------------------------------------------ cache

def en_cache(base, adresse):
    """(lat, lon), None si connue introuvable, False si jamais demandée."""
    r = base._un("SELECT lat, lon FROM geocache WHERE adresse = ?", (cle(adresse),))
    if r is None:
        return False
    if r["lat"] is None:
        return None
    return r["lat"], r["lon"]


def memoriser(base, adresse, coord):
    base._x("INSERT OR REPLACE INTO geocache (adresse, lat, lon, maj_le) VALUES (?,?,?,?)",
            (cle(adresse), coord[0] if coord else None, coord[1] if coord else None, maintenant()))


def oublier(base, adresse):
    base._x("DELETE FROM geocache WHERE adresse = ?", (cle(adresse),))


def etablissement(base) -> str:
    return (base.reglage(REGLAGE_ETABLISSEMENT) or "").strip()


def a_localiser(base, adresses) -> list[str]:
    """Adresses (établissement compris) qui ne sont pas encore dans le cache."""
    vues, res = set(), []
    for a in [etablissement(base), *adresses]:
        a = (a or "").strip()
        if a and cle(a) not in vues and en_cache(base, a) is False:
            vues.add(cle(a))
            res.append(a)
    return res


def distance_km(base, adresse):
    """Distance établissement → adresse, à vol d'oiseau, d'après le cache ; None si inconnue."""
    depart = etablissement(base)
    if not depart or not (adresse or "").strip():
        return None
    a, b = en_cache(base, depart), en_cache(base, adresse)
    if not a or not b:
        return None
    return haversine(a, b)


def format_km(km) -> str:
    if km is None:
        return ""
    return f"{km:.1f} km".replace(".", ",") if km < 100 else f"{km:.0f} km"
