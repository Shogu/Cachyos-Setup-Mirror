import os
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from .cover import CoverPicture
from .player import Player
from .radio import Radio

APP_ID = "fr.ogu.Chihiro"
MEDIA_DIR = Path(os.environ.get("CHIHIRO_MEDIA_DIR", "/usr/share/chihiro/media"))
DEFAULT_VIDEO = "train-close.mp4"
# Point d'intérêt horizontal de chaque vidéo : le recadrage garde Chihiro dans l'image.
FOCUS_X = {"train-close": 0.4, "zeniba-close": 0.3}
RESIZE_GRIP = 24
DRAG_THRESHOLD = 6


class Window(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Chihiro", default_width=260, default_height=225, decorated=False)
        self.set_size_request(160, 120)
        self._videos = sorted(MEDIA_DIR.glob("*.mp4"))
        self._index = next((i for i, v in enumerate(self._videos) if v.name == DEFAULT_VIDEO), 0)
        self._player = Player()
        self._radio = Radio()
        self.playing = True
        self._picture = CoverPicture(self._player.paintable)
        self.set_content(self._picture)

        self._moving = False
        drag = Gtk.GestureDrag(button=Gdk.BUTTON_PRIMARY)
        drag.connect("drag-begin", lambda *_: setattr(self, "_moving", False))
        drag.connect("drag-update", self._on_drag_update)
        self.add_controller(drag)
        self.connect("notify::maximized", self._refuse_maximize)

        right = Gtk.GestureClick(button=Gdk.BUTTON_SECONDARY)
        right.connect("pressed", self._on_right_click)
        left = Gtk.GestureClick(button=Gdk.BUTTON_PRIMARY, propagation_phase=Gtk.PropagationPhase.CAPTURE)
        left.connect("pressed", self._on_left_press)
        for gesture in (right, left):
            self.add_controller(gesture)
        self._error_id = self._player.connect("error", lambda _p, msg: print(f"Chihiro : {msg}", flush=True))
        self.connect("close-request", self._on_close)
        self._load()
        self._radio.play()

    def _load(self):
        if not self._videos:
            print(f"Chihiro : aucune vidéo dans {MEDIA_DIR}", flush=True)
            return
        video = self._videos[self._index]
        self._picture.set_focus_x(FOCUS_X.get(video.stem, 0.5))
        self._player.load(video, -1)
        if self.playing:
            self._player.play()

    def toggle_pause(self):
        self.playing = not self.playing
        if self.playing:
            self._player.play()
            self._radio.play()
        else:
            self._player.pause()
            self._radio.pause()

    def next_video(self):
        if self._videos:
            self._index = (self._index + 1) % len(self._videos)
            self._load()

    def _on_right_click(self, gesture, _n, _x, _y):
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        self.toggle_pause()

    def _on_left_press(self, gesture, n_press, x, y):
        if n_press == 2:
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
            self.next_video()
        elif n_press == 1 and x > self.get_width() - RESIZE_GRIP and y > self.get_height() - RESIZE_GRIP:
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
            self.get_surface().begin_resize(Gdk.SurfaceEdge.SOUTH_EAST, gesture.get_current_event_device(),
                                            Gdk.BUTTON_PRIMARY, x, y, gesture.get_current_event_time())

    def _on_drag_update(self, gesture, dx, dy):
        if self._moving or abs(dx) + abs(dy) < DRAG_THRESHOLD:
            return
        self._moving = True
        _ok, x, y = gesture.get_start_point()
        self.get_surface().begin_move(gesture.get_current_event_device(), Gdk.BUTTON_PRIMARY, x, y,
                                      gesture.get_current_event_time())
        gesture.reset()

    def _refuse_maximize(self, *_args):
        if self.is_maximized():
            self.unmaximize()

    def _on_close(self, _window):
        self._player.disconnect(self._error_id)
        self._picture.disconnect_paintable()
        self._player.shutdown()
        self._radio.shutdown()
        return False


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self._quit())
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["Escape", "<Control>q", "<Control>w"])

    def _quit(self):
        window = self.get_active_window()
        if window:
            window.close()
        self.quit()

    def do_activate(self):
        (self.get_active_window() or Window(self)).present()


def main():
    GLib.set_prgname(APP_ID)
    GLib.set_application_name("Chihiro")
    Gtk.Window.set_default_icon_name(APP_ID)
    return Application().run(sys.argv)
