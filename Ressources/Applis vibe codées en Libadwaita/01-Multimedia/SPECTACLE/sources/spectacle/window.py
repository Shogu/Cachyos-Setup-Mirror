"""Fenêtre principale : recherche, résultats et favoris, lecteur, mode Rideau (son seul)."""

from urllib.parse import quote

from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk, Pango

from .extractor import Extractor, Video, js_engine_available, looks_like_url
from .covers import Covers
from .favorites import Favorites
from .mpris import Mpris
from .player import Player

APP_ICON = "io.gitlab.shogu.Spectacle-symbolic"
GRABBER_SCHEME = "grabber"


def _format_time(seconds):
    seconds = int(seconds)
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


class Window(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Spectacle", default_width=960, default_height=600)
        self.set_size_request(360, 300)
        self._extractor = Extractor()
        self._player = Player()
        self._favorites = Favorites()
        self._covers = Covers()
        self._current = None
        self._queue = []
        self._duration = 0.0
        self._position = 0.0
        self._start_at = 0.0
        self._audio_only_stream = False
        self._handlers = [
            (self._player, self._player.connect("state-changed", self._on_state_changed)),
            (self._player, self._player.connect("buffering", self._on_buffering)),
            (self._player, self._player.connect("position", self._on_position)),
            (self._player, self._player.connect("ended", self._on_ended)),
            (self._player, self._player.connect("error", self._on_player_error)),
        ]
        self._build_ui()
        self._install_actions()
        self._fill_favorites()
        self._mpris = Mpris(app.get_dbus_connection(), self)
        self.connect("close-request", self._on_close_request)

    # Construction ---------------------------------------------------------------------------------------------------

    def _build_ui(self):
        self._search = Gtk.SearchEntry(placeholder_text="Rechercher ou coller une adresse YouTube")
        self._search.connect("activate", self._on_search_activate)
        header = Adw.HeaderBar(title_widget=Adw.Clamp(child=self._search, maximum_size=380, tightening_threshold=280))
        self._sidebar_button = Gtk.ToggleButton(icon_name="view-list-symbolic", tooltip_text="Résultats et favoris")
        header.pack_start(self._sidebar_button)
        self._curtain_button = Gtk.ToggleButton(icon_name=APP_ICON, tooltip_text="Rideau : son seul, sans image")
        self._curtain_button.connect("toggled", self._on_curtain_toggled)
        header.pack_end(self._curtain_button)

        banner = Adw.Banner(title="quickjs-ng est absent : la plupart des vidéos YouTube ne pourront pas être lues.",
                            revealed=not js_engine_available())

        self._results = self._new_list()
        self._results_stack = Gtk.Stack()
        self._results_stack.add_named(Adw.StatusPage(icon_name="edit-find-symbolic", title="Rechercher",
                                                     description="Les résultats s'affichent ici."), "empty")
        self._results_stack.add_named(Gtk.ScrolledWindow(child=self._results, hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True), "list")
        self._results_stack.add_named(Adw.Spinner(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, width_request=32, height_request=32),
                                      "loading")
        self._favorites_list = self._new_list()
        self._favorites_stack = Gtk.Stack()
        self._favorites_stack.add_named(Adw.StatusPage(icon_name="non-starred-symbolic", title="Aucun favori",
                                                       description="Utiliser l'étoile pendant la lecture."), "empty")
        self._favorites_stack.add_named(Gtk.ScrolledWindow(child=self._favorites_list, hscrollbar_policy=Gtk.PolicyType.NEVER,
                                                           vexpand=True), "list")
        self._side = Adw.ViewStack()
        self._side.add_titled_with_icon(self._results_stack, "results", "Résultats", "edit-find-symbolic")
        self._side.add_titled_with_icon(self._favorites_stack, "favorites", "Favoris", "starred-symbolic")
        sidebar = Adw.ToolbarView(content=self._side)
        sidebar.add_top_bar(Adw.ViewSwitcherBar(stack=self._side, reveal=True))

        self._picture = Gtk.Picture(paintable=self._player.paintable, content_fit=Gtk.ContentFit.CONTAIN, hexpand=True, vexpand=True)
        self._picture.add_css_class("spectacle-video")
        self._spinner = Adw.Spinner(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, width_request=48, height_request=48, visible=False)
        video = Gtk.Overlay(child=self._picture)
        video.add_overlay(self._spinner)
        double_click = Gtk.GestureClick()
        double_click.connect("pressed", self._on_video_pressed)
        self._picture.add_controller(double_click)

        self._curtain_page = Adw.StatusPage(icon_name=APP_ICON, title="Rideau", description="Son seul : l'image n'est ni téléchargée ni décodée.")
        self._status = Adw.StatusPage(icon_name=APP_ICON, title="Rechercher une vidéo",
                                      description="Saisir des mots-clés ou coller une adresse YouTube.")
        self._replay = Gtk.Button(label="Revoir", halign=Gtk.Align.CENTER, visible=False)
        self._replay.add_css_class("pill")
        self._replay.connect("clicked", lambda _b: self._open(self._current))
        self._status.set_child(self._replay)

        self._stage = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self._stage.add_named(self._status, "status")
        self._stage.add_named(video, "video")
        self._stage.add_named(self._curtain_page, "curtain")

        self._split = Adw.OverlaySplitView(content=self._stage, sidebar=sidebar, show_sidebar=False,
                                           min_sidebar_width=260, max_sidebar_width=360)
        self._split.bind_property("show-sidebar", self._sidebar_button, "active",
                                  GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)

        self._toolbar = Adw.ToolbarView(content=self._split, top_bar_style=Adw.ToolbarStyle.FLAT)
        self._toolbar.add_top_bar(header)
        self._toolbar.add_top_bar(banner)
        self._toolbar.add_bottom_bar(self._build_controls())
        self._toasts = Adw.ToastOverlay(child=self._toolbar)
        self.set_content(self._toasts)

        css = Gtk.CssProvider()
        css.load_from_string(".spectacle-video { background: black; }")
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _new_list(self):
        box = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        box.add_css_class("navigation-sidebar")
        box.connect("row-activated", self._on_row_activated)
        return box

    def _build_controls(self):
        def button(icon, tooltip, action):
            widget = Gtk.Button(icon_name=icon, tooltip_text=tooltip, action_name=action)
            widget.add_css_class("flat")
            return widget

        self._play_button = button("media-playback-start-symbolic", "Lecture", "win.play-pause")
        previous = button("media-skip-backward-symbolic", "Précédente", "win.previous")
        nxt = button("media-skip-forward-symbolic", "Suivante", "win.next")
        self._star = Gtk.ToggleButton(icon_name="non-starred-symbolic", tooltip_text="Ajouter aux favoris", sensitive=False)
        self._star.add_css_class("flat")
        self._star_id = self._star.connect("toggled", self._on_star_toggled)
        self._continuous = Gtk.ToggleButton(icon_name="media-playlist-consecutive-symbolic", active=True,
                                            tooltip_text="Lecture continue : enchaîner sur la vidéo suivante de la liste")
        self._continuous.add_css_class("flat")
        grabber = button("folder-download-symbolic", "Envoyer à Grabber pour télécharger", "win.send-to-grabber")

        self._title = Gtk.Label(xalign=0, hexpand=True, ellipsize=Pango.EllipsizeMode.END)
        self._title.add_css_class("heading")
        self._channel = Gtk.Label(xalign=0, hexpand=True, ellipsize=Pango.EllipsizeMode.END)
        self._channel.add_css_class("dim-label")
        self._channel.add_css_class("caption")
        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER, hexpand=True)
        titles.append(self._title)
        titles.append(self._channel)
        self._time = Gtk.Label(label="0:00")
        self._time.add_css_class("numeric")
        self._time.add_css_class("dim-label")

        volume = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 0.05)
        volume.set_draw_value(False)
        volume.set_size_request(100, -1)
        volume.set_tooltip_text("Volume")
        volume.set_value(self._player.volume)
        volume.connect("value-changed", self._on_volume_changed)
        self._volume_icon = Gtk.Button(icon_name="audio-volume-high-symbolic", tooltip_text="Couper le son")
        self._volume_icon.add_css_class("flat")
        self._volume_icon.connect("clicked", self._on_mute_clicked)
        self._volume_scale = volume

        self._progress = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 1)
        self._progress.set_draw_value(False)
        self._progress.set_sensitive(False)
        self._progress.connect("change-value", self._on_progress_change)

        row = Gtk.Box(spacing=4)
        for widget in (previous, self._play_button, nxt, titles, self._star, self._continuous, grabber, self._time, self._volume_icon, volume,
                       button("view-fullscreen-symbolic", "Plein écran", "win.fullscreen")):
            row.append(widget)
        controls = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin_start=6, margin_end=6, margin_bottom=6)
        controls.append(self._progress)
        controls.append(row)
        return controls

    def _install_actions(self):
        for name, callback in (("play-pause", lambda *_: self.play_pause()), ("stop", lambda *_: self.stop()),
                               ("next", lambda *_: self.next()), ("previous", lambda *_: self.previous()),
                               ("fullscreen", self._toggle_fullscreen), ("leave-fullscreen", lambda *_: self.unfullscreen()),
                               ("focus-search", lambda *_: self._search.grab_focus()),
                               ("send-to-grabber", lambda *_: self._send_to_grabber())):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)
        self.connect("notify::fullscreened", self._on_fullscreened)
        keys = Gtk.EventControllerKey(propagation_phase=Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self._on_key_pressed)
        self.add_controller(keys)
        self._sync_actions()

    # Interface publique (utilisée aussi par MPRIS) ------------------------------------------------------------------

    @property
    def status(self):
        if self._current is None or self._stage.get_visible_child_name() == "status":
            return "Stopped"
        return "Playing" if self._player.playing else "Paused"

    @property
    def has_media(self):
        return self._current is not None and self._stage.get_visible_child_name() in ("video", "curtain")

    @property
    def can_seek(self):
        return self.has_media and self._duration > 0 and not self._current.is_live

    @property
    def can_next(self):
        return self._queue_index() + 1 < len(self._queue) if self._current else False

    @property
    def can_previous(self):
        return self._queue_index() > 0 if self._current else False

    @property
    def volume(self):
        return 0.0 if self._player.muted else self._player.volume

    def metadata(self):
        if self._current is None:
            return None
        return {"title": self._current.title, "channel": self._current.channel, "url": self._current.page_url,
                "thumbnail": self._current.thumbnail, "duration": self._current.duration}

    def position(self):
        return self._position

    def play(self):
        if self.has_media:
            self._player.play()
        elif self._current:
            self._open(self._current)

    def pause(self):
        if self.has_media:
            self._player.pause()

    def play_pause(self):
        if self.has_media and self._player.playing:
            self._player.pause()
        else:
            self.play()

    def stop(self):
        self._player.stop()
        self._duration = self._position = 0.0
        self._progress.set_sensitive(False)
        self._time.set_text("0:00")
        if self._current:
            self._show_status(APP_ICON, "Lecture arrêtée", self._current.title, replay=True)

    def next(self):
        index = self._queue_index()
        if 0 <= index < len(self._queue) - 1:
            self._open(self._queue[index + 1])

    def previous(self):
        index = self._queue_index()
        if index > 0:
            self._open(self._queue[index - 1])
        elif self.can_seek:
            self.seek_to(0)

    def seek_to(self, seconds):
        if self.can_seek:
            self._player.seek(min(seconds, self._duration))
            self._mpris.seeked(seconds)

    def open_url(self, url):
        self._open(Video("", "", url))

    def quit(self):
        self.close()

    def _send_to_grabber(self):
        if Gio.AppInfo.get_default_for_uri_scheme(GRABBER_SCHEME) is None:
            self._toast("Grabber n'est pas installé ou son protocole n'est pas enregistré.")
            return
        uri = f"{GRABBER_SCHEME}://add?url={quote(self._current.page_url, safe='')}"
        Gio.AppInfo.launch_default_for_uri_async(uri, self.get_display().get_app_launch_context(), None, self._on_grabber_launched)

    def _on_grabber_launched(self, _source, result):
        try:
            Gio.AppInfo.launch_default_for_uri_finish(result)
            self._toast("Envoyé à Grabber")
        except GLib.Error as error:
            self._toast(f"Envoi à Grabber impossible : {error.message}")

    def _toast(self, text):
        self._toasts.add_toast(Adw.Toast(title=GLib.markup_escape_text(text), timeout=3))

    # Recherche, listes, favoris -------------------------------------------------------------------------------------

    def _on_search_activate(self, entry):
        text = entry.get_text().strip()
        if not text:
            return
        if looks_like_url(text):
            self._queue = []
            self.open_url(text)
            return
        self._results_stack.set_visible_child_name("loading")
        self._side.set_visible_child_name("results")
        self._split.set_show_sidebar(True)
        self._extractor.search(text, self._on_search_done)

    def _on_search_done(self, videos, error):
        self._results.remove_all()
        if error:
            self._show_error(error)
            self._results_stack.set_visible_child_name("empty")
            return
        for video in videos:
            self._results.append(self._make_row(video))
        self._results_stack.set_visible_child_name("list" if videos else "empty")

    def _make_row(self, video, removable=False):
        row = Adw.ActionRow(title=video.title, subtitle=video.channel, use_markup=False, activatable=True, title_lines=2)
        row.video = video
        if removable:
            remove = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text="Retirer des favoris", valign=Gtk.Align.CENTER)
            remove.add_css_class("flat")
            remove.connect("clicked", lambda _b: self._remove_favorite(video.page_url))
            row.add_suffix(remove)
        return row

    def _fill_favorites(self):
        self._favorites_list.remove_all()
        for item in self._favorites.items:
            self._favorites_list.append(self._make_row(Video(item["title"], item["channel"], item["url"]), removable=True))
        self._favorites_stack.set_visible_child_name("list" if self._favorites.items else "empty")

    def _remove_favorite(self, url):
        self._favorites.remove(url)
        self._fill_favorites()
        self._sync_star()

    def _on_star_toggled(self, button):
        if self._current is None:
            return
        if button.get_active():
            self._favorites.add(self._current.title, self._current.channel, self._current.page_url)
        else:
            self._favorites.remove(self._current.page_url)
        self._fill_favorites()
        self._sync_star()

    def _sync_star(self):
        starred = self._current is not None and self._favorites.contains(self._current.page_url)
        with self._star.handler_block(self._star_id):
            self._star.set_active(starred)
        self._star.set_icon_name("starred-symbolic" if starred else "non-starred-symbolic")
        self._star.set_tooltip_text("Retirer des favoris" if starred else "Ajouter aux favoris")
        self._star.set_sensitive(self._current is not None)

    def _on_row_activated(self, box, row):
        self._queue = [r.video for r in box]
        if self._split.get_collapsed():
            self._split.set_show_sidebar(False)
        self._open(row.video)

    def _queue_index(self):
        url = self._current.page_url if self._current else None
        return next((i for i, v in enumerate(self._queue) if v.page_url == url), -1)

    # Lecture ---------------------------------------------------------------------------------------------------------

    def _open(self, video, start_at=0.0):
        self._player.stop()
        self._current = video
        self._start_at = start_at
        self._title.set_text(video.title or "Chargement…")
        self._channel.set_text(video.channel)
        self._show_stage("curtain" if self._curtain_button.get_active() else "video")
        self._spinner.set_visible(True)
        self._extractor.resolve(video.page_url, self._on_resolved, audio_only=self._curtain_button.get_active())

    def _on_resolved(self, video, error):
        if error:
            self._spinner.set_visible(False)
            self._show_error(error)
            return
        video.page_url = self._current.page_url
        self._current = video
        self._title.set_text(video.title)
        self._channel.set_text(video.channel + (" · En direct" if video.is_live else ""))
        self._curtain_page.set_description(GLib.markup_escape_text(video.title))
        self._duration = video.duration
        self._sync_star()
        self._sync_actions()
        self._mpris.new_track()
        self._covers.fetch(video.id, lambda uri, v=video: self._on_cover(v, uri))
        self._audio_only_stream = self._curtain_button.get_active()
        self._player.open(video.stream_url, video.headers, audio_only=self._audio_only_stream, start_at=self._start_at)

    def _on_cover(self, video, uri):
        if video is self._current:
            video.thumbnail = uri
            self._mpris.changed("Metadata")

    def _on_curtain_toggled(self, button):
        curtain = button.get_active()
        if self._current is None or not self.has_media:
            return
        if not curtain and self._audio_only_stream:
            resume = 0.0 if self._current.is_live else self._position
            self._open(self._current, start_at=resume)
            return
        self._player.set_video_enabled(not curtain)
        self._show_stage("curtain" if curtain else "video")

    def _show_error(self, error):
        text = "\n\n".join(part for part in (error.advice, error.details) if part)
        self._show_status("dialog-warning-symbolic", str(error), text)

    def _show_status(self, icon, title, description, replay=False):
        self._status.set_icon_name(icon)
        self._status.set_title(title)
        self._status.set_description(GLib.markup_escape_text(description))
        self._replay.set_visible(replay)
        self._show_stage("status")

    def _on_player_error(self, _player, message, debug):
        self._spinner.set_visible(False)
        self._show_status("dialog-warning-symbolic", "Lecture impossible", message, replay=self._current is not None)
        if debug:
            print(debug, flush=True)

    def _on_ended(self, _player):
        if self._continuous.get_active() and self.can_next:
            self.next()
            return
        self._show_status("object-select-symbolic", "Lecture terminée", self._current.title if self._current else "", replay=True)

    def _on_state_changed(self, _player, playing):
        self._play_button.set_icon_name("media-playback-pause-symbolic" if playing else "media-playback-start-symbolic")
        self._play_button.set_tooltip_text("Pause" if playing else "Lecture")
        self._sync_actions()
        self._mpris.changed("PlaybackStatus")

    def _show_stage(self, name):
        self._stage.set_visible_child_name(name)
        self._sync_actions()

    def _sync_actions(self):
        self.lookup_action("play-pause").set_enabled(self._current is not None)
        self.lookup_action("stop").set_enabled(self.has_media)
        self.lookup_action("send-to-grabber").set_enabled(self._current is not None and bool(self._current.page_url))
        self.lookup_action("next").set_enabled(self.can_next)
        self.lookup_action("previous").set_enabled(self.can_previous or self.can_seek)

    def _on_buffering(self, _player, percent):
        self._spinner.set_visible(percent < 100)

    def _on_position(self, _player, position, duration):
        if position > 0:
            self._spinner.set_visible(False)
        self._position = position
        if duration > 0:
            self._duration = duration
        self._progress.set_sensitive(self.can_seek)
        self._progress.set_range(0, max(self._duration, 1))
        self._progress.set_value(position)
        total = f" / {_format_time(self._duration)}" if self._duration > 0 else ""
        self._time.set_text(_format_time(position) + total)

    def _on_progress_change(self, _scale, _scroll, value):
        self.seek_to(value)
        return False

    def _on_volume_changed(self, scale):
        self._player.volume = scale.get_value()
        if self._player.muted:
            self._player.muted = False
        self._sync_volume_icon()
        self._mpris.changed("Volume")

    def _on_mute_clicked(self, _button):
        self._player.muted = not self._player.muted
        self._sync_volume_icon()
        self._mpris.changed("Volume")

    def _sync_volume_icon(self):
        value = self._volume_scale.get_value()
        muted = self._player.muted
        name = "muted" if muted or value == 0 else "low" if value < 0.34 else "medium" if value < 0.67 else "high"
        self._volume_icon.set_icon_name(f"audio-volume-{name}-symbolic")
        self._volume_icon.set_tooltip_text("Rétablir le son" if muted else "Couper le son")

    # Fenêtre ---------------------------------------------------------------------------------------------------------

    def _on_key_pressed(self, _ctrl, keyval, _code, state):
        if keyval != Gdk.KEY_space or state & Gtk.accelerator_get_default_mod_mask():
            return False
        if isinstance(self.get_focus(), Gtk.Text):
            return False
        self.play_pause()
        return True

    def _toggle_fullscreen(self, *_args):
        if self.is_fullscreen():
            self.unfullscreen()
        else:
            self.fullscreen()

    def _on_fullscreened(self, *_args):
        full = self.is_fullscreen()
        self._toolbar.set_reveal_top_bars(not full)
        if full:
            self._split.set_show_sidebar(False)

    def _on_video_pressed(self, gesture, n_press, _x, _y):
        if n_press == 2:
            self._toggle_fullscreen()
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)

    def _on_close_request(self, _window):
        self._extractor.shutdown()
        self._covers.cancel()
        self._mpris.destroy()
        for obj, handler in self._handlers:
            obj.disconnect(handler)
        self._player.shutdown()
        return False
