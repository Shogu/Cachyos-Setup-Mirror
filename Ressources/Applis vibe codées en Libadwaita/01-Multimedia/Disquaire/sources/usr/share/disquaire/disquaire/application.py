# SPDX-License-Identifier: GPL-3.0-or-later
"""Application Disquaire."""

import os
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gst", "1.0")

from gi.repository import Adw, Gdk, Gio, Gtk  # noqa: E402

from . import __version__  # noqa: E402
from .window import Window  # noqa: E402

APP_ID = "io.gitlab.shogu.Disquaire"

CSS = """
.cover { border-radius: 12px; }
.cover-placeholder { border-radius: 12px; background-color: alpha(currentColor, 0.06); }
.thumb { border-radius: 6px; }
.thumb-placeholder { border-radius: 6px; background-color: alpha(currentColor, 0.08); }
.dirty-dot {
  min-width: 8px; min-height: 8px; border-radius: 99px;
  background-color: @accent_bg_color;
}
.format-badge {
  font-size: 0.75em; font-weight: 800; letter-spacing: 0.04em;
  padding: 1px 7px; border-radius: 99px;
  background-color: alpha(currentColor, 0.1);
}
.lyrics-frame { border-radius: 12px; }
.lyrics-frame > overlay > scrolledwindow,
.lyrics-frame textview, .lyrics-frame textview > text { background: transparent; }
.lyrics-frame { background-color: @card_bg_color; }
.track-list > row { padding-top: 2px; padding-bottom: 2px; }
treeexpander:drop(active) {
  border-radius: 6px;
  background-color: alpha(@accent_bg_color, 0.18);
  box-shadow: inset 0 0 0 2px @accent_bg_color;
}
.lyrics-badge {
  font-size: 0.75em; font-weight: 800; padding: 1px 7px; border-radius: 99px;
  color: @accent_fg_color; background-color: @accent_bg_color;
}
.keep-badge {
  font-size: 0.8em; font-weight: 700; padding: 2px 8px; border-radius: 99px;
  color: @accent_fg_color; background-color: @accent_bg_color;
}
"""

SHORTCUTS = [
    ("Fichier", [
        ("<Ctrl>s", "Enregistrer la sélection"),
        ("<Ctrl><Shift>s", "Tout enregistrer"),
        ("F2", "Renommer le fichier"),
        ("<Ctrl>p", "Lire / mettre en pause"),
    ]),
    ("Navigation", [
        ("<Ctrl>f", "Rechercher"),
        ("F5", "Rafraîchir la liste"),
        ("F9", "Afficher / masquer les dossiers"),
        ("<Ctrl>a", "Tout sélectionner (dans la liste)"),
    ]),
    ("Général", [
        ("<Ctrl>w", "Fermer la fenêtre"),
        ("<Ctrl>q", "Quitter"),
    ]),
]


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.HANDLES_OPEN)

    def do_startup(self):
        Adw.Application.do_startup(self)
        provider = Gtk.CssProvider()
        provider.load_from_string(CSS) if hasattr(provider, "load_from_string") \
            else provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
        # Icônes fournies avec l'appli : indépendantes de la version du thème.
        Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).add_search_path(
            os.path.join(os.path.dirname(__file__), "icons"))
        for name, callback in (
            ("about", self._about),
            ("shortcuts", self._shortcuts),
            ("quit", self._quit),
        ):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)
        for action, accels in (
            ("app.quit", ["<Ctrl>q"]),
            ("window.close", ["<Ctrl>w"]),
            ("win.save", ["<Ctrl>s"]),
            ("win.save-all", ["<Ctrl><Shift>s"]),
            ("win.refresh", ["F5", "<Ctrl>r"]),
            ("win.search", ["<Ctrl>f"]),
            ("win.rename", ["F2"]),
            ("win.play", ["<Ctrl>p"]),
            ("win.toggle-sidebar", ["F9"]),
            ("win.preferences", ["<Ctrl>comma"]),
        ):
            self.set_accels_for_action(action, accels)

    def do_activate(self):
        win = self.get_active_window()
        if win is None:
            win = Window(self)
        win.present()

    def do_open(self, files, n_files, hint):
        path = files[0].get_path() if files else None
        win = self.get_active_window()
        if win is None:
            win = Window(self, path)
        elif path:
            win.open_path(path)
        win.present()

    def _quit(self, *_):
        for win in list(self.get_windows()):
            win.close()

    def _about(self, *_):
        kwargs = dict(
            application_name="Disquaire",
            application_icon=APP_ID,
            version=__version__,
            developer_name="Shogu",
            comments="Éditeur de tags MP3 et FLAC : ne garde que l'essentiel.",
            license_type=Gtk.License.GPL_3_0,
            website="https://gitlab.com/shogu/disquaire",
        )
        Adw.AboutDialog(**kwargs).present(self.get_active_window())

    def _shortcuts(self, *_):
        dialog = Adw.ShortcutsDialog()
        for title, items in SHORTCUTS:
            section = Adw.ShortcutsSection(title=title)
            for accel, label in items:
                section.add(Adw.ShortcutsItem(title=label, accelerator=accel))
            dialog.add(section)
        dialog.present(self.get_active_window())


def main(argv=None) -> int:
    app = Application()
    return app.run(argv if argv is not None else sys.argv)
