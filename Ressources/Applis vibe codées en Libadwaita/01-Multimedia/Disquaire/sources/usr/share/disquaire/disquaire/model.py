# SPDX-License-Identifier: GPL-3.0-or-later
"""Modèle d'un morceau et chargement des tags en arrière-plan."""

from __future__ import annotations

import hashlib
import os
import re
import threading

import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, GLib, GObject  # noqa: E402

from . import covers, tags  # noqa: E402

THUMB_SIZE = 96
THUMB_DIR = os.path.join(GLib.get_user_cache_dir(), "disquaire", "thumbs")


def _thumb_cache_path(path: str) -> str | None:
    try:
        st = os.stat(path)
    except OSError:
        return None
    key = f"{path}\0{st.st_mtime_ns}\0{st.st_size}".encode("utf-8", "surrogateescape")
    return os.path.join(THUMB_DIR, hashlib.sha1(key).hexdigest() + ".png")


def cached_thumbnail(path: str, cover_data: bytes | None) -> bytes | None:
    """Miniature de la pochette, gardée sur le disque d'un lancement à l'autre."""
    if not cover_data:
        return None
    cache = _thumb_cache_path(path)
    if cache:
        try:
            with open(cache, "rb") as fh:
                return fh.read()
        except OSError:
            pass
    png = make_thumbnail_png(cover_data)
    if png and cache:
        try:
            os.makedirs(THUMB_DIR, exist_ok=True)
            with open(cache + ".tmp", "wb") as fh:
                fh.write(png)
            os.replace(cache + ".tmp", cache)
        except OSError:
            pass
    return png


def sibling_lrc(path: str) -> str | None:
    """Paroles d'un fichier .lrc (ou .txt) de même nom à côté du morceau."""
    from .lyrics import lrc_to_text
    stem = os.path.splitext(path)[0]
    for ext in (".lrc", ".LRC"):
        try:
            with open(stem + ext, encoding="utf-8", errors="replace") as fh:
                text = lrc_to_text(fh.read())
            if text:
                return text
        except OSError:
            continue
    return None


def natural_key(name: str):
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", name.casefold())]


def list_audio_files(folder: str) -> list[str]:
    try:
        with os.scandir(folder) as it:
            paths = [
                e.path for e in it
                if not e.name.startswith(".") and tags.is_audio(e.name)
                and e.is_file()
            ]
    except OSError:
        return []
    paths.sort(key=lambda p: natural_key(os.path.basename(p)))
    return paths


def make_thumbnail_png(data: bytes, size: int = THUMB_SIZE) -> bytes | None:
    """Réduit une pochette en PNG carré-ish (exécuté hors du thread GTK)."""
    try:
        loader = GdkPixbuf.PixbufLoader()

        def on_size(ldr, w, h):
            scale = size / max(1, min(w, h))
            if scale < 1:
                ldr.set_size(max(1, round(w * scale)), max(1, round(h * scale)))

        loader.connect("size-prepared", on_size)
        loader.write(data)
        loader.close()
        pixbuf = loader.get_pixbuf()
        if pixbuf is None:
            return None
        ok, buf = pixbuf.save_to_bufferv("png", [], [])
        return bytes(buf) if ok else None
    except GLib.Error:
        return None


def texture_from_bytes(data: bytes | None):
    if not data:
        return None
    try:
        return Gdk.Texture.new_from_bytes(GLib.Bytes.new(data))
    except GLib.Error:
        return None


