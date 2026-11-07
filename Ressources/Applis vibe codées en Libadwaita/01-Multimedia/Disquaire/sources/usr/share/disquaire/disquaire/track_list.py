# SPDX-License-Identifier: GPL-3.0-or-later
"""Volet central : morceaux du dossier, recherche et sélection multiple."""

import os

from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk, Pango

from .folder_tree import uri_list
from .model import Track, natural_key


def _menu(*sections) -> Gio.Menu:
    menu = Gio.Menu()
    for section in sections:
        sub = Gio.Menu()
        for label, action in section:
            sub.append(label, action)
        menu.append_section(None, sub)
    return menu


class TrackList(Adw.Bin):
    __gtype_name__ = "DisquaireTrackList"
    __gsignals__ = {
        "current-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        # (texte, portée) : portée = "folder" ou "all"
        "search-changed": (GObject.SignalFlags.RUN_FIRST, None, (str, str)),
    }

    def __init__(self):
        super().__init__()
        self._silent = False

        self.store = Gio.ListStore(item_type=Track)
        self._query = ""
        self.scope = "folder"
        self.filters: set[str] = set()
        self.library_mode = False   # vrai quand la liste montre des résultats globaux
        self.root = None
        self._filter = Gtk.CustomFilter.new(self._match)
        self.filtered = Gtk.FilterListModel(model=self.store, filter=self._filter)
        self.selection = Gtk.SingleSelection(
            model=self.filtered, autoselect=False, can_unselect=True,
        )
        self.selection.connect("notify::selected-item", self._on_selected)
        self.filtered.connect("items-changed", lambda *_: self._update_stack())

        # --- barre de titre -------------------------------------------------
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar(show_end_title_buttons=False)
        self.title = Adw.WindowTitle(title="Disquaire")
        header.set_title_widget(self.title)

        self.sidebar_button = Gtk.ToggleButton(
            icon_name="sidebar-show-symbolic", tooltip_text="Afficher les dossiers",
        )
        header.pack_start(self.sidebar_button)
        self.search_button = Gtk.ToggleButton(
            icon_name="system-search-symbolic", tooltip_text="Rechercher (Ctrl+F)",
        )
        header.pack_start(self.search_button)
        self.filter_button = Gtk.MenuButton(icon_name="disquaire-filter-symbolic",
                                            tooltip_text="Filtrer la liste")
        fbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2,
                       margin_top=6, margin_bottom=6, margin_start=6, margin_end=6)
        for key, label in (("no-lyrics", "Sans paroles"), ("no-cover", "Sans pochette"),
                           ("no-year", "Sans année"), ("no-genre", "Sans genre"),
                           ("to-clean", "À enregistrer ou nettoyer")):
            cb = Gtk.CheckButton(label=label)
            cb.connect("toggled", self._on_filter, key)
            fbox.append(cb)
        self._filter_checks = fbox
        self.filter_button.set_popover(Gtk.Popover(child=fbox))
        header.pack_start(self.filter_button)

        menu = _menu(
            [("Tout sélectionner", "win.select-all"),
             ("Tout désélectionner", "win.select-none")],
            [("Tout enregistrer", "win.save-all"),
             ("Annuler la dernière opération", "win.undo"),
             ("Rafraîchir", "win.refresh")],
            [("Paroles : ce dossier et ses sous-dossiers", "win.lyrics-queue-folder"),
             ("Paroles : toute la discothèque", "win.lyrics-queue-all"),
             ("Pochettes manquantes depuis la réserve", "win.reserve-folder"),
             ("Rechercher les doublons…", "win.duplicates")],
            [("Genres…", "win.genres"),
             ("Préférences", "win.preferences")],
            [("Raccourcis clavier", "app.shortcuts"),
             ("À propos de Disquaire", "app.about")],
        )
        header.pack_end(Gtk.MenuButton(
            icon_name="open-menu-symbolic", menu_model=menu,
            tooltip_text="Menu principal", primary=True,
        ))
        header.pack_end(Gtk.Button(
            icon_name="view-refresh-symbolic", action_name="win.refresh",
            tooltip_text="Rafraîchir la liste (F5)",
        ))
        toolbar.add_top_bar(header)

        self.search_entry = Gtk.SearchEntry(
            placeholder_text="Titre, artiste, album, genre, année…", hexpand=True,
        )
        self.search_entry.connect("search-changed", self._on_search)
        self.scope_folder = Gtk.ToggleButton(label="Dossier en cours", active=True,
                                             hexpand=True)
        self.scope_all = Gtk.ToggleButton(label="Tous les morceaux", group=self.scope_folder,
                                          hexpand=True)
        self.scope_all.connect("toggled", self._on_scope)
        scope_box = Gtk.Box(homogeneous=True)
        scope_box.add_css_class("linked")
        scope_box.append(self.scope_folder)
        scope_box.append(self.scope_all)
        search_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        search_box.append(self.search_entry)
        search_box.append(scope_box)
        self.search_bar = Gtk.SearchBar(child=Adw.Clamp(child=search_box,
                                                       maximum_size=420))
        self.search_bar.connect_entry(self.search_entry)
        self.search_bar.bind_property(
            "search-mode-enabled", self.search_button, "active",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
        )
        toolbar.add_top_bar(self.search_bar)

        self.banner = Adw.Banner(button_label="Tout enregistrer")
        self.banner.set_action_name("win.save-all")
        toolbar.add_top_bar(self.banner)
        self.cover_banner = Adw.Banner(title="folder.jpg trouvé dans ce dossier",
                                       button_label="Intégrer partout")
        self.cover_banner.set_action_name("win.folder-cover-all")
        toolbar.add_top_bar(self.cover_banner)

        # --- liste ----------------------------------------------------------
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._setup)
        factory.connect("bind", self._bind)
        factory.connect("unbind", self._unbind)
        self.view = Gtk.ListView(model=self.selection, factory=factory)
        self.view.add_css_class("navigation-sidebar")
        self.view.add_css_class("track-list")
        keys = Gtk.ShortcutController(scope=Gtk.ShortcutScope.LOCAL)
        keys.add_shortcut(Gtk.Shortcut.new(
            Gtk.ShortcutTrigger.parse_string("<Control>a"),
            Gtk.NamedAction.new("win.select-all")))
        keys.add_shortcut(Gtk.Shortcut.new(
            Gtk.ShortcutTrigger.parse_string("Escape"),
            Gtk.NamedAction.new("win.select-none")))
        self.view.add_controller(keys)
        scrolled = Gtk.ScrolledWindow(
            child=self.view, hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True,
        )

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.stack.add_named(scrolled, "list")
        self.stack.add_named(Adw.StatusPage(
            icon_name="disquaire-music-symbolic", title="Aucun morceau",
            description="Ce dossier ne contient ni MP3 ni FLAC.",
        ), "empty")
        self.stack.add_named(Adw.StatusPage(
            icon_name="system-search-symbolic", title="Aucun résultat",
            description="Essayez une autre recherche.",
        ), "no-results")
        searching = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                            valign=Gtk.Align.CENTER, margin_start=36, margin_end=36)
        self.searching_label = Gtk.Label(label="Lecture des tags de la discothèque…",
                                         wrap=True, justify=Gtk.Justification.CENTER)
        self.searching_label.add_css_class("dim-label")
        self.searching_bar = Gtk.ProgressBar()
        searching.append(self.searching_label)
        searching.append(self.searching_bar)
        self.stack.add_named(searching, "searching")
        self.stack.add_named(Adw.StatusPage(
            icon_name="folder-symbolic", title="Choisissez un dossier",
            description="Les MP3 et FLAC du dossier s'afficheront ici.",
        ), "no-folder")
        self.stack.set_visible_child_name("no-folder")
        toolbar.set_content(self.stack)

        # --- barre de sélection --------------------------------------------
        self.action_bar = Gtk.ActionBar(revealed=False)
        self.selection_label = Gtk.Label(css_classes=["heading"], visible=False)
        self.action_bar.pack_start(self.selection_label)

        def icon_button(icon, action, tip):
            b = Gtk.Button(icon_name=icon, action_name=action, tooltip_text=tip)
            b.add_css_class("flat")
            return b

        self.select_button = icon_button("disquaire-select-all-symbolic",
                                         "win.toggle-check-all", "Tout sélectionner")
        self.tidy_mp3_button = icon_button("disquaire-tidy-symbolic", "win.tidy-mp3-folder",
                                           "Mettre en forme tous les MP3 du dossier")
        self.action_bar.pack_start(self.select_button)
        self.action_bar.pack_start(self.tidy_mp3_button)
        self.trash_button = icon_button("user-trash-symbolic", "win.trash",
                                        "Mettre à la corbeille")
        self.move_button = icon_button("disquaire-move-symbolic", "win.move",
                                       "Déplacer vers un autre dossier…")
        self.convert_button = icon_button("disquaire-convert-symbolic", "win.convert",
                                          "Convertir les FLAC sélectionnés en MP3")
        self.unselect_button = icon_button("edit-clear-symbolic", "win.select-none",
                                           "Tout désélectionner")
        for button in (self.trash_button, self.move_button, self.convert_button):
            button.set_visible(False)
            self.action_bar.pack_end(button)
        self.unselect_button.set_visible(False)
        toolbar.add_bottom_bar(self.action_bar)

        # --- file d'attente des paroles --------------------------------------
        self.lyrics_revealer = Gtk.Revealer(
            transition_type=Gtk.RevealerTransitionType.SLIDE_UP)
        lbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4,
                       margin_top=6, margin_bottom=8, margin_start=12, margin_end=12)
        lrow = Gtk.Box(spacing=6)
        self.lyrics_label = Gtk.Label(xalign=0, hexpand=True,
                                      ellipsize=Pango.EllipsizeMode.END)
        self.lyrics_label.add_css_class("caption")
        self.lyrics_pause = Gtk.Button(icon_name="media-playback-pause-symbolic",
                                       action_name="win.lyrics-queue-toggle")
        self.lyrics_stop = Gtk.Button(icon_name="process-stop-symbolic",
                                      action_name="win.lyrics-queue-stop",
                                      tooltip_text="Arrêter et vider la file")
        for b in (self.lyrics_pause, self.lyrics_stop):
            b.add_css_class("flat")
            b.add_css_class("circular")
            lrow.append(b)
        lrow.prepend(self.lyrics_label)
        self.lyrics_bar = Gtk.ProgressBar()
        lbox.append(lrow)
        lbox.append(self.lyrics_bar)
        self.lyrics_revealer.set_child(lbox)
        toolbar.add_bottom_bar(self.lyrics_revealer)

        # --- progression ----------------------------------------------------
        self.progress_revealer = Gtk.Revealer(
            transition_type=Gtk.RevealerTransitionType.SLIDE_UP,
        )
        pbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                       margin_top=8, margin_bottom=10, margin_start=12, margin_end=12)
        prow = Gtk.Box(spacing=8)
        self.progress_label = Gtk.Label(xalign=0, hexpand=True,
                                        ellipsize=Pango.EllipsizeMode.MIDDLE)
        self.progress_label.add_css_class("caption")
        self.progress_cancel = Gtk.Button(icon_name="process-stop-symbolic",
                                          tooltip_text="Annuler")
        self.progress_cancel.add_css_class("flat")
        self.progress_cancel.add_css_class("circular")
        prow.append(self.progress_label)
        prow.append(self.progress_cancel)
        self.progress_bar = Gtk.ProgressBar()
        pbox.append(prow)
        pbox.append(self.progress_bar)
        self.progress_revealer.set_child(pbox)
        toolbar.add_bottom_bar(self.progress_revealer)

        self.set_child(toolbar)

    # --- contenu ----------------------------------------------------------
    def tracks(self) -> list[Track]:
        return [self.store.get_item(i) for i in range(self.store.get_n_items())]

    def set_tracks(self, tracks: list[Track]) -> None:
        self._silent = True
        # Un seul remplacement : évite d'afficher « Aucun morceau » un instant.
        self.store.splice(0, self.store.get_n_items(), tracks)
        self.selection.set_selected(Gtk.INVALID_LIST_POSITION)
        self._silent = False
        self._update_stack()

    def clear(self) -> None:
        self.set_tracks([])
        self.stack.set_visible_child_name("no-folder")

    def find(self, path: str):
        for t in self.tracks():
            if t.path == path:
                return t
        return None

    def insert_sorted(self, track: Track) -> None:
        key = natural_key(track.name)
        n = self.store.get_n_items()
        pos = n
        for i in range(n):
            if natural_key(self.store.get_item(i).name) > key:
                pos = i
                break
        self.store.insert(pos, track)

    def remove(self, track: Track) -> None:
        found, pos = self.store.find(track)
        if found:
            self.store.remove(pos)

    def replace(self, old: Track, new: Track) -> None:
        found, pos = self.store.find(old)
        if found:
            self.store.splice(pos, 1, [new])
        else:
            self.insert_sorted(new)

    def resort(self, track: Track) -> None:
        current = self.current()
        self._silent = True
        self.remove(track)
        self.insert_sorted(track)
        self._silent = False
        if current is not None:
            self.select(current)

    # --- sélection courante -----------------------------------------------
    def current(self):
        return self.selection.get_selected_item()

    def select(self, track) -> None:
        if track is None:
            self.selection.set_selected(Gtk.INVALID_LIST_POSITION)
            return
        for i in range(self.filtered.get_n_items()):
            if self.filtered.get_item(i) is track:
                self.selection.set_selected(i)
                # Amène le morceau à l'écran (ouverture depuis le lecteur ou Fichiers).
                GLib.idle_add(self._scroll_to, i)
                return

    def _scroll_to(self, position: int) -> bool:
        if position < self.filtered.get_n_items():
            self.view.scroll_to(position, Gtk.ListScrollFlags.FOCUS, None)
        return GLib.SOURCE_REMOVE

    def _on_selected(self, *_):
        if not self._silent:
            self.emit("current-changed")

    # --- recherche --------------------------------------------------------
    def _on_search(self, entry):
        self._query = entry.get_text().strip().casefold()
        if not self.library_mode:
            self._filter.changed(Gtk.FilterChange.DIFFERENT)
            self._update_stack()
        self.emit("search-changed", entry.get_text(), self.scope)

    def _on_scope(self, button):
        self.scope = "all" if button.get_active() else "folder"
        self.search_entry.grab_focus()
        self.emit("search-changed", self.search_entry.get_text(), self.scope)

    def set_scope(self, scope: str) -> None:
        """Change la portée sans émettre de signal."""
        self.scope_all.handler_block_by_func(self._on_scope)
        (self.scope_all if scope == "all" else self.scope_folder).set_active(True)
        self.scope_all.handler_unblock_by_func(self._on_scope)
        self.scope = scope

    def set_library_mode(self, enabled: bool) -> None:
        self.library_mode = enabled
        self._filter.changed(Gtk.FilterChange.DIFFERENT)
        self._update_stack()

    def _on_filter(self, button, key):
        (self.filters.add if button.get_active() else self.filters.discard)(key)
        if self.filters:
            self.filter_button.add_css_class("accent")
        else:
            self.filter_button.remove_css_class("accent")
        self._filter.changed(Gtk.FilterChange.DIFFERENT)
        self._update_stack()

    def _passes_filters(self, track) -> bool:
        if not self.filters:
            return True
        if not track.loaded:
            return True
        v = track.values
        checks = {
            "no-lyrics": not v.lyrics.strip(),
            "no-cover": v.cover is None,
            "no-year": not v.date.strip(),
            "no-genre": not v.genre.strip(),
            "to-clean": track.dirty,
        }
        return all(checks[f] for f in self.filters)

    def _match(self, track) -> bool:
        if not self._passes_filters(track):
            return False
        if self.library_mode or not self._query:
            return True
        v = track.values
        hay = " ".join((track.name, v.title, v.artist, v.album, v.genre, v.date)).casefold()
        return all(word in hay for word in self._query.split())

    def refilter(self) -> None:
        if self._query or self.filters:
            self._filter.changed(Gtk.FilterChange.DIFFERENT)

    def show_searching(self, fraction: float | None = None) -> None:
        if fraction is None:
            self.searching_bar.pulse()
        else:
            self.searching_bar.set_fraction(fraction)
        self.stack.set_visible_child_name("searching")

    def _update_stack(self) -> None:
        if self.stack.get_visible_child_name() == "no-folder" and self.store.get_n_items() == 0:
            return
        if self.library_mode and self.store.get_n_items() == 0:
            self.stack.set_visible_child_name("no-results")
            return
        if self.store.get_n_items() == 0:
            self.stack.set_visible_child_name("empty")
        elif self.filtered.get_n_items() == 0:
            self.stack.set_visible_child_name("no-results")
        else:
            self.stack.set_visible_child_name("list")

    def show_list_state(self) -> None:
        self.stack.set_visible_child_name("list")
        self._update_stack()

    # --- lignes -----------------------------------------------------------
    def _setup(self, _factory, list_item):
        row = Gtk.Box(spacing=12, margin_top=4, margin_bottom=4)

        check = Gtk.CheckButton(valign=Gtk.Align.CENTER,
                                tooltip_text="Sélectionner pour modifier en lot")
        check.add_css_class("selection-mode")
        row.append(check)

        thumb = Gtk.Overlay()
        placeholder = Gtk.Image(icon_name="disquaire-music-symbolic", pixel_size=20)
        placeholder.add_css_class("thumb-placeholder")
        placeholder.set_size_request(44, 44)
        thumb.set_child(placeholder)
        picture = Gtk.Picture(content_fit=Gtk.ContentFit.COVER, can_shrink=True)
        picture.set_size_request(44, 44)
        picture.set_overflow(Gtk.Overflow.HIDDEN)
        picture.add_css_class("thumb")
        thumb.add_overlay(picture)
        thumb.set_valign(Gtk.Align.CENTER)
        row.append(thumb)

        texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True,
                        valign=Gtk.Align.CENTER, spacing=1)
        title = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END)
        title.add_css_class("heading")
        subtitle = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END)
        subtitle.add_css_class("dim-label")
        filename = Gtk.Label(xalign=0, wrap=True,
                             wrap_mode=Pango.WrapMode.CHAR)
        filename.set_ellipsize(Pango.EllipsizeMode.NONE)
        filename.add_css_class("caption")
        filename.add_css_class("dim-label")
        texts.append(title)
        texts.append(subtitle)
        texts.append(filename)
        row.append(texts)

        badge = Gtk.Label(label="FLAC", valign=Gtk.Align.CENTER)
        badge.add_css_class("format-badge")
        row.append(badge)

        lyr = Gtk.Label(label="Paroles", valign=Gtk.Align.CENTER,
                        tooltip_text="Paroles enregistrées dans les tags")
        lyr.add_css_class("lyrics-badge")
        row.append(lyr)

        dot = Gtk.Box(valign=Gtk.Align.CENTER, tooltip_text="Modifications non enregistrées")
        dot.add_css_class("dirty-dot")
        row.append(dot)

        drag = Gtk.DragSource(actions=Gdk.DragAction.MOVE)
        drag.connect("prepare", self._on_drag_prepare, row)
        drag.connect("drag-begin", lambda src, _d, r=row: src.set_icon(
            Gtk.WidgetPaintable.new(r), 0, 0))
        row.add_controller(drag)

        row._w = (check, picture, title, subtitle, filename, badge, dot, lyr)
        row._bindings = []
        list_item.set_child(row)

    def _bind(self, _factory, list_item):
        row = list_item.get_child()
        track = list_item.get_item()
        check, picture, title, subtitle, filename, badge, dot, lyr = row._w
        flags = GObject.BindingFlags.SYNC_CREATE
        row._bindings = [
            track.bind_property("checked", check, "active",
                                flags | GObject.BindingFlags.BIDIRECTIONAL),
            track.bind_property("thumbnail", picture, "paintable", flags),
            track.bind_property("display-title", title, "label", flags),
            track.bind_property("display-subtitle", subtitle, "label", flags),
            track.bind_property("dirty", dot, "visible", flags),
            track.bind_property("has-lyrics", lyr, "visible", flags),
        ]
        if self.library_mode and self.root:
            # Résultats de toute la discothèque : on montre le dossier.
            rel = os.path.relpath(track.path, self.root)
            filename.set_label(rel)
            filename.set_tooltip_text(track.path)
        else:
            row._bindings.append(
                track.bind_property("display-filename", filename, "label", flags))
            filename.set_tooltip_text(None)
        badge.set_visible(track.is_flac)
        row._track = track

    def _unbind(self, _factory, list_item):
        row = list_item.get_child()
        for binding in row._bindings:
            binding.unbind()
        row._bindings = []

    def _on_drag_prepare(self, _source, _x, _y, row):
        track = getattr(row, "_track", None)
        if track is None:
            return None
        if track.checked:
            paths = [t.path for t in self.tracks() if t.checked]
        else:
            paths = [track.path]
        return uri_list(paths)

    # --- progression ------------------------------------------------------
    def show_progress(self, text: str, fraction: float, cancellable: bool) -> None:
        self.progress_label.set_label(text)
        self.progress_bar.set_fraction(max(0.0, min(1.0, fraction)))
        self.progress_cancel.set_visible(cancellable)
        self.progress_revealer.set_reveal_child(True)

    def hide_progress(self) -> None:
        self.progress_revealer.set_reveal_child(False)
