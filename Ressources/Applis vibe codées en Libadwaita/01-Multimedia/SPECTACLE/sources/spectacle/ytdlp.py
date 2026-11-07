"""yt-dlp officiel, téléchargé et tenu à jour dans le dossier de l'utilisateur (partagé avec Chihiro).

Premier usage : téléchargement, puis vérification de la somme SHA-256 publiée par yt-dlp.
Ensuite : si la copie a plus de MAX_AGE, elle sert quand même et une mise à jour part en arrière-plan.
Le remplacement est atomique (fichier temporaire puis renommage), donc sans risque si les deux applis tournent.
"""

import hashlib
import os
import time
from pathlib import Path

import gi

gi.require_version("Soup", "3.0")
from gi.repository import GLib, Soup

DIR = Path(GLib.get_user_data_dir()) / "yt-dlp-ogu"
BIN = DIR / "yt-dlp"
BASE = os.environ.get("YTDLP_OGU_BASE", "https://github.com/yt-dlp/yt-dlp/releases/latest/download")
ASSET = "yt-dlp_linux"
MAX_AGE = 7 * 24 * 3600


class YtDlp:
    def __init__(self):
        self._session = Soup.Session(timeout=60)
        self._waiting = []
        self._busy = False

    def get(self, callback):
        """callback(path, erreur) : path est prêt à l'emploi, ou None avec un message d'erreur."""
        if BIN.is_file():
            callback(BIN, None)
            if time.time() - BIN.stat().st_mtime > MAX_AGE:
                self._download(lambda *_: None)
            return
        self._download(callback)

    def cancel(self):
        self._session.abort()

    def _download(self, callback):
        self._waiting.append(callback)
        if self._busy:
            return
        self._busy = True
        self._fetch(f"{BASE}/SHA2-256SUMS", self._on_sums)

    def _fetch(self, url, handler):
        message = Soup.Message.new("GET", url)
        self._session.send_and_read_async(message, GLib.PRIORITY_LOW, None, handler, message)

    def _read(self, session, result, message):
        data = session.send_and_read_finish(result).get_data()
        if message.get_status() != Soup.Status.OK:
            raise OSError(f"HTTP {message.get_status()}")
        return data

    def _on_sums(self, session, result, message):
        try:
            sums = self._read(session, result, message).decode()
            expected = next(line.split()[0] for line in sums.splitlines() if line.split()[-1:] == [ASSET])
        except (GLib.Error, OSError, StopIteration, UnicodeDecodeError) as exc:
            self._finish(None, f"Sommes de contrôle de yt-dlp introuvables ({exc}).")
            return
        self._fetch(f"{BASE}/{ASSET}", lambda s, r, m: self._on_binary(s, r, m, expected))

    def _on_binary(self, session, result, message, expected):
        try:
            data = self._read(session, result, message)
        except (GLib.Error, OSError) as exc:
            self._finish(None, f"Téléchargement de yt-dlp impossible ({exc}).")
            return
        if hashlib.sha256(data).hexdigest() != expected:
            self._finish(None, "yt-dlp téléchargé corrompu (somme SHA-256 différente) : ignoré.")
            return
        DIR.mkdir(parents=True, exist_ok=True)
        tmp = DIR / f".yt-dlp.{os.getpid()}.tmp"
        tmp.write_bytes(data)
        tmp.chmod(0o755)
        tmp.replace(BIN)
        self._finish(BIN, None)

    def _finish(self, path, error):
        self._busy = False
        if error and BIN.is_file():
            path, error = BIN, None
        callbacks, self._waiting = self._waiting, []
        for callback in callbacks:
            callback(path, error)
