# SPDX-License-Identifier: GPL-3.0-or-later
"""Réserve de pochettes, rangées par genre.

Les images sont dans ~/.local/share/disquaire/reserve/, une par fichier,
nommées d'après le genre : « Jazz.jpg », « Reggae.jpg », « Électro 2.jpg »…
"""

from __future__ import annotations

import os
import re

from gi.repository import Gio, GLib

from . import covers, tags, textfmt
from .model import natural_key

DIR = os.path.join(GLib.get_user_data_dir(), "disquaire", "reserve")
_EXTS = (".jpg", ".jpeg", ".png")
_cache: dict[str, tuple[float, tags.Cover]] = {}
_listing: tuple[float, list[tuple[str, str]]] | None = None


def _ensure_dir() -> None:
    os.makedirs(DIR, exist_ok=True)


def entries() -> list[tuple[str, str]]:
    """[(nom, chemin)] triés ; relu seulement si le dossier a changé."""
    global _listing
    try:
        mtime = os.stat(DIR).st_mtime
    except OSError:
        return []
    if _listing and _listing[0] == mtime:
        return _listing[1]
    out = []
    for name in os.listdir(DIR):
        stem, ext = os.path.splitext(name)
        if ext.lower() in _EXTS and not name.startswith("."):
            out.append((stem, os.path.join(DIR, name)))
    out.sort(key=lambda e: natural_key(e[0]))
    _listing = (mtime, out)
    return out


def load(path: str) -> tags.Cover | None:
    try:
        mtime = os.stat(path).st_mtime
    except OSError:
        return None
    hit = _cache.get(path)
    if hit and hit[0] == mtime:
        return hit[1]
    try:
        with open(path, "rb") as fh:
            cover = covers.prepare(fh.read())
    except (OSError, covers.CoverError):
        return None
    _cache[path] = (mtime, cover)
    return cover


def clean_name(name: str) -> str:
    name = textfmt.clean_spaces(name.replace(os.sep, "-")).strip(" .")
    return name[:80]


def path_for(name: str) -> str:
    return os.path.join(DIR, clean_name(name) + ".jpg")


def add(name: str, cover: tags.Cover) -> str:
    """Enregistre (ou remplace) la pochette `name`."""
    name = clean_name(name)
    if not name:
        raise covers.CoverError("Nom invalide.")
    _ensure_dir()
    path = path_for(name)
    for ext in _EXTS:  # remplace aussi une ancienne version .png
        other = os.path.join(DIR, name + ext)
        if other != path and os.path.exists(other):
            os.remove(other)
    data = covers.as_jpeg(covers.prepare(cover.data))
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, path)
    return path


def rename(path: str, new_name: str) -> str:
    new_name = clean_name(new_name)
    if not new_name:
        raise covers.CoverError("Nom invalide.")
    dest = os.path.join(DIR, new_name + os.path.splitext(path)[1].lower())
    if os.path.exists(dest) and os.path.normcase(dest) != os.path.normcase(path):
        raise covers.CoverError("Une pochette porte déjà ce nom.")
    os.rename(path, dest)
    return dest


def remove(path: str) -> None:
    try:
        Gio.File.new_for_path(path).trash(None)
    except GLib.Error:
        os.remove(path)


def _key(name: str) -> str:
    # « Jazz 2 » et « Jazz » vont avec le même genre.
    return textfmt.match_key(re.sub(r"\s*\(?\d+\)?$", "", name))


def for_genre(genre: str) -> tuple[str, str] | None:
    """La pochette de la réserve qui correspond au genre, ou None."""
    parts = [textfmt.match_key(g) for g in re.split(r"[;,/]", genre) if g.strip()]
    if not parts:
        return None
    items = [(name, path, _key(name)) for name, path in entries()]
    for part in parts:                      # nom identique au genre
        for name, path, key in items:
            if key and key == part:
                return name, path
    for part in parts:                      # « Jazz » pour « Jazz Vocal »
        for name, path, key in items:
            if key and (f" {key} " in f" {part} " or f" {part} " in f" {key} "):
                return name, path
    return None
