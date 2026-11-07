# SPDX-License-Identifier: GPL-3.0-or-later
"""Index des tags de toute la discothèque, pour la recherche globale.

L'index est gardé en cache (~/.cache/disquaire/index.json) : seuls les
fichiers nouveaux ou modifiés depuis la dernière fois sont relus.
"""

from __future__ import annotations

import json
import os
import threading

from gi.repository import GLib
from mutagen import File as MutagenFile

from . import textfmt
from .duplicates import list_audio

_CACHE_DIR = os.path.join(GLib.get_user_cache_dir(), "disquaire")
_CACHE = os.path.join(_CACHE_DIR, "index.json")
_FIELDS = ("artist", "title", "album", "genre", "date")
_ID3 = {"artist": "TPE1", "title": "TIT2", "album": "TALB", "genre": "TCON", "date": "TDRC"}


def _read(path: str) -> dict:
    rec = {k: "" for k in _FIELDS}
    try:
        audio = MutagenFile(path)
    except Exception:
        return rec
    rec["length"] = round(getattr(getattr(audio, "info", None), "length", 0) or 0)
    tags = getattr(audio, "tags", None)
    if tags is None:
        return rec
    flac = path.lower().endswith(".flac")
    for key in _FIELDS:
        try:
            if flac:
                value = tags.get(key.upper()) or tags.get(key)
            else:
                frame = tags.get(_ID3[key])
                value = (frame.genres if key == "genre" else frame.text) if frame else None
        except (KeyError, ValueError, AttributeError):
            value = None
        if value:
            rec[key] = "; ".join(str(v) for v in value)
    return rec


class LibraryIndex:
    def __init__(self):
        self._lock = threading.Lock()
        self._entries: dict[str, dict] = {}
        self._root: str | None = None
        self._loaded_cache = False

    def _load_cache(self):
        if self._loaded_cache:
            return
        self._loaded_cache = True
        try:
            with open(_CACHE, encoding="utf-8") as fh:
                self._entries = json.load(fh)
        except (OSError, ValueError):
            self._entries = {}

    def _save_cache(self):
        try:
            os.makedirs(_CACHE_DIR, exist_ok=True)
            tmp = _CACHE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self._entries, fh, ensure_ascii=False)
            os.replace(tmp, _CACHE)
        except OSError:
            pass

    def update(self, root: str, progress=None, should_stop=lambda: False) -> None:
        """Met l'index à jour pour `root` (à appeler hors du thread GTK)."""
        with self._lock:
            self._load_cache()
            paths = list_audio(root)
            fresh: dict[str, dict] = {}
            dirty = False
            for i, path in enumerate(paths):
                if should_stop():
                    return
                try:
                    mtime = os.stat(path).st_mtime
                except OSError:
                    continue
                old = self._entries.get(path)
                if old and old.get("mtime") == mtime:
                    fresh[path] = old
                    continue
                rec = _read(path)
                rec["mtime"] = mtime
                fresh[path] = rec
                dirty = True
                if progress and i % 50 == 0:
                    progress(i, len(paths))
            # On garde les entrées des autres dossiers de base éventuels.
            prefix = root.rstrip(os.sep) + os.sep
            for path, rec in self._entries.items():
                if not path.startswith(prefix) and path not in fresh:
                    fresh[path] = rec
            if dirty or len(fresh) != len(self._entries):
                self._entries = fresh
                self._save_cache()
            else:
                self._entries = fresh
            self._root = root

    def forget(self, path: str) -> None:
        with self._lock:
            self._entries.pop(path, None)

    def search(self, root: str, query: str, limit: int = 500) -> list[str]:
        words = textfmt.match_key(query).split()
        if not words:
            return []
        prefix = root.rstrip(os.sep) + os.sep
        hits = []
        with self._lock:
            for path, rec in self._entries.items():
                if not path.startswith(prefix):
                    continue
                hay = textfmt.match_key(" ".join(
                    [os.path.basename(path)] + [rec.get(k, "") for k in _FIELDS]))
                if all(w in hay for w in words):
                    hits.append(path)
        hits.sort(key=lambda p: textfmt.match_key(os.path.basename(p)))
        return hits[:limit]


INDEX = LibraryIndex()
