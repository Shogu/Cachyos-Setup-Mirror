# SPDX-License-Identifier: GPL-3.0-or-later
"""Mise en forme du texte : majuscules, « Feat. », noms de fichiers."""

from __future__ import annotations

import re
import unicodedata

# « (feat. X) », « [ft X] », « (featuring X) » n'importe où
_FEAT_BRACKET = re.compile(
    r"\s*[\(\[]\s*(?:feat\.?|ft\.?|featuring)\s+([^\)\]]+?)\s*[\)\]]", re.IGNORECASE)
# « feat. X » en fin de chaîne
_FEAT_TRAIL = re.compile(
    r"\s+(?:feat\.?|ft\.?|featuring)\s+(.+)$", re.IGNORECASE)
_SPACES = re.compile(r"\s+")
_TRACK_PREFIX = re.compile(r"^\s*\d{1,3}\s*[-._)]\s*")
# Caractères après lesquels un mot commence
_WORD_START = set(" \t([{\"“«/-&+–—")


def clean_spaces(text: str) -> str:
    return _SPACES.sub(" ", text).strip()


# Séparateurs entre plusieurs noms dans un même champ.
_SEGMENTS = re.compile(
    r"(\s*[|;,&+/]\s*|\s+(?:feat\.?|ft\.?|featuring|vs\.?|x|et|and|with)\s+)",
    re.IGNORECASE)


def _uncap(segment: str) -> str:
    """« KID FRANCESCOLI » → « kid francescoli » ; un sigle court reste
    (AC, DC, MGMT, IAM)."""
    letters = [c for c in segment if c.isalpha()]
    if letters and all(c.isupper() for c in letters) and \
            (len(segment.split()) > 1 or len(letters) > 5):
        return segment.lower()
    return segment


def title_case(text: str) -> str:
    """Majuscule à chaque mot.

    Chaque nom tout en capitales est d'abord passé en minuscules
    (« KID FRANCESCOLI & Julia Minkin » → « Kid Francescoli & Julia Minkin »),
    même s'il partage le champ avec d'autres noms ; les sigles courts
    (AC/DC, MGMT) et les capitales internes (McCartney) sont gardés.
    """
    text = clean_spaces(text)
    parts = _SEGMENTS.split(text)
    text = "".join(p if i % 2 else _uncap(p) for i, p in enumerate(parts))
    out = []
    for i, ch in enumerate(text):
        prev = text[i - 1] if i else " "
        start = prev in _WORD_START
        # L'amour, D'Artagnan : après une élision d'une seule lettre
        if prev in "'’" and i >= 2 and text[i - 2].isalpha() and \
                (i < 3 or text[i - 3] in _WORD_START):
            start = True
        out.append(ch.upper() if start and ch.isalpha() else ch)
    return "".join(out)


def split_feat(text: str) -> tuple[str, list[str]]:
    """Sépare « Titre (feat. X) » en (« Titre », [« X »])."""
    guests: list[str] = []

    def grab(match):
        guests.append(match.group(1))
        return ""

    text = _FEAT_BRACKET.sub(grab, text)
    m = _FEAT_TRAIL.search(text)
    if m:
        guests.append(m.group(1))
        text = text[:m.start()]
    return clean_spaces(text), [clean_spaces(g) for g in guests if g.strip()]


def _join_guests(guests: list[str]) -> str:
    seen, out = set(), []
    for g in guests:
        for part in re.split(r"\s*(?:;|,|&| et | and )\s*", g):
            part = title_case(part)
            if part and part.casefold() not in seen:
                seen.add(part.casefold())
                out.append(part)
    return " & ".join(out)


def format_artist(artist: str) -> str:
    """Majuscules + « Feat. » normalisé, sans déplacer l'invité."""
    parts = [p for p in (s.strip() for s in artist.split(";")) if p]
    formatted = []
    for part in parts:
        main, guests = split_feat(part)
        text = title_case(main)
        if guests:
            text += " Feat. " + _join_guests(guests)
        formatted.append(text)
    return "; ".join(formatted)


def format_title(title: str) -> str:
    main, guests = split_feat(title)
    text = title_case(main)
    if guests:
        text += " (Feat. " + _join_guests(guests) + ")"
    return text


def _safe(name: str) -> str:
    name = name.replace("/", "-").replace("\0", "")
    name = clean_spaces(name).strip(" .")
    return name[:200]


def filename_from_tags(artist: str, title: str, ext: str) -> str | None:
    """« Artiste - Titre Feat. Invité.ext », ou None si un tag manque."""
    if not artist.strip() or not title.strip():
        return None
    guests: list[str] = []
    mains = []
    for part in (s.strip() for s in artist.split(";")):
        if not part:
            continue
        main, g = split_feat(part)
        guests += g
        if main:
            mains.append(title_case(main))
    title_main, g = split_feat(title)
    guests += g
    name = " & ".join(mains) + " - " + title_case(title_main)
    if guests:
        name += " Feat. " + _join_guests(guests)
    name = _safe(name)
    return name + ext.lower() if name else None


def tags_from_filename(stem: str) -> tuple[str, str]:
    """« 01 - Artiste - Titre » → (« Artiste », « Titre »)."""
    stem = stem.replace("_", " ")
    stem = _TRACK_PREFIX.sub("", stem)
    if " - " in stem:
        artist, title = stem.split(" - ", 1)
    else:
        artist, title = "", stem
    return format_artist(artist), format_title(title)


def match_key(text: str) -> str:
    """Clé de comparaison : sans accents, ponctuation ni casse."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w]+", " ", text.casefold())
    return clean_spaces(text)


def tidy(artist: str, title: str, stem: str) -> tuple[str, str]:
    """Mise en forme complète des tags artiste et titre.

    Ce qui manque est repris du nom du fichier, puis majuscules,
    sigles et « Feat. » sont mis en forme. L'album n'est jamais touché.
    """
    if not artist.strip() or not title.strip():
        name_artist, name_title = tags_from_filename(stem)
        artist = artist if artist.strip() else name_artist
        title = title if title.strip() else name_title
    return format_artist(artist), format_title(title)


def folder_name(artist: str, album: str) -> str:
    """« Artiste - Album » pour un dossier (artiste principal, sans invité)."""
    main = split_feat(artist.split(";")[0])[0]
    parts = [p for p in (title_case(main), clean_spaces(album)) if p]
    return _safe(" - ".join(parts))


_YEAR = re.compile(r"(1[89]\d\d|20\d\d|21\d\d)")


def year_only(date: str) -> str:
    """« 2014-03-01 », « 01/03/2014 », « 2014 (réédition) » → « 2014 »."""
    m = _YEAR.search(date or "")
    return m.group(1) if m else ""
