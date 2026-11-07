"""Application entry point."""

from __future__ import annotations

import gettext
import locale
import os
import sys
from contextlib import suppress
from gettext import gettext as _
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from .window import PactoWindow  # noqa: E402

APP_ID = "io.github.ugotrevisiol.Pacto"
VERSION = "1.0.0"


class PactoApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self._add_action("quit", lambda *_a: self.quit(), ["<Control>q"])
        self._add_action("about", lambda *_a: self._show_about())
        self.set_accels_for_action("win.refresh", ["<Control>r"])
        self.set_accels_for_action("win.next-change", ["<Control>n"])
        self.set_accels_for_action("win.previous-change", ["<Control>p"])
        self.set_accels_for_action("win.focus-search", ["<Control>f"])

    def do_activate(self) -> None:
        self._load_css()
        Gtk.Window.set_default_icon_name(APP_ID)
        window = self.props.active_window or PactoWindow(application=self)
        window.present()

    def _add_action(self, name: str, callback, accels: list[str] | None = None) -> None:
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if accels:
            self.set_accels_for_action(f"app.{name}", accels)

    def _load_css(self) -> None:
        provider = Gtk.CssProvider()
        provider.load_from_path(str(Path(__file__).parent / "style.css"))
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def _show_about(self) -> None:
        about = Adw.AboutDialog(
            application_name=_("Pacto"),
            application_icon=APP_ID,
            version=VERSION,
            developer_name="Ugo Trevisiol",
            comments=_("Find pacman maintainer files and merge them side by side."),
            license_type=Gtk.License.GPL_3_0,
            website="https://github.com/ugotrevisiol/pacto",
            issue_url="https://github.com/ugotrevisiol/pacto/issues",
        )
        about.present(self.props.active_window)


def main() -> int:
    locale_dir = os.environ.get("PACTO_LOCALEDIR", "/usr/share/locale")
    with suppress(locale.Error):
        locale.setlocale(locale.LC_ALL, "")
    gettext.bindtextdomain("pacto", locale_dir)
    gettext.textdomain("pacto")
    GLib.set_application_name(_("Pacto"))
    try:
        return PactoApplication().run(sys.argv)
    except KeyboardInterrupt:
        return 130
