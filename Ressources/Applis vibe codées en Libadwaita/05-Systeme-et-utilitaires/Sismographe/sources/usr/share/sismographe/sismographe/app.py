"""Point d’entrée de Sismographe."""
import os
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, Gtk  # noqa: E402

from . import __version__  # noqa: E402
from . import widgets  # noqa: E402
from .window import APP_ID, Window  # noqa: E402


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        for name, callback, accels in (("about", self.about, []),
                                       ("quit", lambda *_: self.quit(), ["<Control>q"])):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)
            if accels:
                self.set_accels_for_action(f"app.{name}", accels)

    def do_startup(self):
        Adw.Application.do_startup(self)
        Gtk.Window.set_default_icon_name(APP_ID)
        # lancement depuis les sources : les icônes ne sont pas encore dans hicolor
        local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "icons")
        if os.path.isdir(local):
            Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).add_search_path(local)
        widgets.install_css()

    def do_activate(self):
        window = self.get_active_window() or Window(self)
        window.present()

    def about(self, *_):
        about = Adw.AboutDialog(
            application_name="Sismographe", application_icon=APP_ID, version=__version__,
            developer_name="Ogu", license_type=Gtk.License.GPL_3_0,
            comments="Ausculte le système : journaux, démarrage, services, plantages, stockage.\n"
                     "Dessiné au pied du puy de Dôme.")
        about.present(self.get_active_window())


def main():
    return Application().run(sys.argv)
