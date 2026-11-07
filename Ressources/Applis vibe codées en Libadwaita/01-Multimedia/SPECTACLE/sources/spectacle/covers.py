"""Miniatures YouTube mises en cache localement (~/.cache/spectacle-ogu/covers) pour MPRIS.

Les extensions de lecteurs arrondissent une pochette locale (file://), pas une adresse web.
On prend « mqdefault.jpg » (320×180, 16:9, sans bandes noires, en JPEG lisible partout).
"""

import os
import re
from pathlib import Path

import gi

gi.require_version("Soup", "3.0")
from gi.repository import Gio, GLib, Soup

DIR = Path(GLib.get_user_cache_dir()) / "spectacle-ogu" / "covers"
KEEP = 60
BASE = os.environ.get("SPECTACLE_COVER_BASE", "https://i.ytimg.com/vi")
ID_RE = re.compile(r"^[\w-]{6,20}$")


class Covers:
    def __init__(self):
        self._session = Soup.Session(timeout=20)
        self._cancellable = None

    def fetch(self, video_id, callback):
        """callback(uri) avec l'adresse file:// de la miniature, ou rien si elle est indisponible."""
        if self._cancellable:
            self._cancellable.cancel()
        if not video_id or not ID_RE.match(video_id):
            return
        path = DIR / f"{video_id}.jpg"
        if path.is_file():
            callback(GLib.filename_to_uri(str(path), None))
            return
        self._cancellable = Gio.Cancellable()
        message = Soup.Message.new("GET", f"{BASE}/{video_id}/mqdefault.jpg")
        self._session.send_and_read_async(message, GLib.PRIORITY_LOW, self._cancellable, self._on_read, message, path, callback)

    def cancel(self):
        if self._cancellable:
            self._cancellable.cancel()
            self._cancellable = None
        self._session.abort()

    def _on_read(self, session, result, message, path, callback):
        try:
            data = session.send_and_read_finish(result).get_data()
        except GLib.Error:
            return
        if message.get_status() != Soup.Status.OK or not data:
            return
        DIR.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)
        self._prune()
        callback(GLib.filename_to_uri(str(path), None))

    @staticmethod
    def _prune():
        files = sorted(DIR.glob("*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in files[KEEP:]:
            old.unlink(missing_ok=True)
