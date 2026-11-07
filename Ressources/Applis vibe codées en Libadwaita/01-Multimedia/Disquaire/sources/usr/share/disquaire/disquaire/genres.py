# SPDX-License-Identifier: GPL-3.0-or-later
"""Liste des genres proposés (éditable), dans ~/.config/disquaire/genres.txt."""

from __future__ import annotations

import os

from gi.repository import GLib

from . import textfmt

PATH = os.path.join(GLib.get_user_config_dir(), "disquaire", "genres.txt")

DEFAULT = [
    "Abstract Hip-Hop", "Bossa Nova", "Chanson Française", "Chants Révolutionnaires",
    "Chiptune", "Cumbia", "Dance", "Dessin Animé", "Discours", "Drum & Bass", "Dubstep",
    "Electro Cumbia", "Electro Dub", "Electro Reggae", "Electro Swing", "Electronica",
    "Folk", "Fusion", "Grunge", "Hardcore", "HardTek", "Hip-Hop", "House", "Jazz", "Metal",
    "Musique Classique", "Musiques du Monde", "New Wave", "Pop", "Punk", "R&B", "Reggae",
    "Reggae Dub", "Reggae Ska", "Rock", "Rock Alternatif", "Techno", "Trance", "Trip-Hop",
]


def _sort(items):
    return sorted(items, key=textfmt.match_key)


def load() -> list[str]:
    try:
        with open(PATH, encoding="utf-8") as fh:
            items = [line.strip() for line in fh if line.strip()]
        return _sort(dict.fromkeys(items))
    except OSError:
        return list(DEFAULT)


def save(items) -> None:
    items = _sort(dict.fromkeys(i.strip() for i in items if i.strip()))
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH + ".tmp", "w", encoding="utf-8") as fh:
        fh.write("\n".join(items) + "\n")
    os.replace(PATH + ".tmp", PATH)


def canonical(genre: str, items=None) -> str | None:
    """Le genre de la liste qui correspond (accents, casse, tirets ignorés)."""
    key = textfmt.match_key(genre).replace(" ", "")
    for g in items if items is not None else load():
        if textfmt.match_key(g).replace(" ", "") == key:
            return g
    return None


def suggest(text: str, items=None, limit: int = 12) -> list[str]:
    """Genres de la liste qui contiennent ce qui est tapé (dernier genre après « ; »)."""
    part = textfmt.match_key(text.split(";")[-1])
    items = items if items is not None else load()
    if not part:
        return items[:limit]
    starts = [g for g in items if textfmt.match_key(g).startswith(part)]
    inside = [g for g in items if part in textfmt.match_key(g) and g not in starts]
    return (starts + inside)[:limit]
