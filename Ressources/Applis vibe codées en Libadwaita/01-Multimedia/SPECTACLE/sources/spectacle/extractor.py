"""Appels asynchrones au binaire yt-dlp privé de l'application. Aucun fichier n'est téléchargé."""

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from gi.repository import Gio

from .ytdlp import YtDlp

QJS = Path(os.environ.get("SPECTACLE_QJS", "/usr/bin/qjs"))
SEARCH_RESULTS = 20
FORMAT = "best[vcodec!=none][acodec!=none][protocol^=http]/best[vcodec!=none][acodec!=none]"
AUDIO_FORMAT = "bestaudio[protocol^=http]/bestaudio/" + FORMAT
URL_RE = re.compile(r"^(https?://)?([\w-]+\.)*(youtube\.com|youtu\.be|youtube-nocookie\.com)/\S+$", re.IGNORECASE)

_KNOWN_ERRORS = (
    (("unsupported url", "is not a valid url", "incomplete youtube id"), "Adresse non valide", "L'adresse saisie n'est pas une vidéo YouTube."),
    (("private video", "video unavailable", "has been removed", "members-only", "not available in your country"),
     "Vidéo indisponible", "La vidéo est privée, supprimée ou bloquée."),
    (("sign in to confirm your age", "age-restricted"), "Vidéo soumise à l'âge", "Lecture impossible sans compte YouTube."),
    (("javascript runtime", "js runtime", "n challenge", "signature solving", "ejs"),
     "Déchiffrement impossible", "Vérifier que quickjs-ng est installé et que l'application est à jour."),
    (("requested format is not available", "no video formats found"), "Aucun format lisible", "Pas de flux audio + vidéo lisible directement."),
    (("unable to download", "timed out", "name or service not known", "network is unreachable", "connection"),
     "YouTube injoignable", "Vérifier la connexion."),
)


class ExtractError(Exception):
    def __init__(self, message, details="", advice=""):
        super().__init__(message)
        self.details = details
        self.advice = advice


@dataclass
class Video:
    title: str
    channel: str
    page_url: str
    stream_url: str = ""
    headers: dict = None
    is_live: bool = False
    thumbnail: str = ""
    duration: float = 0.0
    id: str = ""


def looks_like_url(text):
    return bool(URL_RE.match(text.strip()))


def js_engine_available():
    return QJS.is_file() and os.access(QJS, os.X_OK)


def _explain(stderr):
    lines = [line for line in stderr.splitlines() if line.startswith("ERROR")]
    details = "\n".join(lines) or stderr.strip()[-600:]
    low = details.lower()
    for keys, message, advice in _KNOWN_ERRORS:
        if any(key in low for key in keys):
            return ExtractError(message, details, advice)
    return ExtractError("Extraction impossible.", details)


class Extractor:
    """Une seule requête à la fois : une nouvelle requête annule la précédente."""

    def __init__(self):
        self._cancellable = None
        self._ytdlp = YtDlp()
        self._request = 0

    def cancel(self):
        self._request += 1
        if self._cancellable:
            self._cancellable.cancel()
            self._cancellable = None

    def search(self, query, callback):
        self._run(["--flat-playlist", f"ytsearch{SEARCH_RESULTS}:{query}"], self._parse_search, callback)

    def resolve(self, url, callback, audio_only=False):
        fmt = AUDIO_FORMAT if audio_only else FORMAT
        self._run(["--no-playlist", "-f", fmt, "--", url.strip()], self._parse_video, callback)

    def _run(self, args, parse, callback):
        self.cancel()
        request = self._request
        self._ytdlp.get(lambda path, error: self._spawn(path, error, request, args, parse, callback))

    def shutdown(self):
        self.cancel()
        self._ytdlp.cancel()

    def _spawn(self, ytdlp, error, request, args, parse, callback):
        if request != self._request:
            return
        if error:
            callback(None, ExtractError("yt-dlp indisponible", error, "Vérifier la connexion : yt-dlp est téléchargé au premier lancement."))
            return
        argv = [str(ytdlp), "-J", "--no-warnings", "--ignore-config", "--no-cache-dir", "--no-js-runtimes"]
        if js_engine_available():
            argv += ["--js-runtimes", f"quickjs:{QJS}"]
        argv += args
        self._cancellable = cancellable = Gio.Cancellable()
        flags = Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE
        try:
            process = Gio.Subprocess.new(argv, flags)
        except Exception as exc:
            callback(None, ExtractError("Lancement de yt-dlp impossible.", str(exc)))
            return
        cancellable.connect(lambda _c: process.force_exit())
        process.communicate_utf8_async(None, cancellable, self._on_done, parse, callback, cancellable)

    def _on_done(self, process, result, parse, callback, cancellable):
        if cancellable.is_cancelled():
            return
        if self._cancellable is cancellable:
            self._cancellable = None
        try:
            _ok, stdout, stderr = process.communicate_utf8_finish(result)
        except Exception as exc:
            callback(None, ExtractError("yt-dlp s'est arrêté de façon inattendue.", str(exc)))
            return
        if process.get_exit_status() != 0 or not stdout:
            callback(None, _explain(stderr or ""))
            return
        try:
            callback(parse(json.loads(stdout)), None)
        except (ValueError, KeyError) as exc:
            callback(None, ExtractError("Réponse de yt-dlp inattendue.", str(exc)))

    @staticmethod
    def _parse_search(data):
        videos = []
        for entry in data.get("entries") or []:
            url = entry.get("url") or entry.get("webpage_url")
            if not url and entry.get("id"):
                url = f"https://www.youtube.com/watch?v={entry['id']}"
            if url:
                videos.append(Video(entry.get("title") or "Sans titre", entry.get("channel") or entry.get("uploader") or "", url))
        return videos

    @staticmethod
    def _parse_video(data):
        url = data.get("url") or data.get("manifest_url")
        if not url:
            raise KeyError("url")
        return Video(
            title=data.get("title") or "Sans titre",
            channel=data.get("channel") or data.get("uploader") or "",
            page_url=data.get("webpage_url") or "",
            stream_url=url,
            headers=data.get("http_headers") or {},
            is_live=bool(data.get("is_live")),
            thumbnail="",
            id=data.get("id") or "",
            duration=float(data.get("duration") or 0),
        )
