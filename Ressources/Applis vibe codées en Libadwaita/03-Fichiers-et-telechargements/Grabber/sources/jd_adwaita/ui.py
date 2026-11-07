from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import gi

gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Pango


ICON_BUTTON_SIZE = 28
_css_installed = False


def install_css() -> None:
    global _css_installed
    if _css_installed:
        return
    _css_installed = True
    provider = Gtk.CssProvider()
    provider.load_from_data(
        b"""
        .connection-indicator.offline { opacity: 0.68; }
        button.icon-action,
        button.icon-action.circular,
        button.icon-action.circular.suggested-action,
        button.icon-action.circular.destructive-action,
        button.icon-action.circular.suggested-action {
            min-width: 28px;
            min-height: 28px;
            padding: 0;
            margin: 0;
            border-radius: 999px;
        }
        button.icon-action > image {
            min-width: 16px;
            min-height: 16px;
        }
        button.icon-action {
            background-image: none;
            background-color: transparent;
            box-shadow: none;
        }
        button.icon-action:hover {
            background-color: alpha(@window_fg_color, 0.10);
        }
        menubutton.icon-action {
            min-width: 28px;
            min-height: 28px;
            padding: 0;
            margin: 0;
            border-radius: 999px;
            background-image: none;
            background-color: transparent;
            box-shadow: none;
        }
        menubutton.icon-action:hover {
            background-color: alpha(@window_fg_color, 0.10);
        }
        button.icon-action.suggested-action,
        button.icon-action.destructive-action {
            color: @window_fg_color;
        }
        .download-complete { color: @window_fg_color; }
        .download-done { opacity: 0.62; }
        checkbutton.selection-mode > check {
            border-radius: 999px;
            min-width: 18px;
            min-height: 18px;
        }
        checkbutton.selection-mode:checked > check {
            border-radius: 999px;
        }
        .download-status { font-weight: 600; }
        .muted { opacity: 0.72; }
        .host-badge {
            background: alpha(@window_fg_color, 0.06);
            border-radius: 8px;
            padding: 4px 6px;
            min-width: 104px;
            min-height: 60px;
        }
        .host-favicon {
            min-width: 20px;
            min-height: 20px;
        }
        .host-favicon-frame {
            min-width: 24px;
            min-height: 24px;
        }
        .host-label { font-weight: 600; min-width: 90px; }
        .privacy-shield {
            background-color: @window_bg_color;
        }
        .privacy-title { font-weight: 700; }
        .privacy-icon {
            min-width: 128px;
            min-height: 128px;
        }
        """
    )
    display = Gdk.Display.get_default()
    if display is not None:
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )


def icon_button(icon_name: str) -> Gtk.Button:
    button = Gtk.Button.new_from_icon_name(icon_name)
    button.add_css_class("circular")
    button.add_css_class("icon-action")
    button.set_size_request(ICON_BUTTON_SIZE, ICON_BUTTON_SIZE)
    button.set_halign(Gtk.Align.CENTER)
    button.set_valign(Gtk.Align.CENTER)
    button.set_hexpand(False)
    button.set_vexpand(False)
    icon = button.get_child()
    if isinstance(icon, Gtk.Image):
        icon.set_pixel_size(16)
    return button


def trash_button() -> Gtk.Button:
    button = icon_button("user-trash-symbolic")
    button.add_css_class("destructive-action")
    return button


def button_with_icon(label: str, icon_name: str) -> Gtk.Button:
    button = Gtk.Button()
    button.set_valign(Gtk.Align.CENTER)
    button_content_type = getattr(Adw, "ButtonContent", None)
    if button_content_type is not None:
        content = button_content_type()
        content.set_label(label)
        content.set_icon_name(icon_name)
    else:
        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        content.append(Gtk.Image.new_from_icon_name(icon_name))
        content.append(Gtk.Label(label=label))
    button.set_child(content)
    return button


