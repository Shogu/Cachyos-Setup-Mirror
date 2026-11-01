from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import unquote, urlsplit


MUSIC_EXTENSIONS = {
    "aac",
    "aiff",
    "alac",
    "ape",
    "flac",
    "m4a",
    "mka",
    "mid",
    "midi",
    "mp3",
    "oga",
    "ogg",
    "opus",
    "wav",
    "wma",
}

VIDEO_EXTENSIONS = {
    "3gp",
    "avi",
    "flv",
    "m2ts",
    "m4v",
    "mkv",
    "mov",
    "mp4",
    "mpeg",
    "mpg",
    "ogv",
    "ts",
    "vob",
    "webm",
    "wmv",
}

DOCUMENT_EXTENSIONS = {
    "csv",
    "djvu",
    "doc",
    "docx",
    "epub",
    "html",
    "md",
    "mobi",
    "odp",
    "ods",
    "odt",
    "pdf",
    "ppt",
    "pptx",
    "rtf",
    "tex",
    "txt",
    "xls",
    "xlsx",
}

YOUTUBE_SERVICE_HOSTS = {
    "youtube.com",
    "youtu.be",
    "youtube-nocookie.com",
    "ytimg.com",
}
YOUTUBE_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
MEDIA_HINT = re.compile(
    r"\b(audio|music|musique|video|vidéo|videos|vidéos|"
    r"3gp|avi|flv|m2ts|m4v|mkv|mov|mp4|mpeg|mpg|ogv|ts|vob|webm|wmv|"
    r"aac|aiff|alac|ape|flac|m4a|mka|mid|midi|mp3|oga|ogg|opus|wav|wma)\b",
    re.IGNORECASE,
)


def _host_from_value(value: Any) -> str:
    raw = unquote(str(value or "")).strip()
    if not raw:
        return ""
    try:
        parsed = urlsplit(raw if "://" in raw else f"//{raw}")
    except ValueError:
        return ""
    hostname = parsed.hostname
    if hostname:
        return hostname.removeprefix("www.").lower()
    return raw.split("/", 1)[0].strip().lower()


def _is_youtube_host(host: str) -> bool:
    return (
        host in YOUTUBE_SERVICE_HOSTS
        or any(host.endswith("." + suffix) for suffix in YOUTUBE_SERVICE_HOSTS)
        or host == "googlevideo.com"
        or host.endswith(".googlevideo.com")
    )


def host_name(item: dict[str, Any]) -> str:
    """Return a compact host/service name from a JDownloader item."""

    first_host = ""
    looks_like_youtube_id = False
    values = (
        item.get("host"),
        item.get("hosts"),
        item.get("url"),
    )
    for value in values:
        if isinstance(value, (list, tuple)):
            candidates = value
        else:
            candidates = (value,)
        for candidate in candidates:
            host = _host_from_value(candidate)
            if not host:
                continue
            if not first_host:
                first_host = host
            if YOUTUBE_VIDEO_ID.fullmatch(host):
                looks_like_youtube_id = True
            # LinkGrabber can expose the YouTube video id (for example
            # ``zI6iatmdlv8``) in ``host`` while the actual URL points to
            # youtube.com or a googlevideo CDN. Prefer the canonical service
            # whenever any field identifies YouTube.
            if _is_youtube_host(host):
                return "youtube.com"
    if looks_like_youtube_id:
        # Some YouTube LinkGrabber results expose only the eleven-character
        # video id as their host. Restrict the heuristic to media-looking
        # entries so a random hostname is not relabelled as YouTube.
        media_values = (
            item.get("name"),
            item.get("extension"),
            item.get("variantName"),
            item.get("mimeType"),
            item.get("contentType"),
        )
        if any(MEDIA_HINT.search(str(value or "")) for value in media_values):
            return "youtube.com"
    return first_host


def source_host_name(item: dict[str, Any]) -> str:
    """Return the service that originated a LinkGrabber item.

    A resolved media URL can point at a short-lived CDN host or even expose
    the YouTube video id in its ``host`` field.  The whitelist must therefore
    prefer origin/source/referrer fields and the original URL before falling
    back to the compact display host.
    """

    source_keys = (
        "origin",
        "originUrl",
        "origin_url",
        "source",
        "sourceUrl",
        "source_url",
        "referrer",
        "referer",
        "url",
    )
    for key in source_keys:
        value = item.get(key)
        candidates = value if isinstance(value, (list, tuple)) else (value,)
        for candidate in candidates:
            host = _host_from_value(candidate)
            if not host or YOUTUBE_VIDEO_ID.fullmatch(host):
                continue
            if _is_youtube_host(host):
                return "youtube.com"
            return host

    # The API may expose only a canonicalized host plus a media-like item.
    # Reuse the existing conservative YouTube heuristic in that case.
    display_host = host_name(item)
    return display_host


