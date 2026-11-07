"""Vidange — point d'entrée."""

import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, Gtk  # noqa: E402

from . import backend as be  # noqa: E402
from .window import VidangeWindow  # noqa: E402

VERSION = "1.3.1"


class VidangeApp(Adw.Application):

    def __init__(self):
        super().__init__(application_id=be.APP_ID,
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.add_simple_action("about", self.on_about)
        self.add_simple_action("quit", lambda *_: self.quit())
        self.set_accels_for_action("app.quit", ["<Control>q"])
        self.set_accels_for_action("window.close", ["<Control>w"])

    def add_simple_action(self, name, callback):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)

    def do_activate(self):
        window = self.props.active_window or VidangeWindow(self)
        window.present()

    def on_about(self, *_):
        about = Adw.AboutDialog(
            application_name="Vidange",
            application_icon=be.APP_ID,
            version=VERSION,
            developer_name="Shogu",
            comments="Nettoyer le système : orphelins, caches, journaux, navigateurs.",
            license_type=Gtk.License.GPL_3_0,
        )
        about.present(self.props.active_window)


def main():
    return VidangeApp().run(sys.argv)