def application_icon(size: int = 128) -> Gtk.Image:
    """Load the bundled Grabber icon, with a themed-icon fallback."""

    icon_path = os.environ.get("JD_ADWAITA_ICON_PATH", "")
    icon: Gtk.Image | None = None
    if icon_path and Path(icon_path).is_file():
        try:
            icon = Gtk.Image.new_from_file(icon_path)
        except (GLib.Error, TypeError, ValueError):
            icon = None
    if icon is None:
        icon = Gtk.Image.new_from_icon_name("com.ogu.Grabber")
    icon.set_pixel_size(size)
    icon.set_size_request(size, size)
    icon.set_halign(Gtk.Align.CENTER)
    icon.set_valign(Gtk.Align.CENTER)
    icon.add_css_class("privacy-icon")
    return icon


def build_privacy_shield(window: Any) -> None:
    shield = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    shield.add_css_class("privacy-shield")
    shield.set_hexpand(True)
    shield.set_vexpand(True)

    top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    top_bar.set_margin_top(10)
    top_bar.set_margin_end(10)
    top_bar.append(Gtk.Box(hexpand=True))
    reveal = icon_button("view-reveal-symbolic")
    reveal.set_tooltip_text("Afficher l’interface")
    reveal.connect("clicked", window._toggle_privacy_mode)
    top_bar.append(reveal)
    shield.append(top_bar)

    center = Gtk.CenterBox()
    center.set_hexpand(True)
    center.set_vexpand(True)
    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
    content.set_halign(Gtk.Align.CENTER)
    content.set_valign(Gtk.Align.CENTER)
    content.append(application_icon(128))

    title = Gtk.Label(label="Grabber")
    title.add_css_class("privacy-title")
    title.set_halign(Gtk.Align.CENTER)
    content.append(title)

    center.set_center_widget(content)
    shield.append(center)
    window._privacy_overlay.add_overlay(shield)
    window._privacy_panel = shield
    shield.set_visible(False)


def build_download_page(window: Any) -> Gtk.Widget:
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    page.set_margin_top(16)
    page.set_margin_bottom(12)
    page.set_margin_start(16)
    page.set_margin_end(16)

    window.download_list = Gtk.ListBox()
    window.download_list.set_selection_mode(Gtk.SelectionMode.NONE)
    window.download_list.set_show_separators(True)
    empty = Gtk.Label(label="Aucun téléchargement dans la file")
    empty.set_margin_top(32)
    empty.set_margin_bottom(32)
    empty.add_css_class("muted")
    window.download_list.set_placeholder(empty)
    scroll = Gtk.ScrolledWindow()
    scroll.set_vexpand(True)
    scroll.set_child(window.download_list)
    page.append(scroll)

    footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    footer.set_margin_start(4)
    window.engine_hint = Gtk.Label(label="")
    window.engine_hint.set_xalign(0)
    window.engine_hint.add_css_class("muted")
    footer.append(window.engine_hint)
    footer.append(Gtk.Box(hexpand=True))
    window.global_progress = Gtk.ProgressBar()
    window.global_progress.set_size_request(140, -1)
    window.global_progress.set_valign(Gtk.Align.CENTER)
    window.global_progress.set_tooltip_text("Progression globale des téléchargements")
    footer.append(window.global_progress)
    window.global_progress_label = Gtk.Label(label="")
    window.global_progress_label.add_css_class("numeric")
    window.global_progress_label.add_css_class("muted")
    footer.append(window.global_progress_label)
    window.global_activity_label = Gtk.Label(label="")
    window.global_activity_label.add_css_class("numeric")
    window.global_activity_label.add_css_class("muted")
    window.global_activity_label.set_tooltip_text("Vitesse globale et estimation du temps restant")
    footer.append(window.global_activity_label)
    window.delete_selected_downloads_button = icon_button("user-trash-symbolic")
    window.delete_selected_downloads_button.add_css_class("destructive-action")
    window.delete_selected_downloads_button.set_tooltip_text(
        "Supprimer définitivement les fichiers sélectionnés et leurs entrées JDownloader"
    )
    window.delete_selected_downloads_button.set_sensitive(False)
    window.delete_selected_downloads_button.connect("clicked", window._delete_selected_downloads)
    footer.append(window.delete_selected_downloads_button)
    clear_finished = icon_button("edit-clear-all-symbolic")
    clear_finished.set_tooltip_text("Retirer de la liste les téléchargements terminés, sans supprimer les fichiers")
    clear_finished.connect("clicked", window._remove_finished_downloads)
    footer.append(clear_finished)
    footer.append(window.connection_button)
    page.append(footer)
    return page


