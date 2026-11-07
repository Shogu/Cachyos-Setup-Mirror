# SPDX-License-Identifier: GPL-3.0-or-later
"""Fenêtre principale : assemble les trois volets et porte les actions."""

from __future__ import annotations

import os
import shutil
import threading

from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk

from . import config, convert, covers, library, reserve, tags, textfmt
from .lyricsqueue import LyricsQueue
from .duplicates import list_audio
from .dialogs import (CoverSearchDialog, DuplicatesDialog, GenresDialog, LyricsDialog,
                      ReleaseDialog, ReserveDialog, rename_preview)
from .editor import Editor
from .folder_tree import FolderTree
from .model import TagLoader, Track, list_audio_files, make_thumbnail_png, natural_key
from .player import Player
from .track_list import TrackList


def _plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


class Window(Adw.ApplicationWindow):
    __gtype_name__ = "DisquaireWindow"

    def __init__(self, app, path: str | None = None):
        super().__init__(application=app, title="Disquaire")
        self.set_icon_name("io.gitlab.shogu.Disquaire")
        self.cfg = config.load()
        self.set_default_size(self.cfg["width"], self.cfg["height"])
        self.set_size_request(700, 480)
        if self.cfg["maximized"]:
            self.maximize()

        self.folder: str | None = None
        self.monitor: Gio.FileMonitor | None = None
        self._reconcile_id = 0
        self._update_id = 0
        self._busy = False
        self._converter: convert.Converter | None = None
        self._cancel_job = threading.Event()
        self._closing = False
        self._track_handlers: dict[Track, list[int]] = {}
        self._undo: list[dict] = []
        self._bulk_folder_rename_active = False
        self._select_after_load: str | None = None
        self._last_library_track: str | None = None
        self.folder_cover: tags.Cover | None = None

        self.player = Player()
        self.player.connect("error", lambda _p, msg: self.toast(msg))
        self.loader = TagLoader(self._on_tags_loaded,
                                lambda: self.cfg.get("auto_clean", True))
        self.lyrics_queue = LyricsQueue()
        self.lyrics_queue.connect("changed", lambda *_: self._update_lyrics_bar())
        self.lyrics_queue.connect("saved", lambda _q, p, text: self._on_queue_lyrics(p, text, True))
        self.lyrics_queue.connect("found-unsaved",
                                  lambda _q, p, text: self._on_queue_lyrics(p, text, False))
        self.lyrics_queue.connect("error", lambda _q, msg: self.toast(msg))
        self.lyrics_queue.connect("finished", self._on_lyrics_queue_finished)

        # --- volets ---------------------------------------------------------
        self.tree = FolderTree()
        self.tree.connect("folder-selected", lambda _t, path: self.request_folder(path))
        self.tree.connect("change-root", lambda *_: self._pick_root())
        self.tree.connect("rename-folder", lambda _t, path: self.rename_folder(path))
        self.tree.connect("rename-all-folders", lambda *_: self.rename_all_folders())
        self.tree.connect("new-folder", lambda _t, path: self.new_folder(path))
        self.tree.connect("trash-folder", lambda _t, path: self.trash_folder(path))
        self.tree.connect("open-path", lambda _t, path: self.open_path(path))
        self.tree.connect("drop-paths", lambda _t, dest, paths: self.move_paths(paths, dest))

        self.list = TrackList()
        self.list.connect("current-changed", lambda *_: self._targets_changed())
        self.list.connect("search-changed",
                          lambda _l, text, scope: self._on_search_changed(text, scope))
        self._lib_gen = 0
        self._lib_timer = 0
        self._online_folder = None
        self.list.progress_cancel.connect("clicked", lambda *_: self._cancel())

        self.editor = Editor(self.player)
        self.editor.connect("rename", lambda _e, name: self._rename(name))
        self.editor.connect("pick-cover", lambda *_: self._pick_cover())
        self.editor.connect("cover-dropped", lambda _e, value: self._on_cover_dropped(value))

        # Trois volets redimensionnables à la souris (poignées entre chaque volet).
        self.tree.set_size_request(180, -1)
        self.list.set_size_request(300, -1)
        self.editor.set_size_request(360, -1)
        self.paned = Gtk.Paned(
            start_child=self.list, end_child=self.editor,
            resize_start_child=False, shrink_start_child=False,
            resize_end_child=True, shrink_end_child=False,
            position=self.cfg.get("list_width", 400),
        )
        self.split = Gtk.Paned(
            start_child=self.tree, end_child=self.paned,
            resize_start_child=False, shrink_start_child=False,
            resize_end_child=True, shrink_end_child=False,
            position=self.cfg.get("sidebar_width", 260),
        )
        self.tree.set_visible(self.cfg["sidebar"])
        self.tree.bind_property(
            "visible", self.list.sidebar_button, "active",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
        )
        self.toasts = Adw.ToastOverlay(child=self.split)
        self.set_content(self.toasts)

        # Fenêtre étroite : le volet des dossiers se replie (bouton pour le rouvrir).
        bp = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 1000sp"))
        bp.add_setter(self.tree, "visible", False)
        self.add_breakpoint(bp)

        drop = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        drop.connect("drop", lambda _t, value, _x, _y: self._on_window_drop(value))
        self.toasts.add_controller(drop)

        self._setup_actions()
        self.list.search_bar.set_key_capture_widget(self)
        self.connect("close-request", self._on_close_request)

        # --- démarrage ------------------------------------------------------
        self._update_lyrics_bar()
        self.lyrics_queue.start()   # reprend la file là où elle s'était arrêtée

        self.tree.set_root(self.cfg["root"])
        if path and self.open_path(path):
            return
        start = self.cfg["folder"] or self.cfg["root"]
        if not self.tree.select_path(start, silent=True):
            start = self.cfg["root"]
            self.tree.select_path(start, silent=True)
        self.open_folder(start)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _setup_actions(self) -> None:
        self._actions = {}
        for name, callback in (
            ("save", lambda *_: self.save(self.targets())),
            ("save-all", lambda *_: self.save(self.dirty_tracks())),
            ("revert", lambda *_: self._revert()),
            ("refresh", lambda *_: self.refresh()),
            ("search", lambda *_: self.list.search_bar.set_search_mode(True)),
            ("select-all", lambda *_: self._check_all(True)),
            ("select-none", lambda *_: self._check_all(False)),
            ("toggle-check-all", lambda *_: self._check_all(
                not self._all_visible_checked())),
            ("rename", lambda *_: self.editor.focus_name()),
            ("move", lambda *_: self._pick_move_destination()),
            ("trash", lambda *_: self._trash()),
            ("convert", lambda *_: self._confirm_convert()),
            ("open-default", lambda *_: self._launch(False)),
            ("open-with", lambda *_: self._launch(True)),
            ("show-folder", lambda *_: self._show_in_folder()),
            ("play", lambda *_: self.player.toggle() if self.editor.single else None),
            ("toggle-sidebar", lambda *_: self.tree.set_visible(not self.tree.get_visible())),
            ("tidy", lambda *_: self.tidy(self.targets(), False)),
            ("tidy-folder", lambda *_: self.tidy(self.tracks(), True)),
            ("tidy-mp3-folder", lambda *_: self.tidy_mp3_folder()),
            ("folder-cover", lambda *_: self.apply_folder_cover(self.targets())),
            ("folder-cover-all", lambda *_: self.apply_folder_cover(self.tracks())),
            ("cover-online", lambda *_: self.search_cover_online()),
            ("duplicates", lambda *_: self.find_duplicates()),
            ("undo", lambda *_: self.undo()),
            ("reserve", lambda *_: self.open_reserve()),
            ("lyrics-online", lambda *_: self.search_lyrics()),
            ("lyrics-queue-folder", lambda *_: self.queue_lyrics(False)),
            ("lyrics-queue-all", lambda *_: self.queue_lyrics(True)),
            ("lyrics-queue-toggle", lambda *_: self._toggle_queue()),
            ("lyrics-queue-stop", lambda *_: self.lyrics_queue.cancel()),
            ("release-online", lambda *_: self.search_release()),
            ("genres", lambda *_: self.open_genres()),
            ("preferences", lambda *_: self.open_preferences()),
            ("reserve-by-genre", lambda *_: self.reserve_by_genre(self.targets())),
            ("reserve-folder", lambda *_: self.reserve_by_genre(self.tracks())),
            ("goto-track", lambda *_: self.editor.single and self.open_path(self.editor.single.path)),
        ):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)
            self._actions[name] = action
        auto = Gio.SimpleAction.new_stateful(
            "auto-clean", None, GLib.Variant("b", self.cfg.get("auto_clean", True)))
        auto.connect("change-state", self._on_auto_clean)
        self.add_action(auto)
        self._update_actions()

    def _set_enabled(self, name: str, enabled: bool) -> None:
        self._actions[name].set_enabled(bool(enabled))

    def _update_actions(self) -> None:
        targets = self.targets()
        busy = self._busy
        single = len(targets) == 1
        loaded = [t for t in targets if t.loaded and not t.error]
        self._set_enabled("save", not busy and any(t.dirty for t in targets))
        self._set_enabled("save-all", not busy and bool(self.dirty_tracks()))
        self._set_enabled("revert", not busy and any(t.edited for t in targets))
        self._set_enabled("refresh", not busy and self.folder is not None)
        visible_count = self.list.filtered.get_n_items()
        self._set_enabled("toggle-check-all", not busy and visible_count > 0)
        mp3_tracks = [t for t in self.tracks()
                      if os.path.splitext(t.path)[1].lower() == ".mp3"]
        mp3_ready = self._ready(mp3_tracks)
        self._set_enabled("tidy-mp3-folder", not busy and not self.list.library_mode
                          and bool(mp3_ready)
                          and all(t.loaded for t in mp3_tracks))
        self.tree.rename_all_button.set_sensitive(
            not busy and bool(self.tree.root) and not self._bulk_folder_rename_active)
        for name in ("rename", "open-default", "open-with", "show-folder"):
            self._set_enabled(name, not busy and single)
        self._set_enabled("move", not busy and bool(targets))
        self._set_enabled("trash", not busy and bool(targets))
        self._set_enabled("convert", not busy and convert.ffmpeg_available()
                          and any(t.is_flac for t in loaded))
        self._set_enabled("play", single)
        ready = [t for t in targets if t.loaded and not t.error]
        all_ready = [t for t in self.tracks() if t.loaded and not t.error]
        for name in ("tidy", "cover-online"):
            self._set_enabled(name, not busy and bool(ready))
        self._set_enabled("tidy-folder", not busy and bool(all_ready))
        self._set_enabled("folder-cover", not busy and bool(ready) and self.folder_cover is not None)
        self._set_enabled("folder-cover-all",
                          not busy and bool(all_ready) and self.folder_cover is not None)
        self._set_enabled("duplicates", not busy)
        self._set_enabled("undo", not busy and bool(self._undo))
        self._set_enabled("reserve", not busy and bool(ready))
        self._set_enabled("lyrics-online", not busy and single and bool(ready))
        self._set_enabled("lyrics-queue-folder", not busy and bool(
            self.tree.selected_path() or self.folder) and not self.list.library_mode)
        self._set_enabled("release-online", not busy and single and bool(ready))
        self.lyrics_queue.protected = {t.path for t in self.tracks() if t.edited}
        self._set_enabled("reserve-by-genre", not busy and bool(self._reserve_matches(ready)))
        self._set_enabled("reserve-folder", not busy and bool(all_ready))
        self._set_enabled("goto-track", not busy and single and self.list.library_mode)

    def _schedule_update(self) -> None:
        if not self._update_id:
            self._update_id = GLib.idle_add(self._do_update)

    def _do_update(self) -> bool:
        self._update_id = 0
        self._update_actions()
        dirty = self.dirty_tracks()
        n = len(dirty)
        if n:
            edited = sum(1 for t in dirty if t.edited)
            if edited:
                text = _plural(n, "fichier modifié", "fichiers modifiés")
            else:
                text = _plural(n, "fichier à nettoyer", "fichiers à nettoyer")
            self.list.banner.set_title(text)
        self.list.banner.set_revealed(n > 0 and not self._busy)
        fc = self.folder_cover
        self.list.cover_banner.set_revealed(
            fc is not None and not self._busy and any(
                t.loaded and not t.error and t.values.cover != fc for t in self.tracks()))
        self.editor.set_folder_image(fc is not None)
        matches = self._reserve_matches(self._ready(self.targets()))
        if not matches:
            self.editor.set_reserve_suggestion(None)
        elif len(matches) == 1:
            self.editor.set_reserve_suggestion(
                f"Pochette « {matches[0][1]} » de la réserve")
        else:
            names = {m[1] for m in matches}
            self.editor.set_reserve_suggestion(
                f"Pochette « {names.pop()} » pour {len(matches)} morceaux" if len(names) == 1
                else f"Pochettes de la réserve selon le genre ({len(matches)})")
        checked = self.checked_tracks()
        self.list.action_bar.set_revealed(bool(checked) or bool(self.tracks()))
        self.list.selection_label.set_label(str(len(checked)))
        self.list.selection_label.set_tooltip_text(
            _plural(len(checked), "morceau sélectionné", "morceaux sélectionnés"))
        self.list.selection_label.set_visible(bool(checked))
        all_checked = self._all_visible_checked()
        self.list.select_button.set_tooltip_text(
            "Tout désélectionner" if all_checked else "Tout sélectionner")
        if all_checked:
            self.list.select_button.add_css_class("accent")
        else:
            self.list.select_button.remove_css_class("accent")
        for button in (self.list.trash_button, self.list.move_button,
                       self.list.convert_button):
            button.set_visible(bool(checked))
        self.editor.refresh_status()
        return GLib.SOURCE_REMOVE

    # ------------------------------------------------------------------
    # Morceaux, sélection
    # ------------------------------------------------------------------
    def tracks(self) -> list[Track]:
        return self.list.tracks()

    def checked_tracks(self) -> list[Track]:
        return [t for t in self.tracks() if t.checked]

    def dirty_tracks(self) -> list[Track]:
        return [t for t in self.tracks() if t.dirty]

    def targets(self) -> list[Track]:
        checked = self.checked_tracks()
        if checked:
            return checked
        current = self.list.current()
        return [current] if current is not None else []

    def _targets_changed(self) -> None:
        self.editor.set_targets(self.targets())
        self._schedule_update()

    def _watch(self, track: Track) -> None:
        if track in self._track_handlers:
            return
        self._track_handlers[track] = [
            track.connect("notify::checked", lambda *_: self._targets_changed()),
            track.connect("notify::dirty", lambda *_: self._schedule_update()),
            track.connect("values-changed", lambda *_: self._schedule_update()),
            track.connect("notify::display-title", lambda *_: self.list.refilter()),
        ]

    def _unwatch(self, track: Track) -> None:
        for hid in self._track_handlers.pop(track, []):
            track.disconnect(hid)

    def _check_all(self, value: bool) -> None:
        for i in range(self.list.filtered.get_n_items()):
            self.list.filtered.get_item(i).checked = value
        if not value:
            for t in self.tracks():
                t.checked = False

    def _all_visible_checked(self) -> bool:
        count = self.list.filtered.get_n_items()
        return count > 0 and all(
            self.list.filtered.get_item(i).checked for i in range(count))

    def tidy_mp3_folder(self) -> None:
        if self.list.library_mode or not self.folder:
            return
        tracks = [t for t in self.tracks()
                  if os.path.splitext(t.path)[1].lower() == ".mp3"]
        self.tidy(tracks, True)

    def _add_track(self, path: str) -> Track | None:
        if self.list.find(path) is not None:
            return None
        track = Track(path)
        self._watch(track)
        self.list.insert_sorted(track)
        return track

    def _drop_track(self, track: Track) -> None:
        if self.player.path == track.path:
            self.player.load(None)
        self._unwatch(track)
        self.list.remove(track)

    # ------------------------------------------------------------------
    # Dossiers
    # ------------------------------------------------------------------
    def request_folder(self, path: str) -> None:
        if path == self.folder and not self.list.library_mode:
            return
        dirty = self.dirty_tracks()
        if not dirty:
            self.open_folder(path)
            return

        def restore_selection():
            self._select_after_load = None
            if self.folder and not self.tree.select_path(self.folder, silent=True):
                self.tree.set_root(self.cfg["root"])
                self.tree.select_path(self.folder, silent=True)

        self.save_before(dirty, lambda: self.open_folder(path), restore_selection)

    def open_folder(self, path: str) -> None:
        if self.list.library_mode:
            self._lib_gen += 1
            self.list.set_library_mode(False)
            self.list.set_scope("folder")
        self.player.load(None)
        self.loader.cancel()
        for t in list(self._track_handlers):
            self._unwatch(t)
        self.folder = path
        self.cfg["folder"] = path
        tracks = [Track(p) for p in list_audio_files(path)]
        for t in tracks:
            self._watch(t)
        self.list.set_tracks(tracks)
        self.list.show_list_state()
        self._update_title()
        self._watch_folder(path)
        self._load_folder_cover()
        self.loader.start(tracks)
        target = self._select_after_load
        self._select_after_load = None
        if target:
            self.list.select(self.list.find(target))
        self._targets_changed()

    def _update_title(self) -> None:
        if self.list.library_mode:
            n = self.list.store.get_n_items()
            self.list.title.set_title("Toute la discothèque")
            self.list.title.set_subtitle(_plural(n, "morceau trouvé", "morceaux trouvés"))
            self.set_title("Recherche — Disquaire")
            return
        if not self.folder:
            return
        name = os.path.basename(self.folder.rstrip(os.sep)) or self.folder
        self.list.title.set_title(name)
        n = self.list.store.get_n_items()
        self.list.title.set_subtitle(_plural(n, "morceau", "morceaux"))
        self.set_title(f"{name} — Disquaire")

    def _watch_folder(self, path: str) -> None:
        if self.monitor is not None:
            self.monitor.cancel()
            self.monitor = None
        try:
            self.monitor = Gio.File.new_for_path(path).monitor_directory(
                Gio.FileMonitorFlags.WATCH_MOVES, None)
            self.monitor.connect("changed", self._on_folder_changed)
        except GLib.Error:
            self.monitor = None

    def _on_folder_changed(self, _monitor, file, other, event):
        if event in (Gio.FileMonitorEvent.CHANGED, Gio.FileMonitorEvent.CHANGES_DONE_HINT,
                     Gio.FileMonitorEvent.ATTRIBUTE_CHANGED):
            return
        names = [f.get_basename() for f in (file, other) if f is not None]
        if all(n.startswith(".") for n in names):
            return
        if self._reconcile_id:
            GLib.source_remove(self._reconcile_id)
        self._reconcile_id = GLib.timeout_add(400, self._reconcile)

    def _reconcile(self) -> bool:
        """Aligne la liste sur le contenu réel du dossier."""
        self._reconcile_id = 0
        if not self.folder or self._busy or self.list.library_mode:
            return GLib.SOURCE_REMOVE
        on_disk = set(list_audio_files(self.folder))
        for t in self.tracks():
            if t.path not in on_disk:
                self._drop_track(t)
        known = {t.path for t in self.tracks()}
        new = [t for p in sorted(on_disk - known) if (t := self._add_track(p))]
        if new:
            self.loader.start(new, invalidate=False)
        self._update_title()
        self._targets_changed()
        return GLib.SOURCE_REMOVE

    def refresh(self) -> None:
        """Relit le dossier ; les morceaux sans modification sont relus."""
        if self.list.library_mode:
            self._search_library(self.list.search_entry.get_text().strip())
            return
        if not self.folder:
            return
        if not os.path.isdir(self.folder):
            self.toast("Ce dossier n'existe plus.")
            return
        self._reconcile()
        stale = [t for t in self.tracks() if not t.edited]
        for t in stale:
            t.loaded = False
        self.loader.start(stale, invalidate=False)
        self.tree.reload()
        self.toast("Liste rafraîchie")

    def _on_tags_loaded(self, track, report, thumb, error, resized=None, big=None) -> None:
        if self.list.find(track.path) is not track:
            return
        if error:
            track.apply_error(error)
        else:
            track.apply_report(report, thumb, resized, big)
        if track in self.editor.targets:
            self.editor.refresh()
        self._schedule_update()

    def _pick_root(self) -> None:
        dialog = Gtk.FileDialog(title="Dossier de base",
                                initial_folder=Gio.File.new_for_path(self.tree.root))

        def done(dlg, result):
            try:
                folder = dlg.select_folder_finish(result)
            except GLib.Error:
                return
            path = folder.get_path()
            if not path:
                return

            def apply():
                self.cfg["root"] = path
                self.tree.set_root(path)
                self.tree.select_path(path, silent=True)
                self.open_folder(path)

            dirty = self.dirty_tracks()
            if dirty:
                self.save_before(dirty, apply)
            else:
                apply()

        dialog.select_folder(self, None, done)

    # ------------------------------------------------------------------
    # Enregistrement
    # ------------------------------------------------------------------
    def save_before(self, tracks, on_continue, on_error=None) -> None:
        """L'action déclenchée vaut acceptation : on enregistre puis on continue.

        Plus de dialogue « Enregistrer les modifications ? » : changer de
        dossier, chercher, déplacer ou fermer enregistre d'abord les
        modifications en attente, puis exécute l'action demandée. Un toast
        permet d'annuler l'enregistrement s'il était involontaire.
        """
        dirty = [t for t in tracks if t.dirty]
        if not dirty:
            on_continue()
            return
        self.save(dirty, then=on_continue, on_error=on_error, notify=True)

    def save(self, tracks, then=None, undo_sink=None, notify=False, on_error=None) -> None:
        tracks = [t for t in tracks if t.dirty]
        if not tracks:
            if then:
                then()
            return
        jobs = [(t, t.path, t.values.copy(), t.values.cover != t.saved.cover) for t in tracks]
        undo = {"kind": "tags", "items": [(t, t.path, t.saved.copy()) for t in tracks]}
        self._set_busy(True)
        self._cancel_job.clear()
        show = len(jobs) > 2

        def work():
            errors = []
            for i, (track, path, values, cover_changed) in enumerate(jobs):
                if self._cancel_job.is_set():
                    break
                if show:
                    GLib.idle_add(self.list.show_progress,
                                  f"Enregistrement {i + 1}/{len(jobs)} — {os.path.basename(path)}",
                                  i / len(jobs), True)
                try:
                    tags.write(path, values)
                    thumb = (make_thumbnail_png(values.cover.data)
                             if cover_changed and values.cover else None)
                    GLib.idle_add(track.mark_saved, values, thumb, cover_changed)
                except tags.TagError as exc:
                    errors.append(f"{os.path.basename(path)} : {exc}")
            GLib.idle_add(finish, errors)

        def finish(errors):
            self.list.hide_progress()
            self._set_busy(False)
            self.editor.refresh_status()
            if errors:
                self.error_dialog("Certains fichiers n'ont pas pu être enregistrés",
                                  "\n".join(errors))
                if on_error:
                    on_error()
            else:
                if undo_sink is not None:
                    undo_sink.append(undo)
                elif notify:
                    self._push_undo(undo, _plural(len(jobs), "fichier enregistré",
                                                  "fichiers enregistrés"))
                else:
                    self._record_undo(undo)
                if then:
                    then()
            return GLib.SOURCE_REMOVE

        threading.Thread(target=work, daemon=True).start()

    def _revert(self) -> None:
        for t in self.targets():
            t.revert()
        self.editor.refresh()
        self._schedule_update()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.editor.set_sensitive(not busy)
        self._schedule_update()

    def _cancel(self) -> None:
        self._cancel_job.set()
        if self._converter is not None:
            self._converter.cancel()

    # ------------------------------------------------------------------
    # Pochette
    # ------------------------------------------------------------------
    def _pick_cover(self) -> None:
        if not self.editor.targets:
            return
        images = Gtk.FileFilter(name="Images")
        images.add_mime_type("image/*")
        filters = Gio.ListStore(item_type=Gtk.FileFilter)
        filters.append(images)
        dialog = Gtk.FileDialog(title="Choisir une pochette", filters=filters,
                                default_filter=images)
        single = self.editor.single
        if single:
            dialog.set_initial_folder(Gio.File.new_for_path(single.folder))
        elif self.folder:
            dialog.set_initial_folder(Gio.File.new_for_path(self.folder))

        def done(dlg, result):
            try:
                file = dlg.open_finish(result)
            except GLib.Error:
                return
            self._load_cover_file(file)

        dialog.open(self, None, done)

    def _load_cover_file(self, file: Gio.File) -> None:
        def done(f, result):
            try:
                ok, data, _etag = f.load_contents_finish(result)
            except GLib.Error as exc:
                self.toast(f"Image illisible : {exc.message}")
                return
            self._apply_cover_bytes(bytes(data))

        file.load_contents_async(None, done)

    def _apply_cover_bytes(self, data: bytes) -> tags.Cover | None:
        """Réduit à 1024 px si besoin, puis applique aux morceaux ciblés."""
        try:
            cover = covers.prepare(data)
        except covers.CoverError as exc:
            self.toast(str(exc))
            return None
        self.editor.set_cover(cover)
        self.autosave(self.editor.targets)
        return cover

    def _on_cover_dropped(self, value) -> None:
        if isinstance(value, Gdk.Texture):
            self._apply_cover_bytes(bytes(value.save_to_png_bytes().get_data()))
            return
        files = value.get_files() if hasattr(value, "get_files") else []
        if not files:
            return
        path = files[0].get_path()
        if path and (os.path.isdir(path) or tags.is_audio(path)):
            self.open_path(path)
            return
        self._load_cover_file(files[0])

    # ------------------------------------------------------------------
    # Fichiers : renommer, déplacer, corbeille, ouvrir
    # ------------------------------------------------------------------
    def _rename(self, new_name: str) -> None:
        track = self.editor.single
        if track is None:
            return
        name = new_name.strip()
        ext = os.path.splitext(track.path)[1]
        if not name or name in (".", "..") or os.sep in name:
            self.toast("Nom de fichier invalide.")
            return
        if not name.lower().endswith(ext.lower()):
            name += ext
        dest = os.path.join(track.folder, name)
        if dest == track.path:
            return
        if os.path.exists(dest) and os.path.normcase(dest) != os.path.normcase(track.path):
            self.toast("Un fichier porte déjà ce nom.")
            return
        try:
            os.rename(track.path, dest)
        except OSError as exc:
            self.toast(f"Renommage impossible : {exc.strerror}")
            return
        was_player = self.player.path == track.path
        track.set_path(dest)
        if was_player:
            self.player.load(dest)
        self.list.resort(track)
        self.editor.refresh()
        self.toast(f"Renommé en « {name} »")

    def _pick_move_destination(self) -> None:
        targets = self.targets()
        if not targets:
            return
        dialog = Gtk.FileDialog(title=f"Déplacer {_plural(len(targets), 'morceau', 'morceaux')} vers…",
                                accept_label="Déplacer ici")
        if self.folder:
            dialog.set_initial_folder(Gio.File.new_for_path(self.folder))

        def done(dlg, result):
            try:
                folder = dlg.select_folder_finish(result)
            except GLib.Error:
                return
            dest = folder.get_path()
            if not dest:
                self.toast("Ce dossier n'est pas accessible.")
                return
            if os.path.normpath(dest) == os.path.normpath(self.folder or ""):
                self.toast("Les fichiers sont déjà dans ce dossier.")
                return
            self.move_paths([t.path for t in targets], dest)

        dialog.select_folder(self, None, done)

    # ------------------------------------------------------------------
    # Déplacements (dialogue, glisser-déposer dans l'arborescence)
    # ------------------------------------------------------------------
    def move_paths(self, paths, dest: str) -> None:
        dest = os.path.normpath(dest)
        valid, errors = [], []
        for p in (os.path.normpath(p) for p in paths):
            name = os.path.basename(p)
            if not os.path.exists(p) or os.path.dirname(p) == dest:
                continue
            if p == self.tree.root:
                errors.append(f"{name} : le dossier de base ne se déplace pas")
                continue
            if os.path.isdir(p) and (dest == p or dest.startswith(p + os.sep)):
                errors.append(f"{name} : un dossier ne peut pas aller dans lui-même")
                continue
            valid.append(p)
        if not valid:
            if errors:
                self.toast(errors[0])
            return
        dirty = [t for t in self.tracks() if t.dirty and any(
            t.path == p or t.path.startswith(p + os.sep) for p in valid)]
        if dirty:
            self.save_before(dirty, lambda: self._do_move(valid, dest, errors))
        else:
            self._do_move(valid, dest, errors)

    def _do_move(self, paths, dest: str, errors) -> None:
        items = []
        for p in paths:
            name = os.path.basename(p)
            is_dir = os.path.isdir(p)
            target = os.path.join(dest, name)
            if is_dir and os.path.exists(target):
                errors.append(f"{name} : un dossier de ce nom existe déjà à cet endroit")
                continue
            if not is_dir:
                target = convert.unique_path(target)
            try:
                shutil.move(p, target)
            except OSError as exc:
                errors.append(f"{name} : {exc.strerror or exc}")
                continue
            items.append((p, target, is_dir))
            self._after_move(p, target, is_dir)
        self._finish_moves()
        if errors:
            self.error_dialog("Certains éléments n'ont pas été déplacés", "\n".join(errors))
        if items:
            self._push_undo({"kind": "move", "items": items},
                            _plural(len(items), "élément déplacé", "éléments déplacés")
                            + f" vers « {os.path.basename(dest)} »")

    def _after_move(self, old: str, new: str, is_dir: bool) -> None:
        if is_dir:
            self._folder_moved(old, new)
        else:
            t = self.list.find(old)
            if t is not None:
                self._drop_track(t)

    def _finish_moves(self) -> None:
        self.tree.reload()
        if self.folder:
            self.tree.select_path(self.folder, silent=True)
        self._reconcile()
        self._update_title()
        self._targets_changed()

    # ------------------------------------------------------------------
    # Créer / supprimer un dossier
    # ------------------------------------------------------------------
    def new_folder(self, parent: str) -> None:
        if not parent or not os.path.isdir(parent):
            return
        dialog = Adw.AlertDialog(heading="Nouveau dossier",
                                 body=GLib.markup_escape_text(f"Dans « {os.path.basename(parent)} »"))
        entry = Gtk.Entry(text="Nouveau dossier", activates_default=True)
        dialog.set_extra_child(entry)
        dialog.add_response("cancel", "Annuler")
        dialog.add_response("create", "Créer")
        dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("create")
        dialog.set_close_response("cancel")

        def on_response(_d, response):
            if response != "create":
                return
            name = textfmt.clean_spaces(entry.get_text()).strip(" .")
            if not name or os.sep in name or name in (".", ".."):
                self.toast("Nom de dossier invalide.")
                return
            path = os.path.join(parent, name)
            try:
                os.mkdir(path)
            except FileExistsError:
                self.toast("Un dossier porte déjà ce nom.")
                return
            except OSError as exc:
                self.toast(f"Création impossible : {exc.strerror}")
                return
            self.tree.reload()
            self.tree.select_path(path)  # ouvre le nouveau dossier
            self.toast(f"Dossier « {name} » créé")

        dialog.connect("response", on_response)
        dialog.present(self)
        GLib.idle_add(lambda: (entry.grab_focus(), False)[1])

    def trash_folder(self, path: str) -> None:
        if not path or not os.path.isdir(path) or path == self.tree.root:
            return
        try:
            from .duplicates import list_audio
            n = len(list_audio(path))
        except OSError:
            n = 0
        name = os.path.basename(path)
        dialog = Adw.AlertDialog(
            heading=f"Mettre « {name} » à la corbeille ?",
            body=(_plural(n, "morceau", "morceaux") + " à l'intérieur, sous-dossiers compris. "
                  if n else "Ce dossier ne contient aucun morceau. ")
            + "Il pourra être restauré depuis la corbeille.",
        )
        dialog.add_response("cancel", "Annuler")
        dialog.add_response("trash", "Mettre à la corbeille")
        dialog.set_response_appearance("trash", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_close_response("cancel")

        def on_response(_d, response):
            if response != "trash":
                return
            try:
                Gio.File.new_for_path(path).trash(None)
            except GLib.Error as exc:
                self.error_dialog("Mise à la corbeille impossible", exc.message)
                return
            inside = self.folder and (self.folder == path or self.folder.startswith(path + os.sep))
            parent = os.path.dirname(path)
            self.tree.reload()
            if inside:
                for t in self.tracks():
                    t.revert()
                self.tree.select_path(parent, silent=True)
                self.open_folder(parent)
            elif self.folder:
                self.tree.select_path(self.folder, silent=True)
            self.toast(f"« {name} » mis à la corbeille")

        dialog.connect("response", on_response)
        dialog.present(self)

    def _goto(self, path: str) -> None:
        if not self.tree.select_path(path, silent=True):
            self.tree.set_root(path)
            self.cfg["root"] = path
            self.tree.select_path(path, silent=True)
        self.request_folder(path)

    def _trash(self) -> None:
        targets = self.targets()
        done, errors = 0, []
        for t in targets:
            try:
                Gio.File.new_for_path(t.path).trash(None)
                done += 1
                self._drop_track(t)
            except GLib.Error as exc:
                errors.append(f"{t.name} : {exc.message}")
        self._update_title()
        self._targets_changed()
        if errors:
            self.error_dialog("Mise à la corbeille impossible", "\n".join(errors))
        if done:
            self.toast(_plural(done, "morceau mis", "morceaux mis") + " à la corbeille")

    def _launch(self, ask: bool) -> None:
        track = self.editor.single
        if track is None:
            return
        self.player.pause() if self.player.playing else None
        launcher = Gtk.FileLauncher.new(Gio.File.new_for_path(track.path))
        if ask and hasattr(launcher, "set_always_ask"):
            launcher.set_always_ask(True)

        def done(l, result):
            try:
                l.launch_finish(result)
            except GLib.Error as exc:
                if exc.domain != "gtk-dialog-error-quark":
                    self.toast(f"Ouverture impossible : {exc.message}")

        launcher.launch(self, None, done)

    def _show_in_folder(self) -> None:
        track = self.editor.single
        if track is None:
            return
        launcher = Gtk.FileLauncher.new(Gio.File.new_for_path(track.path))

        def done(l, result):
            try:
                l.open_containing_folder_finish(result)
            except GLib.Error as exc:
                self.toast(f"Ouverture impossible : {exc.message}")

        launcher.open_containing_folder(self, None, done)

    # ------------------------------------------------------------------
    # Conversion FLAC → MP3
    # ------------------------------------------------------------------
    def _confirm_convert(self) -> None:
        flacs = [t for t in self.targets() if t.is_flac and t.loaded and not t.error]
        if not flacs:
            return
        n = len(flacs)
        dialog = Adw.AlertDialog(
            heading=f"Convertir {_plural(n, 'FLAC', 'FLAC')} en MP3 ?",
            body="MP3 320 kb/s, 44,1 kHz. Les tags affichés (même non enregistrés) "
                 "sont repris dans le MP3. "
                 + ("Le FLAC sera ensuite mis à la corbeille." if n == 1 else
                    "Les FLAC seront ensuite mis à la corbeille."),
        )
        dialog.add_response("cancel", "Annuler")
        dialog.add_response("convert", "Convertir")
        dialog.set_response_appearance("convert", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("convert")
        dialog.set_close_response("cancel")
        dialog.connect("response",
                       lambda _d, r: self._convert(flacs) if r == "convert" else None)
        dialog.present(self)

    def _convert(self, flacs) -> None:
        self.player.load(None)
        self._set_busy(True)
        self._cancel_job.clear()
        jobs = [(t, t.path, t.values.copy(), t.info.length) for t in flacs]
        n = len(jobs)

        def work():
            errors, converted = [], 0
            for i, (track, path, values, length) in enumerate(jobs):
                if self._cancel_job.is_set():
                    break
                name = os.path.basename(path)
                label = f"Conversion {i + 1}/{n} — {name}"
                GLib.idle_add(self.list.show_progress, label, i / n, True)
                self._converter = convert.Converter()

                def progress(frac, i=i, label=label):
                    GLib.idle_add(self.list.show_progress, label, (i + frac) / n, True)

                try:
                    mp3 = self._converter.convert(path, values, length, progress)
                except convert.ConversionError as exc:
                    if not self._cancel_job.is_set():
                        errors.append(f"{name} : {exc}")
                    continue
                trashed = True
                try:
                    Gio.File.new_for_path(path).trash(None)
                except GLib.Error as exc:
                    trashed = False
                    errors.append(f"{name} : MP3 créé, mais le FLAC n'a pas pu être "
                                  f"mis à la corbeille ({exc.message})")
                converted += 1
                GLib.idle_add(self._converted, track, mp3, trashed)
            self._converter = None
            GLib.idle_add(finish, errors, converted)

        def finish(errors, converted):
            self.list.hide_progress()
            self._set_busy(False)
            self._update_title()
            if errors:
                self.error_dialog("Conversion incomplète", "\n".join(errors))
            elif converted:
                self.toast(_plural(converted, "FLAC converti", "FLAC convertis") + " en MP3")
            return GLib.SOURCE_REMOVE

        threading.Thread(target=work, daemon=True).start()

    def _converted(self, old: Track, mp3: str, trashed: bool) -> bool:
        was_current = self.list.current() is old
        was_checked = old.checked
        existing = self.list.find(mp3)
        if existing is not None:
            new = existing
            if trashed:
                self._drop_track(old)
        else:
            new = Track(mp3)
            self._watch(new)
            if trashed:
                self._unwatch(old)
                self.list.replace(old, new)
            else:
                self.list.insert_sorted(new)
            self.loader.start([new], invalidate=False)
        new.checked = was_checked
        if was_current:
            self.list.select(new)
        self._targets_changed()
        return GLib.SOURCE_REMOVE

    # ------------------------------------------------------------------
    # Mise en forme et renommage d'après les tags
    # ------------------------------------------------------------------
    @staticmethod
    def _ready(tracks):
        return [t for t in tracks if t.loaded and not t.error]

    def _plan_renames(self, items):
        """`items` : liste de (morceau, artiste, titre). Renvoie (plan, ignorés)."""
        plan, skipped, reserved = [], [], set()
        for t, artist, title in items:
            ext = os.path.splitext(t.path)[1]
            new = textfmt.filename_from_tags(artist, title, ext)
            if new is None:
                skipped.append(t.name)
                continue
            dest = os.path.join(t.folder, new)
            if dest == t.path:
                continue
            taken = os.path.exists(dest) and os.path.normcase(dest) != os.path.normcase(t.path)
            if taken or dest in reserved:
                stem, ext2 = os.path.splitext(dest)
                n = 2
                while os.path.exists(f"{stem} ({n}){ext2}") or f"{stem} ({n}){ext2}" in reserved:
                    n += 1
                dest = f"{stem} ({n}){ext2}"
            reserved.add(dest)
            plan.append((t, dest))
        return plan, skipped

    def tidy(self, tracks, confirm: bool) -> None:
        """Mise en forme complète : tags artiste/titre, enregistrement, renommage."""
        ready = self._ready(tracks)
        items = [(t, *textfmt.tidy(t.values.artist, t.values.title, t.stem)) for t in ready]
        albums = {t: textfmt.title_case(t.values.album) for t in ready}
        plan, skipped = self._plan_renames(items)
        changes = [(t, a, ti) for t, a, ti in items
                   if (a, ti) != (t.values.artist, t.values.title) or t.dirty
                   or albums[t] != t.values.album]
        if not plan and not changes:
            if skipped:
                self.toast("Artiste ou titre introuvable, même dans le nom du fichier.")
            return

        def run():
            for t, a, ti in items:
                if a.strip():
                    t.set_value("artist", a)
                if ti.strip():
                    t.set_value("title", ti)
                t.set_value("album", albums[t])
            sink: list = []

            def after_save():
                # Le plan est recalculé : les chemins n'ont pas changé, mais
                # c'est plus sûr si un fichier a disparu entre-temps.
                plan2, _ = self._plan_renames(
                    [(t, t.values.artist, t.values.title) for t, _a, _ti in items
                     if os.path.exists(t.path)])
                self._apply_renames(plan2, undo_sink=sink)
                self.editor.refresh()
                if sink:
                    entry = {"kind": "multi", "entries": sink}
                    if confirm:   # tout un dossier : notification avec « Annuler »
                        self._push_undo(entry, _plural(len(items) - len(skipped),
                                                       "morceau mis", "morceaux mis")
                                        + " en forme")
                    else:
                        self._record_undo(entry)
                if skipped and confirm:
                    self.toast(_plural(len(skipped), "fichier ignoré", "fichiers ignorés")
                               + " : artiste ou titre introuvable")

            self.save([t for t, _a, _ti in items if t.dirty], then=after_save,
                      undo_sink=sink)

        if confirm:
            rename_preview(self, [(t.name, os.path.basename(d)) for t, d in plan], skipped, run,
                           heading=f"Mettre en forme {_plural(len(ready), 'morceau', 'morceaux')} ?",
                           note="Les tags sont enregistrés, puis les fichiers renommés.")
        else:
            run()

    def _apply_renames(self, plan, undo_sink=None) -> None:
        items, errors = [], []
        for t, dest in plan:
            old = t.path
            try:
                os.rename(old, dest)
            except OSError as exc:
                errors.append(f"{t.name} : {exc.strerror or exc}")
                continue
            if self.player.path == old:
                self.player.path = dest
            t.set_path(dest)
            items.append((t, old, dest))
        self._resort_all()
        self.editor.refresh()
        if errors:
            self.error_dialog("Certains fichiers n'ont pas pu être renommés", "\n".join(errors))
        if items:
            entry = {"kind": "rename", "items": items}
            if undo_sink is not None:
                undo_sink.append(entry)
            else:
                self._push_undo(entry, _plural(len(items), "fichier renommé",
                                               "fichiers renommés"))

    def _resort_all(self) -> None:
        current = self.list.current()
        tracks = sorted(self.tracks(), key=lambda t: natural_key(t.name))
        self.list.set_tracks(tracks)
        self.list.show_list_state()
        if current is not None:
            self.list.select(current)
        self._targets_changed()

    # ------------------------------------------------------------------
    # Renommer un dossier en « Artiste - Album »
    # ------------------------------------------------------------------
    def rename_folder(self, path: str) -> None:
        if not path or not os.path.isdir(path):
            return
        if path == self.tree.root:
            self.toast("Le dossier de base ne peut pas être renommé ici.")
            return
        suggestion = self._suggest_folder_name(path) or os.path.basename(path)
        dialog = Adw.AlertDialog(heading="Renommer le dossier",
                                 body=GLib.markup_escape_text(os.path.basename(path)))
        entry = Gtk.Entry(text=suggestion, activates_default=True)
        dialog.set_extra_child(entry)
        dialog.add_response("cancel", "Annuler")
        dialog.add_response("rename", "Renommer")
        dialog.set_response_appearance("rename", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("rename")
        dialog.set_close_response("cancel")
        dialog.connect("response", lambda _d, r: self._do_rename_folder(path, entry.get_text())
                       if r == "rename" else None)
        dialog.present(self)
        GLib.idle_add(lambda: (entry.grab_focus(), False)[1])

    @staticmethod
    def _folder_name_from_values(metadata, total: int) -> str | None:
        artists: dict[str, int] = {}
        albums: dict[str, int] = {}
        for raw_artist, raw_album, stem in metadata:
            artist = textfmt.split_feat(raw_artist.split(";")[0])[0]
            if not artist:
                artist = textfmt.tags_from_filename(stem)[0]
            if artist:
                key = textfmt.title_case(artist)
                artists[key] = artists.get(key, 0) + 1
            if raw_album.strip():
                albums[raw_album.strip()] = albums.get(raw_album.strip(), 0) + 1
        artist = max(artists, key=artists.get) if artists else ""
        album = max(albums, key=albums.get) if albums else ""
        if len(artists) > 1 and artists[artist] < total / 2:
            artist = "Artistes divers"
        name = textfmt.folder_name(artist, album)
        return name or None

    def _suggest_folder_name(self, path: str) -> str | None:
        """Artiste et album les plus fréquents parmi les morceaux du dossier."""
        files = list_audio_files(path)
        metadata = []
        for f in files[:60]:
            track = self.list.find(f)
            if track is not None and track.loaded:
                values = track.values
            else:
                try:
                    values = tags.read(f).values
                except tags.TagError:
                    continue
            metadata.append((values.artist, values.album,
                             os.path.splitext(os.path.basename(f))[0]))
        return self._folder_name_from_values(metadata, len(files))

    @staticmethod
    def _map_folder_path(path: str, moves: list[tuple[str, str]]) -> str:
        for old, new in moves:
            if path == old or path.startswith(old + os.sep):
                path = new + path[len(old):]
        return path

    def rename_all_folders(self) -> None:
        root = self.tree.root
        if not root or self._busy or self._bulk_folder_rename_active:
            return
        self._bulk_folder_rename_active = True
        self._schedule_update()
        self.toast("Analyse des dossiers…")

        def work():
            candidates = []
            skipped = []
            errors = []
            for directory, subdirs, filenames in os.walk(
                    root, topdown=True, followlinks=False,
                    onerror=lambda exc: errors.append(str(exc))):
                subdirs[:] = [name for name in subdirs if not name.startswith(".")]
                if directory == root:
                    continue
                files = [
                    os.path.join(directory, name) for name in filenames
                    if not name.startswith(".") and tags.is_audio(name)
                ]
                if not files:
                    continue
                files.sort(key=lambda path: natural_key(os.path.basename(path)))
                metadata = []
                for path in files[:60]:
                    try:
                        values = tags.read(path).values
                    except tags.TagError:
                        continue
                    metadata.append((values.artist, values.album,
                                     os.path.splitext(os.path.basename(path))[0]))
                name = self._folder_name_from_values(metadata, len(files))
                if not name:
                    skipped.append(os.path.relpath(directory, root))
                    continue
                candidates.append((directory, name))

            mappings = []
            plan = []
            reserved = set()
            for path, name in sorted(
                    candidates, key=lambda item: item[0].count(os.sep)):
                old = self._map_folder_path(path, mappings)
                dest = os.path.join(os.path.dirname(old), name)
                key = os.path.normcase(dest)
                if dest == old:
                    continue
                if os.path.exists(dest) or key in reserved:
                    skipped.append(os.path.relpath(path, root))
                    continue
                plan.append((old, dest))
                mappings.append((old, dest))
                reserved.add(key)
            GLib.idle_add(self._show_bulk_folder_rename, root, plan, skipped, errors)

        threading.Thread(target=work, daemon=True).start()

    def _show_bulk_folder_rename(self, root, plan, skipped, errors) -> bool:
        self._bulk_folder_rename_active = False
        self._schedule_update()
        if errors:
            self.error_dialog("Certains dossiers n’ont pas pu être analysés",
                              "\n".join(errors[:20]))
        if root != self.tree.root:
            return GLib.SOURCE_REMOVE
        if not plan:
            self.toast("Aucun dossier à renommer.")
            return GLib.SOURCE_REMOVE
        rename_preview(
            self,
            [(os.path.relpath(old, root), os.path.relpath(new, root))
             for old, new in plan],
            skipped,
            lambda: self._apply_bulk_folder_renames(plan),
            heading=f"Renommer {_plural(len(plan), 'dossier', 'dossiers')} ?",
            note="Les noms sont déduits des tags artiste et album.",
            item_label="dossier",
            skipped_reason="aucun tag exploitable ou nom déjà utilisé",
            confirm_label="Renommer",
        )
        return GLib.SOURCE_REMOVE

    def _apply_bulk_folder_renames(self, plan) -> None:
        moved = []
        errors = []
        for old, new in plan:
            if not os.path.isdir(old):
                errors.append(f"{old} : dossier introuvable")
                continue
            if os.path.exists(new):
                errors.append(f"{new} : un dossier porte déjà ce nom")
                continue
            try:
                os.rename(old, new)
            except OSError as exc:
                errors.append(f"{old} : {exc.strerror or exc}")
                continue
            moved.append((old, new))

        if moved:
            self._update_paths_after_folder_renames(moved)
            self._push_undo(
                {"kind": "folder-batch", "items": moved},
                _plural(len(moved), "dossier renommé", "dossiers renommés"),
            )
        if errors:
            self.error_dialog("Certains dossiers n’ont pas pu être renommés",
                              "\n".join(errors[:20]))

    def _update_paths_after_folder_renames(self, moves) -> None:
        if self.player.path:
            self.player.path = self._map_folder_path(self.player.path, moves)
        for track in self.tracks():
            old_path = track.path
            new_path = self._map_folder_path(old_path, moves)
            if new_path != old_path:
                track.set_path(new_path)
        if self.folder:
            self.folder = self._map_folder_path(self.folder, moves)
            self.cfg["folder"] = self.folder
            self._watch_folder(self.folder)
            self._update_title()
            self._load_folder_cover()
        self.tree.reload()
        if self.folder:
            self.tree.select_path(self.folder, silent=True)
        self.editor.refresh()

    def _do_rename_folder(self, path: str, name: str, record: bool = True) -> None:
        name = textfmt.clean_spaces(name).strip(" .")
        if not name or os.sep in name or name in (".", ".."):
            self.toast("Nom de dossier invalide.")
            return
        dest = os.path.join(os.path.dirname(path), name)
        if dest == path:
            return
        if os.path.exists(dest) and os.path.normcase(dest) != os.path.normcase(path):
            self.toast("Un dossier porte déjà ce nom.")
            return
        try:
            os.rename(path, dest)
        except OSError as exc:
            self.toast(f"Renommage impossible : {exc.strerror}")
            return
        self._folder_moved(path, dest)
        if record:
            self._push_undo({"kind": "folder", "old": path, "new": dest},
                            f"Dossier renommé en « {name} »")

    def _folder_moved(self, old: str, new: str) -> None:
        """Met à jour l'appli après le renommage d'un dossier."""
        prefix = old + os.sep
        if self.folder and (self.folder == old or self.folder.startswith(prefix)):
            self.folder = new + self.folder[len(old):]
            self.cfg["folder"] = self.folder
            for t in self.tracks():
                if t.path.startswith(prefix):
                    if self.player.path == t.path:
                        self.player.path = new + t.path[len(old):]
                    t.set_path(new + t.path[len(old):])
            self._watch_folder(self.folder)
            self._update_title()
        self.tree.reload()
        if self.folder:
            self.tree.select_path(self.folder, silent=True)
        self.editor.refresh()

    # ------------------------------------------------------------------
    # folder.jpg et pochette en ligne
    # ------------------------------------------------------------------
    def _load_folder_cover(self) -> None:
        self.folder_cover = None
        path = covers.find_folder_image(self.folder) if self.folder else None
        if path:
            try:
                with open(path, "rb") as fh:
                    self.folder_cover = covers.prepare(fh.read())
            except (OSError, covers.CoverError):
                self.folder_cover = None
        self._schedule_update()

    def apply_folder_cover(self, tracks) -> None:
        if self.folder_cover is None:
            return
        n = 0
        for t in self._ready(tracks):
            if t.values.cover != self.folder_cover:
                t.set_value("cover", self.folder_cover)
                n += 1
        self.editor.refresh()
        changed = [t for t in self._ready(tracks) if t.dirty]
        if len(changed) > 1:
            self.save(changed, notify=True)
        else:
            self.autosave(changed)

    def search_cover_online(self) -> None:
        ready = self._ready(self.targets())
        if not ready:
            return
        v = ready[0].values
        artist = textfmt.split_feat(v.artist.split(";")[0])[0]
        query = f"{artist} {v.album or v.title}".strip()
        self._online_folder = ready[0].folder
        CoverSearchDialog(query, self._on_online_cover).present(self)

    def _on_online_cover(self, data: bytes) -> None:
        cover = self._apply_cover_bytes(data)
        folder = self._online_folder or self.folder
        if cover is None or not folder:
            return
        # La pochette est aussi rangée dans le dossier, toujours sous le nom folder.jpg.
        try:
            jpeg = covers.as_jpeg(cover)
            existing = covers.find_folder_image(folder)
            if existing:
                Gio.File.new_for_path(existing).trash(None)
            with open(os.path.join(folder, covers.FOLDER_IMAGE), "wb") as fh:
                fh.write(jpeg)
        except (OSError, GLib.Error, covers.CoverError) as exc:
            self.toast(f"folder.jpg non enregistré : {exc}")
            return
        if folder == self.folder and not self.list.library_mode:
            self.folder_cover = cover
        self._schedule_update()

    # ------------------------------------------------------------------
    # Doublons
    # ------------------------------------------------------------------
    def find_duplicates(self) -> None:
        root = self.cfg["root"]
        DuplicatesDialog(root, self._on_duplicates_trashed, self.open_path).present(self)

    def _on_duplicates_trashed(self, paths) -> None:
        if self.folder and any(os.path.dirname(p) == self.folder for p in paths):
            self._reconcile()

    # ------------------------------------------------------------------
    # Annulation
    # ------------------------------------------------------------------
    def _record_undo(self, entry: dict) -> None:
        """Annulation possible (menu principal) sans notification."""
        self._undo.append(entry)
        del self._undo[:-20]
        self._schedule_update()

    def autosave(self, tracks) -> None:
        """Enregistrement direct, sans notification (pochettes, mise en forme…)."""
        dirty = [t for t in tracks if t.dirty]
        if dirty:
            self.save(dirty)

    def _push_undo(self, entry: dict, message: str) -> None:
        self._undo.append(entry)
        del self._undo[:-20]
        toast = Adw.Toast(title=GLib.markup_escape_text(message), button_label="Annuler",
                          timeout=6)
        toast.connect("button-clicked", lambda *_: self.undo(entry))
        self.toasts.add_toast(toast)
        self._schedule_update()

    def undo(self, entry: dict | None = None) -> None:
        if entry is None:
            if not self._undo:
                return
            entry = self._undo[-1]
        if not any(e is entry for e in self._undo):
            return
        self._undo = [e for e in self._undo if e is not entry]
        self._revert_entry(entry)

    def _revert_entry(self, entry: dict) -> None:
        kind = entry["kind"]
        if kind == "multi":
            for sub in reversed(entry["entries"]):
                self._revert_entry(sub)
            return
        if kind == "move":
            done = 0
            for old, new, is_dir in reversed(entry["items"]):
                if not os.path.exists(new) or os.path.exists(old):
                    continue
                try:
                    shutil.move(new, old)
                except OSError:
                    continue
                done += 1
                self._after_move(new, old, is_dir)
            self._finish_moves()
            self.toast(_plural(done, "déplacement annulé", "déplacements annulés"))
            return
        if kind == "folder":
            if os.path.isdir(entry["new"]) and not os.path.exists(entry["old"]):
                try:
                    os.rename(entry["new"], entry["old"])
                except OSError as exc:
                    self.toast(f"Annulation impossible : {exc.strerror}")
                    return
                self._folder_moved(entry["new"], entry["old"])
                self.toast("Renommage du dossier annulé")
            return
        if kind == "folder-batch":
            undone = []
            errors = []
            for old, new in reversed(entry["items"]):
                if not os.path.isdir(new) or os.path.exists(old):
                    continue
                try:
                    os.rename(new, old)
                except OSError as exc:
                    errors.append(f"{new} : {exc.strerror or exc}")
                    continue
                undone.append((new, old))
            if undone:
                self._update_paths_after_folder_renames(undone)
                self.toast(_plural(len(undone), "renommage annulé",
                                   "renommages annulés"))
            if errors:
                self.error_dialog("Certains renommages n’ont pas pu être annulés",
                                  "\n".join(errors[:20]))
            return

        if kind == "rename":
            done = 0
            for t, old, new in reversed(entry["items"]):
                in_list = self.list.find(t.path) is t
                current = t.path if in_list else new
                if not os.path.exists(current) or os.path.exists(old):
                    continue
                try:
                    os.rename(current, old)
                except OSError:
                    continue
                done += 1
                if in_list:
                    if self.player.path == current:
                        self.player.path = old
                    t.set_path(old)
            self._resort_all()
            self.editor.refresh()
            self.toast(_plural(done, "renommage annulé", "renommages annulés"))
            return

        items = []
        for t, path, old in entry["items"]:
            in_list = self.list.find(t.path) is t
            items.append((t, t.path if in_list else path, old, in_list))
        self._set_busy(True)

        def work():
            errors = []
            for _t, path, old, _in in items:
                if not os.path.exists(path):
                    continue
                try:
                    tags.write(path, old)
                except tags.TagError as exc:
                    errors.append(f"{os.path.basename(path)} : {exc}")
            GLib.idle_add(finish, errors)

        def finish(errors):
            self._set_busy(False)
            reload = [t for t, _p, _o, in_list in items if in_list]
            for t in reload:
                t.loaded = False
            self.loader.start(reload, invalidate=False)
            if errors:
                self.error_dialog("Annulation incomplète", "\n".join(errors))
            else:
                self.toast("Anciens tags restaurés")
            return GLib.SOURCE_REMOVE

        threading.Thread(target=work, daemon=True).start()

    # ------------------------------------------------------------------
    # Recherche dans toute la discothèque
    # ------------------------------------------------------------------
    def _on_search_changed(self, text: str, scope: str) -> None:
        if self._lib_timer:
            GLib.source_remove(self._lib_timer)
        self._lib_timer = GLib.timeout_add(300, self._apply_search, text.strip(), scope)

    def _apply_search(self, text: str, scope: str) -> bool:
        self._lib_timer = 0
        if scope == "all" and text:
            if self.list.library_mode:
                self._search_library(text)
            else:
                # Seules les vraies modifications sont enregistrées ici : le
                # nettoyage des tags superflus sera de nouveau proposé au retour.
                dirty = [t for t in self.dirty_tracks() if t.edited]
                if dirty:
                    self.save_before(dirty, lambda: self._search_library(text),
                                     lambda: self.list.set_scope("folder"))
                else:
                    self._search_library(text)
        elif self.list.library_mode:
            self._leave_library(scope)
        return GLib.SOURCE_REMOVE

    def _leave_library(self, scope: str) -> None:
        dirty = [t for t in self.dirty_tracks() if t.edited]

        def go():
            if self.folder:
                self.open_folder(self.folder)
                if self.list.current() is None and self._last_library_track:
                    self.list.select(self.list.find(self._last_library_track))

        if dirty:
            self.save_before(dirty, go, lambda: self.list.set_scope("all"))
        else:
            go()

    def _search_library(self, text: str) -> None:
        root = self.tree.root or self.cfg["root"]
        self._lib_gen += 1
        gen = self._lib_gen
        if not self.list.library_mode:
            self.player.load(None)
            self.loader.cancel()
            if self.monitor is not None:
                self.monitor.cancel()
                self.monitor = None
            self.folder_cover = None
            for t in list(self._track_handlers):
                self._unwatch(t)
            self.list.set_tracks([])   # les lignes seront recréées avec leur dossier
            self.list.root = root
            self.list.set_library_mode(True)
        self._last_library_track = None
        self.list.show_searching(0.0)

        def progress(i, n):
            GLib.idle_add(lambda: (gen == self._lib_gen and
                                   self.list.show_searching(i / n if n else 0), False)[1])

        def work():
            library.INDEX.update(root, progress, lambda: gen != self._lib_gen)
            if gen != self._lib_gen:
                return
            hits = library.INDEX.search(root, text)
            GLib.idle_add(show, hits)

        def show(hits):
            if gen != self._lib_gen or not self.list.library_mode:
                return GLib.SOURCE_REMOVE
            current = self.list.current()
            old = {t.path: t for t in self.tracks()}
            result, fresh = [], []
            for path in hits:
                t = old.pop(path, None)
                if t is None:
                    t = Track(path)
                    self._watch(t)
                    fresh.append(t)
                result.append(t)
            for t in old.values():
                if t.edited:
                    result.append(t)   # une modification en cours n'est jamais perdue
                else:
                    self._unwatch(t)
            self.list.set_tracks(result)
            self.list.show_list_state()
            if current is not None and current in result:
                self.list.select(current)
            self.loader.start([t for t in result if not t.loaded])
            self._update_title()
            self._targets_changed()
            if len(hits) >= 500:
                self.toast("Seuls les 500 premiers résultats sont affichés.")
            return GLib.SOURCE_REMOVE

        threading.Thread(target=work, daemon=True).start()

    # ------------------------------------------------------------------
    # Paroles en ligne
    # ------------------------------------------------------------------
    def search_lyrics(self) -> None:
        ready = self._ready(self.targets())
        if len(ready) != 1:
            return
        t = ready[0]
        artist, title = t.values.artist, t.values.title
        filename_artist, filename_title = textfmt.tags_from_filename(t.stem)
        artist = artist.strip() or filename_artist
        title = title.strip() or filename_title
        artist = textfmt.split_feat(artist.split(";")[0])[0]
        title = textfmt.split_feat(title)[0]

        def chosen(text):
            if self.list.find(t.path) is not t:
                return
            t.set_value("lyrics", text)
            self.editor.refresh()
            self._schedule_update()
            self.toast("Paroles ajoutées — à enregistrer")

        LyricsDialog(artist, title, t.values.album, t.info.length, chosen).present(self)

    # ------------------------------------------------------------------
    # File d'attente des paroles
    # ------------------------------------------------------------------
    def queue_lyrics(self, everything: bool) -> None:
        if everything:
            root = self.tree.root or self.cfg["root"]
            paths, where = list_audio(root), "la discothèque"
        else:
            folder = self.tree.selected_path() or self.folder
            if not folder:
                return
            paths, where = list_audio(folder), f"« {os.path.basename(folder)} »"
        added = self.lyrics_queue.enqueue(paths)
        if not added:
            self.toast("Rien à ajouter : ces morceaux sont déjà dans la file ou déjà essayés.")
        else:
            self.toast(_plural(added, "morceau ajouté", "morceaux ajoutés")
                       + f" à la file des paroles ({where})")

    def _toggle_queue(self) -> None:
        q = self.lyrics_queue
        q.resume() if q.paused else q.pause()

    def _update_lyrics_bar(self) -> None:
        q = self.lyrics_queue
        self.list.lyrics_revealer.set_reveal_child(q.active)
        if not q.active:
            return
        state = "en pause" if q.paused else (q.current or "en cours")
        self.list.lyrics_label.set_label(
            f"Paroles : {q.done}/{q.total} · {q.found} trouvées · "
            f"{q.not_found} sans résultat · {state}")
        self.list.lyrics_bar.set_fraction(q.done / q.total if q.total else 0)
        self.list.lyrics_pause.set_icon_name(
            "media-playback-start-symbolic" if q.paused else "media-playback-pause-symbolic")
        self.list.lyrics_pause.set_tooltip_text("Reprendre" if q.paused else "Mettre en pause")

    def _on_queue_lyrics(self, path: str, text: str, written: bool) -> None:
        t = self.list.find(path)
        if t is None or not t.loaded:
            return
        if written:
            t.apply_lyrics_saved(text)
        elif not t.values.lyrics.strip():
            t.set_value("lyrics", text)
        if t in self.editor.targets:
            self.editor.refresh()
        self._schedule_update()

    def _on_lyrics_queue_finished(self, _queue, found: int, not_found: int) -> None:
        self.toast(f"Recherche terminée : {found} paroles trouvées, "
                   f"{not_found} sans résultat.")

    # ------------------------------------------------------------------
    # Année et album en ligne
    # ------------------------------------------------------------------
    def search_release(self) -> None:
        ready = self._ready(self.targets())
        if len(ready) != 1:
            return
        t = ready[0]
        artist, title = t.values.artist, t.values.title
        if not title.strip():
            artist, title = textfmt.tags_from_filename(t.stem)
        artist = textfmt.split_feat(artist.split(";")[0])[0]
        title = textfmt.split_feat(title)[0]

        def apply(year, album):
            if self.list.find(t.path) is not t:
                return
            if year:
                t.set_value("date", year)
            if album:
                t.set_value("album", textfmt.title_case(album))
            self.editor.refresh()
            self.autosave([t])

        ReleaseDialog(artist, title, apply).present(self)

    # ------------------------------------------------------------------
    # Genres et listes de lecture
    # ------------------------------------------------------------------
    def _library_data(self, then) -> None:
        """Met l'index à jour en arrière-plan, puis appelle `then(entries)`."""
        root = self.tree.root or self.cfg["root"]
        self.list.show_progress("Lecture de la discothèque…", 0, False)

        def work():
            library.INDEX.update(root)
            prefix = root.rstrip(os.sep) + os.sep
            entries = {p: r for p, r in library.INDEX._entries.items() if p.startswith(prefix)}
            GLib.idle_add(done, entries)

        def done(entries):
            self.list.hide_progress()
            then(entries, root)
            return GLib.SOURCE_REMOVE

        threading.Thread(target=work, daemon=True).start()

    def open_genres(self) -> None:
        def show(entries, root):
            counts: dict[str, int] = {}
            for rec in entries.values():
                for g in (x.strip() for x in rec.get("genre", "").split(";")):
                    if g:
                        counts[g] = counts.get(g, 0) + 1
            GenresDialog(counts, lambda old, new: self.replace_genre(old, new, entries)).present(self)

        self._library_data(show)

    def replace_genre(self, old: str, new: str, entries: dict) -> None:
        """Remplace un genre par un autre dans toute la discothèque."""
        paths = [p for p, r in entries.items()
                 if old in [g.strip() for g in r.get("genre", "").split(";")]]
        if not paths:
            return
        self._set_busy(True)

        def work():
            errors, done = [], 0
            for i, path in enumerate(paths):
                GLib.idle_add(self.list.show_progress, f"Genre « {old} » → « {new} »",
                              i / len(paths), False)
                try:
                    v = tags.read(path).values
                    parts = [new if g.strip() == old else g.strip() for g in v.genre.split(";")]
                    v.genre = "; ".join(dict.fromkeys(g for g in parts if g))
                    tags.write(path, v)
                    done += 1
                except tags.TagError as exc:
                    errors.append(f"{os.path.basename(path)} : {exc}")
            GLib.idle_add(finish, done, errors)

        def finish(done, errors):
            self.list.hide_progress()
            self._set_busy(False)
            for t in self.tracks():
                if t.path in paths and not t.edited:
                    t.loaded = False
            self.loader.start([t for t in self.tracks() if not t.loaded], invalidate=False)
            if errors:
                self.error_dialog("Certains fichiers n'ont pas été modifiés", "\n".join(errors))
            else:
                self.toast(f"« {old} » remplacé par « {new} » ({_plural(done, 'morceau', 'morceaux')})")
            return GLib.SOURCE_REMOVE

        threading.Thread(target=work, daemon=True).start()

    def open_preferences(self) -> None:
        from .model import THUMB_DIR

        def cache_size():
            total = n = 0
            try:
                with os.scandir(THUMB_DIR) as it:
                    for e in it:
                        if e.is_file():
                            total += e.stat().st_size
                            n += 1
            except OSError:
                pass
            from .duplicates import human_size
            return f"{n} miniature{'s' if n > 1 else ''} · {human_size(total)}"

        dialog = Adw.PreferencesDialog(title="Préférences")
        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(title="Tags")
        auto = Adw.SwitchRow(
            title="Nettoyage automatique",
            subtitle="Supprimer les tags superflus dès l'ouverture d'un dossier, "
                     "sans enregistrement",
            active=self.cfg.get("auto_clean", True))
        auto.connect("notify::active", lambda r, _p: self.activate_action(
            "win.auto-clean", GLib.Variant("b", r.get_active())))
        group.add(auto)
        page.add(group)

        cache = Adw.PreferencesGroup(
            title="Cache",
            description="Les miniatures des pochettes sont gardées pour accélérer le "
                        "lancement. Les vider libère de la place ; elles sont "
                        "recréées au besoin.")
        row = Adw.ActionRow(title="Miniatures des pochettes", subtitle=cache_size())
        button = Gtk.Button(label="Vider", valign=Gtk.Align.CENTER)
        button.add_css_class("destructive-action")

        def clear(*_):
            import shutil
            shutil.rmtree(THUMB_DIR, ignore_errors=True)
            row.set_subtitle(cache_size())

        button.connect("clicked", clear)
        row.add_suffix(button)
        cache.add(row)
        page.add(cache)
        dialog.add(page)
        dialog.present(self)

    def _on_auto_clean(self, action, value) -> None:
        if action.get_state().get_boolean() == value.get_boolean():
            return
        action.set_state(value)
        self.cfg["auto_clean"] = value.get_boolean()
        config.save(self.cfg)
        if value.get_boolean() and self.folder and not self.list.library_mode:
            # Nettoie tout de suite ce qui attendait dans le dossier ouvert.
            self.autosave([t for t in self.tracks() if t.dirty and not t.edited])

    # ------------------------------------------------------------------
    # Réserve de pochettes
    # ------------------------------------------------------------------
    def _reserve_matches(self, tracks):
        """[(morceau, nom, chemin)] pour les morceaux SANS pochette dont le
        genre correspond à une pochette de la réserve."""
        if not reserve.entries():
            return []
        out = []
        for t in tracks:
            if t.values.cover is None and t.values.genre.strip():
                hit = reserve.for_genre(t.values.genre)
                if hit:
                    out.append((t, hit[0], hit[1]))
        return out

    def reserve_by_genre(self, tracks) -> None:
        matches = self._reserve_matches(self._ready(tracks))
        if not matches:
            self.toast("Aucun morceau sans pochette ne correspond à la réserve.")
            return
        for t, _name, path in matches:
            cover = reserve.load(path)
            if cover is not None:
                t.set_value("cover", cover)
        self.editor.refresh()
        changed = [t for t, _n, _p in matches if t.dirty]
        if len(changed) > 1:
            self.save(changed, notify=True)
        else:
            self.autosave(changed)

    def open_reserve(self) -> None:
        targets = self._ready(self.targets())
        if not targets:
            return
        covers_set = {t.values.cover.data if t.values.cover else None for t in targets}
        current = targets[0].values.cover if len(covers_set) == 1 else None
        genre = targets[0].values.genre.split(";")[0].strip()

        def chosen(cover, name):
            for t in self._ready(self.targets()):
                t.set_value("cover", cover)
            self.editor.refresh()
            self.autosave(self._ready(self.targets()))

        ReserveDialog(current, genre, len(targets), chosen).present(self)

    # ------------------------------------------------------------------
    # Ouverture d'un chemin (ligne de commande, Fichiers, glisser-déposer)
    # ------------------------------------------------------------------
    def open_path(self, path: str) -> bool:
        path = os.path.abspath(path)
        if os.path.isdir(path):
            folder, select = path, None
        elif os.path.isfile(path) and tags.is_audio(path):
            folder, select = os.path.dirname(path), path
        else:
            return False
        if not self.tree.select_path(folder, silent=True):
            # Hors du dossier de base : on l'affiche le temps de la session.
            self.tree.set_root(folder)
            self.tree.select_path(folder, silent=True)
        if folder == self.folder and not self.list.library_mode:
            if select:
                self.list.select(self.list.find(select))
            return True
        self._select_after_load = select
        self.request_folder(folder)
        return True

    def _on_window_drop(self, value) -> bool:
        files = value.get_files() if hasattr(value, "get_files") else []
        path = files[0].get_path() if files else None
        if path and (os.path.isdir(path) or tags.is_audio(path)):
            return self.open_path(path)
        return False

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------
    def toast(self, text: str) -> None:
        self.toasts.add_toast(Adw.Toast(title=GLib.markup_escape_text(text), timeout=3))

    def error_dialog(self, heading: str, body: str) -> None:
        dialog = Adw.AlertDialog(heading=heading, body=body)
        dialog.add_response("ok", "OK")
        dialog.present(self)

    # ------------------------------------------------------------------
    # Fermeture
    # ------------------------------------------------------------------
    def _on_close_request(self, *_):
        if self._closing:
            return False
        if self._busy:
            self.toast("Patientez jusqu'à la fin de l'opération en cours.")
            return True
        dirty = self.dirty_tracks()
        if dirty:
            self.save_before(dirty, self._force_close)
            return True
        self._persist()
        self.player.stop()
        self.lyrics_queue.shutdown()
        return False

    def _force_close(self) -> None:
        self.lyrics_queue.shutdown()
        self._closing = True
        self._persist()
        self.player.stop()
        self.close()

    def _persist(self) -> None:
        self.cfg["maximized"] = self.is_maximized()
        if not self.cfg["maximized"]:
            w, h = self.get_default_size()
            self.cfg["width"], self.cfg["height"] = w, h
        self.cfg["list_width"] = self.paned.get_position()
        if self.tree.get_visible():
            self.cfg["sidebar_width"] = self.split.get_position()
        self.cfg["sidebar"] = self.tree.get_visible()
        config.save(self.cfg)
