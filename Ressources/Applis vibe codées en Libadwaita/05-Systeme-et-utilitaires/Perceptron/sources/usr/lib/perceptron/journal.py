"""Journal de diagnostic, vidé à chaque lancement."""

import os
import time

from config import DATA_DIR, LOG_FILE


def reset():
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LOG_FILE, "w", encoding="utf-8"):
        pass


def log(message):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as handle:
            handle.write(time.strftime("%H:%M:%S ") + message + "\n")
    except OSError:
        pass