def build_grabber_page(window: Any) -> Gtk.Widget:
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    page.set_margin_top(16)
    page.set_margin_bottom(12)
    page.set_margin_start(16)
    page.set_margin_end(16)

    scan_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    window.grabber_url_entry = Gtk.Entry(hexpand=True)
    window.grabber_url_entry.set_placeholder_text("URL à scanner dans le Grabber…")
    window.grabber_url_entry.set_tooltip_text("Coller une URL puis lancer l’analyse avec Entrée")
    window.grabber_url_entry.connect("activate", window._scan_grabber_url)
    window.grabber_url_entry.connect("changed", window._on_grabber_entry_changed)
    scan_row.append(window.grabber_url_entry)
    window.grabber_scan_button = icon_button("system-search-symbolic")
    # L'icône d'origine est conservée : pendant une analyse, le bouton
    # l'échange contre un spinner, puis la récupère.
    window.scan_button_icon = window.grabber_scan_button.get_child()
    window.grabber_scan_button.set_tooltip_text("Envoyer cette URL au Grabber")
    window.grabber_scan_button.connect("clicked", window._scan_grabber_url)
    scan_row.append(window.grabber_scan_button)
    page.append(scan_row)

    controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    window.grabber_filter_buttons = []
    previous_filter_button = None
    for option_label, filter_key in window.GRABBER_FILTERS:
        filter_button = Gtk.ToggleButton(label=option_label)
        if previous_filter_button is not None:
            filter_button.set_group(previous_filter_button)
        filter_button.set_active(filter_key == window._grabber_filter)
        filter_button.connect(
            "toggled",
            lambda button, key=filter_key: window._on_grabber_filter_toggle(button, key),
        )
        controls.append(filter_button)
        window.grabber_filter_buttons.append(filter_button)
        previous_filter_button = filter_button
    controls.append(Gtk.Box(hexpand=True))
    page.append(controls)

    automation = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    clipboard_icon = Gtk.Image.new_from_icon_name("edit-paste-symbolic")
    clipboard_icon.set_tooltip_text("Scanner automatiquement les URL copiées")
    automation.append(clipboard_icon)
    window.grabber_clipboard_switch = Gtk.Switch()
    window.grabber_clipboard_switch.set_active(window.config.clipboard_scan_enabled)
    window.grabber_clipboard_switch.set_valign(Gtk.Align.CENTER)
    window.grabber_clipboard_switch.set_tooltip_text(
        "Coller et analyser automatiquement les URL copiées"
    )
    window.grabber_clipboard_switch.connect(
        "notify::active", window._on_clipboard_switch_changed
    )
    automation.append(window.grabber_clipboard_switch)

    whitelist_icon = Gtk.Image.new_from_icon_name("security-high-symbolic")
    whitelist_icon.set_tooltip_text("Limiter aux domaines autorisés")
    automation.append(whitelist_icon)
    window.grabber_whitelist_switch = Gtk.Switch()
    window.grabber_whitelist_switch.set_active(
        window.config.grabber_whitelist_enabled
    )
    window.grabber_whitelist_switch.set_valign(Gtk.Align.CENTER)
    window.grabber_whitelist_switch.set_tooltip_text(
        "N’afficher que les liens provenant des domaines autorisés"
    )
    window.grabber_whitelist_switch.connect(
        "notify::active", window._on_whitelist_switch_changed
    )
    automation.append(window.grabber_whitelist_switch)

    window.grabber_domains_button = icon_button("web-browser-symbolic")
    window.grabber_domains_button.set_tooltip_text("Modifier les domaines autorisés")
    window.grabber_domains_button.connect("clicked", window._open_settings)
    automation.append(window.grabber_domains_button)
    automation.append(Gtk.Box(hexpand=True))
    page.append(automation)

    window.grabber_list = Gtk.ListBox()
    window.grabber_list.set_selection_mode(Gtk.SelectionMode.NONE)
    window.grabber_list.set_show_separators(True)
    window.grabber_empty = Gtk.Label(label="Aucun lien analysé")
    window.grabber_empty.set_margin_top(32)
    window.grabber_empty.set_margin_bottom(32)
    window.grabber_empty.add_css_class("muted")
    window.grabber_list.set_placeholder(window.grabber_empty)
    scroll = Gtk.ScrolledWindow()
    scroll.set_vexpand(True)
    scroll.set_child(window.grabber_list)
    page.append(scroll)

    actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    clear = icon_button("edit-clear-all-symbolic")
    clear.set_tooltip_text("Vider la liste des liens analysés")
    clear.connect("clicked", window._clear_grabber)
    actions.append(clear)
    window.grabber_select_all_button = icon_button("edit-select-all-symbolic")
    window.grabber_select_all_button.set_tooltip_text("Sélectionner tous les liens affichés")
    window.grabber_select_all_button.set_sensitive(False)
    window.grabber_select_all_button.connect(
        "clicked", window._select_all_grabber
    )
    actions.append(window.grabber_select_all_button)
    actions.append(Gtk.Box(hexpand=True))
    confirm = icon_button("list-add-symbolic")
    confirm.set_tooltip_text("Ajouter les liens sélectionnés et démarrer")
    confirm.connect("clicked", window._confirm_grabber)
    actions.append(confirm)
    # Keep the engine status alongside the bottom action icons on this page too.
    window.grabber_connection_button = icon_button("network-offline-symbolic")
    window.grabber_connection_button.add_css_class("connection-indicator")
    window.grabber_connection_button.add_css_class("offline")
    window.grabber_connection_button.set_tooltip_text("Déconnecté")
    window.grabber_connection_button.get_child().set_tooltip_text("Déconnecté")
    actions.append(window.grabber_connection_button)
    page.append(actions)
    return page


