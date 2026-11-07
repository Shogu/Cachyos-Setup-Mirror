"""Lecture d'un flux réseau avec playbin, rendu dans un Gdk.Paintable GTK4."""

import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstPbutils", "1.0")
from gi.repository import GLib, GObject, Gst, GstPbutils

Gst.init(None)

PLAY_FLAG_VIDEO = 1 << 0
PLAY_FLAG_TEXT = 1 << 2


class SinkMissingError(RuntimeError):
    pass


def _make_video_sink():
    sink = Gst.ElementFactory.make("gtk4paintablesink", None)
    if sink is None:
        raise SinkMissingError("Greffon gtk4paintablesink absent (paquet gst-plugin-gtk4).")
    paintable = sink.props.paintable
    if paintable.props.gl_context is None:
        return sink, paintable
    glsink = Gst.ElementFactory.make("glsinkbin", None)
    glsink.props.sink = sink
    return glsink, paintable


class Player(GObject.Object):
    """Enveloppe minimale de playbin. Les erreurs remontent par le signal « error »."""

    __gsignals__ = {
        "state-changed": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
        "buffering": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "position": (GObject.SignalFlags.RUN_FIRST, None, (float, float)),
        "ended": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "error": (GObject.SignalFlags.RUN_FIRST, None, (str, str)),
    }

    def __init__(self):
        super().__init__()
        self._playbin = Gst.ElementFactory.make("playbin", None)
        sink, self.paintable = _make_video_sink()
        self._playbin.props.video_sink = sink
        self._all_flags = self._playbin.props.flags
        self._start_at = 0.0
        self._headers = {}
        self._wants_play = False
        self._buffering = False
        self._failed = False
        self._tick_id = 0
        self._source_setup_id = self._playbin.connect("source-setup", self._on_source_setup)
        bus = self._playbin.get_bus()
        bus.add_signal_watch()
        self._bus_id = bus.connect("message", self._on_message)

    @property
    def playing(self):
        return self._wants_play

    def open(self, uri, headers, audio_only=False, start_at=0.0):
        """audio_only : ni décodage ni affichage vidéo (mode Rideau). start_at : reprise à cette position (s)."""
        self.stop()
        flags = self._all_flags
        if audio_only:
            flags &= ~(PLAY_FLAG_VIDEO | PLAY_FLAG_TEXT)
        self._playbin.props.flags = flags
        self._start_at = start_at
        self._headers = headers
        self._failed = False
        self._playbin.props.uri = uri
        self._wants_play = True
        self._playbin.set_state(Gst.State.PAUSED)
        self._start_ticks()
        self.emit("state-changed", True)

    def set_video_enabled(self, enabled):
        """Coupe ou rétablit le décodage et l'affichage de l'image sans interrompre la lecture (Rideau)."""
        flags = self._playbin.props.flags
        self._playbin.props.flags = flags | PLAY_FLAG_VIDEO if enabled else flags & ~(PLAY_FLAG_VIDEO | PLAY_FLAG_TEXT)

    @property
    def muted(self):
        return self._playbin.props.mute

    @muted.setter
    def muted(self, value):
        self._playbin.props.mute = value

    def play(self):
        self._wants_play = True
        if not self._buffering:
            self._playbin.set_state(Gst.State.PLAYING)
        self.emit("state-changed", True)

    def pause(self):
        self._wants_play = False
        self._playbin.set_state(Gst.State.PAUSED)
        self.emit("state-changed", False)

    def stop(self):
        self._wants_play = False
        self._buffering = False
        self._stop_ticks()
        self._playbin.set_state(Gst.State.NULL)
        self.emit("state-changed", False)
        self.emit("position", 0.0, 0.0)

    def seek(self, seconds):
        self._playbin.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, int(seconds * Gst.SECOND))

    @property
    def volume(self):
        return self._playbin.props.volume

    @volume.setter
    def volume(self, value):
        self._playbin.props.volume = value

    def shutdown(self):
        self._stop_ticks()
        self._playbin.set_state(Gst.State.NULL)
        bus = self._playbin.get_bus()
        bus.disconnect(self._bus_id)
        bus.remove_signal_watch()
        self._playbin.disconnect(self._source_setup_id)

    def _start_ticks(self):
        self._stop_ticks()
        self._tick_id = GLib.timeout_add(500, self._on_tick)

    def _stop_ticks(self):
        if self._tick_id:
            GLib.source_remove(self._tick_id)
            self._tick_id = 0

    def _on_tick(self):
        ok_pos, pos = self._playbin.query_position(Gst.Format.TIME)
        ok_dur, dur = self._playbin.query_duration(Gst.Format.TIME)
        if ok_pos:
            self.emit("position", pos / Gst.SECOND, dur / Gst.SECOND if ok_dur else 0.0)
        return GLib.SOURCE_CONTINUE

    def _on_source_setup(self, _playbin, source):
        if source.find_property("user-agent") is None:
            return
        headers = dict(self._headers)
        agent = headers.pop("User-Agent", None)
        if agent:
            source.props.user_agent = agent
        if headers and source.find_property("extra-headers") is not None:
            structure = Gst.Structure.new_empty("extra-headers")
            for key, value in headers.items():
                structure.set_value(key, value)
            source.props.extra_headers = structure

    def _fail(self, text, debug):
        if self._failed:
            return
        self._failed = True
        self.stop()
        self.emit("error", text, debug)

    def _on_message(self, _bus, message):
        kind = message.type
        if kind == Gst.MessageType.EOS:
            self.stop()
            self.emit("ended")
        elif kind == Gst.MessageType.ERROR:
            error, debug = message.parse_error()
            self._fail(error.message, debug or "")
        elif kind == Gst.MessageType.BUFFERING:
            percent = message.parse_buffering()
            self._buffering = percent < 100
            target = Gst.State.PLAYING if self._wants_play and not self._buffering else Gst.State.PAUSED
            self._playbin.set_state(target)
            self.emit("buffering", percent)
        elif kind == Gst.MessageType.ELEMENT and GstPbutils.is_missing_plugin_message(message):
            detail = GstPbutils.missing_plugin_message_get_description(message)
            self._fail(f"Greffon GStreamer manquant : {detail}", "")
        elif kind == Gst.MessageType.ASYNC_DONE:
            if self._start_at:
                start, self._start_at = self._start_at, 0.0
                self.seek(start)
            if self._wants_play and not self._buffering:
                self._playbin.set_state(Gst.State.PLAYING)
