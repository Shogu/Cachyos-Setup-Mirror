"""Lecture d'un fichier vidéo local muet avec playbin, rendu dans un Gdk.Paintable GTK4."""

import gi

gi.require_version("Gst", "1.0")
from gi.repository import GLib, GObject, Gst

Gst.init(None)

PLAY_FLAG_VIDEO = 1 << 0


def _make_video_sink():
    sink = Gst.ElementFactory.make("gtk4paintablesink", None)
    if sink is None:
        raise RuntimeError("Greffon gtk4paintablesink absent (paquet gst-plugin-gtk4).")
    paintable = sink.props.paintable
    if paintable.props.gl_context is None:
        return sink, paintable
    glsink = Gst.ElementFactory.make("glsinkbin", None)
    glsink.props.sink = sink
    return glsink, paintable


class Player(GObject.Object):
    """Un lecteur par plan à l'écran. Reprises sans coupure via « about-to-finish » ; fin signalée par le message EOS."""

    __gsignals__ = {
        "ready": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "ended": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "error": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self):
        super().__init__()
        self._playbin = Gst.ElementFactory.make("playbin", None)
        sink, self.paintable = _make_video_sink()
        self._playbin.props.video_sink = sink
        self._playbin.props.flags = PLAY_FLAG_VIDEO
        self._uri = None
        self.repeats = 0
        self._prerolled = False
        self._about_id = self._playbin.connect("about-to-finish", self._on_about_to_finish)
        bus = self._playbin.get_bus()
        bus.add_signal_watch()
        self._bus_id = bus.connect("message", self._on_message)

    def load(self, path, repeats):
        """repeats : nombre de reprises sans coupure après la première lecture, -1 pour une boucle infinie."""
        self._playbin.set_state(Gst.State.NULL)
        self._uri = GLib.filename_to_uri(str(path), None)
        self.repeats = repeats
        self._prerolled = False
        self._playbin.props.uri = self._uri
        self._playbin.set_state(Gst.State.PAUSED)

    def play(self):
        self._playbin.set_state(Gst.State.PLAYING)

    def pause(self):
        self._playbin.set_state(Gst.State.PAUSED)

    def rewind(self):
        self._playbin.set_state(Gst.State.PAUSED)
        self._playbin.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE, 0)

    def unload(self):
        self._playbin.set_state(Gst.State.NULL)
        self._uri = None

    def shutdown(self):
        self._playbin.set_state(Gst.State.NULL)
        self._playbin.disconnect(self._about_id)
        bus = self._playbin.get_bus()
        bus.disconnect(self._bus_id)
        bus.remove_signal_watch()

    def _on_about_to_finish(self, playbin):
        # Appelé depuis un thread GStreamer : on se contente de réenfiler le même fichier.
        if self.repeats != 0 and self._uri:
            if self.repeats > 0:
                self.repeats -= 1
            playbin.props.uri = self._uri

    def _on_message(self, _bus, message):
        if message.src is not self._playbin and message.type != Gst.MessageType.ERROR:
            return
        if message.type == Gst.MessageType.ASYNC_DONE and not self._prerolled:
            self._prerolled = True
            self.emit("ready")
        elif message.type == Gst.MessageType.EOS:
            self.emit("ended")
        elif message.type == Gst.MessageType.ERROR:
            error, _debug = message.parse_error()
            self._playbin.set_state(Gst.State.NULL)
            self.emit("error", error.message)
