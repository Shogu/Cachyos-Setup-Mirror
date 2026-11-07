"""Réservé aux tests : comble ce qui manque à libadwaita 1.5 / GTK 4.14 du conteneur de test.

L'appli vise GNOME 51 ; ce module n'est jamais installé.
"""
import re

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk  # noqa: E402

if Adw.get_minor_version() < 8:
    class Spinner(Gtk.Spinner):
        def __init__(self, **kw):
            super().__init__(spinning=True, **kw)
    Adw.Spinner = Spinner

    class ShortcutsDialog(Adw.Dialog):
        def __init__(self, **kw):
            super().__init__(title="Raccourcis", **kw)
            self._boite = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin_top=12, margin_start=12, margin_end=12)
            self.set_child(self._boite)

        def add(self, section):
            self._boite.append(section)

    class ShortcutsSection(Gtk.Box):
        def __init__(self, title=""):
            super().__init__(orientation=Gtk.Orientation.VERTICAL)
            self.append(Gtk.Label(label=title, css_classes=["heading"]))

        def add(self, item):
            self.append(item)

    class ShortcutsItem(Gtk.Label):
        @classmethod
        def new(cls, titre, touches):
            return cls(label=f"{titre}    {touches}", xalign=0)

    Adw.ShortcutsDialog, Adw.ShortcutsSection, Adw.ShortcutsItem = ShortcutsDialog, ShortcutsSection, ShortcutsItem
    def accent(_self):
        couleur = Gdk.RGBA()
        couleur.red, couleur.green, couleur.blue, couleur.alpha = 0.21, 0.52, 0.89, 1.0
        return couleur
    Adw.StyleManager.get_accent_color_rgba = accent

    COULEURS = {"blue-3": "#3584e4", "green-4": "#2ec27e", "orange-3": "#ff7800", "purple-3": "#9141ac",
                "yellow-4": "#f5c211", "red-3": "#e01b24", "accent-bg-color": "@accent_bg_color"}
    _charger = Gtk.CssProvider.load_from_path

    def load_from_path(self, chemin):
        css = open(chemin).read()
        css = re.sub(r"var\(--([a-z0-9-]+)\)", lambda m: COULEURS.get(m.group(1), "black"), css)
        self.load_from_string(css)
    Gtk.CssProvider.load_from_path = load_from_path