def file_category(item: dict[str, Any]) -> str:
    """Return a small display category for a JDownloader LinkGrabber item."""

    mime_values = (
        str(item.get(key) or "").lower()
        for key in ("mimeType", "mime_type", "mime", "contentType", "content_type", "type")
    )
    for mime in mime_values:
        if mime.startswith("audio/"):
            return "music"
        if mime.startswith("video/"):
            return "videos"
        if re.search(r"\b(audio|music|musique)\b", mime):
            return "music"
        if re.search(r"\b(video|vidéo|videos|vidéos)\b", mime):
            return "videos"
        if mime.startswith(
            (
                "application/pdf",
                "application/epub",
                "application/msword",
                "application/vnd.",
                "text/plain",
                "text/csv",
                "text/markdown",
            )
        ):
            return "documents"

    extensions: set[str] = set()
    for key in ("extension", "name", "fileName", "filename", "url", "variantName"):
        value = unquote(str(item.get(key) or "")).lower().strip()
        if not value:
            continue
        if key == "extension":
            extensions.add(value.lstrip(".").split("?", 1)[0].split("#", 1)[0])
            continue
        if key == "variantName":
            if re.search(r"\b(audio|music|musique)\b", value):
                return "music"
            if re.search(r"\b(video|vidéo|videos|vidéos)\b", value):
                return "videos"
            extensions.update(
                re.findall(
                    r"\b(?:aac|aiff|alac|ape|flac|m4a|mka|mid|midi|mp3|oga|ogg|opus|wav|wma|"
                    r"3gp|avi|flv|m2ts|m4v|mkv|mov|mp4|mpeg|mpg|ogv|ts|vob|webm|wmv)\b",
                    value,
                )
            )
        path = urlsplit(value).path
        suffix = PurePosixPath(path).suffix.lower().lstrip(".")
        if suffix:
            extensions.add(suffix)
        extensions.update(re.findall(r"\.([a-z0-9]{2,6})(?:$|[^a-z0-9])", value))

    if extensions & MUSIC_EXTENSIONS:
        return "music"
    if extensions & VIDEO_EXTENSIONS:
        return "videos"
    if extensions & DOCUMENT_EXTENSIONS:
        return "documents"
    return "other"


def as_number(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def format_bytes(value: Any) -> str:
    amount = max(0, as_number(value))
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    number = float(amount)
    unit = units[0]
    for unit in units:
        if number < 1024 or unit == units[-1]:
            break
        number /= 1024
    if unit == "B":
        return f"{int(number)} B"
    return f"{number:.1f} {unit}"


def format_speed(value: Any) -> str:
    speed = as_number(value)
    return "à l'arrêt" if speed <= 0 else f"{format_bytes(speed)}/s"


def format_duration_seconds(value: Any) -> str:
    """Format a duration that is already expressed in seconds."""
    seconds = as_number(value, -1)
    if seconds < 0:
        return "—"
    if seconds < 60:
        return f"{seconds} s"
    minutes, remainder = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes} min {remainder:02d} s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes:02d}"


def format_eta(value: Any) -> str:
    """Format JDownloader's legacy ETA value.

    The download list uses ``estimate_eta_seconds`` instead because some
    hosts expose a stale or otherwise unreliable ``eta`` field.
    """
    raw = as_number(value, -1)
    if raw < 0:
        return "—"
    seconds = raw // 1000 if raw >= 1000 else raw
    return format_duration_seconds(seconds)


def estimate_eta_seconds(
    item: dict[str, Any], observed_speed: int | None = None
) -> int | None:
    """Estimate remaining time from bytes and an observed transfer rate.

    JDownloader's ``eta`` is not consistent enough across hosts to display it
    directly. Streaming hosts can report a short stale value while the
    transfer still has a long way to go. A missing ETA is preferable to a
    misleading countdown, so a known total and a measured rate are required.
    """
    total = as_number(item.get("bytesTotal"), -1)
    loaded = max(0, as_number(item.get("bytesLoaded"), 0))
    if total <= 0 or loaded >= total:
        return None

    speed = as_number(observed_speed, 0)
    if speed <= 0:
        return None

    remaining = total - loaded
    return (remaining + speed - 1) // speed


def progress_for(item: dict[str, Any]) -> float:
    total = as_number(item.get("bytesTotal"))
    loaded = as_number(item.get("bytesLoaded"))
    if total <= 0:
        return 1.0 if item.get("finished") else 0.0
    return max(0.0, min(1.0, loaded / total))


def progress_percent(item: dict[str, Any]) -> int | None:
    """Return the completed percentage when JDownloader knows the total."""

    total = as_number(item.get("bytesTotal"), -1)
    if total <= 0:
        return 100 if item.get("finished") else None
    loaded = max(0, min(total, as_number(item.get("bytesLoaded"), 0)))
    return int((loaded * 100) / total)


def status_text(item: dict[str, Any]) -> str:
    if item.get("finished"):
        return "Terminé"
    if item.get("enabled") is False and not item.get("skipped"):
        return "En pause"
    if item.get("running"):
        return "Téléchargement"
    if item.get("skipped"):
        return "Ignoré"
    status = str(item.get("status") or "En attente").strip()
    translations = {
        "WAITING": "En attente",
        "QUEUED": "En file",
        "CHECKING": "Vérification",
        "CONNECTING": "Connexion",
        "DOWNLOADING": "Téléchargement",
        "FINISHED": "Terminé",
        "ERROR": "Erreur",
        "OFFLINE": "Hors ligne",
        "TEMP_UNAVAILABLE": "Temporairement indisponible",
        "RETRYING": "Nouvelle tentative",
    }
    return translations.get(status.upper(), status or "En attente")
