"""Main window: file list on the left, current file and maintainer file side by side."""

from __future__ import annotations

import threading
from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk, Pango  # noqa: E402

from . import files, scanner  # noqa: E402
from .diff import EQUAL, SKIP, DiffStats, build_rows  # noqa: E402
from .diffview import DiffView  # noqa: E402


class FileRow(Adw.ActionRow):
    """A sidebar entry for one maintainer file."""

    def __init__(self, pacfile: scanner.PacFile) -> None:
        super().__init__(
            title=GLib.markup_escape_text(pacfile.target.name),
            subtitle=GLib.markup_escape_text(str(pacfile.target.parent)),
        )
        self.pacfile = pacfile
        badge = Gtk.Label(label=f".{pacfile.kind}", valign=Gtk.Align.CENTER)
        badge.add_css_class("caption")
        badge.add_css_class("pac-badge")
        badge.add_css_class(f"pac-badge-{pacfile.kind}")
        self.add_suffix(badge)


class PactoWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.set_title(_("Pacto"))
        self.set_default_size(1280, 820)

        self._files: list[scanner.PacFile] = []
        self._current: scanner.PacFile | None = None
        self._change_rows: list[int] = []
        self._change_index = -1
        self._collapse = False

        self._diff_view = DiffView()
        self._build_ui()
        self._install_actions()
        self.refresh()

    # UI construction -----------------------------------------------------

    def _build_ui(self) -> None:
        self._split = Adw.NavigationSplitView(
            sidebar=self._build_sidebar(), content=self._build_content()
        )
        self._split.set_min_sidebar_width(280)
        self._split.set_max_sidebar_width(380)

        self._toast_overlay = Adw.ToastOverlay(child=self._split)
        self.set_content(self._toast_overlay)

        breakpoint_ = Adw.Breakpoint.new(
            Adw.BreakpointCondition.parse("max-width: 860sp")
        )
        breakpoint_.add_setter(self._split, "collapsed", True)
        self.add_breakpoint(breakpoint_)

    def _build_sidebar(self) -> Adw.NavigationPage:
        header = Adw.HeaderBar()
        refresh = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text=_("Rescan (Ctrl+R)"))
        refresh.set_action_name("win.refresh")
        header.pack_start(refresh)

        menu = Gio.Menu()
        section = Gio.Menu()
        section.append(_("Hide Unchanged Lines"), "win.collapse")
        menu.append_section(None, section)
        about = Gio.Menu()
        about.append(_("Keyboard Shortcuts"), "win.shortcuts")
        about.append(_("About Pacto"), "app.about")
        menu.append_section(None, about)
        header.pack_end(
            Gtk.MenuButton(
                icon_name="open-menu-symbolic",
                menu_model=menu,
                tooltip_text=_("Main Menu"),
            )
        )

        self._search = Gtk.SearchEntry(
            placeholder_text=_("Filter files"), margin_start=6, margin_end=6, margin_bottom=6
        )
        self._search.connect("search-changed", lambda *_a: self._list.invalidate_filter())

        self._list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self._list.add_css_class("navigation-sidebar")
        self._list.set_filter_func(self._filter_row)
        self._list.connect("row-selected", self._on_row_selected)

        self._sidebar_stack = Gtk.Stack()
        self._sidebar_stack.add_named(
            Gtk.ScrolledWindow(child=self._list, vexpand=True), "list"
        )
        self._sidebar_stack.add_named(
            Adw.StatusPage(
                icon_name="emblem-ok-symbolic",
                title=_("Nothing to Merge"),
                description=_("No .pacnew, .pacsave or .pacorig file was found."),
            ),
            "empty",
        )
        self._sidebar_stack.add_named(
            Adw.StatusPage(title=_("Scanning…"), child=Gtk.Spinner(spinning=True, width_request=32, height_request=32)),
            "loading",
        )

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(self._search)
        box.append(self._sidebar_stack)

        toolbar = Adw.ToolbarView(content=box)
        toolbar.add_top_bar(header)
        return Adw.NavigationPage(title=_("Pacman Files"), child=toolbar)

    def _build_content(self) -> Adw.NavigationPage:
        self._window_title = Adw.WindowTitle(title=_("Pacto"), subtitle="")
        header = Adw.HeaderBar(title_widget=self._window_title)

        navigation = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        navigation.add_css_class("linked")
        self._previous = Gtk.Button(icon_name="go-up-symbolic", tooltip_text=_("Previous change"))
        self._previous.set_action_name("win.previous-change")
        self._next = Gtk.Button(icon_name="go-down-symbolic", tooltip_text=_("Next change"))
        self._next.set_action_name("win.next-change")
        navigation.append(self._previous)
        navigation.append(self._next)
        header.pack_start(navigation)

        self._banner = Adw.Banner(button_label=_("Read as Administrator"), revealed=False)
        self._banner.connect("button-clicked", lambda *_a: self._show_file(self._current, privileged=True))

        titles = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, homogeneous=True)
        titles.add_css_class("pac-column-headers")
        title_props = dict(
            xalign=0.0,
            ellipsize=Pango.EllipsizeMode.MIDDLE,
            margin_start=12,
            margin_end=12,
            margin_top=6,
            margin_bottom=6,
        )
        self._left_title = Gtk.Label(**title_props)
        self._right_title = Gtk.Label(**title_props)
        for label in (self._left_title, self._right_title):
            label.add_css_class("caption-heading")
            label.add_css_class("dim-label")
            titles.append(label)

        diff_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        diff_box.append(self._banner)
        diff_box.append(titles)
        diff_box.append(Gtk.Separator())
        diff_box.append(self._diff_view)

        self._content_stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self._content_stack.add_named(
            Adw.StatusPage(
                icon_name="edit-select-all-symbolic",
                title=_("Select a File"),
                description=_("Pick a maintainer file on the left to compare it with the file in use."),
            ),
            "placeholder",
        )
        self._content_stack.add_named(diff_box, "diff")
        self._error_page = Adw.StatusPage(icon_name="dialog-warning-symbolic", title=_("Cannot Compare"))
        self._content_stack.add_named(self._error_page, "error")

        toolbar = Adw.ToolbarView(content=self._content_stack)
        toolbar.add_top_bar(header)
        toolbar.add_bottom_bar(self._build_action_bar())
        return Adw.NavigationPage(title=_("Comparison"), child=toolbar)

    def _build_action_bar(self) -> Gtk.Widget:
        self._stats_label = Gtk.Label(xalign=0.0)
        self._stats_label.add_css_class("dim-label")
        self._stats_label.add_css_class("caption")

        legend = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, margin_start=12)
        for css, text in (
            ("pac-legend-delete", _("Removed")),
            ("pac-legend-replace", _("Modified")),
            ("pac-legend-insert", _("Added")),
        ):
            item = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, valign=Gtk.Align.CENTER)
            swatch = Gtk.Box(width_request=12, height_request=12, valign=Gtk.Align.CENTER)
            swatch.add_css_class("pac-swatch")
            swatch.add_css_class(css)
            item.append(swatch)
            caption = Gtk.Label(label=text)
            caption.add_css_class("caption")
            caption.add_css_class("dim-label")
            item.append(caption)
            legend.append(item)

        self._keep_button = Gtk.Button(label=_("Keep Current"), tooltip_text=_("Delete the maintainer file"))
        self._keep_button.set_action_name("win.keep-current")
        self._apply_button = Gtk.Button(label=_("Use New File"))
        self._apply_button.add_css_class("suggested-action")
        self._apply_button.set_action_name("win.use-new")

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, halign=Gtk.Align.END, hexpand=True)
        actions.append(self._keep_button)
        actions.append(self._apply_button)

        bar = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
            margin_top=6,
            margin_bottom=6,
            margin_start=6,
            margin_end=6,
        )
        bar.append(self._stats_label)
        bar.append(legend)
        bar.append(actions)
        return bar

    def _install_actions(self) -> None:
        for name, callback in (
            ("refresh", lambda *_a: self.refresh()),
            ("next-change", lambda *_a: self._jump(1)),
            ("previous-change", lambda *_a: self._jump(-1)),
            ("keep-current", lambda *_a: self._confirm_keep()),
            ("use-new", lambda *_a: self._confirm_apply()),
            ("shortcuts", lambda *_a: self._show_shortcuts()),
            ("focus-search", lambda *_a: self._search.grab_focus()),
        ):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

        collapse = Gio.SimpleAction.new_stateful("collapse", None, GLib.Variant.new_boolean(False))
        collapse.connect("activate", self._on_collapse)
        self.add_action(collapse)

    # Behaviour -----------------------------------------------------------

    def _filter_row(self, row: Gtk.ListBoxRow) -> bool:
        needle = self._search.get_text().strip().lower()
        return not needle or needle in str(row.pacfile.path).lower()

    def _on_collapse(self, action: Gio.SimpleAction, _param) -> None:
        self._collapse = not action.get_state().get_boolean()
        action.set_state(GLib.Variant.new_boolean(self._collapse))
        if self._current:
            self._show_file(self._current)

    def refresh(self) -> None:
        self._sidebar_stack.set_visible_child_name("loading")

        def work() -> None:
            found = scanner.scan()
            GLib.idle_add(self._populate, found)

        threading.Thread(target=work, daemon=True).start()

    def _populate(self, found: list[scanner.PacFile]) -> None:
        previous = self._current.path if self._current else None
        self._files = found
        while (row := self._list.get_row_at_index(0)) is not None:
            self._list.remove(row)
        for pacfile in found:
            self._list.append(FileRow(pacfile))
        self._sidebar_stack.set_visible_child_name("list" if found else "empty")
        if not found:
            self._current = None
            self._content_stack.set_visible_child_name("placeholder")
            self._window_title.set_title(_("Pacto"))
            self._window_title.set_subtitle("")
            self._update_sensitivity()
            return
        index = next((i for i, f in enumerate(found) if f.path == previous), 0)
        self._list.select_row(self._list.get_row_at_index(index))
        return False

    def _on_row_selected(self, _list: Gtk.ListBox, row: FileRow | None) -> None:
        if row is None:
            return
        self._show_file(row.pacfile)
        if self._split.get_collapsed():
            self._split.set_show_content(True)

    def _show_file(self, pacfile: scanner.PacFile | None, privileged: bool = False) -> None:
        if pacfile is None:
            return
        self._current = pacfile
        self._window_title.set_title(pacfile.target.name)
        self._window_title.set_subtitle(str(pacfile.target.parent))
        self._left_title.set_label(_("In use — {path}").format(path=pacfile.target))
        self._right_title.set_label(_("New — {path}").format(path=pacfile.path))

        try:
            old = files.read_lines(pacfile.target, privileged)
            new = files.read_lines(pacfile.path, privileged)
        except files.ReadError as error:
            if error.needs_root:
                self._banner.set_title(_("Administrator rights are required to read this file."))
                self._banner.set_revealed(True)
                self._content_stack.set_visible_child_name("diff")
            else:
                self._error_page.set_description(str(error))
                self._content_stack.set_visible_child_name("error")
            self._update_sensitivity()
            return

        self._banner.set_revealed(False)
        rows, stats = build_rows(old, new, collapse=self._collapse)
        self._diff_view.set_rows(rows)
        self._change_rows = [i for i, row in enumerate(rows) if row.kind not in (EQUAL, SKIP)]
        self._change_index = -1
        self._set_stats(stats)
        self._content_stack.set_visible_child_name("diff")
        self._update_sensitivity()

    def _set_stats(self, stats: DiffStats) -> None:
        if stats.total == 0:
            self._stats_label.set_label(_("Files are identical"))
        else:
            self._stats_label.set_label(
                _("{removed} removed · {modified} modified · {added} added").format(
                    removed=stats.deletions, modified=stats.changes, added=stats.insertions
                )
            )

    def _update_sensitivity(self) -> None:
        has_file = self._current is not None
        has_changes = bool(self._change_rows)
        for widget in (self._keep_button, self._apply_button):
            widget.set_sensitive(has_file)
        self._next.set_sensitive(has_changes)
        self._previous.set_sensitive(has_changes)

    def _jump(self, direction: int) -> None:
        if not self._change_rows:
            return
        self._change_index = (self._change_index + direction) % len(self._change_rows)
        self._diff_view.scroll_to_row(self._change_rows[self._change_index])

    # File operations -----------------------------------------------------

    def _confirm_apply(self) -> None:
        if self._current is None:
            return
        pacfile = self._current
        dialog = Adw.AlertDialog(
            heading=_("Use the new file?"),
            body=_("{new} will replace {target}. The current file is lost.").format(
                new=pacfile.path.name, target=pacfile.target
            ),
        )
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("apply", _("Replace"))
        dialog.set_response_appearance("apply", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.connect("response", self._on_apply_response, pacfile)
        dialog.present(self)

    def _on_apply_response(self, _dialog, response: str, pacfile: scanner.PacFile) -> None:
        if response != "apply":
            return
        self._run_operation(
            lambda: files.apply_new(pacfile.path, pacfile.target),
            _("{name} installed").format(name=pacfile.target.name),
        )

    def _confirm_keep(self) -> None:
        if self._current is None:
            return
        pacfile = self._current
        dialog = Adw.AlertDialog(
            heading=_("Keep the current file?"),
            body=_("{new} will be deleted and {target} left untouched.").format(
                new=pacfile.path.name, target=pacfile.target
            ),
        )
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("delete", _("Delete"))
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.connect("response", self._on_keep_response, pacfile)
        dialog.present(self)

    def _on_keep_response(self, _dialog, response: str, pacfile: scanner.PacFile) -> None:
        if response != "delete":
            return
        self._run_operation(lambda: files.discard_new(pacfile.path), _("{name} deleted").format(name=pacfile.path.name))

    def _run_operation(self, operation, message: str) -> None:
        try:
            operation()
        except files.ReadError as error:
            self._toast_overlay.add_toast(Adw.Toast(title=str(error)))
            return
        self._current = None
        self._toast_overlay.add_toast(Adw.Toast(title=message))
        self.refresh()

    def _show_shortcuts(self) -> None:
        dialog = Adw.ShortcutsDialog()
        section = Adw.ShortcutsSection(title=_("General"))
        for accelerator, title in (
            ("<Control>r", _("Rescan")),
            ("<Control>f", _("Filter files")),
            ("<Control>n", _("Next change")),
            ("<Control>p", _("Previous change")),
            ("<Control>q", _("Quit")),
        ):
            section.add(Adw.ShortcutsItem(title=title, accelerator=accelerator))
        dialog.add(section)
        dialog.present(self)
