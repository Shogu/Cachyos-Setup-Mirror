# SPDX-License-Identifier: GPL-3.0-or-later
"""Petits réglages persistants (~/.config/disquaire/config.json)."""

import json
import os

from gi.repository import GLib

_DIR = os.path.join(GLib.get_user_config_dir(), "disquaire")
_PATH = os.path.join(_DIR, "config.json")


def default_root() -> str:
    music = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_MUSIC)
    if music and os.path.isdir(music):
        return music
    return GLib.get_home_dir()


DEFAULTS = {
    "root": None,
    "folder": None,
    "width": 1280,
    "height": 800,
    "maximized": False,
    "paned": 440,
    "sidebar": True,
    "auto_clean": True,
}


def load() -> dict:
    data = dict(DEFAULTS)
    try:
        with open(_PATH, encoding="utf-8") as fh:
            data.update(json.load(fh))
    except (OSError, ValueError):
        pass
    if not data["root"] or not os.path.isdir(data["root"]):
        data["root"] = default_root()
    if data["folder"] and not os.path.isdir(data["folder"]):
        data["folder"] = None
    return data


def save(data: dict) -> None:
    try:
        os.makedirs(_DIR, exist_ok=True)
        tmp = _PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, _PATH)
    except OSError:
        pass