class Track(GObject.Object):
    __gtype_name__ = "DisquaireTrack"
    __gsignals__ = {
        # émis à chaque changement de valeur (saisie, chargement, annulation…)
        "values-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    checked = GObject.Property(type=bool, default=False)
    dirty = GObject.Property(type=bool, default=False)
    loaded = GObject.Property(type=bool, default=False)
    display_title = GObject.Property(type=str, default="")
    display_subtitle = GObject.Property(type=str, default="")
    display_filename = GObject.Property(type=str, default="")
    has_lyrics = GObject.Property(type=bool, default=False)   # paroles enregistrées
    thumbnail = GObject.Property(type=Gdk.Paintable)

    def __init__(self, path: str):
        super().__init__()
        self.path = path
        self.saved = tags.TagValues()
        self.values = tags.TagValues()
        self.info = tags.AudioInfo(format="FLAC" if tags.is_flac(path) else "MP3")
        self.extras: list[str] = []
        self.error: str | None = None
        self.pending_cover: tags.Cover | None = None  # pochette réduite à 1024 px
        self._update()

    # --- propriétés pratiques ---------------------------------------------
    @property
    def name(self) -> str:
        return os.path.basename(self.path)

    @property
    def stem(self) -> str:
        return os.path.splitext(self.name)[0]

    @property
    def folder(self) -> str:
        return os.path.dirname(self.path)

    @property
    def is_flac(self) -> bool:
        return tags.is_flac(self.path)

    # --- mises à jour -----------------------------------------------------
    def apply_report(self, report: tags.TagReport, thumb_png: bytes | None,
                     resized: tags.Cover | None = None, big=None):
        self.saved = report.values
        self.values = report.values.copy()
        self.info = report.info
        self.extras = list(report.extras)
        self.pending_cover = resized
        if resized is not None:
            self.values.cover = resized
            self.extras.append(f"Pochette {big[0]}×{big[1]} (réduite à 1024 px)")
        self.error = None
        self.thumbnail = texture_from_bytes(thumb_png)
        self.loaded = True
        self._update()

    def apply_error(self, message: str):
        self.error = message
        self.loaded = True
        self._update()

    def set_value(self, key: str, value) -> None:
        if self.values.get(key) == value:
            return
        self.values.set(key, value)
        self._update()

    def revert(self) -> None:
        self.values = self.saved.copy()
        if self.pending_cover is not None:
            self.values.cover = self.pending_cover
        self._update()

    @property
    def edited(self) -> bool:
        """Vrai si l'utilisateur a modifié une valeur (hors nettoyage)."""
        expected = self.saved
        if self.pending_cover is not None:
            expected = self.saved.copy()
            expected.cover = self.pending_cover
        return self.values != expected

    def apply_lyrics_saved(self, text: str) -> None:
        """Paroles écrites dans le fichier par la file d'attente."""
        self.saved.lyrics = text
        if not self.values.lyrics.strip():
            self.values.lyrics = text
        self._update()

    def mark_saved(self, values: tags.TagValues, thumb_png: bytes | None,
                   cover_changed: bool) -> None:
        self.saved = values.copy()
        self.extras = []
        self.pending_cover = None
        if cover_changed:
            self.thumbnail = texture_from_bytes(thumb_png)
        self._update()

    def set_path(self, path: str) -> None:
        self.path = path
        self._update()

    def _update(self) -> None:
        self.emit("values-changed")
        dirty = bool(self.loaded and self.error is None
                     and (self.values != self.saved or self.extras))
        if dirty != self.dirty:
            self.dirty = dirty
        v = self.values
        title = v.title.strip() or self.stem
        parts = [p for p in (v.artist.strip(), v.album.strip()) if p]
        if self.error:
            subtitle = self.error
        elif not self.loaded:
            subtitle = "Lecture…"
        else:
            subtitle = " — ".join(parts) if parts else "Sans artiste ni album"
        if title != self.display_title:
            self.display_title = title
        if subtitle != self.display_subtitle:
            self.display_subtitle = subtitle
        if self.name != self.display_filename:
            self.display_filename = self.name
        has = bool(self.loaded and self.saved.lyrics.strip())
        if has != self.has_lyrics:
            self.has_lyrics = has


class TagLoader:
    """Lit les tags d'une liste de morceaux dans un thread.

    Les résultats sont renvoyés dans le thread GTK via `callback(track,
    report, thumb_png, error)`. Un nouvel appel à `start()` invalide les
    résultats du précédent.
    """

    def __init__(self, callback, auto_clean=lambda: True):
        self._callback = callback
        self._auto_clean = auto_clean
        self._generation = 0
        self._lock = threading.Lock()

    def cancel(self) -> None:
        with self._lock:
            self._generation += 1

    def start(self, tracks: list[Track], invalidate: bool = True) -> None:
        if invalidate:
            self.cancel()
        with self._lock:
            gen = self._generation
        items = [(t, t.path) for t in tracks]
        threading.Thread(target=self._run, args=(gen, items), daemon=True).start()

    def _run(self, gen: int, items) -> None:
        for track, path in items:
            with self._lock:
                if gen != self._generation:
                    return
            try:
                report = tags.read(path)
                resized = big = None
                if report.values.cover is not None:
                    big = covers.is_too_big(report.values.cover)
                    if big:
                        try:
                            resized = covers.prepare(report.values.cover.data)
                        except covers.CoverError:
                            big = None
                lrc = None if report.values.lyrics.strip() else sibling_lrc(path)
                if lrc:
                    report.extras.append("Paroles du fichier .lrc à intégrer")
                if (report.extras or resized) and self._auto_clean():
                    # Nettoyage automatique : les tags superflus sont supprimés
                    # tout de suite, sans attendre un enregistrement.
                    cleaned = report.values.copy()
                    if resized is not None:
                        cleaned.cover = resized
                    if lrc:
                        cleaned.lyrics = lrc
                    try:
                        tags.write(path, cleaned)
                        report.values, report.extras = cleaned, []
                        resized = big = lrc = None
                    except tags.TagError:
                        pass   # fichier protégé : il reste « à nettoyer »
                if lrc:
                    report.values.lyrics = lrc
                    report.extras.remove("Paroles du fichier .lrc à intégrer")
                    report.extras.append("Paroles du fichier .lrc")
                cover = report.values.cover
                thumb = cached_thumbnail(path, cover.data) if cover else None
                result = (track, report, thumb, None, resized, big)
            except Exception as exc:  # fichier corrompu, illisible…
                result = (track, None, None, str(exc) or "Fichier illisible", None, None)
            GLib.idle_add(self._deliver, gen, result)

    def _deliver(self, gen: int, result) -> bool:
        with self._lock:
            current = gen == self._generation
        if current:
            self._callback(*result)
        return GLib.SOURCE_REMOVE
