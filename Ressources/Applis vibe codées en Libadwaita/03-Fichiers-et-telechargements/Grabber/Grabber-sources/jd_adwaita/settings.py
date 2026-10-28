from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gio, GLib, Gtk

from . import ytdlp
from .domains import normalize_domain_list
from .maintenance import human_size, logs_size, tidy_logs
from .ui import icon_button


def open_settings(window: Any, *_args: Any) -> None:
    dialog = Adw.Window(
        transient_for=window,
        modal=True,
        title="Réglages minimaux",
        default_width=620,
        default_height=700,
    )
    toolbar = Adw.ToolbarView()
    header = Adw.HeaderBar()
    cancel = Gtk.Button(label="Annuler")
    cancel.connect("clicked", lambda *_: dialog.close())
    header.pack_start(cancel)
    save = Gtk.Button(label="Enregistrer")
    header.pack_end(save)
    toolbar.add_top_bar(header)

    page = Adw.PreferencesPage()
    engine_group = Adw.PreferencesGroup(title="Moteur JDownloader")
    jar_row = Adw.ActionRow(title="JDownloader.jar", subtitle="Chemin du moteur à lancer directement")
    jar_entry = Gtk.Entry(hexpand=True)
    jar_entry.set_text(window.config.jar_path)
    jar_entry.set_placeholder_text("/chemin/vers/JDownloader.jar")
    jar_row.add_suffix(jar_entry)
    choose_jar = Gtk.Button(label="Choisir…")
    choose_jar.set_valign(Gtk.Align.CENTER)
    jar_row.add_suffix(choose_jar)
    engine_group.add(jar_row)

    java_row = Adw.ActionRow(title="Java (facultatif)", subtitle="Laisser vide pour utiliser java du PATH")
    java_entry = Gtk.Entry(hexpand=True)
    java_entry.set_text(window.config.java_path)
    java_row.add_suffix(java_entry)
    engine_group.add(java_row)

    update_row = Adw.ActionRow(
        title="Mettre à jour JDownloader",
        subtitle="Utiliser l'outil de mise à jour natif de JDownloader",
    )
    update_button = icon_button("view-refresh-symbolic")
    update_button.set_tooltip_text("Rechercher et installer les mises à jour")
    update_button.set_valign(Gtk.Align.CENTER)
    update_button.connect("clicked", window._request_jdownloader_update)
    update_row.add_suffix(update_button)
    engine_group.add(update_row)
    page.add(engine_group)

    def runtime_dir() -> Path | None:
        jar = window.backend.find_jar()
        return jar.parent if jar is not None else None


    def refresh_log_subtitle(message: str | None = None) -> None:
        directory = runtime_dir()
        if directory is None:
            logs_row.set_subtitle("Chemin du moteur JDownloader inconnu")
            return
        size = human_size(
            logs_size(directory, window.backend.cache_log_path, ytdlp.log_directory())
        )
        base = f"{size} occupés par les fichiers de journal"
        logs_row.set_subtitle(f"{message} — {base}" if message else base)


    def purge_logs(*_args: Any) -> None:
        directory = runtime_dir()
        if directory is None:
            window._show_error(RuntimeError("Chemin du moteur JDownloader inconnu."))
            return
        logs_row.set_subtitle("Vidage en cours…")

        def work() -> tuple[int, int]:
            return tidy_logs(directory, window.backend.cache_log_path, ytdlp.log_directory())

        def done(result: Any = None) -> None:
            emptied, freed = result if result else (0, 0)
            refresh_log_subtitle(f"{emptied} fichier(s) vidé(s), {human_size(freed)} libérés")

        window._run_thread(work, done, window._show_error)


    def open_account_manager(*_args: Any) -> None:
        jar = window.backend.find_jar()
        if jar is None:
            window._show_error(RuntimeError("JDownloader.jar est introuvable."))
            return
        accounts_row.set_subtitle("Arrêt du moteur, puis ouverture de JDownloader…")

        def work() -> str:
            window.backend.stop(window.api)
            try:
                subprocess.run(
                    [
                        window.backend.java_binary(),
                        "-Djava.awt.headless=false",
                        "-jar",
                        str(jar),
                        "-norestart",
                    ],
                    cwd=str(jar.parent),
                    check=False,
                )
            finally:
                window.backend.start_and_wait(window.api, timeout=240.0)
            return "Compte saisi dans JDownloader : il est utilisé immédiatement"

        def done(message: Any = None) -> None:
            accounts_row.set_subtitle(str(message or "Compte enregistré"))

        window._run_thread(work, done, window._show_error)


    accounts_group = Adw.PreferencesGroup(
        title="Comptes",
        description=(
            "Grabber ne touche pas au stockage chiffré de JDownloader : les identifiants "
            "se saisissent dans la fenêtre de JDownloader, ouverte ici sur le même dossier "
            "de travail."
        ),
    )
    accounts_row = Adw.ActionRow(
        title="Enregistrer un compte hébergeur",
        subtitle="Arrête le moteur, ouvre JDownloader, puis le redémarre",
    )
    accounts_button = Gtk.Button(label="Ouvrir")
    accounts_button.set_valign(Gtk.Align.CENTER)
    accounts_button.set_tooltip_text("Gérer les comptes dans JDownloader lui-même")
    accounts_button.connect("clicked", open_account_manager)
    accounts_row.add_suffix(accounts_button)
    accounts_group.add(accounts_row)

    logs_group = Adw.PreferencesGroup(title="Journaux")
    logs_row = Adw.ActionRow(title="Journaux de JDownloader", subtitle="Mesure en cours…")
    logs_button = Gtk.Button(label="Vider")
    logs_button.set_valign(Gtk.Align.CENTER)
    logs_button.set_tooltip_text("Vider les journaux sans interrompre les téléchargements")
    logs_button.connect("clicked", purge_logs)
    logs_row.add_suffix(logs_button)
    logs_group.add(logs_row)
    refresh_log_subtitle()


    download_group = Adw.PreferencesGroup(title="Téléchargements")
    close_warning_row = Adw.SwitchRow(
        title="Avertir avant de quitter pendant un téléchargement",
        subtitle="Permet de reprendre les téléchargements au prochain lancement",
    )
    close_warning_row.set_active(window.config.close_warning_enabled)
    download_group.add(close_warning_row)
    folder_row = Adw.ActionRow(title="Dossier de destination")
    folder_entry = Gtk.Entry(hexpand=True)
    folder_entry.set_text(window.config.download_dir)
    folder_row.add_suffix(folder_entry)
    choose_folder = Gtk.Button(label="Choisir…")
    choose_folder.set_valign(Gtk.Align.CENTER)
    folder_row.add_suffix(choose_folder)
    download_group.add(folder_row)
    simultaneous_row = Adw.ComboRow(
        title="Téléchargements simultanés",
        subtitle="Nombre maximal de fichiers téléchargés en même temps",
    )
    simultaneous_model = Gtk.StringList.new(
        [str(value) for value in window.SIMULTANEOUS_DOWNLOAD_OPTIONS]
    )
    simultaneous_row.set_model(simultaneous_model)
    simultaneous_row.set_selected(
        window.SIMULTANEOUS_DOWNLOAD_OPTIONS.index(
            window.config.max_simultaneous_downloads
        )
        if window.config.max_simultaneous_downloads
        in window.SIMULTANEOUS_DOWNLOAD_OPTIONS
        else 2
    )
    download_group.add(simultaneous_row)

    video_group = Adw.PreferencesGroup(title="Déplacement automatique des vidéos")
    auto_move_row = Adw.SwitchRow(
        title="Déplacer automatiquement les vidéos terminées",
        subtitle="Déplacer uniquement les vidéos téléchargées par JDownloader",
    )
    auto_move_row.set_active(window.config.auto_move_videos_enabled)
    video_group.add(auto_move_row)

    source_row = Adw.ActionRow(title="Dossier source des vidéos")
    source_entry = Gtk.Entry(hexpand=True)
    source_entry.set_text(window.config.video_source_dir)
    source_row.add_suffix(source_entry)
    choose_source = Gtk.Button(label="Choisir…")
    choose_source.set_valign(Gtk.Align.CENTER)
    source_row.add_suffix(choose_source)
    video_group.add(source_row)

    destination_row = Adw.ActionRow(title="Dossier de destination")
    destination_entry = Gtk.Entry(hexpand=True)
    destination_entry.set_text(window.config.video_destination_dir)
    destination_row.add_suffix(destination_entry)
    choose_destination = Gtk.Button(label="Choisir…")
    choose_destination.set_valign(Gtk.Align.CENTER)
    destination_row.add_suffix(choose_destination)
    video_group.add(destination_row)

    remove_empty_row = Adw.SwitchRow(
        title="Supprimer les dossiers parents devenus vides",
        subtitle="Suppression directe, sans corbeille ni confirmation ; le dossier source est conservé",
    )
    remove_empty_row.set_active(window.config.remove_empty_video_folders)
    video_group.add(remove_empty_row)
    grabber_group = Adw.PreferencesGroup(
        title="Grabber",
        description=(
            "Le filtre est appliqué aux liens affichés. Un domaine autorise aussi "
            "ses sous-domaines."
        ),
    )
    clipboard_row = Adw.SwitchRow(
        title="Scanner automatiquement le presse-papiers",
        subtitle="Coller une URL copiée, ouvrir le Grabber et lancer l’analyse",
    )
    clipboard_row.set_active(window.config.clipboard_scan_enabled)
    grabber_group.add(clipboard_row)

    focus_row = Adw.SwitchRow(
        title="Mettre Grabber au premier plan à chaque envoi",
        subtitle="Désactivé : Grabber ne prend le focus qu’au premier lancement",
    )
    focus_row.set_active(window.config.focus_on_delivery)
    grabber_group.add(focus_row)

    whitelist_switch = Adw.SwitchRow(
        title="Limiter les liens aux domaines autorisés",
        subtitle="Désactivé : tous les liens analysés restent visibles",
    )
    whitelist_switch.set_active(window.config.grabber_whitelist_enabled)
    grabber_group.add(whitelist_switch)

    whitelist_row = Adw.ActionRow(
        title="Domaines autorisés",
        subtitle="Un domaine par ligne — youtube.com inclut ses sous-domaines",
    )
    whitelist_buffer = Gtk.TextBuffer()
    whitelist_buffer.set_text("\n".join(window.config.grabber_domain_whitelist))
    whitelist_view = Gtk.TextView(buffer=whitelist_buffer)
    whitelist_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
    whitelist_view.set_vexpand(True)
    whitelist_view.set_monospace(True)
    whitelist_view.set_tooltip_text(
        "Exemples : youtube.com, *.example.org, example.net"
    )
    whitelist_scroll = Gtk.ScrolledWindow()
    whitelist_scroll.set_min_content_width(280)
    whitelist_scroll.set_min_content_height(120)
    whitelist_scroll.set_max_content_height(180)
    whitelist_scroll.set_child(whitelist_view)
    whitelist_row.add_suffix(whitelist_scroll)
    grabber_group.add(whitelist_row)
    # Ordre voulu de la page : Moteur, Grabber (filtres), Comptes, Journaux,
    # Téléchargements, Vidéos, yt-dlp.
    page.add(grabber_group)
    page.add(accounts_group)
    page.add(logs_group)
    page.add(download_group)
    page.add(video_group)

    def on_jar_chosen(file_dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            selected = file_dialog.open_finish(result)
        except GLib.Error:
            return
        if selected is not None:
            jar_entry.set_text(selected.get_path() or "")

    def choose_jar_file(*_args: Any) -> None:
        chooser = Gtk.FileDialog(title="Choisir JDownloader.jar")
        chooser.open(dialog, None, on_jar_chosen)

    def on_folder_chosen(file_dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            selected = file_dialog.select_folder_finish(result)
        except GLib.Error:
            return
        if selected is not None:
            folder_entry.set_text(selected.get_path() or "")

    def choose_folder_file(*_args: Any) -> None:
        chooser = Gtk.FileDialog(title="Choisir le dossier de destination")
        chooser.select_folder(dialog, None, on_folder_chosen)

    def on_source_chosen(file_dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            selected = file_dialog.select_folder_finish(result)
        except GLib.Error:
            return
        if selected is not None:
            source_entry.set_text(selected.get_path() or "")

    def choose_source_folder(*_args: Any) -> None:
        chooser = Gtk.FileDialog(title="Choisir le dossier source des vidéos")
        chooser.select_folder(dialog, None, on_source_chosen)

    def on_destination_chosen(file_dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            selected = file_dialog.select_folder_finish(result)
        except GLib.Error:
            return
        if selected is not None:
            destination_entry.set_text(selected.get_path() or "")

    def choose_destination_folder(*_args: Any) -> None:
        chooser = Gtk.FileDialog(title="Choisir le dossier de destination des vidéos")
        chooser.select_folder(dialog, None, on_destination_chosen)

    choose_jar.connect("clicked", choose_jar_file)
    choose_folder.connect("clicked", choose_folder_file)
    choose_source.connect("clicked", choose_source_folder)
    choose_destination.connect("clicked", choose_destination_folder)

    ytdlp_group = Adw.PreferencesGroup(
        title="Liens confiés à yt-dlp",
        description=(
            "Certains sites ne peuvent pas être téléchargés par JDownloader : leurs liens "
            "partent vers yt-dlp, avec les cookies du navigateur. Le choix des sites "
            "t’appartient — la liste est vide par défaut et aucun site n’est inscrit dans "
            "le programme. Un domaine autorise aussi ses sous-domaines."
        ),
    )
    ytdlp_row = Adw.ActionRow(
        title="Domaines",
        subtitle="Un par ligne, par exemple : exemple.com",
    )
    ytdlp_buffer = Gtk.TextBuffer()
    ytdlp_buffer.set_text("\n".join(window.config.ytdlp_domains))
    ytdlp_view = Gtk.TextView(buffer=ytdlp_buffer)
    ytdlp_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
    ytdlp_view.set_vexpand(True)
    ytdlp_view.set_monospace(True)
    ytdlp_view.set_tooltip_text(
        "Ces domaines restent dans ta configuration locale, "
        "~/.config/jd-adwaita/config.json : ils ne partent ni dans le dépôt ni dans l’AppImage."
    )
    ytdlp_scroll = Gtk.ScrolledWindow()
    ytdlp_scroll.set_min_content_width(280)
    ytdlp_scroll.set_min_content_height(90)
    ytdlp_scroll.set_max_content_height(160)
    ytdlp_scroll.set_child(ytdlp_view)
    ytdlp_row.add_suffix(ytdlp_scroll)
    ytdlp_group.add(ytdlp_row)
    page.add(ytdlp_group)


    def save_settings(*_args: Any) -> None:
        source_path = Path(source_entry.get_text()).expanduser().resolve()
        destination_path = Path(destination_entry.get_text()).expanduser().resolve()
        if source_path == destination_path or source_path in destination_path.parents:
            window._show_error(RuntimeError(
                "Le dossier de destination des vidéos doit être différent du dossier source et ne pas se trouver à l’intérieur de celui-ci."
            ))
            return
        window.config.jar_path = jar_entry.get_text()
        window.config.java_path = java_entry.get_text()
        window.config.download_dir = folder_entry.get_text()
        window.config.close_warning_enabled = close_warning_row.get_active()
        window.config.auto_move_videos_enabled = auto_move_row.get_active()
        window.config.video_source_dir = source_entry.get_text()
        window.config.video_destination_dir = destination_entry.get_text()
        window.config.remove_empty_video_folders = remove_empty_row.get_active()
        window.config.clipboard_scan_enabled = clipboard_row.get_active()
        window.config.focus_on_delivery = focus_row.get_active()
        window.config.grabber_whitelist_enabled = whitelist_switch.get_active()
        start, end = whitelist_buffer.get_bounds()
        window.config.grabber_domain_whitelist = normalize_domain_list(
            whitelist_buffer.get_text(start, end, False).splitlines()
        )
        ytdlp_start, ytdlp_end = ytdlp_buffer.get_bounds()
        window.config.ytdlp_domains = normalize_domain_list(
            ytdlp_buffer.get_text(ytdlp_start, ytdlp_end, False).splitlines()
        )
        simultaneous_index = simultaneous_row.get_selected()
        if 0 <= simultaneous_index < len(window.SIMULTANEOUS_DOWNLOAD_OPTIONS):
            window.config.max_simultaneous_downloads = (
                window.SIMULTANEOUS_DOWNLOAD_OPTIONS[simultaneous_index]
            )
        try:
            window.config.save()
        except OSError as exc:
            window._show_error(exc)
            return
        if window.config.clipboard_scan_enabled:
            window._clipboard_monitor.start()
        else:
            window._clipboard_monitor.stop()
        window._sync_grabber_option_switches()
        window._populate_grabber(window._grabber_items)
        dialog.close()
        if window._known_online:
            window._run_thread(
                window._apply_download_preferences,
                window._on_preferences_applied,
                window._show_error,
            )
        else:
            window._refresh_now()

    save.connect("clicked", save_settings)
    toolbar.set_content(page)
    dialog.set_content(toolbar)
    dialog.present()


def request_jdownloader_update(window: Any, *_args: Any) -> None:
    dialog = Adw.MessageDialog(
        transient_for=window,
        heading="Mettre à jour JDownloader ?",
        body=(
            "JDownloader sera arrêté puis relancé avec son outil de mise à jour natif. "
            "Les téléchargements en cours seront momentanément interrompus."
        ),
    )
    dialog.add_response("cancel", "Annuler")
    dialog.add_response("update", "Mettre à jour")
    dialog.set_default_response("update")
    dialog.set_close_response("cancel")

    def confirm_update(*_confirm_args: Any) -> None:
        dialog.close()
        window._set_starting()

        def work() -> str:
            return window.backend.update(window.api)

        def done(message: str) -> None:
            window.engine_hint.set_text(message)
            window._refresh_now()

        window._run_thread(work, done, window._show_error)

    dialog.connect(
        "response",
        lambda _dialog, response: (
            confirm_update() if response == "update" else None
        ),
    )
    dialog.present()