def build_window(window: Any) -> None:
    header = Adw.HeaderBar()
    window.start_button = icon_button("media-playback-start-symbolic")
    window.start_button.set_tooltip_text("Démarrer les téléchargements")
    window.start_button.connect("clicked", window._start_downloads)
    header.pack_start(window.start_button)

    window.stop_button = icon_button("media-playback-stop-symbolic")
    window.stop_button.set_tooltip_text("Arrêter les téléchargements")
    window.stop_button.connect("clicked", window._stop_downloads)
    header.pack_start(window.stop_button)

    # L'indicateur d'attente natif de GNOME : un spinner dans la barre
    # d'en-tête, là où Nautilus, Logiciels ou Builder montrent une activité.
    # Adw.Spinner (libadwaita 1.6+) est le widget officiel ; Gtk.Spinner le
    # remplace sur les vieilles libadwaita. L'emplacement reste réservé pour
    # que la barre ne bouge pas quand le spinner apparaît.
    if hasattr(Adw, "Spinner"):
        window.scan_spinner = Adw.Spinner()
    else:
        window.scan_spinner = Gtk.Spinner()
    window.scan_spinner.set_tooltip_text("Analyse en cours…")
    window.scan_spinner.set_visible(False)
    window.scan_spinner.set_size_request(16, 16)
    header.pack_start(window.scan_spinner)


    window.connection_button = icon_button("network-offline-symbolic")
    window.connection_icon = window.connection_button.get_child()
    window.connection_icon.set_tooltip_text("Déconnecté")
    window.connection_button.set_tooltip_text("Déconnecté")
    window.connection_button.add_css_class("connection-indicator")
    window.connection_button.add_css_class("offline")

    settings_action = Gio.SimpleAction.new("settings", None)
    settings_action.connect("activate", window._open_settings)
    window.add_action(settings_action)
    update_action = Gio.SimpleAction.new("update-jdownloader", None)
    update_action.connect("activate", window._request_jdownloader_update)
    window.add_action(update_action)
    about_action = Gio.SimpleAction.new("about", None)
    about_action.connect("activate", window._show_about)
    window.add_action(about_action)
    main_menu = Gio.Menu()
    main_menu.append("Préférences", "win.settings")
    main_menu.append("Mettre à jour JDownloader", "win.update-jdownloader")
    main_menu.append("À propos de Grabber", "win.about")
    menu_button = Gtk.MenuButton()
    menu_button.set_icon_name("open-menu-symbolic")
    menu_button.set_menu_model(main_menu)
    menu_button.set_tooltip_text("Menu principal")
    menu_button.add_css_class("flat")
    menu_button.add_css_class("icon-action")
    header.pack_end(menu_button)

    window.privacy_button = icon_button("view-conceal-symbolic")
    window.privacy_button.set_tooltip_text("Masquer l’interface")
    window.privacy_button.connect("clicked", window._toggle_privacy_mode)
    header.pack_end(window.privacy_button)

    window.stack = Adw.ViewStack()
    window.stack.set_vexpand(True)
    window.stack.add_titled_with_icon(
        build_download_page(window),
        "downloads",
        "Téléchargements",
        "folder-download-symbolic",
    )
    window.stack.add_titled_with_icon(
        build_grabber_page(window),
        "grabber",
        "Grabber",
        "system-search-symbolic",
    )

    switcher = Adw.ViewSwitcher()
    switcher.set_stack(window.stack)
    switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
    header.set_title_widget(switcher)

    toolbar = Adw.ToolbarView()
    toolbar.add_top_bar(header)
    main_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    main_content.append(window.stack)
    toolbar.set_content(main_content)

    window._privacy_overlay = Gtk.Overlay()
    window._privacy_overlay.set_child(toolbar)
    build_privacy_shield(window)
    # Les toasts se posent au-dessus de tout, y compris du voile de confidentialite.
    window.toast_overlay = Adw.ToastOverlay()
    window.toast_overlay.set_child(window._privacy_overlay)
    window.set_content(window.toast_overlay)
    shortcuts = Gtk.ShortcutController()
    shortcuts.set_scope(Gtk.ShortcutScope.LOCAL)
    for trigger_text, callback in (
        ("<Control>r", window._refresh_now),
        ("<Control>l", lambda: (window.stack.set_visible_child_name("grabber"), window.grabber_url_entry.grab_focus())),
        ("<Control>Return", window._confirm_grabber),
        ("Escape", lambda: window.grabber_url_entry.set_text("")),
    ):
        trigger = Gtk.ShortcutTrigger.parse_string(trigger_text)
        if trigger is not None:
            shortcuts.add_shortcut(Gtk.Shortcut.new(trigger, Gtk.CallbackAction.new(lambda _widget, _args, cb=callback: (cb(), True)[1])))
    window.add_controller(shortcuts)
    # Some GTK versions re-evaluate an overlay child's visibility when the
    # toplevel receives its content.  Privacy mode must never be the startup
    # view, otherwise the normal interface looks like a blank dark window.
    window._privacy_panel.set_visible(False)
    window._set_download_controller_state(False)
