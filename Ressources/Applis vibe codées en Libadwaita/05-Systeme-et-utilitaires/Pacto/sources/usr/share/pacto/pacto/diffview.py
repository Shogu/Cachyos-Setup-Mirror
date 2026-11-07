"""Side by side diff widget built on two synchronised text views."""

from __future__ import annotations

from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gtk, Pango  # noqa: E402

from .diff import DELETE, EQUAL, INSERT, REPLACE, SKIP, Row  # noqa: E402

LIGHT = {
    "delete": (0.878, 0.106, 0.141, 0.16),
    "insert": (0.207, 0.517, 0.894, 0.16),
    "replace": (0.180, 0.760, 0.494, 0.18),
    "delete-word": (0.878, 0.106, 0.141, 0.34),
    "insert-word": (0.207, 0.517, 0.894, 0.34),
    "filler": (0.0, 0.0, 0.0, 0.05),
    "skip": (0.0, 0.0, 0.0, 0.04),
}

DARK = {
    "delete": (0.878, 0.106, 0.141, 0.28),
    "insert": (0.207, 0.517, 0.894, 0.30),
    "replace": (0.180, 0.760, 0.494, 0.26),
    "delete-word": (0.878, 0.106, 0.141, 0.52),
    "insert-word": (0.207, 0.517, 0.894, 0.52),
    "filler": (1.0, 1.0, 1.0, 0.04),
    "skip": (1.0, 1.0, 1.0, 0.04),
}


def _rgba(values: tuple[float, float, float, float]) -> Gdk.RGBA:
    color = Gdk.RGBA()
    color.red, color.green, color.blue, color.alpha = values
    return color


class DiffPane(Gtk.Box):
    """A gutter with line numbers next to the text of one side of the diff."""

    def __init__(self, side: str, hadjustment: Gtk.Adjustment, vadjustment: Gtk.Adjustment) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, vexpand=True)
        self._side = side

        self._gutter = Gtk.TextView(
            editable=False,
            cursor_visible=False,
            monospace=True,
            justification=Gtk.Justification.RIGHT,
            left_margin=6,
            right_margin=6,
            top_margin=6,
            bottom_margin=6,
        )
        self._gutter.add_css_class("diff-gutter")
        self._gutter.add_css_class("dim-label")
        gutter_window = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            vscrollbar_policy=Gtk.PolicyType.EXTERNAL,
            vadjustment=vadjustment,
            child=self._gutter,
        )

        self._view = Gtk.TextView(
            editable=False,
            cursor_visible=False,
            monospace=True,
            wrap_mode=Gtk.WrapMode.NONE,
            left_margin=8,
            right_margin=8,
            top_margin=6,
            bottom_margin=6,
        )
        self._view.add_css_class("diff-view")
        self.scroller = Gtk.ScrolledWindow(
            hexpand=True,
            vexpand=True,
            hadjustment=hadjustment,
            vadjustment=vadjustment,
            child=self._view,
        )

        self.append(gutter_window)
        self.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        self.append(self.scroller)

        self._tags: dict[str, Gtk.TextTag] = {}
        self._refresh_tags()
        Adw.StyleManager.get_default().connect("notify::dark", lambda *args: self._refresh_tags())

    def _refresh_tags(self) -> None:
        palette = DARK if Adw.StyleManager.get_default().get_dark() else LIGHT
        table = self._view.get_buffer().get_tag_table()
        for name, tag in self._tags.items():
            table.remove(tag)
        self._tags = {}
        for name in ("delete", "insert", "replace", "filler", "skip"):
            tag = Gtk.TextTag(name=name, paragraph_background_rgba=_rgba(palette[name]))
            table.add(tag)
            self._tags[name] = tag
        for name in ("delete-word", "insert-word"):
            tag = Gtk.TextTag(name=name, background_rgba=_rgba(palette[name]))
            table.add(tag)
            self._tags[name] = tag
        self._tags["skip-text"] = Gtk.TextTag(
            name="skip-text", style=Pango.Style.ITALIC, paragraph_background_rgba=_rgba(palette["skip"])
        )
        table.add(self._tags["skip-text"])

    def set_content(self, lines: list[tuple[str, str | None, list[tuple[int, int]], int | None]]) -> None:
        """Fill the pane. Each entry is (text, row tag, inline spans, line number)."""
        buffer = self._view.get_buffer()
        gutter = self._gutter.get_buffer()
        gutter.set_text("\n".join("" if entry[3] is None else str(entry[3]) for entry in lines))

        buffer.set_text("\n".join(entry[0] for entry in lines))
        width = max((len(str(entry[3])) for entry in lines if entry[3] is not None), default=1)
        self._gutter.set_size_request(width * 9 + 18, -1)

        for index, (_text, tag_name, spans, _number) in enumerate(lines):
            if tag_name is None:
                continue
            start = buffer.get_iter_at_line(index)[1]
            end = start.copy()
            if not end.ends_line():
                end.forward_to_line_end()
            buffer.apply_tag(self._tags[tag_name], start, end)
            inline = "delete-word" if self._side == "left" else "insert-word"
            for span_start, span_end in spans:
                line_start = buffer.get_iter_at_line(index)[1]
                span_from = line_start.copy()
                span_from.forward_chars(span_start)
                span_to = line_start.copy()
                span_to.forward_chars(span_end)
                buffer.apply_tag(self._tags[inline], span_from, span_to)

    def y_for_line(self, line: int) -> int:
        buffer = self._view.get_buffer()
        position = buffer.get_iter_at_line(min(line, buffer.get_line_count() - 1))[1]
        return self._view.get_iter_location(position).y


