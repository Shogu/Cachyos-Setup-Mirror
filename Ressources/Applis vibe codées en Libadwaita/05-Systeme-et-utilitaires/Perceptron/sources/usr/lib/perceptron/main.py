"""Perceptron : coquille GTK4/libadwaita autour de l'interface web d'OpenCode."""

import ctypes
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")

from gi.repository import GLib  # noqa: E402

import journal  # noqa: E402
from app import PerceptronApp  # noqa: E402
from config import APP_ID, APP_NAME  # noqa: E402

PR_SET_NAME = 15


def main():
    ctypes.CDLL(None).prctl(PR_SET_NAME, b"perceptron", 0, 0, 0)
    GLib.set_prgname(APP_ID)
    GLib.set_application_name(APP_NAME)
    journal.reset()
    return PerceptronApp().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
