"""Favoris : titre, chaîne et adresse, enregistrés dans ~/.local/share/spectacle-ogu/favoris.json."""

import json
from pathlib import Path

from gi.repository import GLib

PATH = Path(GLib.get_user_data_dir()) / "spectacle-ogu" / "favoris.json"


class Favorites:
    def __init__(self):
        try:
            self.items = json.loads(PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.items = []

    def contains(self, url):
        return any(item["url"] == url for item in self.items)

    def add(self, title, channel, url):
        if not self.contains(url):
            self.items.insert(0, {"title": title, "channel": channel, "url": url})
            self._save()

    def remove(self, url):
        self.items = [item for item in self.items if item["url"] != url]
        self._save()

    def _save(self):
        PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.items, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(PATH)