class DiffView(Gtk.Box):
    """Two panes sharing their scroll position, showing the old and the new file."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, vexpand=True)
        vadjustment = Gtk.Adjustment()
        self._vadjustment = vadjustment
        self._rows: list[Row] = []
        self.left = DiffPane("left", Gtk.Adjustment(), vadjustment)
        self.right = DiffPane("right", Gtk.Adjustment(), vadjustment)

        self.paned = Gtk.Paned(
            orientation=Gtk.Orientation.HORIZONTAL,
            start_child=self.left,
            end_child=self.right,
            resize_start_child=True,
            resize_end_child=True,
            shrink_start_child=False,
            shrink_end_child=False,
            position=520,
        )
        self.append(self.paned)
        Adw.StyleManager.get_default().connect(
            "notify::dark", lambda *args: self.set_rows(self._rows)
        )

    def set_rows(self, rows: list[Row]) -> None:
        self._rows = rows
        left: list[tuple[str, str | None, list[tuple[int, int]], int | None]] = []
        right: list[tuple[str, str | None, list[tuple[int, int]], int | None]] = []
        for row in rows:
            if row.kind == EQUAL:
                left.append((row.left_text, None, [], row.left_no))
                right.append((row.right_text, None, [], row.right_no))
            elif row.kind == SKIP:
                label = _("⋯ {count} identical lines").format(count=row.skipped)
                left.append((label, "skip-text", [], None))
                right.append((label, "skip-text", [], None))
            elif row.kind == DELETE:
                left.append((row.left_text, "delete", [], row.left_no))
                right.append(("", "filler", [], None))
            elif row.kind == INSERT:
                left.append(("", "filler", [], None))
                right.append((row.right_text, "insert", [], row.right_no))
            elif row.kind == REPLACE:
                left.append((row.left_text, "replace", row.left_spans, row.left_no))
                right.append((row.right_text, "replace", row.right_spans, row.right_no))
        self.left.set_content(left)
        self.right.set_content(right)

    def scroll_to_row(self, index: int) -> None:
        self._vadjustment.set_value(max(0, self.left.y_for_line(index) - 48))
