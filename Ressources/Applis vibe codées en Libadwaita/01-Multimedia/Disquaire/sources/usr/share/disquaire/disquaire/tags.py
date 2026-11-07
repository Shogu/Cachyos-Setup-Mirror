# SPDX-License-Identifier: GPL-3.0-or-later
"""Lecture, nettoyage et écriture des tags MP3 (ID3) et FLAC (Vorbis comments).

Seuls sept éléments sont conservés : artiste, titre, album, date, genre,
pochette (image de face) et paroles. Tout le reste est supprimé à
l'enregistrement.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from mutagen import MutagenError
from mutagen.id3 import (
    APIC, ID3, ID3NoHeaderError, TALB, TCON, TDRC, TIT2, TPE1, USLT,
    PictureType,
)
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3

from .textfmt import year_only

FIELDS = ("artist", "title", "album", "date", "genre")
FIELD_LABELS = {
    "artist": "Artiste",
    "title": "Titre",
    "album": "Album",
    "date": "Date",
    "genre": "Genre",
    "lyrics": "Paroles",
    "cover": "Pochette",
}

AUDIO_EXTENSIONS = (".mp3", ".flac")

# --- ID3 -------------------------------------------------------------------
_ID3_FRAMES = {
    "artist": "TPE1",
    "title": "TIT2",
    "album": "TALB",
    "date": "TDRC",
    "genre": "TCON",
}
_ID3_KEEP = {"TPE1", "TIT2", "TALB", "TDRC", "TCON", "USLT", "APIC"}

# Noms lisibles des cadres ID3 les plus courants, pour l'affichage.
ID3_NAMES = {
    "TRCK": "Numéro de piste",
    "TPOS": "Numéro de disque",
    "TPE2": "Artiste de l'album",
    "TCOM": "Compositeur",
    "TCOP": "Copyright",
    "TENC": "Encodé par",
    "TSSE": "Logiciel d'encodage",
    "TPUB": "Éditeur",
    "TBPM": "Tempo",
    "TKEY": "Tonalité",
    "TLEN": "Durée",
    "TSRC": "ISRC",
    "TXXX": "Champ personnalisé",
    "COMM": "Commentaire",
    "PRIV": "Données privées",
    "UFID": "Identifiant",
    "WXXX": "Lien",
    "SYLT": "Paroles synchronisées",
    "POPM": "Popularité",
    "PCNT": "Compteur d'écoute",
    "GEOB": "Objet joint",
    "MCDI": "Identifiant CD",
    "RVA2": "Volume relatif",
    "TSOP": "Tri artiste",
    "TSOA": "Tri album",
    "TSOT": "Tri titre",
    "TSO2": "Tri artiste de l'album",
    "TCMP": "Compilation",
    "TDRL": "Date de sortie",
    "TDOR": "Date originale",
    "TMED": "Support",
    "TLAN": "Langue",
    "TIT1": "Regroupement",
    "TIT3": "Sous-titre",
    "TOPE": "Artiste original",
    "TEXT": "Parolier",
}

# --- FLAC ------------------------------------------------------------------
_VORBIS_KEYS = {
    "artist": "ARTIST",
    "title": "TITLE",
    "album": "ALBUM",
    "date": "DATE",
    "genre": "GENRE",
}
_VORBIS_LYRICS_KEYS = ("LYRICS", "UNSYNCEDLYRICS")
_VORBIS_KEEP = {"ARTIST", "TITLE", "ALBUM", "DATE", "GENRE", "LYRICS"}

VORBIS_NAMES = {
    "TRACKNUMBER": "Numéro de piste",
    "TRACKTOTAL": "Nombre de pistes",
    "TOTALTRACKS": "Nombre de pistes",
    "DISCNUMBER": "Numéro de disque",
    "DISCTOTAL": "Nombre de disques",
    "TOTALDISCS": "Nombre de disques",
    "ALBUMARTIST": "Artiste de l'album",
    "ALBUM ARTIST": "Artiste de l'album",
    "COMMENT": "Commentaire",
    "DESCRIPTION": "Description",
    "COMPOSER": "Compositeur",
    "ENCODER": "Logiciel d'encodage",
    "ENCODED-BY": "Encodé par",
    "COPYRIGHT": "Copyright",
    "LABEL": "Label",
    "ORGANIZATION": "Label",
    "ISRC": "ISRC",
    "BARCODE": "Code-barres",
    "CATALOGNUMBER": "Numéro de catalogue",
    "UNSYNCEDLYRICS": "Paroles (ancien nom)",
    "REPLAYGAIN_TRACK_GAIN": "ReplayGain",
    "REPLAYGAIN_TRACK_PEAK": "ReplayGain",
    "REPLAYGAIN_ALBUM_GAIN": "ReplayGain",
    "REPLAYGAIN_ALBUM_PEAK": "ReplayGain",
}


class TagError(Exception):
    """Erreur lisible lors de la lecture ou de l'écriture des tags."""


