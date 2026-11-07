# SPDX-License-Identifier: GPL-3.0-or-later
"""Pochettes : redimensionnement à 1024 px, folder.jpg, recherche en ligne."""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import subprocess

import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, GLib  # noqa: E402

from . import __version__, tags

MAX_SIZE = 1024
JPEG_QUALITY = "95"   # visuellement sans perte
FOLDER_IMAGE = "folder.jpg"
USER_AGENT = f"Disquaire/{__version__} ( https://gitlab.com/shogu/disquaire )"


class CoverError(Exception):
    pass


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------

def _load(data: bytes):
    try:
        loader = GdkPixbuf.PixbufLoader()
        loader.write(data)
        loader.close()
        return loader.get_pixbuf()
    except GLib.Error:
        return None


def _pixbuf(data: bytes) -> GdkPixbuf.Pixbuf:
    pixbuf = _load(data)
    if pixbuf is None:
        # Format inconnu de GdkPixbuf (WebP, AVIF…) : ffmpeg le convertit.
        try:
            png = subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0",
                 "-frames:v", "1", "-f", "image2pipe", "-c:v", "png", "pipe:1"],
                input=data, capture_output=True, timeout=30, check=True,
            ).stdout
            pixbuf = _load(png)
        except (OSError, subprocess.SubprocessError):
            pixbuf = None
    if pixbuf is None:
        raise CoverError("Image illisible.")
    return pixbuf.apply_embedded_orientation() or pixbuf


def image_size(data: bytes) -> tuple[int, int]:
    """Dimensions sans décoder toute l'image."""
    size = [0, 0]

    def on_size(_loader, w, h):
        size[0], size[1] = w, h

    loader = GdkPixbuf.PixbufLoader()
    loader.connect("size-prepared", on_size)
    try:
        loader.write(data)
        loader.close()
    except GLib.Error:
        pass
    return size[0], size[1]


def prepare(data: bytes) -> tags.Cover:
    """Prépare une image pour l'intégrer.

    Plus grande que 1024 px : réduite à 1024 px (côté le plus long) en JPEG
    qualité 95. Sinon gardée telle quelle si c'est déjà du JPEG ou du PNG
    (aucune recompression, donc aucune perte).
    """
    mime = tags._sniff_mime(data, "")
    w, h = image_size(data)
    if max(w, h) <= MAX_SIZE and mime in ("image/jpeg", "image/png"):
        return tags.Cover(data, mime)
    pixbuf = _pixbuf(data)
    w, h = pixbuf.get_width(), pixbuf.get_height()
    if max(w, h) > MAX_SIZE:
        scale = MAX_SIZE / max(w, h)
        pixbuf = pixbuf.scale_simple(max(1, round(w * scale)), max(1, round(h * scale)),
                                     GdkPixbuf.InterpType.HYPER)
    if pixbuf.get_has_alpha():
        pixbuf = pixbuf.composite_color_simple(
            pixbuf.get_width(), pixbuf.get_height(), GdkPixbuf.InterpType.BILINEAR,
            255, 8, 0xFFFFFF, 0xFFFFFF)
    ok, buf = pixbuf.save_to_bufferv("jpeg", ["quality"], [JPEG_QUALITY])
    if not ok:
        raise CoverError("Conversion de l'image impossible.")
    return tags.Cover(bytes(buf), "image/jpeg")


def as_jpeg(cover: tags.Cover) -> bytes:
    """Les octets JPEG de la pochette (pour écrire folder.jpg)."""
    if cover.mime == "image/jpeg":
        return cover.data
    pixbuf = _pixbuf(cover.data)
    if pixbuf.get_has_alpha():
        pixbuf = pixbuf.composite_color_simple(
            pixbuf.get_width(), pixbuf.get_height(), GdkPixbuf.InterpType.BILINEAR,
            255, 8, 0xFFFFFF, 0xFFFFFF)
    ok, buf = pixbuf.save_to_bufferv("jpeg", ["quality"], [JPEG_QUALITY])
    if not ok:
        raise CoverError("Conversion de l'image impossible.")
    return bytes(buf)


def is_too_big(cover: tags.Cover | None) -> tuple[int, int] | None:
    if cover is None:
        return None
    w, h = image_size(cover.data)
    return (w, h) if max(w, h) > MAX_SIZE else None


def find_folder_image(folder: str) -> str | None:
    try:
        for name in os.listdir(folder):
            if name.lower() == FOLDER_IMAGE:
                path = os.path.join(folder, name)
                if os.path.isfile(path):
                    return path
    except OSError:
        pass
    return None


