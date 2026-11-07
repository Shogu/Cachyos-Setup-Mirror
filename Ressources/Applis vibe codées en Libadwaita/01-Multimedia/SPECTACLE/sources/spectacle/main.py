import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

APP_ID = "io.gitlab.shogu.Spectacle"


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.set_accels_for_action("win.fullscreen", ["F11"])
        self.set_accels_for_action("win.leave-fullscreen", ["Escape"])
        self.set_accels_for_action("win.focus-search", ["<Control>l", "<Control>f"])
        self.set_accels_for_action("window.close", ["<Control>w"])
        self.set_accels_for_action("app.quit", ["<Control>q"])
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.quit())
        self.add_action(quit_action)

    def do_activate(self):
        from .window import Window

        window = self.get_active_window() or Window(self)
        window.present()


def main():
    GLib.set_prgname(APP_ID)
    GLib.set_application_name("Spectacle")
    Gtk.Window.set_default_icon_name(APP_ID)
    return Application().run(sys.argv)
