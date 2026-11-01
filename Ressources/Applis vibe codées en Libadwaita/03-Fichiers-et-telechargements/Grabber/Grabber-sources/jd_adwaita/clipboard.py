from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib


class ClipboardMonitor:
    """Small GTK clipboard observer used by the frontend Grabber.

    JDownloader's own clipboard observer is disabled by the frontend to
    avoid duplicate packages.  This observer only reads plain text and hands
    it to the GTK main loop callback; it never adds links by itself.
    """

    def __init__(self, callback: Callable[[str], None]) -> None:
        self._callback = callback
        self._clipboard = None
        self._handler_id: int | None = None
        display = Gdk.Display.get_default()
        if display is not None:
            self._clipboard = display.get_clipboard()

    @property
    def available(self) -> bool:
        return self._clipboard is not None

    def start(self) -> None:
        if self._clipboard is None:
            display = Gdk.Display.get_default()
            if display is not None:
                self._clipboard = display.get_clipboard()
        if self._clipboard is None or self._handler_id is not None:
            return
        self._handler_id = self._clipboard.connect("changed", self._on_changed)

    def stop(self) -> None:
        if self._clipboard is None or self._handler_id is None:
            return
        try:
            self._clipboard.disconnect(self._handler_id)
        except (GLib.Error, TypeError, ValueError):
            pass
        self._handler_id = None

    def _on_changed(self, clipboard: Gdk.Clipboard) -> None:
        try:
            clipboard.read_text_async(None, self._on_text_read)
        except (GLib.Error, TypeError):
            return

    def _on_text_read(self, clipboard: Gdk.Clipboard, result: object) -> None:
        try:
            text = clipboard.read_text_finish(result)
        except (GLib.Error, TypeError):
            return
        if text:
            self._callback(str(text))
