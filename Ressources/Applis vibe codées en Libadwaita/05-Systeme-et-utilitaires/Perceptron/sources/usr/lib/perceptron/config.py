import os
import re

from gi.repository import GLib

APP_ID = "io.gitlab.shogu.Perceptron"
APP_NAME = "Perceptron"
VERSION = "1.1.0"
BASE_URL = "http://127.0.0.1:49374"
HOME_URI = BASE_URL + "/#/"
NEW_SESSION_URI = BASE_URL + "/#/new-session"
SESSION_ROUTE = re.compile(r"#/server/([^/?#]+)/session/([^/?#]+)")

DATA_DIR = os.path.join(GLib.get_user_data_dir(), "perceptron")
CACHE_DIR = os.path.join(GLib.get_user_cache_dir(), "perceptron")
WEBKIT_DATA_DIR = os.path.join(DATA_DIR, "data")
STATE_FILE = os.path.join(DATA_DIR, "window.json")
LOG_FILE = os.path.join(DATA_DIR, "perceptron.log")

# L'installateur d'OpenCode n'ajoute son dossier qu'au PATH du shell (fish_add_path),
# invisible pour une appli lancée depuis GNOME.
OPENCODE_FALLBACKS = (
    "~/.opencode/bin/opencode",
    "~/.local/bin/opencode",
    "~/.bun/bin/opencode",
    "~/.npm-global/bin/opencode",
)


def is_local(uri):
    return uri == BASE_URL or uri.startswith(BASE_URL + "/")


def session_uri(server_key, session_id):
    return "%s/#/server/%s/session/%s" % (BASE_URL, server_key, session_id)


def find_opencode():
    found = GLib.find_program_in_path("opencode")
    if found:
        return found
    for candidate in map(os.path.expanduser, OPENCODE_FALLBACKS):
        if os.access(candidate, os.X_OK):
            return candidate
    return None
