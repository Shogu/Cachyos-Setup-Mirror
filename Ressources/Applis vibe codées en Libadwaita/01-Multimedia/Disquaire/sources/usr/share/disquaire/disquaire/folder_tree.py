# SPDX-License-Identifier: GPL-3.0-or-later
"""Volet de gauche : arborescence des dossiers."""

import os
import threading

from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk

from .model import natural_key
from .tags import is_audio
from .textfmt import match_key


def uri_list(paths) -> Gdk.ContentProvider:
    """Contenu glissé : une liste d'URI, comprise aussi par Fichiers."""
    data = "".join(Gio.File.new_for_path(p).get_uri() + "\r\n" for p in paths)
    return Gdk.ContentProvider.new_for_bytes("text/uri-list", GLib.Bytes.new(data.encode()))


class FolderItem(GObject.Object):
    __gtype_name__ = "DisquaireFolderItem"

    def __init__(self, path: str, name: str | None = None):
        super().__init__()
        self.path = path
        self.name = name or os.path.basename(path.rstrip(os.sep)) or path


def _subfolders(path: str) -> list[FolderItem]:
    try:
        with os.scandir(path) as it:
            dirs = [
                e for e in it
                if not e.name.startswith(".") and e.is_dir(follow_symlinks=True)
            ]
    except OSError:
        return []
    dirs.sort(key=lambda e: natural_key(e.name))
    return [FolderItem(e.path, e.name) for e in dirs]


def _prefix(path: str) -> str:
    return path if path.endswith(os.sep) else path + os.sep


