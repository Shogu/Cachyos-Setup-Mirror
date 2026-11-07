# SPDX-License-Identifier: GPL-3.0-or-later
"""Lecture simple d'un morceau avec GStreamer (playbin, audio seul)."""

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gio, GLib, GObject, Gst  # noqa: E402

_FLAG_AUDIO = 1 << 1
_FLAG_SOFT_VOLUME = 1 << 4


class Player(GObject.Object):
    __gtype_name__ = "DisquairePlayer"
    __gsignals__ = {
        "state-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "position": (GObject.SignalFlags.RUN_FIRST, None, (float, float)),
        "error": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self):
        super().__init__()
        self.playing = False
        self.path = None
        self._timer = 0
        self._bin = None
        ok, _ = Gst.init_check(None)
        if not ok:
            return
        self._bin = Gst.ElementFactory.make("playbin", "disquaire-player")
        if self._bin is None:
            return
        # Audio uniquement : sans ça, la pochette intégrée s'ouvrirait
        # dans une fenêtre vidéo.
        self._bin.set_property("flags", _FLAG_AUDIO | _FLAG_SOFT_VOLUME)
        fakesink = Gst.ElementFactory.make("fakesink", None)
        if fakesink is not None:
            self._bin.set_property("video-sink", fakesink)
        bus = self._bin.get_bus()
        bus.add_signal_watch()
        bus.connect("message::eos", self._on_eos)
        bus.connect("message::error", self._on_error)

    @property
    def available(self) -> bool:
        return self._bin is not None

    def load(self, path: str | None) -> None:
        if path == self.path:
            return
        self.stop()
        self.path = path

    def toggle(self) -> None:
        if self.playing:
            self.pause()
        else:
            self.play()

    def play(self) -> None:
        if not self.available or not self.path:
            return
        state = self._bin.get_state(0).state
        if state in (Gst.State.NULL, Gst.State.READY):
            self._bin.set_property("uri", Gio.File.new_for_path(self.path).get_uri())
        if self._bin.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
            self.emit("error", "Lecture impossible.")
            self.stop()
            return
        self.playing = True
        self._start_timer()
        self.emit("state-changed")

    def pause(self) -> None:
        if not self.available:
            return
        self._bin.set_state(Gst.State.PAUSED)
        self.playing = False
        self._stop_timer()
        self.emit("state-changed")

    def stop(self) -> None:
        if self.available:
            self._bin.set_state(Gst.State.NULL)
        was_playing = self.playing
        self.playing = False
        self._stop_timer()
        self.emit("position", 0.0, 0.0)
        if was_playing:
            self.emit("state-changed")

    def seek(self, seconds: float) -> None:
        if not self.available:
            return
        state = self._bin.get_state(0).state
        if state in (Gst.State.NULL, Gst.State.READY):
            return
        self._bin.seek_simple(
            Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            int(seconds * Gst.SECOND),
        )

    def _start_timer(self) -> None:
        if not self._timer:
            self._timer = GLib.timeout_add(250, self._tick)

    def _stop_timer(self) -> None:
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = 0

    def _tick(self) -> bool:
        ok_pos, pos = self._bin.query_position(Gst.Format.TIME)
        ok_dur, dur = self._bin.query_duration(Gst.Format.TIME)
        if ok_pos:
            self.emit("position", pos / Gst.SECOND, dur / Gst.SECOND if ok_dur else 0.0)
        return GLib.SOURCE_CONTINUE

    def _on_eos(self, *_):
        self.stop()

    def _on_error(self, _bus, message):
        err, _dbg = message.parse_error()
        self.stop()
        self.emit("error", err.message if err else "Erreur de lecture")
