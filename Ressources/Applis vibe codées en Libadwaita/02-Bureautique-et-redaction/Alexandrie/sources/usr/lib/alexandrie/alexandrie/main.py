"""Point d'entrée d'Alexandrie."""

import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from . import api  # noqa: E402

APP_CSS = """
.alex-badge { background: @accent_bg_color; color: @accent_fg_color; border-radius: 999px;
  font-size: 0.68em; font-weight: bold; min-width: 15px; padding: 0 4px; margin: -5px -8px 0 0; }
.alex-tag { border-radius: 999px; padding: 2px 10px; min-height: 22px; font-size: 0.9em; }
.alex-thumb { border-radius: 8px; }
.alex-map { border-radius: 12px; }
"""


class AlexApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=api.APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        GLib.set_prgname(api.APP_ID)
        GLib.set_application_name("Alexandrie")
        self.settings = None

    def do_startup(self):
        Adw.Application.do_startup(self)
        provider = Gtk.CssProvider()
        provider.load_from_string(APP_CSS)
        display = Gdk.Display.get_default()
        Gtk.StyleContext.add_provider_for_display(display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        # Icônes symboliques embarquées (absentes du thème Adwaita).
        Gtk.IconTheme.get_for_display(display).add_search_path(str(Path(__file__).parent / "icons"))
        for name, cb, accels in (("quit", lambda *_: self.quit(), ["<Control>q"]),
                                 ("about", self._about, None)):
            a = Gio.SimpleAction.new(name, None)
            a.connect("activate", cb)
            self.add_action(a)
            if accels:
                self.set_accels_for_action(f"app.{name}", accels)
        self.set_accels_for_action("window.close", ["<Control><Shift>w"])

    def do_activate(self):
        if self.settings is None:
            src = Gio.SettingsSchemaSource.get_default()
            if not src or not src.lookup(api.APP_ID, True):
                sys.stderr.write(f"Schéma GSettings {api.APP_ID} introuvable. Installez le paquet ou lancez "
                                 "./run.sh depuis les sources.\n")
                self.quit()
                return
            self.settings = Gio.Settings.new(api.APP_ID)
        from .window import AlexWindow
        win = self.props.active_window or AlexWindow(self)
        win.present()

    def _about(self, *_):
        Adw.AboutDialog(
            application_name="Alexandrie", application_icon=api.APP_ID, version=api.VERSION,
            developer_name="Shogu", license_type=Gtk.License.GPL_3_0,
            comments="Visionneuse simple de Wikipédia, Wikisource et Wikimedia Commons en français.",
            website="https://gitlab.com/shogu/alexandrie",
        ).present(self.props.active_window)


def main():
    return AlexApp().run(sys.argv)
