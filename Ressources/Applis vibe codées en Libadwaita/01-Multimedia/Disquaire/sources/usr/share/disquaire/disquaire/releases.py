# SPDX-License-Identifier: GPL-3.0-or-later
"""Année et album d'un morceau, d'après MusicBrainz et iTunes."""

from __future__ import annotations

import json
import re
import threading
import urllib.parse
import urllib.request
from dataclasses import dataclass

from . import __version__, textfmt

TIMEOUT = 10
USER_AGENT = f"Disquaire/{__version__} ( https://gitlab.com/shogu/disquaire )"

TYPE_LABELS = {"album": "Album", "single": "Single", "ep": "EP", "compilation": "Compilation",
               "live": "Live", "soundtrack": "B.O.", "remix": "Remix", "other": "Autre"}


class ReleaseError(Exception):
    pass


@dataclass
class Release:
    year: str
    album: str
    kind: str          # album, single, compilation…
    artist: str
    source: str
    match: bool = False   # même artiste et même titre

    def kind_label(self) -> str:
        return TYPE_LABELS.get(self.kind, self.kind.title() if self.kind else "")


def _get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        reason = str(getattr(exc, "reason", "") or exc)
        raise ReleaseError("le service ne répond pas" if "timed out" in reason
                           else "pas de connexion au service") from exc


def _year(date: str) -> str:
    m = re.match(r"(\d{4})", date or "")
    return m.group(1) if m else ""


def _same(a: str, b: str) -> bool:
    ka, kb = textfmt.match_key(a), textfmt.match_key(b)
    return bool(ka) and (ka == kb or ka in kb or kb in ka)


def _musicbrainz(artist: str, title: str) -> list[Release]:
    q = f'recording:"{title}"' + (f' AND artist:"{artist}"' if artist else "")
    data = _get("https://musicbrainz.org/ws/2/recording/?" +
                urllib.parse.urlencode({"query": q, "fmt": "json", "limit": 25}))
    out = []
    for rec in data.get("recordings", []):
        credit = "".join(c.get("name", "") + c.get("joinphrase", "")
                         for c in rec.get("artist-credit") or [])
        match = _same(rec.get("title", ""), title) and (not artist or _same(credit, artist))
        for rel in rec.get("releases", []):
            group = rel.get("release-group", {})
            kind = (group.get("primary-type") or "").lower()
            secondary = [t.lower() for t in group.get("secondary-types") or []]
            if "compilation" in secondary:
                kind = "compilation"
            elif "live" in secondary:
                kind = "live"
            elif "soundtrack" in secondary:
                kind = "soundtrack"
            elif "remix" in secondary:
                kind = "remix"
            year = _year(rel.get("date", ""))
            if year:
                out.append(Release(year, rel.get("title", ""), kind, credit, "MusicBrainz", match))
    return out


def _itunes(artist: str, title: str) -> list[Release]:
    out = []
    for country in ("FR", "US"):
        data = _get("https://itunes.apple.com/search?" + urllib.parse.urlencode(
            {"term": f"{artist} {title}".strip(), "entity": "song", "limit": 15,
             "country": country}))
        for r in data.get("results", []):
            name = re.sub(r"\s*-\s*(Single|EP)$", "", r.get("collectionName", ""))
            kind = "single" if r.get("collectionName", "").endswith(" - Single") else \
                "ep" if r.get("collectionName", "").endswith(" - EP") else "album"
            match = _same(r.get("trackName", ""), title) and \
                (not artist or _same(r.get("artistName", ""), artist))
            year = _year(r.get("releaseDate", ""))
            if year and name:
                out.append(Release(year, name, kind, r.get("artistName", ""), "iTunes", match))
        if out:
            break
    return out


_ORDER = {"album": 0, "ep": 1, "single": 2, "soundtrack": 3, "live": 4,
          "remix": 5, "compilation": 6}


def search(artist: str, title: str) -> list[Release]:
    """Sorties du morceau : les concordantes d'abord, puis la plus ancienne,
    les albums avant singles et compilations."""
    artist = textfmt.split_feat(artist.split(";")[0])[0]
    title = textfmt.split_feat(title)[0]
    if not title.strip():
        raise ReleaseError("titre manquant")
    results: list[Release] = []
    errors: list[str] = []
    lock = threading.Lock()

    def run(func):
        try:
            found = func(artist, title)
        except ReleaseError as exc:
            with lock:
                errors.append(str(exc))
            return
        with lock:
            results.extend(found)

    threads = [threading.Thread(target=run, args=(f,), daemon=True)
               for f in (_musicbrainz, _itunes)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(TIMEOUT * 2 + 2)
    if not results and errors:
        raise ReleaseError(errors[0])
    seen, unique = set(), []
    for r in sorted(results, key=lambda r: (not r.match, r.year,
                                            _ORDER.get(r.kind, 7), r.source)):
        key = (r.year, textfmt.match_key(r.album))
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique[:30]
