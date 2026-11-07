"""Bande son : direct audio de Lofi Girl, résolu par yt-dlp (téléchargé et tenu à jour dans le dossier de l'utilisateur), lu par playbin (audio seul)."""

from pathlib import Path

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gio, Gst

from .ytdlp import YtDlp

QJS = Path("/usr/bin/qjs")
LIVE_URL = "https://www.youtube.com/@LofiGirl/live"
PLAY_FLAG_AUDIO = 1 << 1


class Radio:
    def __init__(self):
        self._playbin = Gst.ElementFactory.make("playbin", None)
        self._playbin.props.flags = PLAY_FLAG_AUDIO
        self._playbin.props.video_sink = Gst.ElementFactory.make("fakesink", None)
        self._uri = None
        self._retried = False
        self._wanted = False
        self._cancellable = Gio.Cancellable()
        self._ytdlp = YtDlp()
        bus = self._playbin.get_bus()
        bus.add_signal_watch()
        self._bus_id = bus.connect("message", self._on_message)

    def play(self):
        self._wanted = True
        if self._uri:
            self._start()
        else:
            self._resolve()

    def pause(self):
        self._wanted = False
        self._playbin.set_state(Gst.State.NULL)

    def shutdown(self):
        self._cancellable.cancel()
        self._ytdlp.cancel()
        self._playbin.set_state(Gst.State.NULL)
        bus = self._playbin.get_bus()
        bus.disconnect(self._bus_id)
        bus.remove_signal_watch()

    def _start(self):
        self._playbin.set_state(Gst.State.NULL)
        self._playbin.props.uri = self._uri
        self._playbin.set_state(Gst.State.PLAYING)

    def _resolve(self):
        self._ytdlp.get(self._spawn)

    def _spawn(self, ytdlp, error):
        if error:
            print(f"Chihiro : {error} Pas de bande son.", flush=True)
            return
        argv = [str(ytdlp), "-g", "--no-warnings", "--ignore-config", "--no-cache-dir", "--no-js-runtimes",
                "--js-runtimes", f"quickjs:{QJS}", "-f", "bestaudio/best", LIVE_URL]
        flags = Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE
        process = Gio.Subprocess.new(argv, flags)
        process.communicate_utf8_async(None, self._cancellable, self._on_resolved)

    def _on_resolved(self, process, result):
        try:
            _ok, stdout, stderr = process.communicate_utf8_finish(result)
        except Exception as exc:
            print(f"Chihiro : résolution du direct interrompue ({exc}).", flush=True)
            return
        lines = (stdout or "").split()
        if process.get_exit_status() != 0 or not lines:
            print(f"Chihiro : direct Lofi Girl indisponible.\n{(stderr or '').strip()[-400:]}", flush=True)
            return
        self._uri = lines[0]
        if self._wanted:
            self._start()

    def _on_message(self, _bus, message):
        if message.type == Gst.MessageType.ERROR:
            error, _debug = message.parse_error()
            self._playbin.set_state(Gst.State.NULL)
            print(f"Chihiro : lecture du direct impossible ({error.message}).", flush=True)
            if not self._retried and self._wanted:
                self._retried = True
                self._uri = None
                self._resolve()
        elif message.type == Gst.MessageType.STREAM_START:
            self._retried = False
