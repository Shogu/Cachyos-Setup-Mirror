# SPDX-License-Identifier: GPL-3.0-or-later
"""Volet de droite : pochette, lecture, tags, paroles et fichier."""

import os

from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk

from . import tags, textfmt
from .model import Track, texture_from_bytes

MULTIPLE = "Valeurs différentes"


def _menu(*sections) -> Gio.Menu:
    menu = Gio.Menu()
    for section in sections:
        sub = Gio.Menu()
        for label, action in section:
            sub.append(label, action)
        menu.append_section(None, sub)
    return menu


class Editor(Adw.Bin):
    __gtype_name__ = "DisquaireEditor"
    __gsignals__ = {
        "rename": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "pick-cover": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "cover-dropped": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }

    def __init__(self, player):
        super().__init__()
        self.player = player
        self.targets: list[Track] = []
        self._updating = False
        self._seeking = False

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar(show_start_title_buttons=False)
        self.title = Adw.WindowTitle(title="")
        header.set_title_widget(self.title)

        self.revert_button = Gtk.Button(
            icon_name="edit-undo-symbolic", action_name="win.revert",
            tooltip_text="Annuler les modifications",
        )
        header.pack_start(self.revert_button)
        menu = _menu(
            [("Aller au dossier du morceau", "win.goto-track"),
             ("Lire dans le lecteur par défaut", "win.open-default"),
             ("Ouvrir avec…", "win.open-with"),
             ("Afficher dans le dossier", "win.show-folder")],
            [("Renommer", "win.rename"),
             ("Déplacer vers…", "win.move"),
             ("Convertir en MP3", "win.convert")],
            [("Mettre à la corbeille", "win.trash")],
        )
        header.pack_end(Gtk.MenuButton(
            icon_name="view-more-symbolic", menu_model=menu,
            tooltip_text="Actions sur le fichier",
        ))
        self.save_button = Gtk.Button(label="Enregistrer", action_name="win.save",
                                      tooltip_text="Enregistrer (Ctrl+S)")
        self.save_button.add_css_class("suggested-action")
        header.pack_end(self.save_button)
        toolbar.add_top_bar(header)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.stack.add_named(Adw.StatusPage(
            icon_name="disquaire-music-symbolic", title="Aucun morceau",
            description="Choisissez un morceau, ou cochez-en plusieurs "
                        "pour les modifier ensemble.",
        ), "empty")
        self.stack.add_named(self._build_form(), "form")
        toolbar.set_content(self.stack)
        self.set_child(toolbar)

        player.connect("state-changed", self._on_player_state)
        player.connect("position", self._on_player_position)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def _build_form(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24,
                      margin_top=24, margin_bottom=32, margin_start=12, margin_end=12)

        # --- pochette ------------------------------------------------------
        cover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                            halign=Gtk.Align.CENTER)
        self.cover_stack = Gtk.Stack()
        self.cover_stack.set_size_request(220, 220)
        # CONTAIN : la pochette est affichée en entière, jamais recadrée.
        self.cover_picture = Gtk.Picture(content_fit=Gtk.ContentFit.CONTAIN, can_shrink=True)
        self.cover_picture.set_overflow(Gtk.Overflow.HIDDEN)
        self.cover_picture.add_css_class("cover")
        self.cover_stack.add_named(self.cover_picture, "picture")
        self.cover_placeholder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                                         valign=Gtk.Align.FILL)
        self.cover_placeholder.add_css_class("cover-placeholder")
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                        valign=Gtk.Align.CENTER, vexpand=True,
                        margin_start=20, margin_end=20)
        icon = Gtk.Image(icon_name="disquaire-image-symbolic", pixel_size=56,
                         margin_bottom=6)
        icon.add_css_class("dim-label")
        self.cover_title = Gtk.Label(wrap=True, justify=Gtk.Justification.CENTER)
        self.cover_title.add_css_class("title-4")
        self.cover_hint = Gtk.Label(wrap=True, justify=Gtk.Justification.CENTER)
        self.cover_hint.add_css_class("caption")
        self.cover_hint.add_css_class("dim-label")
        inner.append(icon)
        inner.append(self.cover_title)
        inner.append(self.cover_hint)
        self.cover_placeholder.append(inner)
        self.cover_stack.add_named(self.cover_placeholder, "placeholder")

        drop = Gtk.DropTarget.new(GObject.TYPE_NONE, Gdk.DragAction.COPY)
        drop.set_gtypes([Gdk.FileList, Gdk.Texture])
        drop.connect("drop", self._on_drop)
        self.cover_stack.add_controller(drop)

        buttons = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
        change = Gtk.Button(icon_name="disquaire-image-symbolic",
                            tooltip_text="Changer la pochette…", valign=Gtk.Align.CENTER)
        change.add_css_class("circular")
        change.connect("clicked", lambda *_: self.emit("pick-cover"))
        self.remove_cover_button = Gtk.Button(icon_name="user-trash-symbolic",
                                              tooltip_text="Retirer la pochette",
                                              valign=Gtk.Align.CENTER)
        self.remove_cover_button.add_css_class("circular")
        self.remove_cover_button.connect("clicked", self._on_remove_cover)
        online = Gtk.Button(icon_name="system-search-symbolic",
                            tooltip_text="Chercher une pochette en ligne (≥ 1024 px)",
                            valign=Gtk.Align.CENTER, action_name="win.cover-online")
        online.add_css_class("circular")
        reserve_btn = Gtk.Button(icon_name="disquaire-reserve-symbolic",
                                 tooltip_text="Réserve de pochettes",
                                 valign=Gtk.Align.CENTER, action_name="win.reserve")
        reserve_btn.add_css_class("circular")
        self.folder_cover_button = Gtk.Button(
            icon_name="disquaire-folder-cover-symbolic", action_name="win.folder-cover",
            valign=Gtk.Align.CENTER, visible=False,
            tooltip_text="Utiliser folder.jpg (pour tout le dossier : bandeau de la liste)",
        )
        self.folder_cover_button.add_css_class("circular")
        for b in (change, self.folder_cover_button, reserve_btn, online,
                  self.remove_cover_button):
            buttons.append(b)
        cover_box.append(self.cover_stack)
        cover_box.append(buttons)
        self.reserve_suggest = Gtk.Button(action_name="win.reserve-by-genre",
                                          halign=Gtk.Align.CENTER, visible=False)
        self.reserve_suggest.add_css_class("pill")
        self.reserve_suggest.add_css_class("suggested-action")
        cover_box.append(self.reserve_suggest)
        box.append(cover_box)

        # --- lecture -------------------------------------------------------
        self.player_box = Gtk.Box(spacing=8)
        self.play_button = Gtk.Button(icon_name="media-playback-start-symbolic",
                                      tooltip_text="Lire", valign=Gtk.Align.CENTER)
        self.play_button.add_css_class("circular")
        self.play_button.connect("clicked", self._on_play)
        self.seek_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 1)
        self.seek_scale.set_draw_value(False)
        self.seek_scale.set_hexpand(True)
        self.seek_scale.connect("change-value", self._on_seek)
        self.time_label = Gtk.Label(label="0:00 / 0:00")
        self.time_label.add_css_class("numeric")
        self.time_label.add_css_class("caption")
        self.player_box.append(self.play_button)
        self.player_box.append(self.seek_scale)
        self.player_box.append(self.time_label)
        box.append(self.player_box)

        # --- outils --------------------------------------------------------
        tools = Adw.PreferencesGroup(title="Mise en forme")
        self.tidy_row = Adw.ActionRow(title="Mise en forme complète")
        self.tidy_row.set_subtitle_lines(2)
        self.tidy_button = self._tool_row(
            self.tidy_row, "Mettre en forme", "win.tidy",
            "Tout le dossier…", "win.tidy-folder",
        )
        tools.add(self.tidy_row)
        self.tidy_button.set_tooltip_text(
            "Artiste et titre complétés d'après le nom du fichier, majuscules, "
            "« Feat. Invité », puis fichier renommé « Artiste - Titre Feat. Invité »")
        box.append(tools)

        # --- tags ----------------------------------------------------------
        group = Adw.PreferencesGroup(title="Tags")
        self.rows: dict[str, Adw.EntryRow] = {}
        self.multi_labels: dict[str, Gtk.Label] = {}
        for key in tags.FIELDS:
            row = Adw.EntryRow(title="Année" if key == "date" else tags.FIELD_LABELS[key])
            if key == "date":
                row.set_input_purpose(Gtk.InputPurpose.DIGITS)
            label = Gtk.Label(label=MULTIPLE, valign=Gtk.Align.CENTER)
            label.add_css_class("dim-label")
            label.add_css_class("caption")
            row.add_suffix(label)
            row.connect("changed", self._on_entry_changed, key)
            group.add(row)
            self.rows[key] = row
            self.multi_labels[key] = label
        for key in ("date", "album"):
            find = Gtk.Button(icon_name="system-search-symbolic", valign=Gtk.Align.CENTER,
                              action_name="win.release-online",
                              tooltip_text="Chercher l'année et l'album en ligne")
            find.add_css_class("flat")
            self.rows[key].add_suffix(find)
        self._setup_genre_completion()
        self.rows["genre"].set_tooltip_text("Plusieurs genres : séparez-les par « ; »")
        self.rows["artist"].set_tooltip_text("Plusieurs artistes : séparez-les par « ; »")
        box.append(group)

        # --- paroles -------------------------------------------------------
        lyrics_group = Adw.PreferencesGroup(title="Paroles")
        lyrics_btn = Gtk.Button(label="Chercher en ligne", action_name="win.lyrics-online",
                                tooltip_text="Chercher les paroles de ce morceau sur LRCLIB",
                                valign=Gtk.Align.CENTER)
        lyrics_btn.add_css_class("flat")
        lyrics_group.set_header_suffix(lyrics_btn)
        self.lyrics_view = Gtk.TextView(
            wrap_mode=Gtk.WrapMode.WORD_CHAR, top_margin=12, bottom_margin=12,
            left_margin=12, right_margin=12, accepts_tab=False,
        )
        self.lyrics_view.add_css_class("lyrics")
        self.lyrics_view.get_buffer().connect("changed", self._on_lyrics_changed)
        scrolled = Gtk.ScrolledWindow(
            child=self.lyrics_view, hscrollbar_policy=Gtk.PolicyType.NEVER,
            min_content_height=40, max_content_height=420,
            propagate_natural_height=True,
        )
        overlay = Gtk.Overlay(child=scrolled)
        self.lyrics_hint = Gtk.Label(
            label=MULTIPLE + " — ce que vous saisirez remplacera tout",
            can_target=False, halign=Gtk.Align.START, valign=Gtk.Align.START,
            margin_top=12, margin_start=14,
        )
        self.lyrics_hint.add_css_class("dim-label")
        overlay.add_overlay(self.lyrics_hint)
        frame = Gtk.Frame(child=overlay)
        frame.add_css_class("lyrics-frame")
        lyrics_group.add(frame)
        box.append(lyrics_group)

        # --- nettoyage -----------------------------------------------------
        self.clean_group = Adw.PreferencesGroup(title="Nettoyage")
        self.clean_row = Adw.ActionRow(title="Supprimé à l'enregistrement")
        self.clean_row.set_subtitle_lines(4)
        self.clean_row.add_prefix(Gtk.Image(icon_name="disquaire-clean-symbolic"))
        self.clean_group.add(self.clean_row)
        box.append(self.clean_group)

        # --- fichier -------------------------------------------------------
        self.file_group = Adw.PreferencesGroup(title="Fichier")
        self.name_row = Adw.EntryRow(title="Nom du fichier", show_apply_button=True)
        self.name_row.connect("apply", self._on_rename)
        self.file_group.add(self.name_row)
        self.format_row = Adw.ActionRow(title="Format")
        self.format_row.add_css_class("property")
        self.file_group.add(self.format_row)
        self.folder_row = Adw.ActionRow(title="Dossier", subtitle_selectable=True)
        self.folder_row.add_css_class("property")
        self.file_group.add(self.folder_row)
        box.append(self.file_group)

        clamp = Adw.Clamp(child=box, maximum_size=560, tightening_threshold=420)
        return Gtk.ScrolledWindow(child=clamp, hscrollbar_policy=Gtk.PolicyType.NEVER)

    # --- genres -----------------------------------------------------------
    def _setup_genre_completion(self):
        row = self.rows["genre"]
        self._genre_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self._genre_list.add_css_class("navigation-sidebar")
        self._genre_list.connect("row-activated", self._on_genre_chosen)
        scroller = Gtk.ScrolledWindow(child=self._genre_list, propagate_natural_height=True,
                                      max_content_height=320, min_content_width=240,
                                      hscrollbar_policy=Gtk.PolicyType.NEVER)
        self._genre_pop = Gtk.Popover(child=scroller, autohide=False, has_arrow=False,
                                      position=Gtk.PositionType.BOTTOM,
                                      halign=Gtk.Align.START)
        self._genre_pop.add_css_class("menu")
        self._genre_pop.set_parent(row)
        all_btn = Gtk.MenuButton(icon_name="pan-down-symbolic", valign=Gtk.Align.CENTER,
                                 tooltip_text="Liste des genres")
        all_btn.add_css_class("flat")
        self._genre_menu = Gtk.Popover()
        all_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        all_list.add_css_class("navigation-sidebar")
        all_list.connect("row-activated", self._on_genre_menu)
        self._genre_all = all_list
        self._genre_menu.set_child(Gtk.ScrolledWindow(
            child=all_list, propagate_natural_height=True, max_content_height=420,
            min_content_width=240, hscrollbar_policy=Gtk.PolicyType.NEVER))
        self._genre_menu.connect("show", lambda *_: self._fill_genres(all_list, ""))
        all_btn.set_popover(self._genre_menu)
        row.add_suffix(all_btn)
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_genre_key)
        row.add_controller(keys)
        focus = Gtk.EventControllerFocus()
        focus.connect("leave", lambda *_: GLib.timeout_add(150, self._hide_genre_pop))
        row.add_controller(focus)

    def _hide_genre_pop(self):
        self._genre_pop.popdown()
        return GLib.SOURCE_REMOVE

    def _fill_genres(self, listbox, text):
        from . import genres
        child = listbox.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            listbox.remove(child)
            child = nxt
        items = genres.suggest(text, limit=200 if not text else 10)
        for g in items:
            label = Gtk.Label(label=g, xalign=0, margin_start=6, margin_end=6)
            listbox.append(label)
        return items

    def _update_genre_pop(self):
        row = self.rows["genre"]
        text = row.get_text()
        part = text.split(";")[-1].strip()
        if not part or not row.has_focus() and not row.get_focus_child():
            self._genre_pop.popdown()
            return
        items = self._fill_genres(self._genre_list, text)
        if not items or (len(items) == 1 and items[0] == part):
            self._genre_pop.popdown()
        else:
            self._genre_pop.popup()

    def _apply_genre(self, genre):
        row = self.rows["genre"]
        parts = [p.strip() for p in row.get_text().split(";")]
        parts[-1] = genre
        row.set_text("; ".join(p for p in parts if p))
        row.set_position(-1)
        self._genre_pop.popdown()

    def _on_genre_chosen(self, _box, listrow):
        self._apply_genre(listrow.get_child().get_label())
        self.rows["genre"].grab_focus_without_selecting()

    def _on_genre_menu(self, _box, listrow):
        self._genre_menu.popdown()
        self._apply_genre(listrow.get_child().get_label())

    def _on_genre_key(self, _ctrl, keyval, _code, _state):
        from gi.repository import Gdk
        if not self._genre_pop.get_visible():
            return False
        if keyval in (Gdk.KEY_Down, Gdk.KEY_Tab):
            first = self._genre_list.get_row_at_index(0)
            if first is not None:
                first.grab_focus()
            return True
        if keyval == Gdk.KEY_Escape:
            self._genre_pop.popdown()
            return True
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            first = self._genre_list.get_row_at_index(0)
            if first is not None:
                self._on_genre_chosen(self._genre_list, first)
                return True
        return False

    @staticmethod
    def _tool_row(row, label, action, menu_label, menu_action):
        menu = Gio.Menu()
        menu.append(menu_label, menu_action)
        button = Adw.SplitButton(label=label, action_name=action, menu_model=menu,
                                 valign=Gtk.Align.CENTER)
        row.add_suffix(button)
        return button

    def set_reserve_suggestion(self, text) -> None:
        self.reserve_suggest.set_visible(bool(text))
        if text:
            self.reserve_suggest.set_label(text)

    def set_folder_image(self, available: bool) -> None:
        self.folder_cover_button.set_visible(available)

    # ------------------------------------------------------------------
    # Remplissage
    # ------------------------------------------------------------------
    def set_targets(self, targets: list[Track]) -> None:
        same = targets == self.targets
        self.targets = list(targets)
        single = self.single
        self.player.load(single.path if single else None)
        if not same:
            self.refresh()
        else:
            self.refresh_status()

    @property
    def single(self):
        return self.targets[0] if len(self.targets) == 1 else None

    def _common(self, key):
        values = [t.values.get(key) for t in self.targets]
        first = values[0]
        return first, all(v == first for v in values[1:])

    def refresh(self) -> None:
        """Relit toutes les valeurs depuis les morceaux ciblés."""
        if not self.targets:
            self.stack.set_visible_child_name("empty")
            self.title.set_title("")
            self.title.set_subtitle("")
            return
        self.stack.set_visible_child_name("form")
        self._updating = True
        try:
            for key in tags.FIELDS:
                value, same = self._common(key)
                row = self.rows[key]
                text = value if same else ""
                if row.get_text() != text:
                    row.set_text(text)
                self.multi_labels[key].set_visible(not same)
            lyrics, same = self._common("lyrics")
            buf = self.lyrics_view.get_buffer()
            text = lyrics if same else ""
            if buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False) != text:
                buf.set_text(text)
            self.lyrics_hint.set_visible(not same)
            single = self.single
            self.name_row.set_text(single.name if single else "")
        finally:
            self._updating = False
        self._refresh_cover()
        self.refresh_status()

    def refresh_status(self) -> None:
        """Met à jour ce qui ne dépend pas des champs saisis."""
        if not self.targets:
            return
        single = self.single
        if single:
            self.title.set_title(single.values.title.strip() or single.stem)
            self.title.set_subtitle(single.values.artist.strip())
            self.format_row.set_subtitle(
                single.error or tags.describe(single.info) if single.loaded else "Lecture…"
            )
            self.folder_row.set_subtitle(single.folder)
        else:
            n = len(self.targets)
            flacs = sum(1 for t in self.targets if t.is_flac)
            self.title.set_title(f"{n} morceaux")
            self.title.set_subtitle("Modification en lot")
            detail = []
            if n - flacs:
                detail.append(f"{n - flacs} MP3")
            if flacs:
                detail.append(f"{flacs} FLAC")
            self.format_row.set_subtitle(", ".join(detail))
        if single:
            artist, title = textfmt.tidy(single.values.artist, single.values.title, single.stem)
            new = textfmt.filename_from_tags(artist, title, os.path.splitext(single.path)[1])
            if new is None:
                self.tidy_row.set_subtitle("Artiste ou titre introuvable")
                already_formatted = False
            elif new == single.name and (artist, title) == (single.values.artist,
                                                            single.values.title) \
                    and textfmt.title_case(single.values.album) == single.values.album \
                    and not single.dirty:
                self.tidy_row.set_subtitle("Déjà en forme")
                already_formatted = True
            else:
                self.tidy_row.set_subtitle(GLib.markup_escape_text("→ " + new))
                already_formatted = False
            self.tidy_button.set_sensitive(
                single.loaded and not single.error and not already_formatted)
        else:
            self.tidy_row.set_subtitle(f"{len(self.targets)} morceaux sélectionnés")
            self.tidy_button.set_sensitive(bool(self.targets))
        self.player_box.set_visible(bool(single) and self.player.available)
        self.name_row.set_visible(bool(single))
        self.folder_row.set_visible(bool(single))

        extras: list[str] = []
        files_with_extras = 0
        for t in self.targets:
            if t.extras:
                files_with_extras += 1
                for e in t.extras:
                    if e not in extras:
                        extras.append(e)
        self.clean_group.set_visible(bool(extras))
        if extras:
            self.clean_row.set_subtitle(", ".join(extras))
            if single:
                self.clean_group.set_description(None)
            else:
                self.clean_group.set_description(
                    f"{files_with_extras} fichier(s) sur {len(self.targets)} concernés"
                )

    def _refresh_cover(self) -> None:
        value, same = self._common("cover")
        if same and value is not None:
            texture = texture_from_bytes(value.data)
            self.cover_picture.set_paintable(texture)
            self.cover_stack.set_visible_child_name("picture" if texture else "placeholder")
            if texture is None:
                self.cover_title.set_label("Image illisible")
                self.cover_hint.set_label("Choisissez une autre image")
        else:
            self.cover_picture.set_paintable(None)
            self.cover_title.set_label("Pochettes différentes" if not same
                                       else "Pas de pochette")
            self.cover_hint.set_label(
                "Glissez une image ici" if same else
                "Une nouvelle image remplacera toutes les pochettes"
            )
            self.cover_stack.set_visible_child_name("placeholder")
        self.remove_cover_button.set_sensitive(any(t.values.cover for t in self.targets))

    # ------------------------------------------------------------------
    # Saisie
    # ------------------------------------------------------------------
    def _on_entry_changed(self, row, key):
        if self._updating:
            return
        self.multi_labels[key].set_visible(False)
        text = row.get_text()
        if key == "genre":
            self._update_genre_pop()
        if key == "date":
            # L'année seule : quatre chiffres, rien d'autre.
            digits = "".join(c for c in text if c.isdigit())[:4]
            if digits != text:
                self._updating = True
                row.set_text(digits)
                row.set_position(-1)
                self._updating = False
                text = digits
        for t in self.targets:
            t.set_value(key, text)
        self.refresh_status()

    def _on_lyrics_changed(self, buf):
        if self._updating:
            return
        self.lyrics_hint.set_visible(False)
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
        for t in self.targets:
            t.set_value("lyrics", text)

    def set_cover(self, cover) -> None:
        for t in self.targets:
            t.set_value("cover", cover)
        self._refresh_cover()

    def _on_remove_cover(self, *_):
        self.set_cover(None)

    def _on_drop(self, _target, value, _x, _y):
        if not self.targets:
            return False
        self.emit("cover-dropped", value)
        return True

    def _on_rename(self, row):
        if self.single:
            self.emit("rename", row.get_text())

    def focus_name(self) -> None:
        if self.single:
            stem_len = len(self.single.stem)
            self.name_row.grab_focus()

            def select():
                # Sélectionne le nom sans l'extension, comme Fichiers.
                self.name_row.select_region(0, stem_len)
                return GLib.SOURCE_REMOVE

            GLib.idle_add(select)

    # ------------------------------------------------------------------
    # Lecture
    # ------------------------------------------------------------------
    def _on_play(self, *_):
        self.player.toggle()

    def _on_player_state(self, player):
        playing = player.playing
        self.play_button.set_icon_name(
            "media-playback-pause-symbolic" if playing else "media-playback-start-symbolic"
        )
        self.play_button.set_tooltip_text("Pause" if playing else "Lire")

    def _on_player_position(self, _player, pos, dur):
        if dur <= 0 and self.single:
            dur = self.single.info.length
        adj = self.seek_scale.get_adjustment()
        adj.set_upper(max(dur, 1))
        if not self._seeking:
            self.seek_scale.set_value(pos)
        self.time_label.set_label(f"{tags.format_duration(pos)} / {tags.format_duration(dur)}")

    def _on_seek(self, _scale, _scroll, value):
        if not self.player.playing and self.player.path:
            self.player.play()
            GLib.timeout_add(150, lambda: (self.player.seek(value), False)[1])
        else:
            self.player.seek(value)
        return False