@dataclass
class Cover:
    data: bytes
    mime: str = "image/jpeg"

    def __eq__(self, other):
        return isinstance(other, Cover) and self.data == other.data


@dataclass
class TagValues:
    """Les sept éléments conservés."""

    artist: str = ""
    title: str = ""
    album: str = ""
    date: str = ""
    genre: str = ""
    lyrics: str = ""
    cover: Cover | None = None

    def copy(self) -> "TagValues":
        return TagValues(
            self.artist, self.title, self.album, self.date, self.genre,
            self.lyrics, self.cover,
        )

    def get(self, key: str):
        return getattr(self, key)

    def set(self, key: str, value) -> None:
        setattr(self, key, value)


@dataclass
class AudioInfo:
    format: str = ""          # "MP3" ou "FLAC"
    length: float = 0.0       # secondes
    bitrate: int = 0          # bit/s
    sample_rate: int = 0      # Hz
    bits_per_sample: int = 0  # FLAC uniquement
    channels: int = 0


@dataclass
class TagReport:
    values: TagValues
    info: AudioInfo
    extras: list[str] = field(default_factory=list)  # libellés à supprimer


def is_audio(path: str) -> bool:
    return path.lower().endswith(AUDIO_EXTENSIONS)


def is_flac(path: str) -> bool:
    return path.lower().endswith(".flac")


def _join(values) -> str:
    return "; ".join(str(v) for v in values if str(v).strip())


def _sniff_mime(data: bytes, fallback: str = "image/jpeg") -> str:
    if data.startswith(b"\x89PNG"):
        return "image/png"
    if data.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:3] == b"GIF":
        return "image/gif"
    return fallback or "image/jpeg"


def _date_to_year(values: "TagValues", extras: list[str]) -> None:
    """La date ne garde que l'année ; une date complète est à nettoyer."""
    year = year_only(values.date)
    if year != values.date.strip():
        extras.append("Date complète (seule l'année est gardée)")
    values.date = year


def _has_id3v1(path: str) -> bool:
    try:
        with open(path, "rb") as fh:
            fh.seek(-128, os.SEEK_END)
            return fh.read(3) == b"TAG"
    except OSError:
        return False


def _has_apev2(path: str) -> bool:
    try:
        from mutagen.apev2 import APEv2
        APEv2(path)
        return True
    except Exception:
        return False


def _dedupe(labels: list[str]) -> list[str]:
    seen, out = set(), []
    for label in labels:
        if label not in seen:
            seen.add(label)
            out.append(label)
    return out


# ---------------------------------------------------------------------------
# Lecture
# ---------------------------------------------------------------------------

def read(path: str) -> TagReport:
    try:
        if is_flac(path):
            return _read_flac(path)
        return _read_mp3(path)
    except MutagenError as exc:
        raise TagError(f"Lecture impossible : {exc}") from exc


def _read_mp3(path: str) -> TagReport:
    audio = MP3(path)
    info = AudioInfo(
        format="MP3",
        length=audio.info.length,
        bitrate=audio.info.bitrate,
        sample_rate=audio.info.sample_rate,
        channels=getattr(audio.info, "channels", 0),
    )
    values = TagValues()
    extras: list[str] = []
    tags = audio.tags
    if tags is not None:
        for key, frame_id in _ID3_FRAMES.items():
            frame = tags.get(frame_id)
            if frame is None:
                continue
            if frame_id == "TCON":
                values.genre = _join(frame.genres)
            else:
                values.set(key, _join(frame.text))
        uslt = tags.getall("USLT")
        if uslt:
            values.lyrics = uslt[0].text
            if len(uslt) > 1:
                extras.append("Paroles en double")
        apics = tags.getall("APIC")
        if apics:
            front = next((p for p in apics if p.type == PictureType.COVER_FRONT), apics[0])
            values.cover = Cover(front.data, _sniff_mime(front.data, front.mime))
            if len(apics) > 1:
                extras.append("Images supplémentaires")
        for frame in tags.values():
            frame_id = frame.FrameID
            if frame_id not in _ID3_KEEP:
                extras.append(ID3_NAMES.get(frame_id, frame_id))
    if _has_id3v1(path):
        extras.append("Tag ID3v1")
    if _has_apev2(path):
        extras.append("Tag APE")
    _date_to_year(values, extras)
    return TagReport(values, info, _dedupe(extras))