# ---------------------------------------------------------------------------
# Recherche en ligne
# ---------------------------------------------------------------------------

API_TIMEOUT = 8       # secondes par requête aux services
IMAGE_TIMEOUT = 12    # secondes par image
DEADLINE = 25         # durée maximale d'une recherche


@dataclass
class Candidate:
    source: str
    label: str
    url: str
    data: bytes = b""
    width: int = 0
    height: int = 0


def _get(url: str, timeout: float) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _short_error(exc: Exception) -> str:
    text = str(getattr(exc, "reason", "") or exc)
    if "timed out" in text or isinstance(exc, TimeoutError):
        return "le service ne répond pas"
    if "Name or service" in text or "resolution" in text:
        return "pas de connexion à Internet"
    if "403" in text or "Forbidden" in text:
        return "accès refusé"
    return text[:80]


def _search_itunes(query: str) -> list[Candidate]:
    out, seen = [], set()
    for country in ("FR", "US"):
        url = "https://itunes.apple.com/search?" + urllib.parse.urlencode(
            {"term": query, "entity": "album", "limit": 8, "country": country})
        try:
            results = json.loads(_get(url, API_TIMEOUT)).get("results", [])
        except Exception:
            if out:
                break
            raise
        for r in results:
            art, cid = r.get("artworkUrl100"), r.get("collectionId")
            if not art or cid in seen:
                continue
            seen.add(cid)
            # La miniature 100x100 se décline en grand format.
            big = re.sub(r"/\d+x\d+bb\.", "/1200x1200bb.", art)
            label = f"{r.get('collectionName', '')} — {r.get('artistName', '')}"
            out.append(Candidate("iTunes", label, big))
    return out


def _search_caa(query: str) -> list[Candidate]:
    url = "https://musicbrainz.org/ws/2/release-group/?" + urllib.parse.urlencode(
        {"query": query, "fmt": "json", "limit": 6})
    groups = json.loads(_get(url, API_TIMEOUT)).get("release-groups", [])
    out = []
    for g in groups:
        gid = g.get("id")
        if not gid:
            continue
        credit = g.get("artist-credit") or []
        artist = "".join(c.get("name", "") + c.get("joinphrase", "") for c in credit)
        # Image de face en 1200 px, directement (404 s'il n'y en a pas).
        out.append(Candidate("Cover Art Archive", f"{g.get('title', '')} — {artist}",
                             f"https://coverartarchive.org/release-group/{gid}/front-1200"))
    return out


def search(query: str, on_result, should_stop=lambda: False, on_status=None) -> list[str]:
    """Cherche des pochettes d'au moins 1024 × 1024, en 25 secondes au plus.

    Les deux services sont interrogés en même temps et les images sont
    téléchargées dès qu'elles sont connues ; `on_result(candidate)` est
    appelé (hors thread GTK) pour chaque image retenue. Renvoie les erreurs.
    """
    import threading
    import time
    from concurrent.futures import wait

    t0 = time.monotonic()

    def stop():
        return should_stop() or time.monotonic() - t0 > DEADLINE

    errors: list[str] = []
    seen: set[str] = set()
    futures = []
    lock = threading.Lock()
    pool = ThreadPoolExecutor(max_workers=6)

    def fetch(c: Candidate):
        if stop():
            return
        try:
            c.data = _get(c.url, IMAGE_TIMEOUT)
        except Exception:
            return
        if stop():
            return
        c.width, c.height = image_size(c.data)
        if min(c.width, c.height) >= MAX_SIZE:
            on_result(c)

    def source(name, func):
        try:
            cands = func(query)
        except Exception as exc:
            with lock:
                errors.append(f"{name} : {_short_error(exc)}")
            return
        if on_status:
            on_status(f"{name} : {len(cands)} album(s)")
        with lock:
            for c in cands:
                if c.url not in seen and not stop():
                    seen.add(c.url)
                    futures.append(pool.submit(fetch, c))

    threads = [threading.Thread(target=source, args=(n, f), daemon=True)
               for n, f in (("iTunes", _search_itunes), ("MusicBrainz", _search_caa))]
    for t in threads:
        t.start()
    for t in threads:
        t.join(max(0.0, DEADLINE - (time.monotonic() - t0)))
    with lock:
        pending = list(futures)
    wait(pending, timeout=max(0.0, DEADLINE - (time.monotonic() - t0)))
    pool.shutdown(wait=False, cancel_futures=True)
    if time.monotonic() - t0 > DEADLINE and not should_stop():
        errors.append(f"recherche arrêtée après {DEADLINE} secondes")
    return errors
