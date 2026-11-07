"""Taille et état de la fenêtre d'une session à l'autre."""

import json
import os

from config import DATA_DIR, STATE_FILE
from journal import log


def load():
    try:
        with open(STATE_FILE, encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as error:
        log("état : lecture impossible (%s)" % error)
        return {}


def save(state):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
    except OSError as error:
        log("état : écriture impossible (%s)" % error)