def _read_flac(path: str) -> TagReport:
    audio = FLAC(path)
    info = AudioInfo(
        format="FLAC",
        length=audio.info.length,
        bitrate=getattr(audio.info, "bitrate", 0),
        sample_rate=audio.info.sample_rate,
        bits_per_sample=audio.info.bits_per_sample,
        channels=audio.info.channels,
    )
    values = TagValues()
    extras: list[str] = []
    tags = audio.tags or {}
    present = {k.upper() for k in tags.keys()} if tags else set()
    for key, vkey in _VORBIS_KEYS.items():
        if vkey in present:
            values.set(key, _join(tags[vkey]))
    for lkey in _VORBIS_LYRICS_KEYS:
        if lkey in present and _join(tags[lkey]):
            values.lyrics = "\n".join(tags[lkey])
            break
    for k in sorted(present):
        if k not in _VORBIS_KEEP:
            if k == "METADATA_BLOCK_PICTURE":
                extras.append("Image intégrée aux commentaires")
            else:
                extras.append(VORBIS_NAMES.get(k, k.title()))
    pictures = audio.pictures
    if pictures:
        front = next((p for p in pictures if p.type == PictureType.COVER_FRONT), pictures[0])
        values.cover = Cover(front.data, _sniff_mime(front.data, front.mime))
        if len(pictures) > 1:
            extras.append("Images supplémentaires")
    try:
        ID3(path)
        extras.append("Tag ID3 parasite")
    except Exception:
        pass
    _date_to_year(values, extras)
    return TagReport(values, info, _dedupe(extras))


# ---------------------------------------------------------------------------
# Écriture (remplace TOUT par les sept éléments conservés)
# ---------------------------------------------------------------------------

def write(path: str, values: TagValues) -> None:
    try:
        if is_flac(path):
            _write_flac(path, values)
        else:
            _write_mp3(path, values)
    except MutagenError as exc:
        raise TagError(f"Écriture impossible : {exc}") from exc
    except OSError as exc:
        raise TagError(f"Écriture impossible : {exc.strerror or exc}") from exc


def _split(value: str) -> list[str]:
    parts = [p.strip() for p in value.split(";")]
    return [p for p in parts if p]


def _write_mp3(path: str, values: TagValues) -> None:
    # Le tag APE éventuel est supprimé d'abord (il se trouve en fin de fichier).
    try:
        from mutagen.apev2 import delete as ape_delete
        ape_delete(path)
    except Exception:
        pass
    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        tags = ID3()
    tags.clear()
    enc = 3  # UTF-8 (converti en UTF-16 par mutagen pour ID3v2.3)
    if values.artist.strip():
        tags.add(TPE1(encoding=enc, text=_split(values.artist)))
    if values.title.strip():
        tags.add(TIT2(encoding=enc, text=[values.title.strip()]))
    if values.album.strip():
        tags.add(TALB(encoding=enc, text=[values.album.strip()]))
    if year_only(values.date):
        tags.add(TDRC(encoding=enc, text=[year_only(values.date)]))
    if values.genre.strip():
        tags.add(TCON(encoding=enc, text=_split(values.genre)))
    if values.lyrics.strip():
        tags.add(USLT(encoding=enc, lang="XXX", desc="", text=values.lyrics))
    if values.cover is not None:
        tags.add(APIC(
            encoding=enc, mime=values.cover.mime, type=PictureType.COVER_FRONT,
            desc="", data=values.cover.data,
        ))
    # ID3v2.3 : le plus compatible (autoradios, Windows…). v1=0 supprime l'ID3v1.
    tags.update_to_v23()
    tags.save(path, v1=0, v2_version=3)


def _write_flac(path: str, values: TagValues) -> None:
    audio = FLAC(path)
    if audio.tags is None:
        audio.add_tags()
    audio.tags.clear()
    for key, vkey in _VORBIS_KEYS.items():
        value = values.get(key).strip()
        if key == "date":
            value = year_only(value)
        if not value:
            continue
        if key in ("artist", "genre"):
            audio.tags[vkey] = _split(value)
        else:
            audio.tags[vkey] = [value]
    if values.lyrics.strip():
        audio.tags["LYRICS"] = [values.lyrics]
    audio.clear_pictures()
    if values.cover is not None:
        pic = Picture()
        pic.type = PictureType.COVER_FRONT
        pic.mime = values.cover.mime
        pic.desc = ""
        pic.data = values.cover.data
        _fill_picture_size(pic)
        audio.add_picture(pic)
    audio.save(deleteid3=True)


def _fill_picture_size(pic: Picture) -> None:
    try:
        from gi.repository import GdkPixbuf
        loader = GdkPixbuf.PixbufLoader()
        loader.write(pic.data)
        loader.close()
        pixbuf = loader.get_pixbuf()
        if pixbuf is not None:
            pic.width = pixbuf.get_width()
            pic.height = pixbuf.get_height()
            pic.depth = 24
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Utilitaires d'affichage
# ---------------------------------------------------------------------------

def format_duration(seconds: float) -> str:
    seconds = int(round(seconds))
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def describe(info: AudioInfo) -> str:
    parts = [info.format]
    if info.bitrate:
        parts.append(f"{round(info.bitrate / 1000)} kb/s")
    if info.sample_rate:
        khz = info.sample_rate / 1000
        parts.append(f"{khz:g} kHz".replace(".", ","))
    if info.bits_per_sample:
        parts.append(f"{info.bits_per_sample} bits")
    if info.length:
        parts.append(format_duration(info.length))
    return " · ".join(parts)
