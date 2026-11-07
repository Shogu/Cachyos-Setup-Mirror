"""Affiche un Gdk.Paintable en remplissant le widget, recadré autour d'un point d'intérêt horizontal."""

import gi

gi.require_version("Graphene", "1.0")
from gi.repository import Graphene, Gtk


class CoverPicture(Gtk.Widget):
    __gtype_name__ = "ChihiroCoverPicture"

    def __init__(self, paintable):
        super().__init__(hexpand=True, vexpand=True, overflow=Gtk.Overflow.HIDDEN)
        self.focus_x = 0.5
        self._paintable = paintable
        self._handlers = [
            paintable.connect("invalidate-contents", lambda *_: self.queue_draw()),
            paintable.connect("invalidate-size", lambda *_: self.queue_draw()),
        ]

    def set_focus_x(self, value):
        self.focus_x = min(max(value, 0.0), 1.0)
        self.queue_draw()

    def do_measure(self, _orientation, _for_size):
        return 0, 0, -1, -1

    def do_snapshot(self, snapshot):
        width, height = self.get_width(), self.get_height()
        src_w = self._paintable.get_intrinsic_width()
        src_h = self._paintable.get_intrinsic_height()
        if not (width and height and src_w and src_h):
            return
        scale = max(width / src_w, height / src_h)
        draw_w, draw_h = src_w * scale, src_h * scale
        x = min(0.0, max(width - draw_w, width / 2 - self.focus_x * draw_w))
        y = (height - draw_h) / 2
        snapshot.save()
        snapshot.translate(Graphene.Point().init(x, y))
        self._paintable.snapshot(snapshot, draw_w, draw_h)
        snapshot.restore()

    def disconnect_paintable(self):
        for handler in self._handlers:
            self._paintable.disconnect(handler)
        self._handlers = []
