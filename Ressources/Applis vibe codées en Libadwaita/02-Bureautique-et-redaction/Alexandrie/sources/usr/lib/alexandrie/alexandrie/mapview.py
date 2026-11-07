"""Cartes natives libshumate (fonds OpenStreetMap)."""

import urllib.parse

import gi

gi.require_version("Shumate", "1.0")
from gi.repository import Adw, Gio, Gtk, Shumate  # noqa: E402

_registry = None


def _source():
    global _registry
    if _registry is None:
        _registry = Shumate.MapSourceRegistry.new_with_defaults()
    return _registry.get_by_id(Shumate.MAP_SOURCE_OSM_MAPNIK)


def guess_zoom(description):
    d = (description or "").lower()
    if any(k in d for k in ("pays", "état ", "continent", "empire", "royaume", "océan", "mer ", "country")):
        return 4.5
    if any(k in d for k in ("région", "province", "département", "massif", "île", "fleuve",
                            "state", "region", "county")):
        return 7
    if any(k in d for k in ("ville", "commune", "capitale", "cité", "village",
                            "city", "town", "municipality", "hamlet")):
        return 11.5
    return 10


def make_map(lat, lon, zoom, compact=False):
    m = Shumate.SimpleMap()
    m.set_map_source(_source())
    if compact:
        # SimpleMap n'a pas de propriété « show-scale » : on masque directement les widgets.
        m.set_show_zoom_buttons(False)
        m.get_scale().set_visible(False)
        m.get_compass().set_visible(False)
    layer = Shumate.MarkerLayer.new(m.get_viewport())
    pin = Shumate.Marker()
    pin.set_child(Gtk.Image(icon_name="mark-location-symbolic", pixel_size=32 if not compact else 24,
                            css_classes=["error"]))
    pin.set_location(lat, lon)
    layer.add_marker(pin)
    m.add_overlay_layer(layer)
    m.get_viewport().set_zoom_level(zoom)
    m.get_map().center_on(lat, lon)
    return m


def maps_available():
    return Gio.AppInfo.get_default_for_uri_scheme("geo") is not None


def open_in_maps(window, lat, lon):
    Gtk.UriLauncher(uri=f"geo:{lat:.6f},{lon:.6f}").launch(window, None, None, None)


def search_in_maps(window, name):
    """Lieu sans coordonnées : on laisse GNOME Cartes chercher le nom."""
    q = urllib.parse.quote(name)
    uri = f"maps:q={q}" if Gio.AppInfo.get_default_for_uri_scheme("maps") else f"geo:0,0?q={q}"
    Gtk.UriLauncher(uri=uri).launch(window, None, None, None)


class MapCard(Gtk.Box):
    """Petite carte du panneau Repères, avec « Agrandir » et « Ouvrir dans Cartes »."""

    def __init__(self, window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.win = window
        self.coords = None
        self.title = ""
        self.zoom = 10
        self.heading = Gtk.Label(label="Lieu", xalign=0, css_classes=["heading"], wrap=True)
        self.append(self.heading)
        self.frame = Gtk.Frame(height_request=210, css_classes=["alex-map"])
        self.frame.set_overflow(Gtk.Overflow.HIDDEN)
        self.append(self.frame)
        btns = Gtk.Box(spacing=6, homogeneous=True)
        big = Gtk.Button(label="Agrandir")
        big.connect("clicked", self._enlarge)
        self.maps_btn = Gtk.Button(label="Ouvrir dans Cartes")
        self.maps_btn.connect("clicked", lambda *_: self.coords and open_in_maps(self.win, *self.coords))
        btns.append(big)
        btns.append(self.maps_btn)
        self.append(btns)

    def show(self, lat, lon, title, description, heading="Lieu"):
        self.heading.set_label(heading)
        self.coords = (lat, lon)
        self.title = title
        self.zoom = guess_zoom(description)
        self.frame.set_child(make_map(lat, lon, self.zoom, compact=True))
        self.maps_btn.set_visible(self.win.settings.get_boolean("maps-button") and maps_available())

    def _enlarge(self, *_):
        if not self.coords:
            return
        w = Adw.Window(transient_for=self.win, default_width=1000, default_height=720, title=self.title)
        tv = Adw.ToolbarView()
        header = Adw.HeaderBar(title_widget=Adw.WindowTitle(title=self.title, subtitle="OpenStreetMap"))
        if self.win.settings.get_boolean("maps-button") and maps_available():
            b = Gtk.Button(label="Ouvrir dans Cartes")
            b.connect("clicked", lambda *_: open_in_maps(self.win, *self.coords))
            header.pack_end(b)
        tv.add_top_bar(header)
        tv.set_content(make_map(*self.coords, min(self.zoom + 2, 16)))
        w.set_content(tv)
        w.present()
