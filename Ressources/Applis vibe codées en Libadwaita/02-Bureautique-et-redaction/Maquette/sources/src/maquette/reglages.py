"""Accès aux réglages GSettings et instantané transmis au moteur."""

from gi.repository import Gio

ID_APPLI = "io.gitlab.shogu.Maquette"


def nouveaux_reglages() -> Gio.Settings:
    return Gio.Settings.new(ID_APPLI)


def instantane(s: Gio.Settings) -> dict:
    """Valeurs utiles au fil du moteur, qui ne lit pas GSettings lui-même."""
    return {
        "images_marges": s.get_double("images-marges"),
        "images_mode": s.get_string("images-mode"),
        "images_orientation_auto": s.get_boolean("images-orientation-auto"),
        "imposition": s.get_string("imposition"),
        "compresser": s.get_boolean("compresser"),
        "reduire_images": s.get_boolean("reduire-images"),
        "dpi_images": s.get_int("dpi-images"),
        "effacer_metadonnees": s.get_boolean("effacer-metadonnees"),
    }
