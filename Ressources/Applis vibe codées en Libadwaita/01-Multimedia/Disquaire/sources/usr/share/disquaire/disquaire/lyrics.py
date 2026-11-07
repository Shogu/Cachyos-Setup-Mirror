# SPDX-License-Identifier: GPL-3.0-or-later
"""Recherche de paroles en ligne avec LRCLIB (https://lrclib.net).

Service libre et gratuit, sans compte ni clé. Les paroles synchronisées
(LRC) sont converties en texte simple : seules les paroles sont gardées.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from . import __version__, textfmt

API = "https://lrclib.net/api"
TIMEOUT = 15
MAX_ATTEMPTS = 3
_RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}
USER_AGENT = f"Disquaire/{__version__} (https://gitlab.com/shogu/disquaire)"
_LRC_TAG = re.compile(r"^\s*(\[[^\]]*\]\s*)+")


class LyricsError(Exception):
    pass


@dataclass
class Candidate:
    artist: str
    title: str
    album: str
    duration: float
    text: str
    exact: bool = False      # artiste, titre et durée concordent

    def label(self) -> str:
        return f"{self.artist} — {self.title}"


def _get(url: str):
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    for attempt in range(MAX_ATTEMPTS):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                exc.close()
                return None
            if exc.code in _RETRYABLE_STATUS and attempt + 1 < MAX_ATTEMPTS:
                retry_after = exc.headers.get("Retry-After", "") if exc.headers else ""
                try:
                    delay = min(5.0, max(1.0, float(retry_after)))
                except ValueError:
                    delay = min(2 ** attempt, 4)
                exc.close()
                time.sleep(delay)
                continue
            code = exc.code
            exc.close()
            raise LyricsError(f"le service a répondu {code}") from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise LyricsError("le service a renvoyé une réponse invalide") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt + 1 < MAX_ATTEMPTS:
                time.sleep(min(2 ** attempt, 4))
                continue
            reason = str(getattr(exc, "reason", "") or exc).casefold()
            if "timed out" in reason or isinstance(exc, TimeoutError):
                raise LyricsError("le service ne répond pas") from exc
            raise LyricsError("pas de connexion au service de paroles") from exc
    return None


def lrc_to_text(lrc: str) -> str:
    lines = [_LRC_TAG.sub("", line).rstrip() for line in lrc.splitlines()]
    text = "\n".join(lines).strip()
    return re.sub(r"\n{3,}", "\n\n", text)


def _candidate(rec: dict) -> Candidate | None:
    if rec.get("instrumental"):
        return None
    text = (rec.get("plainLyrics") or "").strip()
    if not text and rec.get("syncedLyrics"):
        text = lrc_to_text(rec["syncedLyrics"])
    if not text:
        return None
    return Candidate(rec.get("artistName") or "", rec.get("trackName") or "",
                     rec.get("albumName") or "", float(rec.get("duration") or 0), text)


def _main_artist(artist: str) -> str:
    return textfmt.split_feat(artist.split(";")[0])[0]


def _same(a: str, b: str) -> bool:
    ka, kb = textfmt.match_key(a), textfmt.match_key(b)
    return bool(ka) and ka == kb


def search(artist: str, title: str, album: str = "", duration: float = 0) -> list[Candidate]:
    """Liste de paroles possibles, la plus probable en premier."""
    artist = _main_artist(artist)
    title = textfmt.split_feat(title)[0]
    if not title.strip():
        raise LyricsError("titre manquant")
    found: list[Candidate] = []

    if artist and duration:
        params = {"artist_name": artist, "track_name": title, "duration": round(duration)}
        if album:
            params["album_name"] = album
        rec = _get(f"{API}/get?" + urllib.parse.urlencode(params))
        if rec:
            c = _candidate(rec)
            if c:
                found.append(c)

    params = {"track_name": title}
    if artist:
        params["artist_name"] = artist
    records = _get(f"{API}/search?" + urllib.parse.urlencode(params)) or []
    if not records and artist:
        records = _get(f"{API}/search?" + urllib.parse.urlencode(
            {"track_name": title})) or []
    for rec in records:
        c = _candidate(rec)
        if c and not any(c.text == f.text for f in found):
            found.append(c)

    for c in found:
        candidate_title = textfmt.split_feat(c.title)[0]
        c.exact = (_same(candidate_title, title)
                   and (not artist or _same(_main_artist(c.artist), artist))
                   and (not duration or abs(c.duration - duration) <= 3))
    found.sort(key=lambda c: (not c.exact, abs(c.duration - duration) if duration else 0))
    return found[:20]


def best(artist: str, title: str, album: str = "", duration: float = 0) -> Candidate | None:
    """Les paroles qui concordent sûrement (artiste, titre, durée), sinon None."""
    for c in search(artist, title, album, duration):
        if c.exact:
            return c
        break
    return None