class FolderTree(Adw.Bin):
    __gtype_name__ = "DisquaireFolderTree"
    __gsignals__ = {
        "folder-selected": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "change-root": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "rename-folder": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "rename-all-folders": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "new-folder": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "trash-folder": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "open-path": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "drop-paths": (GObject.SignalFlags.RUN_FIRST, None, (str, object)),
    }

    def __init__(self):
        super().__init__()
        self.root = None
        self._silent = False
        self._index: list[tuple[str, bool]] | None = None   # (chemin, est un dossier)
        self._index_root = None
        self._indexing = False
        self._search_id = 0

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar(show_end_title_buttons=False)
        header.set_title_widget(Adw.WindowTitle(title="Dossiers"))
        root_btn = Gtk.Button(icon_name="folder-open-symbolic",
                              tooltip_text="Choisir le dossier de base")
        root_btn.connect("clicked", lambda *_: self.emit("change-root"))
        header.pack_start(root_btn)
        self.rename_all_button = Gtk.Button(
            icon_name="document-edit-symbolic",
            tooltip_text="Renommer tous les dossiers en Artiste - Album",
        )
        self.rename_all_button.connect(
            "clicked", lambda *_: self.emit("rename-all-folders"))
        header.pack_start(self.rename_all_button)
        self.menu_button = Gtk.MenuButton(icon_name="view-more-symbolic",
                                          tooltip_text="Actions sur le dossier")
        self.menu_button.set_create_popup_func(self._fill_header_menu)
        header.pack_end(self.menu_button)
        self.search_button = Gtk.ToggleButton(icon_name="system-search-symbolic",
                                              tooltip_text="Rechercher un dossier ou un morceau")
        header.pack_end(self.search_button)
        toolbar.add_top_bar(header)

        self.search_entry = Gtk.SearchEntry(placeholder_text="Dossier ou morceau", hexpand=True)
        self.search_entry.connect("search-changed", lambda *_: self._schedule_search())
        self.search_entry.connect("activate", lambda *_: self._activate_first())
        self.search_entry.connect("stop-search", lambda *_: self.search_bar.set_search_mode(False))
        self.search_bar = Gtk.SearchBar(child=self.search_entry)
        self.search_bar.connect_entry(self.search_entry)
        self.search_bar.bind_property(
            "search-mode-enabled", self.search_button, "active",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        self.search_bar.connect("notify::search-mode-enabled", self._on_search_mode)
        toolbar.add_top_bar(self.search_bar)

        group = Gio.SimpleActionGroup()
        for name, signal in (("rename", "rename-folder"), ("new", "new-folder"),
                             ("trash", "trash-folder")):
            action = Gio.SimpleAction.new(name, GLib.VariantType.new("s"))
            action.connect("activate", lambda _a, param, sig=signal:
                           self.emit(sig, param.get_string()))
            group.add_action(action)
        self.insert_action_group("tree", group)

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._setup)
        factory.connect("bind", self._bind)

        self._root_store = Gio.ListStore(item_type=FolderItem)
        self._tree = Gtk.TreeListModel.new(
            self._root_store, False, False, self._create_children,
        )
        self._selection = Gtk.SingleSelection(
            model=self._tree, autoselect=False, can_unselect=True,
        )
        self._selection.connect("notify::selected-item", self._on_selected)

        self.view = Gtk.ListView(model=self._selection, factory=factory)
        self.view.add_css_class("navigation-sidebar")
        scrolled = Gtk.ScrolledWindow(
            child=self.view, hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True,
        )
        self.results = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.results.add_css_class("navigation-sidebar")
        self.results.connect("row-activated", self._on_result_activated)
        results_scrolled = Gtk.ScrolledWindow(
            child=self.results, hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True)
        self.none_label = Gtk.Label(label="Aucun dossier ni morceau trouvé", vexpand=True,
                                    valign=Gtk.Align.START, margin_top=24, wrap=True)
        self.none_label.add_css_class("dim-label")
        indexing = Gtk.Label(label="Lecture de l'arborescence…", vexpand=True,
                             valign=Gtk.Align.START, margin_top=24)
        indexing.add_css_class("dim-label")
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.stack.add_named(scrolled, "tree")
        self.stack.add_named(results_scrolled, "results")
        self.stack.add_named(self.none_label, "none")
        self.stack.add_named(indexing, "indexing")
        toolbar.set_content(self.stack)
        self.set_child(toolbar)

    # --- modèle -----------------------------------------------------------
    def _create_children(self, item, *_):
        children = _subfolders(item.path)
        if not children:
            return None
        store = Gio.ListStore(item_type=FolderItem)
        store.splice(0, 0, children)
        return store

    def set_root(self, path: str) -> None:
        self.root = os.path.normpath(path)
        self._index = None
        self._silent = True
        self._root_store.remove_all()
        home = GLib.get_home_dir()
        name = "Dossier personnel" if self.root == home else None
        self._root_store.append(FolderItem(self.root, name))
        row = self._tree.get_item(0)
        if row is not None:
            row.set_expanded(True)
        self._selection.set_selected(Gtk.INVALID_LIST_POSITION)
        self._silent = False

    def reload(self) -> None:
        """Relit l'arborescence (après création ou suppression de dossiers)."""
        current = self.selected_path()
        self._index = None
        if self.root:
            self.set_root(self.root)
            if current:
                self.select_path(current, silent=True)

    def selected_path(self):
        row = self._selection.get_selected_item()
        return row.get_item().path if row is not None else None

    def select_path(self, target: str, silent: bool = False) -> bool:
        """Déplie l'arbre jusqu'à `target` et le sélectionne."""
        if not self.root or not target:
            return False
        target = os.path.normpath(target)
        if target != self.root and not target.startswith(_prefix(self.root)):
            return False
        i = 0
        while i < self._tree.get_n_items():
            row = self._tree.get_item(i)
            path = row.get_item().path
            if path == target:
                self._silent = silent
                self._selection.set_selected(i)
                self._silent = False
                GLib.idle_add(self._scroll_to, i)
                return True
            if target.startswith(_prefix(path)):
                row.set_expanded(True)
            i += 1
        return False

    def _scroll_to(self, position: int) -> bool:
        try:
            self.view.scroll_to(position, Gtk.ListScrollFlags.NONE, None)
        except (AttributeError, TypeError):
            pass
        return GLib.SOURCE_REMOVE

    # --- vue --------------------------------------------------------------
    def _setup(self, _factory, list_item):
        expander = Gtk.TreeExpander()
        box = Gtk.Box(spacing=8)
        icon = Gtk.Image(icon_name="folder-symbolic")
        label = Gtk.Label(xalign=0, ellipsize=3)  # Pango.EllipsizeMode.END
        box.append(icon)
        box.append(label)
        expander.set_child(box)
        click = Gtk.GestureClick(button=3)
        click.connect("pressed", self._on_right_click, expander)
        expander.add_controller(click)
        press = Gtk.GestureLongPress()
        press.connect("pressed", lambda g, x, y, e=expander: self._show_menu(e, x, y))
        expander.add_controller(press)

        drag = Gtk.DragSource(actions=Gdk.DragAction.MOVE)
        drag.connect("prepare", self._on_drag_prepare, expander)
        drag.connect("drag-begin", lambda src, _d, b=box: src.set_icon(
            Gtk.WidgetPaintable.new(b), 0, 0))
        expander.add_controller(drag)
        drop = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.MOVE | Gdk.DragAction.COPY)
        drop.connect("drop", self._on_drop, expander)
        expander.add_controller(drop)
        list_item.set_child(expander)

    def _bind(self, _factory, list_item):
        row = list_item.get_item()
        expander = list_item.get_child()
        expander.set_list_row(row)
        item = row.get_item()
        box = expander.get_child()
        icon = box.get_first_child()
        label = icon.get_next_sibling()
        label.set_label(item.name)
        expander.set_tooltip_text(item.path)
        icon.set_from_icon_name(
            "user-home-symbolic" if item.path == GLib.get_home_dir()
            else "folder-symbolic"
        )

    # --- glisser-déposer ---------------------------------------------------
    def _on_drag_prepare(self, _source, _x, _y, expander):
        row = expander.get_list_row()
        if row is None or row.get_depth() == 0:
            return None  # le dossier de base ne se déplace pas
        return uri_list([row.get_item().path])

    def _on_drop(self, _target, value, _x, _y, expander):
        row = expander.get_list_row()
        if row is None:
            return False
        paths = [f.get_path() for f in value.get_files() if f.get_path()]
        if not paths:
            return False
        self.emit("drop-paths", row.get_item().path, paths)
        return True

    # --- recherche --------------------------------------------------------
    def _on_search_mode(self, *_):
        if not self.search_bar.get_search_mode():
            self.search_entry.set_text("")
            self.stack.set_visible_child_name("tree")
        else:
            self._index = None  # relu à chaque ouverture : toujours à jour
            self._ensure_index()

    def _ensure_index(self):
        if not self.root or self._indexing:
            return
        if self._index is not None and self._index_root == self.root:
            return
        self._indexing = True
        root = self.root

        def work():
            found = []
            for dirpath, dirnames, files in os.walk(root):
                dirnames[:] = [d for d in dirnames if not d.startswith(".")]
                found += [(os.path.join(dirpath, d), True) for d in dirnames]
                found += [(os.path.join(dirpath, f), False) for f in files
                          if not f.startswith(".") and is_audio(f)]
            GLib.idle_add(done, found)

        def done(found):
            self._indexing = False
            if root == self.root:
                self._index, self._index_root = found, root
                self._run_search()
            return GLib.SOURCE_REMOVE

        threading.Thread(target=work, daemon=True).start()

    def _schedule_search(self):
        if self._search_id:
            GLib.source_remove(self._search_id)
        self._search_id = GLib.timeout_add(150, self._run_search)

    def _run_search(self):
        self._search_id = 0
        query = match_key(self.search_entry.get_text())
        if not query:
            self.stack.set_visible_child_name("tree")
            return GLib.SOURCE_REMOVE
        if self._index is None or self._index_root != self.root:
            self.stack.set_visible_child_name("indexing")
            self._ensure_index()
            return GLib.SOURCE_REMOVE
        words = query.split()
        hits = []
        for path, is_dir in self._index:
            rel = os.path.relpath(path, self.root)
            key = match_key(rel)
            if all(w in key for w in words):
                name_key = match_key(os.path.basename(path))
                # D'abord les noms qui contiennent la recherche, dossiers en tête.
                hits.append((not all(w in name_key for w in words), not is_dir,
                             len(rel), rel, path, is_dir))
        hits.sort()
        child = self.results.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.results.remove(child)
            child = nxt
        for _rank, _file, _n, rel, path, is_dir in hits[:200]:
            parent = os.path.dirname(rel)
            name = os.path.basename(path)
            if not is_dir:
                name = os.path.splitext(name)[0]
            row = Adw.ActionRow(title=GLib.markup_escape_text(name),
                                subtitle=GLib.markup_escape_text(parent) if parent else "",
                                activatable=True)
            row.add_prefix(Gtk.Image(
                icon_name="folder-symbolic" if is_dir else "disquaire-music-symbolic"))
            row.path = path
            row.is_dir = is_dir
            self.results.append(row)
        self.stack.set_visible_child_name("results" if hits else "none")
        return GLib.SOURCE_REMOVE

    def _activate_first(self):
        row = self.results.get_row_at_index(0)
        if row is not None and self.stack.get_visible_child_name() == "results":
            self._on_result_activated(self.results, row)

    def _on_result_activated(self, _box, row):
        path = getattr(row, "path", None)
        if not path:
            return
        self.search_bar.set_search_mode(False)
        if getattr(row, "is_dir", True):
            self.select_path(path)
        else:
            self.emit("open-path", path)

    def _menu_for(self, path: str) -> Gio.Menu:
        menu = Gio.Menu()
        target = GLib.Variant("s", path)
        section = Gio.Menu()
        for label, action in (("Nouveau dossier…", "tree.new"),
                              ("Renommer en « Artiste - Album »…", "tree.rename")):
            item = Gio.MenuItem.new(label, None)
            item.set_action_and_target_value(action, target)
            section.append_item(item)
        menu.append_section(None, section)
        if path != self.root:
            danger = Gio.Menu()
            item = Gio.MenuItem.new("Mettre à la corbeille", None)
            item.set_action_and_target_value("tree.trash", target)
            danger.append_item(item)
            menu.append_section(None, danger)
        return menu

    def _fill_header_menu(self, button):
        path = self.selected_path() or self.root
        if path:
            button.set_menu_model(self._menu_for(path))

    def _on_right_click(self, gesture, _n, x, y, expander):
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        self._show_menu(expander, x, y)

    def _show_menu(self, expander, x, y):
        row = expander.get_list_row()
        if row is None:
            return
        popover = Gtk.PopoverMenu.new_from_model(self._menu_for(row.get_item().path))
        popover.set_parent(expander)
        popover.set_has_arrow(False)
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = int(x), int(y), 1, 1
        popover.set_pointing_to(rect)
        popover.connect("closed", lambda p: GLib.idle_add(p.unparent))
        popover.popup()

    def _on_selected(self, *_):
        if self._silent:
            return
        path = self.selected_path()
        if path:
            self.emit("folder-selected", path)
