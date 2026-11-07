# SPDX-License-Identifier: GPL-3.0-or-later
"""Recherche des doublons dans toute la discothèque."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from mutagen import File as MutagenFile

from . import tags, textfmt

# Deux fichiers ne sont des doublons que si leurs durées diffèrent de moins
# de ça (sinon : version live, remix…).
DURATION_TOLERANCE = 4.0
# Ressemblance minimale (0 à 1) entre deux titres, puis entre deux artistes.
TITLE_SIMILARITY = 0.85
ARTIST_SIMILARITY = 0.80

# Mentions sans rapport avec le morceau lui-même, ignorées pour comparer.
_NOISE = re.compile(
    r"\b(remaster(?:ed|isé|isee|ise)?|official|officiel|audio|video|vidéo|clip|"
    r"lyrics?|paroles|hq|hd|explicit|clean|version album|album version|"
    r"mp3|flac|320|kbps)\b|\b(19|20)\d\d\b")


@dataclass
class DupFile:
    path: str
    artist: str
    title: str
    format: str
    bitrate: int
    sample_rate: int
    bits: int
    length: float
    size: int
    key_artist: str = field(default="", repr=False)
    key_title: str = field(default="", repr=False)

    @property
    def is_mp3_320(self) -> bool:
        return self.format == "MP3" and self.bitrate >= 315_000

    @property
    def quality(self):
        # Le MP3 320 est l'exemplaire à garder ; viennent ensuite le FLAC,
        # puis les MP3 par débit décroissant.
        return (self.is_mp3_320, self.format == "FLAC", self.bitrate, self.sample_rate,
                self.size)

    def describe(self) -> str:
        info = tags.AudioInfo(self.format, self.length, self.bitrate,
                              self.sample_rate, self.bits)
        return f"{tags.describe(info)} · {human_size(self.size)}"


def human_size(n: int) -> str:
    for unit in ("o", "Ko", "Mo", "Go"):
        if n < 1024 or unit == "Go":
            return (f"{n:.1f} {unit}" if unit != "o" else f"{n} {unit}").replace(".", ",")
        n /= 1024
    return str(n)


def _first(tags_obj, *keys) -> str:
    if tags_obj is None:
        return ""
    for key in keys:
        try:
            value = tags_obj.get(key)
        except (KeyError, ValueError):
            value = None
        if value is None:
            continue
        text = getattr(value, "text", value)
        if isinstance(text, (list, tuple)):
            text = "; ".join(str(t) for t in text)
        if str(text).strip():
            return str(text)
    return ""


def read_light(path: str) -> DupFile | None:
    try:
        audio = MutagenFile(path)
    except Exception:
        return None
    if audio is None:
        return None
    info = audio.info
    flac = tags.is_flac(path)
    t = audio.tags
    if flac:
        artist, title = _first(t, "artist", "ARTIST"), _first(t, "title", "TITLE")
    else:
        artist, title = _first(t, "TPE1"), _first(t, "TIT2")
    try:
        size = os.path.getsize(path)
    except OSError:
        size = 0
    return DupFile(
        path=path, artist=artist, title=title,
        format="FLAC" if flac else "MP3",
        bitrate=getattr(info, "bitrate", 0) or 0,
        sample_rate=getattr(info, "sample_rate", 0) or 0,
        bits=getattr(info, "bits_per_sample", 0) or 0,
        length=getattr(info, "length", 0.0) or 0.0,
        size=size,
    )


def _clean(text: str) -> str:
    text = textfmt.match_key(text)
    text = _NOISE.sub(" ", text)
    return textfmt.clean_spaces(text)


def _prepare_keys(f: DupFile) -> None:
    artist, title = f.artist, f.title
    if not title.strip():
        artist, title = textfmt.tags_from_filename(os.path.splitext(os.path.basename(f.path))[0])
    f.key_artist = _clean(textfmt.split_feat(artist.split(";")[0])[0])
    f.key_title = _clean(textfmt.split_feat(title)[0])


def _ratio(a: str, b: str) -> float:
    if a == b:
        return 1.0
    m = SequenceMatcher(None, a, b, autojunk=False)
    if m.real_quick_ratio() < TITLE_SIMILARITY - 0.15:
        return 0.0
    return m.ratio()


def similar(a: DupFile, b: DupFile) -> bool:
    """Recherche floue : mêmes morceaux malgré des noms un peu différents."""
    if abs(a.length - b.length) > DURATION_TOLERANCE:
        return False
    if not a.key_title or not b.key_title:
        return False
    if _ratio(a.key_title, b.key_title) < TITLE_SIMILARITY:
        return False
    if a.key_artist and b.key_artist:
        if a.key_artist in b.key_artist or b.key_artist in a.key_artist:
            return True
        return _ratio(a.key_artist, b.key_artist) >= ARTIST_SIMILARITY
    # Un artiste manque : on compare le tout « artiste titre ».
    full_a = f"{a.key_artist} {a.key_title}".strip()
    full_b = f"{b.key_artist} {b.key_title}".strip()
    return _ratio(full_a, full_b) >= TITLE_SIMILARITY or a.key_title == b.key_title


def list_audio(root: str) -> list[str]:
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        out += [os.path.join(dirpath, n) for n in filenames
                if not n.startswith(".") and tags.is_audio(n)]
    return out


def find(root: str, progress=None, should_stop=lambda: False) -> list[list[DupFile]]:
    """Renvoie les groupes de doublons, l'exemplaire à garder en premier."""
    paths = list_audio(root)
    files: list[DupFile] = []
    for i, path in enumerate(paths):
        if should_stop():
            return []
        if progress and i % 25 == 0:
            progress(i, len(paths))
        f = read_light(path)
        if f is None:
            continue
        _prepare_keys(f)
        if f.key_title:
            files.append(f)
    if progress:
        progress(len(paths), len(paths))

    # Comparaison par fenêtre de durée : chaque fichier n'est comparé qu'aux
    # fichiers de durée voisine (rapide même sur une grosse discothèque).
    files.sort(key=lambda f: f.length)
    parent = list(range(len(files)))

    def root_of(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, a in enumerate(files):
        if should_stop():
            return []
        j = i + 1
        while j < len(files) and files[j].length - a.length <= DURATION_TOLERANCE:
            if similar(a, files[j]):
                ri, rj = root_of(i), root_of(j)
                if ri != rj:
                    parent[rj] = ri
            j += 1

    clusters: dict[int, list[DupFile]] = {}
    for i, f in enumerate(files):
        clusters.setdefault(root_of(i), []).append(f)
    groups = [g for g in clusters.values() if len(g) > 1]
    for g in groups:
        g.sort(key=lambda f: f.quality, reverse=True)
    groups.sort(key=lambda g: (g[0].key_artist, g[0].key_title))
    return groups


def exact_names(group: list[DupFile]) -> bool:
    """Vrai si tous les exemplaires ont exactement le même artiste et titre."""
    first = group[0]
    return all((f.key_artist, f.key_title) == (first.key_artist, first.key_title)
               for f in group[1:])
