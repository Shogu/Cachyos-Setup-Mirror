#!/usr/bin/env python3
"""Grimoire — a local-file Markdown editor for GNOME."""
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import quote, urlparse
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('GtkSource', '5')
gi.require_version('WebKit', '6.0')
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk, GtkSource, Pango, WebKit
from core import Document, code_block, headings, render, state_dir


def system_font(key, default_size):
    """Family and size (pt) of a GNOME font setting, e.g. 'Adwaita Mono 11'.

    Pango/fontconfig alone would resolve the generic names to DejaVu on some
    systems; GNOME's own settings are what the other GNOME apps follow.
    """
    source = Gio.SettingsSchemaSource.get_default()
    if source is None or source.lookup('org.gnome.desktop.interface', True) is None:
        return '', default_size
    try:
        desc = Pango.FontDescription.from_string(
            Gio.Settings.new('org.gnome.desktop.interface').get_string(key))
    except GLib.Error:
        return '', default_size
    size = desc.get_size() / Pango.SCALE if desc.get_size() > 0 else default_size
    return desc.get_family() or '', size

APP_ID = 'io.github.shogu.Grimoire'
MODES = [('code', 'Code'), ('split', 'Scindé'), ('render', 'Rendu')]
COLOR_SCHEMES = ['system', 'light', 'dark']


def button(icon, tip, callback):
    b = Gtk.Button(icon_name=icon, tooltip_text=tip)
    b.connect('clicked', lambda *_: callback())
    return b


def scroll(child):
    s = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
    s.set_child(child)
    return s


def clear(box):
    if isinstance(box, Gtk.ListBox):
        while row := box.get_row_at_index(0):
            box.remove(row)
        return
    while box.get_first_child():
        box.remove(box.get_first_child())


def boxed_list(*children):
    box = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
    box.add_css_class('boxed-list')
    for child in children:
        box.append(child)
    return box


def settings():
    source = Gio.SettingsSchemaSource.get_default()
    if source is None or source.lookup(APP_ID, True) is None:
        raise SystemExit('Schéma GSettings ' + APP_ID + ' introuvable : réinstallez Grimoire.')
    return Gio.Settings.new(APP_ID)


def import_legacy_preferences(cfg):
    """Move the pre-0.2 preferences.json into GSettings, once."""
    if cfg.get_boolean('legacy-imported'):
        return
    cfg.set_boolean('legacy-imported', True)
    path = state_dir()/'preferences.json'
    try:
        legacy = json.loads(path.read_text())
    except (OSError, ValueError):
        return
    if isinstance(legacy.get('folder'), str):
        cfg.set_string('pinned-folder', legacy['folder'])
    for key, name in [('folder_expanded', 'documents-expanded'), ('outline_expanded', 'outline-expanded')]:
        if isinstance(legacy.get(key), bool):
            cfg.set_boolean(name, legacy[key])
    try:
        cfg.set_int('text-zoom', max(70, min(200, int(legacy.get('text_zoom', 100)))))
    except (TypeError, ValueError):
        pass
    try:
        path.rename(path.with_suffix('.json.bak'))
    except OSError:
        pass


def migrate_pinned_folder(cfg):
    """Pre-0.2.0-19 settings only knew a single pinned folder."""
    folder = cfg.get_string('pinned-folder')
    folders = cfg.get_strv('pinned-folders')
    if folder and folder not in folders:
        cfg.set_strv('pinned-folders', [folder] + folders)


def home_relative(path):
    home = str(Path.home())
    return '~' + path[len(home):] if path == home or path.startswith(home + '/') else path


class Preferences(Adw.PreferencesDialog):
    def __init__(self, cfg):
        super().__init__(title='Préférences')
        page = Adw.PreferencesPage(title='Général', icon_name='document-edit-symbolic')
        self.add(page)
        appearance = Adw.PreferencesGroup(title='Apparence')
        page.add(appearance)
        scheme = Adw.ComboRow(title='Thème', subtitle='Apparence claire ou sombre de la fenêtre et de l’aperçu',
                              model=Gtk.StringList.new(['Système', 'Clair', 'Sombre']))
        scheme.set_selected(COLOR_SCHEMES.index(cfg.get_string('color-scheme')))
        scheme.connect('notify::selected',
                       lambda row, _p: cfg.set_string('color-scheme', COLOR_SCHEMES[row.get_selected()]))
        appearance.add(scheme)
        editor = Adw.PreferencesGroup(title='Éditeur')
        page.add(editor)
        for key, title, subtitle in [
            ('show-line-numbers', 'Numéros de ligne', 'Afficher la marge des numéros de ligne'),
            ('highlight-current-line', 'Surligner la ligne active', None),
            ('show-grid', 'Grille de fond', 'Afficher une trame discrète derrière le texte')]:
            row = Adw.SwitchRow(title=title, subtitle=subtitle)
            cfg.bind(key, row, 'active', Gio.SettingsBindFlags.DEFAULT)
            editor.add(row)
        system_font_row = Adw.SwitchRow(title='Utiliser la police du système',
                                        subtitle='Police à chasse fixe définie dans GNOME')
        cfg.bind('use-system-font', system_font_row, 'active', Gio.SettingsBindFlags.DEFAULT)
        editor.add(system_font_row)
        font_row = Adw.ActionRow(title='Police de l’éditeur', subtitle='Famille et taille')
        font_dialog = Gtk.FontDialog()
        font_dialog.set_title('Police de l’éditeur')
        font_button = Gtk.FontDialogButton(dialog=font_dialog, valign=Gtk.Align.CENTER)
        font_button.set_font_desc(Pango.FontDescription.from_string(cfg.get_string('editor-font')))
        font_button.connect('notify::font-desc',
                            lambda b, _p: cfg.set_string('editor-font', b.get_font_desc().to_string()))
        font_row.add_suffix(font_button)
        font_row.set_activatable_widget(font_button)
        system_font_row.bind_property('active', font_row, 'sensitive',
                                      GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.INVERT_BOOLEAN)
        editor.add(font_row)
        integration = Adw.PreferencesGroup(title='Intégration')
        page.add(integration)
        row = Adw.ActionRow(title='Éditeur Markdown par défaut',
                            subtitle='Associer les fichiers .md et .markdown à Grimoire')
        row.set_activatable(True)
        row.set_action_name('win.default')
        row.add_suffix(Gtk.Image.new_from_icon_name('go-next-symbolic'))
        integration.add(row)


class Window(Adw.ApplicationWindow):
    def __init__(self, app, path=None):
        super().__init__(application=app, title='Grimoire', default_width=1180, default_height=780)
        self.doc = Document()
        self.loading = False
        self.refresh_id = 0
        self.guard_dialog = None
        self.cfg = settings()
        import_legacy_preferences(self.cfg)
        migrate_pinned_folder(self.cfg)
        self.mode = 'code'
        self.lang = 'fish'
        self.documents = []
        self.active_tab = None
        folders = self.cfg.get_strv('pinned-folders')
        self.folder = self.cfg.get_string('pinned-folder') or (folders[0] if folders else '')
        self.current_folder = self.folder
        self.folder_monitor = None
        self.toasts = Adw.ToastOverlay()
        self.set_content(self.toasts)
        self.split = Adw.OverlaySplitView(min_sidebar_width=260, max_sidebar_width=420,
                                          sidebar_width_fraction=0.22, show_sidebar=False)
        self.toasts.set_child(self.split)
        self.build_sidebar()
        self.build_content()
        self.register_actions()
        self.add_breakpoint_rules()
        self.connect('close-request', self.on_close)
        self.style = Adw.StyleManager.get_default()
        self.style.connect('notify::dark', self.theme_changed)
        self.style.connect('notify::accent-color', self.theme_changed)
        self.zoom_css = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(self.get_display(), self.zoom_css,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.bind_editor_settings()
        self.theme_changed()
        self.cfg.connect('changed::pinned-folders', lambda *_: self.refresh_pinned_list())
        self.refresh_pinned_list()
        self.refresh_folder()
        self.watch_folder()
        if path:
            self.load(path)
        else:
            self.refresh()
        self.add_tab(self.doc)
        self.editor.grab_focus()

    # ---------------------------------------------------------------- chrome

    def add_breakpoint_rules(self):
        bp = Adw.Breakpoint.new(Adw.BreakpointCondition.parse('max-width: 700sp'))
        bp.add_setter(self.split, 'collapsed', True)
        self.add_breakpoint(bp)

    def toast(self, message):
        self.toasts.add_toast(Adw.Toast.new(str(message)))

    def saved_toast(self):
        """Short, native confirmation; replaces the previous one instead of stacking."""
        previous = getattr(self, '_saved_toast', None)
        if previous:
            previous.dismiss()
        toast = Adw.Toast.new(f'« {self.doc.path.name} » enregistré')
        toast.set_timeout(2)
        self._saved_toast = toast
        self.toasts.add_toast(toast)

    def error(self, message):
        d = Adw.AlertDialog.new('Impossible de terminer', str(message))
        d.add_response('ok', 'Fermer')
        d.present(self)

    def build_sidebar(self):
        view = Adw.ToolbarView()
        self.split.set_sidebar(view)
        bar = Adw.HeaderBar()
        self.folder_title = Adw.WindowTitle(title='Documents', subtitle='Aucun dossier épinglé')
        switcher = Gtk.MenuButton(child=self.folder_title, always_show_arrow=True,
                                  popover=self.build_folder_popover())
        switcher.add_css_class('flat')
        bar.set_title_widget(switcher)
        self.folder_up = button('go-up-symbolic', 'Remonter au dossier parent', self.parent_folder)
        bar.pack_start(self.folder_up)
        bar.pack_end(button('folder-new-symbolic', 'Épingler un autre dossier', self.choose_folder))
        view.add_top_bar(bar)
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                          margin_start=6, margin_end=6, margin_bottom=6)
        view.set_content(sidebar)
        documents = bool(self.cfg.get_boolean('documents-expanded'))
        self.folder_expander = Gtk.Expander(label='Documents', expanded=documents, vexpand=documents)
        self.set_section_label(self.folder_expander, 'folder-symbolic', 'Documents')
        self.folder_expander.set_tooltip_text('Afficher ou masquer les documents du dossier épinglé')
        self.folder_expander.connect('notify::expanded', self.expanded_changed, 'documents-expanded')
        sidebar.append(self.folder_expander)
        folder_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_top=6, vexpand=True)
        self.folder_expander.set_child(folder_box)
        self.file_filter = Gtk.SearchEntry(placeholder_text='Filtrer ce dossier…', margin_start=6, margin_end=6)
        self.file_filter.connect('search-changed', lambda *_: self.refresh_folder())
        folder_box.append(self.file_filter)
        self.files = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.files.add_css_class('navigation-sidebar')
        self.files.connect('row-activated', self.activate_file)
        self.build_file_menu()
        folder_box.append(scroll(self.files))
        sidebar.append(Gtk.Separator())
        outline = bool(self.cfg.get_boolean('outline-expanded'))
        self.outline_expander = Gtk.Expander(label='Sommaire', expanded=outline, vexpand=outline)
        self.set_section_label(self.outline_expander, 'view-list-symbolic', 'Sommaire')
        self.outline_expander.set_tooltip_text('Afficher ou masquer le sommaire')
        self.outline_expander.connect('notify::expanded', self.expanded_changed, 'outline-expanded')
        sidebar.append(self.outline_expander)
        self.outline = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.outline.add_css_class('navigation-sidebar')
        self.outline.connect('row-activated', self.jump_heading)
        outline_scroll = scroll(self.outline)
        outline_scroll.set_margin_top(6)
        self.outline_expander.set_child(outline_scroll)
        sidebar.append(Gtk.Box(vexpand=True, visible=not documents and not outline))
        self.sidebar_spacer = sidebar.get_last_child()

    def build_folder_popover(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, width_request=280)
        self.pinned_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.pinned_list.add_css_class('navigation-sidebar')
        empty = Gtk.Label(label='Aucun dossier épinglé', margin_top=12, margin_bottom=12)
        empty.add_css_class('dimmed')
        self.pinned_list.set_placeholder(empty)
        self.pinned_list.connect('row-activated', lambda _, row: self.select_folder(row.folder))
        box.append(self.pinned_list)
        box.append(Gtk.Separator())
        add = Gtk.Button(child=Adw.ButtonContent(icon_name='folder-new-symbolic', label='Épingler un dossier…',
                                                 halign=Gtk.Align.START), action_name='win.pin')
        add.add_css_class('flat')
        box.append(add)
        self.folder_popover = Gtk.Popover(child=box)
        add.connect('clicked', lambda *_: self.folder_popover.popdown())
        return self.folder_popover

    def pinned_row(self, folder):
        row = Gtk.ListBoxRow(tooltip_text=folder)
        row.folder = folder
        box = Gtk.Box(spacing=8, margin_start=4, margin_end=2, margin_top=2, margin_bottom=2)
        check = Gtk.Image.new_from_icon_name('object-select-symbolic')
        check.set_opacity(1 if folder == self.folder else 0)
        box.append(check)
        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
        labels.append(Gtk.Label(label=Path(folder).name or folder, xalign=0, ellipsize=Pango.EllipsizeMode.END))
        missing = not Path(folder).is_dir()
        detail = Gtk.Label(label='Dossier introuvable' if missing else home_relative(str(Path(folder).parent)),
                           xalign=0, ellipsize=Pango.EllipsizeMode.MIDDLE)
        detail.add_css_class('caption')
        detail.add_css_class('error' if missing else 'dimmed')
        labels.append(detail)
        box.append(labels)
        remove = Gtk.Button(icon_name='window-close-symbolic', tooltip_text='Détacher ce dossier',
                            valign=Gtk.Align.CENTER)
        remove.add_css_class('flat')
        remove.add_css_class('circular')
        remove.connect('clicked', lambda *_: self.unpin(folder))
        box.append(remove)
        row.set_child(box)
        return row

    def refresh_pinned_list(self):
        clear(self.pinned_list)
        for folder in self.cfg.get_strv('pinned-folders'):
            self.pinned_list.append(self.pinned_row(folder))
        self.lookup_action('unpin').set_enabled(bool(self.folder))

    def build_file_menu(self):
        self.file_menu = Gtk.PopoverMenu(has_arrow=False, halign=Gtk.Align.START)
        self.file_menu.set_parent(self.files)
        click = Gtk.GestureClick(button=Gdk.BUTTON_SECONDARY)
        click.connect('pressed', self.file_menu_clicked)
        self.files.add_controller(click)
        key = Gtk.EventControllerKey()
        key.connect('key-pressed', self.file_menu_key)
        self.files.add_controller(key)

    def file_menu_clicked(self, _gesture, _n_press, x, y):
        row = self.files.get_row_at_y(int(y))
        if row:
            self.show_file_menu(row, x, y)

    def file_menu_key(self, _, keyval, _keycode, state):
        shift_f10 = keyval == Gdk.KEY_F10 and state & Gdk.ModifierType.SHIFT_MASK
        row = self.files.get_focus_child()
        if (keyval == Gdk.KEY_Menu or shift_f10) and row:
            _ok, bounds = row.compute_bounds(self.files)
            self.show_file_menu(row, bounds.get_x() + 24, bounds.get_y() + bounds.get_height())
            return True
        return False

    def show_file_menu(self, row, x, y):
        target = GLib.Variant.new_string(str(row.path))
        entries = [('Ouvrir', 'win.open-entry')]
        if row.is_folder:
            entries += [('Épingler ce dossier', 'win.pin-entry'), ('Ouvrir dans Fichiers', 'win.reveal-entry')]
        else:
            entries.append(('Afficher dans Fichiers', 'win.reveal-entry'))
        menu = Gio.Menu()
        for label, action in entries:
            item = Gio.MenuItem.new(label, None)
            item.set_action_and_target_value(action, target)
            menu.append_item(item)
        self.file_menu.set_menu_model(menu)
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = int(x), int(y), 1, 1
        self.file_menu.set_pointing_to(rect)
        self.file_menu.popup()

    def build_content(self):
        view = Adw.ToolbarView()
        self.split.set_content(view)
        view.add_top_bar(self.build_header())
        view.add_top_bar(self.build_toolbar())
        view.add_top_bar(self.build_searchbar())
        view.add_bottom_bar(self.build_statusbar())
        view.set_content(self.build_editor())

    def build_header(self):
        bar = Adw.HeaderBar()
        toggle = Gtk.ToggleButton(icon_name='sidebar-show-symbolic', tooltip_text='Dossiers et sommaire · F9')
        self.split.bind_property('show-sidebar', toggle, 'active',
                                 GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        bar.pack_start(toggle)
        bar.pack_start(button('document-open-symbolic', 'Ouvrir · Ctrl+O', self.choose_open))
        self.tabs = Gtk.Box(spacing=4)
        # Keep the tab strip bounded by the current window width.  New tabs
        # scroll horizontally instead of forcing the window to grow.
        self.tabs_scroll = Gtk.ScrolledWindow()
        self.tabs_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self.tabs_scroll.set_propagate_natural_width(False)
        self.tabs_scroll.set_min_content_width(180)
        self.tabs_scroll.set_hexpand(True)
        self.tabs_scroll.set_child(self.tabs)
        bar.set_title_widget(self.tabs_scroll)
        self.window_title = Adw.WindowTitle(title='Sans titre', subtitle='Document non enregistré')
        # Plain header-bar button bound to the window action, like other
        # GNOME apps: no accent colour, greyed out when there is nothing to
        # save, so a click visibly "settles" the button.
        save = Gtk.Button(icon_name='document-save-symbolic', tooltip_text='Enregistrer · Ctrl+S',
                          action_name='win.save')
        bar.pack_end(save)
        search = Gtk.ToggleButton(icon_name='edit-find-symbolic', tooltip_text='Rechercher/remplacer · Ctrl+F')
        self.search_toggle = search
        bar.pack_end(search)
        bar.pack_end(self.build_menu_button())
        return bar

    def build_menu_button(self):
        menu = Gio.Menu()
        section = Gio.Menu()
        for label, action in [('Enregistrer sous…', 'save-as'), ('Renommer le fichier…', 'rename'),
                              ('Recharger le fichier', 'reload')]:
            section.append(label, 'win.' + action)
        menu.append_section(None, section)
        section = Gio.Menu()
        for label, action in [('Épingler un dossier…', 'pin'), ('Détacher ce dossier', 'unpin'),
                              ('Actualiser le dossier', 'refresh-folder')]:
            section.append(label, 'win.' + action)
        menu.append_section(None, section)
        section = Gio.Menu()
        item = Gio.MenuItem()
        item.set_attribute_value('custom', GLib.Variant.new_string('zoom'))
        section.append_item(item)
        menu.append_section(None, section)
        section = Gio.Menu()
        for label, action in [('Préférences', 'app.preferences'), ('Raccourcis clavier', 'win.shortcuts'),
                              ('À propos de Grimoire', 'win.about')]:
            section.append(label, action)
        menu.append_section(None, section)
        popover = Gtk.PopoverMenu.new_from_model(menu)
        popover.add_child(self.build_zoom_widget(), 'zoom')
        return Gtk.MenuButton(icon_name='open-menu-symbolic', tooltip_text='Menu principal', popover=popover)

    def build_zoom_widget(self):
        box = Gtk.Box(spacing=6, margin_start=6, margin_end=6, margin_top=3, margin_bottom=3)
        self.zoom_out = button('zoom-out-symbolic', 'Réduire le texte · Ctrl+−', lambda: self.change_zoom(-10))
        self.zoom_in = button('zoom-in-symbolic', 'Agrandir le texte · Ctrl++', lambda: self.change_zoom(10))
        self.zoom_reset = Gtk.Button(label='100 %', tooltip_text='Rétablir la taille à 100 % · Ctrl+0', hexpand=True)
        self.zoom_reset.add_css_class('flat')
        self.zoom_reset.connect('clicked', lambda *_: self.set_zoom(100))
        self.zoom_out.add_css_class('circular')
        self.zoom_in.add_css_class('circular')
        for widget in (self.zoom_out, self.zoom_reset, self.zoom_in):
            box.append(widget)
        return box

    def build_toolbar(self):
        self.toolbar = Gtk.Box(spacing=3, margin_start=6, margin_end=6, margin_top=3, margin_bottom=3)
        titles = Gio.Menu()
        for n in range(1, 7):
            titles.append('Titre ' + str(n), 'win.h' + str(n))
        self.toolbar.append(Gtk.MenuButton(label='H', menu_model=titles, tooltip_text='Titres'))
        for icon, tip, fun in [
            ('format-text-bold-symbolic', 'Gras · Ctrl+B', lambda: self.wrap('**', '**', 'texte')),
            ('format-text-italic-symbolic', 'Italique · Ctrl+I', lambda: self.wrap('*', '*', 'texte')),
            ('view-list-bullet-symbolic', 'Liste à puces', lambda: self.prefix('- ')),
            ('view-list-ordered-symbolic', 'Liste numérotée', lambda: self.prefix('1. ')),
            ('object-select-symbolic', 'Case à cocher', lambda: self.prefix('- [ ] ')),
            ('insert-link-symbolic', 'Insérer un lien', self.link),
            ('insert-image-symbolic', 'Insérer une image locale', self.image),
            ('io.github.shogu.Grimoire-quote-symbolic', 'Citation', lambda: self.prefix('> ')),
            ('view-grid-symbolic', 'Insérer un tableau Markdown', self.insert_table),
        ]:
            self.toolbar.append(button(icon, tip, fun))
        self.toolbar.append(button('io.github.shogu.Grimoire-inline-code-symbolic', 'Code en ligne',
                                   lambda: self.wrap('`', '`', 'code')))
        code = Gtk.Box(spacing=0)
        code.add_css_class('linked')
        self.code_button = Gtk.Button(label='{} fish', tooltip_text='Insérer un bloc de code (fish par défaut)')
        self.code_button.connect('clicked', lambda *_: self.insert_code())
        code.append(self.code_button)
        languages = Gio.Menu()
        for lang in ('fish', 'python', 'systemd'):
            languages.append(lang, 'win.lang-' + lang)
        languages.append('Sans langage', 'win.lang-plain')
        code.append(Gtk.MenuButton(icon_name='pan-down-symbolic', menu_model=languages))
        self.toolbar.append(code)
        self.toolbar.append(button('edit-undo-symbolic', 'Annuler · Ctrl+Z', self.undo))
        self.toolbar.append(button('edit-redo-symbolic', 'Rétablir · Ctrl+Maj+Z', self.redo))
        holder = Gtk.ScrolledWindow()
        holder.add_css_class('toolbar')
        holder.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        holder.set_child(self.toolbar)
        return holder

    def build_searchbar(self):
        self.searchbar = Gtk.SearchBar()
        box = Gtk.Box(spacing=6)
        self.search = Gtk.SearchEntry(placeholder_text='Rechercher…', hexpand=True)
        self.case_toggle = Gtk.ToggleButton(label='Aa', tooltip_text='Respecter la casse')
        self.match_counter = Gtk.Label(xalign=0, width_chars=9)
        self.case_toggle.set_active(False)
        self.case_toggle.connect('toggled', self.update_matches)
        self.replacement = Gtk.Entry(placeholder_text='Remplacer par…', hexpand=True)
        self.search.connect('search-changed', self.update_matches)
        self.search.connect('activate', lambda *_: self.find_next())
        key = Gtk.EventControllerKey()
        key.connect('key-pressed', self.search_key)
        self.search.add_controller(key)
        self.searchbar.connect('notify::search-mode-enabled', lambda *_: self.highlight_matches())
        box.append(self.search)
        box.append(self.case_toggle)
        box.append(self.match_counter)
        box.append(self.replacement)
        box.append(button('go-down-symbolic', 'Occurrence suivante', self.find_next))
        for label, cb in [('Remplacer', self.replace_one), ('Tout', self.replace_all)]:
            b = Gtk.Button(label=label)
            b.connect('clicked', lambda _, f=cb: f())
            box.append(b)
        self.searchbar.set_child(box)
        self.searchbar.connect_entry(self.search)
        self.searchbar.bind_property('search-mode-enabled', self.search_toggle, 'active',
                                     GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        return self.searchbar

    def build_statusbar(self):
        bar = Gtk.CenterBox(margin_start=12, margin_end=12, margin_top=3, margin_bottom=3)
        self.status = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END)
        self.status.add_css_class('dimmed')
        self.status.add_css_class('numeric')
        bar.set_start_widget(self.status)
        self.modes = Adw.ToggleGroup()
        for name, label in MODES:
            self.modes.add(Adw.Toggle(name=name, label=label))
        self.modes.set_active_name('code')
        self.modes.connect('notify::active-name', self.mode_changed)
        bar.set_center_widget(self.modes)
        return bar

    def build_editor(self):
        self.buffer = GtkSource.Buffer()
        self.buffer.set_enable_undo(True)
        self.buffer.set_language(GtkSource.LanguageManager.get_default().get_language('markdown'))
        self.editor = GtkSource.View.new_with_buffer(self.buffer)
        self.editor.add_css_class('grimoire-editor')
        self.editor.set_monospace(True)
        self.editor.set_auto_indent(True)
        self.editor.set_tab_width(4)
        self.editor.set_insert_spaces_instead_of_tabs(True)
        self.editor.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.editor.set_left_margin(18)
        self.editor.set_right_margin(18)
        self.editor.set_top_margin(16)
        self.editor.set_bottom_margin(32)
        self.source_scroll = scroll(self.editor)
        self.web = WebKit.WebView()
        self.web.get_settings().set_enable_javascript(False)
        self.web.connect('decide-policy', self.web_policy)
        self.panes = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL, vexpand=True,
                               wide_handle=True, shrink_start_child=False, shrink_end_child=False)
        self.panes.set_start_child(self.source_scroll)
        self.preview_scroll = scroll(self.web)
        self.panes.set_end_child(self.preview_scroll)
        self.panes.set_position(470)
        self.match_tag = self.buffer.create_tag('grimoire-match')
        self.buffer.connect('changed', self.changed)
        editor_key = Gtk.EventControllerKey()
        editor_key.connect('key-pressed', self.editor_key)
        self.editor.add_controller(editor_key)
        self.source_scroll.get_vadjustment().connect('value-changed', self.sync_preview_scroll)
        self.preview_scroll.get_vadjustment().connect('value-changed', self.sync_source_scroll)
        self.set_mode('code')
        return self.panes

    def bind_editor_settings(self):
        for key, prop in [('show-line-numbers', 'show-line-numbers'),
                          ('highlight-current-line', 'highlight-current-line'),
                          ('show-grid', 'background-pattern')]:
            if prop == 'background-pattern':
                self.cfg.connect('changed::show-grid', lambda *_: self.apply_grid())
                self.apply_grid()
            else:
                self.cfg.bind(key, self.editor, prop, Gio.SettingsBindFlags.GET)
        self.cfg.connect('changed::text-zoom', lambda *_: self.apply_zoom())
        self.cfg.connect('changed::use-system-font', lambda *_: self.apply_zoom())
        self.cfg.connect('changed::editor-font', lambda *_: self.apply_zoom())
        source = Gio.SettingsSchemaSource.get_default()
        if source is not None and source.lookup('org.gnome.desktop.interface', True) is not None:
            self.system_fonts = Gio.Settings.new('org.gnome.desktop.interface')
            self.system_fonts.connect('changed::monospace-font-name', lambda *_: self.apply_zoom())
            self.system_fonts.connect('changed::font-name', lambda *_: self.refresh_preview())
        self.apply_zoom()

    def apply_grid(self):
        self.editor.set_background_pattern(GtkSource.BackgroundPatternType.GRID
                                           if self.cfg.get_boolean('show-grid')
                                           else GtkSource.BackgroundPatternType.NONE)

    # ------------------------------------------------------------------ zoom

    def zoom(self):
        return max(70, min(200, self.cfg.get_int('text-zoom')))

    def set_zoom(self, value):
        self.cfg.set_int('text-zoom', max(70, min(200, int(value))))

    def change_zoom(self, delta):
        self.set_zoom(self.zoom() + delta)

    def apply_zoom(self):
        zoom = self.zoom()
        system = self.cfg.get_boolean('use-system-font')
        if system:
            family, size = system_font('monospace-font-name', 12)
        else:
            desc = Pango.FontDescription.from_string(self.cfg.get_string('editor-font'))
            family = desc.get_family() or ''
            size = desc.get_size() / Pango.SCALE if desc.get_size() > 0 else 12
        self.editor.set_monospace(system)
        font = f'font-family: "{family}", {"monospace" if system else "sans-serif"}; ' if family else ''
        self.zoom_css.load_from_string(f'.grimoire-editor {{ {font}font-size: {size * zoom / 100:.2f}pt; }}')
        self.web.set_zoom_level(zoom / 100)
        self.zoom_reset.set_label(f'{zoom} %')
        self.zoom_out.set_sensitive(zoom > 70)
        self.zoom_in.set_sensitive(zoom < 200)

    # --------------------------------------------------------------- actions

    def action(self, name, callback, keys=()):
        a = Gio.SimpleAction.new(name, None)
        a.connect('activate', lambda *_: callback())
        self.add_action(a)
        if keys:
            self.get_application().set_accels_for_action('win.' + name, keys)

    def register_actions(self):
        for name, cb, keys in [
            ('new', self.new, ['<Primary>n']), ('open', self.choose_open, ['<Primary>o']),
            ('save', self.save, ['<Primary>s']), ('save-as', lambda: self.save_as(), ['<Primary><Shift>s']),
            ('rename', self.rename, ['F2']), ('pin', self.choose_folder, []),
            ('unpin', self.unpin, []), ('refresh-folder', self.refresh_folder, ['F5']),
            ('reload', lambda: self.guard(lambda: self.load(self.doc.path)) if self.doc.path else None, []),
            ('default', self.make_default, []), ('about', self.about, []),
            ('shortcuts', self.shortcuts, ['<Primary>question']),
            ('sidebar', self.toggle_sidebar, ['F9']),
            ('find', self.show_search, ['<Primary>f', '<Primary>h']),
            ('zoom-in', lambda: self.change_zoom(10), ['<Primary>plus', '<Primary>equal', '<Primary>KP_Add']),
            ('zoom-out', lambda: self.change_zoom(-10), ['<Primary>minus', '<Primary>KP_Subtract']),
            ('zoom-reset', lambda: self.set_zoom(100), ['<Primary>0']),
            ('bold', lambda: self.wrap('**', '**', 'texte'), ['<Primary>b']),
            ('italic', lambda: self.wrap('*', '*', 'texte'), ['<Primary>i']),
            ('close', self.close, ['<Primary>w'])]:
            self.action(name, cb, keys)
        for n in range(1, 7):
            self.action('h' + str(n), lambda n=n: self.prefix('#'*n + ' ', heading=True))
        for lang in ('fish', 'python', 'systemd'):
            self.action('lang-' + lang, lambda lang=lang: self.select_language(lang))
        self.action('lang-plain', lambda: self.select_language(''))
        for name, callback in [('open-entry', self.activate_path), ('pin-entry', self.pin_folder),
                               ('reveal-entry', self.reveal)]:
            self.path_action(name, callback)

    def path_action(self, name, callback):
        a = Gio.SimpleAction.new(name, GLib.VariantType.new('s'))
        a.connect('activate', lambda _a, value: callback(Path(value.get_string())))
        self.add_action(a)

    def set_section_label(self, expander, icon, title):
        label = Gtk.Box(spacing=6)
        label.append(Gtk.Image.new_from_icon_name(icon))
        label.append(Gtk.Label(label=title, xalign=0))
        expander.set_label_widget(label)

    def update_sidebar_spacer(self):
        self.sidebar_spacer.set_visible(not self.folder_expander.get_expanded()
                                        and not self.outline_expander.get_expanded())

    def expanded_changed(self, expander, _property, key):
        expanded = expander.get_expanded()
        expander.set_vexpand(expanded)
        self.cfg.set_boolean(key, expanded)
        self.update_sidebar_spacer()

    def center_panes(self):
        width = self.panes.get_width()
        if width > 0:
            self.panes.set_position(width // 2)
        else:
            GLib.idle_add(self.center_panes)

    def set_mode(self, name):
        self.mode = name

        # Code and Render each use the whole content area. Scindé restores
        # both views at equal width.
        if name == 'code':
            self.panes.set_start_child(self.source_scroll)
            self.panes.set_end_child(None)
            self.source_scroll.set_visible(True)
            self.web.set_visible(False)
        elif name == 'render':
            self.panes.set_start_child(None)
            self.panes.set_end_child(self.preview_scroll)
            self.source_scroll.set_visible(False)
            self.web.set_visible(True)
        else:
            self.panes.set_start_child(self.source_scroll)
            self.panes.set_end_child(self.preview_scroll)
            self.source_scroll.set_visible(True)
            self.web.set_visible(True)
            self.center_panes()

        self.refresh_preview()

    def mode_changed(self, *_):
        self.set_mode(self.modes.get_active_name())

    def back_to_source(self):
        if self.mode == 'render':
            self.modes.set_active_name('code')

    def toggle_sidebar(self):
        self.split.set_show_sidebar(not self.split.get_show_sidebar())

    def theme_changed(self, *_):
        dark = self.style.get_dark()
        manager = GtkSource.StyleSchemeManager.get_default()
        scheme = manager.get_scheme('Adwaita-dark' if dark else 'Adwaita')
        if scheme:
            self.buffer.set_style_scheme(scheme)
        rgba = Gdk.RGBA()
        rgba.parse('#1d1d20' if dark else '#ffffff')
        self.web.set_background_color(rgba)
        self.match_tag.set_property('background-rgba', self.accent_rgba(0.45 if dark else 0.35))
        self.refresh_preview()

    def accent(self):
        try:
            return Adw.StyleManager.get_default().get_accent_color_rgba().to_string()
        except (AttributeError, TypeError):
            return '#3584e4'

    def accent_rgba(self, alpha=1.0):
        rgba = Gdk.RGBA()
        if not rgba.parse(self.accent()):
            rgba.parse('#3584e4')
        rgba.alpha = alpha
        return rgba

    # ------------------------------------------------------------- documents

    def text(self):
        return self.buffer.get_text(*self.buffer.get_bounds(), True)

    def changed(self, *_):
        if self.loading:
            return
        self.doc.text = self.text()
        self.refresh_tabs()
        if self.refresh_id:
            GLib.source_remove(self.refresh_id)
        self.refresh_title()
        self.refresh_id = GLib.timeout_add(350, self.refresh)

    def refresh_title(self):
        name = self.doc.path.name if self.doc.path else 'Sans titre'
        self.window_title.set_title(name + (' •' if self.doc.dirty else ''))
        self.window_title.set_subtitle(str(self.doc.path.parent) if self.doc.path else 'Document non enregistré')
        self.set_title(name + ' — Grimoire')
        state = 'Modifié' if self.doc.dirty else 'Enregistré' if self.doc.path else 'Nouveau document'
        save_action = self.lookup_action('save')
        if save_action:
            save_action.set_enabled(self.doc.dirty or (not self.doc.path and bool(self.doc.text)))
        self.status.set_text(f'{state}  ·  {len(self.doc.text.split())} mots  ·  {self.buffer.get_line_count()} lignes')

    def refresh(self):
        self.refresh_id = 0
        self.refresh_title()
        self.highlight_matches()
        clear(self.outline)
        cursor_line = self.buffer.get_iter_at_mark(self.buffer.get_insert()).get_line()
        active_row = None
        for line, level, title in headings(self.doc.text):
            row = Gtk.ListBoxRow()
            row.line = line
            label = Gtk.Label(label=title, xalign=0, ellipsize=Pango.EllipsizeMode.END,
                              margin_start=(level-1)*12+6, margin_end=6, margin_top=6, margin_bottom=6)
            row.set_child(label)
            self.outline.append(row)
            if line <= cursor_line:
                active_row = row
        if active_row:
            self.outline.select_row(active_row)
        self.update_matches()
        self.refresh_preview()
        return False

    def refresh_preview(self):
        if not hasattr(self, 'web') or self.mode == 'code':
            return
        try:
            base = self.doc.path.parent.as_uri() + '/' if self.doc.path else 'file:///nonexistent-grimoire/'
            self.web.load_html(render(self.doc.text, Adw.StyleManager.get_default().get_dark(), self.accent(),
                                      system_font('font-name', 12)[0], system_font('monospace-font-name', 12)[0]), base)
        except Exception as e:
            self.toast('Aperçu indisponible : ' + str(e))

    def sync_preview_scroll(self, adjustment):
        if getattr(self, '_syncing_scroll', False):
            return
        self._syncing_scroll = True
        other = self.preview_scroll.get_vadjustment()
        upper = max(0, other.get_upper() - other.get_page_size())
        source = max(0, adjustment.get_upper() - adjustment.get_page_size())
        other.set_value(adjustment.get_value() / source * upper if source else 0)
        self._syncing_scroll = False

    def sync_source_scroll(self, adjustment):
        if getattr(self, '_syncing_scroll', False):
            return
        self._syncing_scroll = True
        other = self.source_scroll.get_vadjustment()
        upper = max(0, other.get_upper() - other.get_page_size())
        preview = max(0, adjustment.get_upper() - adjustment.get_page_size())
        other.set_value(adjustment.get_value() / preview * upper if preview else 0)
        self._syncing_scroll = False

    def web_policy(self, _, decision, kind):
        if kind == WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            nav = decision.get_navigation_action()
            if nav.get_navigation_type() == WebKit.NavigationType.LINK_CLICKED:
                uri = nav.get_request().get_uri()
                decision.ignore()
                if urlparse(uri).scheme in ('http', 'https', 'mailto'):
                    Gtk.UriLauncher.new(uri).launch(self, None, None)
                else:
                    self.toast('Seuls les liens Web et e-mail sont ouverts depuis le rendu.')
                return True
        return False

    def jump_heading(self, _, row):
        self.back_to_source()
        it = self.buffer.get_iter_at_line(row.line)
        if isinstance(it, tuple):
            it = it[-1]
        self.buffer.place_cursor(it)
        self.editor.scroll_to_iter(it, 0.1, True, 0, 0.15)
        self.editor.grab_focus()

    def set_text(self, text):
        self.loading = True
        self.buffer.set_enable_undo(False)
        self.buffer.set_text(text)
        self.buffer.set_enable_undo(True)
        self.loading = False
        self.refresh()

    def cancel_timers(self):
        for attr in ('refresh_id',):
            if getattr(self, attr):
                GLib.source_remove(getattr(self, attr))
                setattr(self, attr, 0)

    def load(self, path):
        if not path:
            return
        try:
            doc = Document()
            doc.load(path)
            self.cancel_timers()
            self.doc = doc
            self.set_text(doc.text)
            self.modes.set_active_name('code')
            self.sync_file_selection()
            self.editor.grab_focus()
        except (OSError, UnicodeError) as e:
            self.error(e)

    def add_tab(self, doc):
        if doc not in self.documents:
            self.documents.append(doc)
        self.active_tab = doc
        self.refresh_tabs()

    def refresh_tabs(self):
        if not hasattr(self, 'tabs'):
            return
        while self.tabs.get_first_child():
            self.tabs.remove(self.tabs.get_first_child())
        for doc in self.documents:
            label = doc.path.name if doc.path else 'Sans titre'
            if doc.dirty:
                label += ' •'

            group = Gtk.Box(spacing=0)
            group.add_css_class('linked')

            tab = Gtk.ToggleButton(label=label, active=doc is self.active_tab,
                                   tooltip_text=str(doc.path) if doc.path else 'Document non enregistré')
            tab.connect('clicked', lambda _, d=doc: self.switch_tab(d))
            group.append(tab)

            close = Gtk.Button(icon_name='window-close-symbolic',
                               tooltip_text='Fermer cet onglet')
            close.add_css_class('flat')
            close.connect('clicked', lambda _, d=doc: self.close_tab(d))
            group.append(close)
            self.tabs.append(group)

            # Keep the new-tab control immediately to the right of the
            # currently selected tab, instead of reserving an empty tab at
            # startup.  This is intentionally a plain GNOME symbolic button.
            if doc is self.active_tab:
                add = Gtk.Button(icon_name='list-add-symbolic',
                                 tooltip_text='Nouvel onglet · Ctrl+N')
                add.add_css_class('flat')
                add.connect('clicked', lambda *_: self.new())
                self.tabs.append(add)

    def close_tab(self, doc):
        if doc not in self.documents:
            return

        # Persist the editor buffer in the active in-memory document before any
        # tab is removed or switched.  This avoids losing unsaved text.
        if self.active_tab is self.doc:
            self.doc.text = self.text()

        def finish_close():
            if doc not in self.documents:
                return
            index = self.documents.index(doc)
            self.documents.remove(doc)

            if not self.documents:
                replacement = Document()
                self.documents.append(replacement)
                next_doc = replacement
            else:
                next_doc = self.documents[min(index, len(self.documents) - 1)]

            self.active_tab = next_doc
            self.doc = next_doc
            self.set_text(next_doc.text)
            self.refresh_tabs()
            self.refresh_title()
            self.sync_file_selection()
            self.editor.grab_focus()

        if not doc.dirty:
            finish_close()
            return

        dialog = Adw.AlertDialog.new('Enregistrer les modifications ?',
                                     'Cet onglet contient des modifications non enregistrées.')
        dialog.add_response('cancel', 'Annuler')
        dialog.add_response('discard', 'Ne pas enregistrer')
        dialog.add_response('save', 'Enregistrer')
        dialog.set_response_appearance('discard', Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_response_appearance('save', Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response('save')
        dialog.set_close_response('cancel')

        def response(_dialog, result):
            if result == 'discard':
                finish_close()
                return
            if result != 'save':
                return
            if doc.path:
                try:
                    doc.save()
                    finish_close()
                except (OSError, ValueError) as e:
                    self.error(e)
                return

            # save_as() operates on self.doc, so make this tab current without
            # discarding the previously active document's in-memory text.
            self.active_tab = doc
            self.doc = doc
            self.set_text(doc.text)
            self.refresh_tabs()
            self.refresh_title()
            self.save_as(finish_close)

        dialog.connect('response', response)
        dialog.present(self)

    def open_tab(self, path):
        resolved = Path(path).expanduser().resolve()
        existing = next((d for d in self.documents if d.path and d.path == resolved), None)
        if existing:
            self.switch_tab(existing)
            return

        try:
            # Preserve the current tab in memory. Opening another document no
            # longer needs an unsaved-changes guard because it does not replace
            # the current document.
            self.doc.text = self.text()
            doc = Document()
            doc.load(resolved)

            # A pristine startup placeholder is not a real user-created tab:
            # replace it with the file being opened. This avoids the permanent
            # empty “Sans titre” tab when opening a .md from Files/the shell.
            placeholder = (
                len(self.documents) == 1
                and self.documents[0] is self.doc
                and self.doc.path is None
                and not self.doc.dirty
                and not self.doc.text.strip()
            )
            if placeholder:
                self.documents[0] = doc
            else:
                try:
                    index = self.documents.index(self.active_tab) + 1
                except ValueError:
                    index = len(self.documents)
                self.documents.insert(index, doc)

            self.doc = doc
            self.active_tab = doc
            self.set_text(doc.text)
            self.modes.set_active_name('code')
            self.refresh_tabs()
            self.refresh_title()
            self.sync_file_selection()
            self.editor.grab_focus()
        except (OSError, UnicodeError) as e:
            self.error(e)

    def switch_tab(self, doc):
        if doc is self.active_tab:
            return
        def switch():
            self.doc.text = self.text()
            self.active_tab = doc
            self.doc = doc
            self.set_text(doc.text)
            self.refresh_tabs()
            self.sync_file_selection()
        self.guard(switch)

    def new(self):
        # New documents are genuine tabs. Preserve the current buffer and
        # insert the new tab immediately to the right of the current one.
        self.cancel_timers()
        if self.doc:
            self.doc.text = self.text()
        doc = Document()
        try:
            index = self.documents.index(self.active_tab) + 1
        except ValueError:
            index = len(self.documents)
        self.documents.insert(index, doc)
        self.doc = doc
        self.active_tab = doc
        self.set_text('')
        self.modes.set_active_name('code')
        self.sync_file_selection()
        self.editor.grab_focus()
        self.refresh_tabs()
        self.refresh_title()

    def guard(self, continuation):
        if self.guard_dialog:
            self.guard_dialog.present(self)
            return
        if not self.doc.dirty:
            continuation()
            return
        d = Adw.AlertDialog.new('Enregistrer les modifications ?',
                                'Votre document contient des modifications non enregistrées.')
        self.guard_dialog = d
        for key, label in [('cancel', 'Annuler'), ('discard', 'Ne pas enregistrer'), ('save', 'Enregistrer')]:
            d.add_response(key, label)
        d.set_response_appearance('save', Adw.ResponseAppearance.SUGGESTED)
        d.set_response_appearance('discard', Adw.ResponseAppearance.DESTRUCTIVE)
        d.set_default_response('save')
        d.set_close_response('cancel')

        def answer(_, response):
            self.guard_dialog = None
            if response == 'discard':
                self.cancel_timers()
                self.doc.text = self.doc.saved
                self.set_text(self.doc.text)
                continuation()
            elif response == 'save':
                self.save(continuation)
        d.connect('response', answer)
        d.present(self)

    def save(self, continuation=None):
        if not self.doc.path:
            self.save_as(continuation)
            return
        try:
            self.doc.save()
            self.refresh_tabs()
            self.refresh_title()
            self.saved_toast()
            if continuation:
                continuation()
        except (OSError, ValueError) as e:
            self.error(e)

    # --------------------------------------------------------- file dialogs

    def markdown_filters(self, dialog):
        f = Gtk.FileFilter()
        f.set_name('Markdown (*.md, *.markdown)')
        for pattern in ('*.md', '*.markdown', '*.MD'):
            f.add_pattern(pattern)
        store = Gio.ListStore.new(Gtk.FileFilter)
        store.append(f)
        dialog.set_filters(store)
        dialog.set_default_filter(f)

    def initial_folder(self, dialog):
        base = self.doc.path.parent if self.doc.path else Path(self.folder) if self.folder else None
        if base and base.is_dir():
            dialog.set_initial_folder(Gio.File.new_for_path(str(base)))

    def finish(self, dialog, result, method, callback):
        try:
            file = getattr(dialog, method)(result)
        except GLib.Error:
            return
        if file and file.get_path():
            callback(Path(file.get_path()))

    def choose_open(self):
        d = Gtk.FileDialog(title='Ouvrir un document', modal=True)
        self.markdown_filters(d)
        self.initial_folder(d)
        d.open(self, None, lambda dialog, res: self.finish(
            dialog, res, 'open_finish', self.open_tab))

    def save_as(self, continuation=None):
        def selected(path):
            if path.suffix.lower() not in ('.md', '.markdown'):
                path = path.with_name(path.name + '.md')
            try:
                self.doc.save(path)
                self.refresh_tabs()
                self.refresh_title()
                self.refresh_folder()
                self.saved_toast()
                if continuation:
                    continuation()
            except (OSError, ValueError) as e:
                self.error(e)
        d = Gtk.FileDialog(title='Enregistrer le document', modal=True,
                           initial_name=self.doc.path.name if self.doc.path else 'Sans titre.md')
        self.markdown_filters(d)
        self.initial_folder(d)
        d.save(self, None, lambda dialog, res: self.finish(dialog, res, 'save_finish', selected))

    def choose_folder(self):
        d = Gtk.FileDialog(title='Épingler un dossier Markdown', modal=True)
        self.initial_folder(d)
        d.select_folder(self, None, lambda dialog, res: self.finish(dialog, res, 'select_folder_finish',
                                                                    self.pin_folder))

    def image(self):
        def selected(p):
            link = quote(os.path.relpath(p, self.doc.path.parent), safe='/') if self.doc.path else p.as_uri()
            self.wrap('![', '](' + link + ')', 'Image')
        d = Gtk.FileDialog(title='Insérer une image', modal=True)
        f = Gtk.FileFilter()
        f.set_name('Images')
        for mime in ('image/png', 'image/jpeg', 'image/webp', 'image/gif', 'image/svg+xml'):
            f.add_mime_type(mime)
        store = Gio.ListStore.new(Gtk.FileFilter)
        store.append(f)
        d.set_filters(store)
        d.set_default_filter(f)
        self.initial_folder(d)
        d.open(self, None, lambda dialog, res: self.finish(dialog, res, 'open_finish', selected))

    # --------------------------------------------------------------- editing

    def prompt(self, title, value, callback):
        d = Adw.AlertDialog.new(title, None)
        entry = Adw.EntryRow(title=title, text=value)
        d.set_extra_child(boxed_list(entry))
        d.add_response('cancel', 'Annuler')
        d.add_response('ok', 'Appliquer')
        d.set_response_appearance('ok', Adw.ResponseAppearance.SUGGESTED)
        d.set_default_response('ok')
        d.set_close_response('cancel')
        done = []

        def apply():
            if done:
                return
            done.append(True)
            try:
                callback(entry.get_text())
            except (OSError, ValueError) as e:
                self.error(e)

        def activated(*_):
            d.close()
            apply()

        entry.connect('entry-activated', activated)
        d.connect('response', lambda _, result: apply() if result == 'ok' else None)
        d.present(self)
        entry.grab_focus()

    def rename(self):
        if not self.doc.path:
            self.save_as()
            return

        def apply(name):
            def commit():
                try:
                    self.doc.rename(name)
                    self.refresh()
                    self.refresh_folder()
                except (OSError, ValueError) as e:
                    self.error(e)
            self.guard(commit)
        self.prompt('Renommer le fichier', self.doc.path.name, apply)

    def replace_document(self, text):
        self.buffer.begin_user_action()
        self.buffer.delete(*self.buffer.get_bounds())
        self.buffer.insert(self.buffer.get_start_iter(), text)
        self.buffer.end_user_action()

    def selected(self):
        bounds = self.buffer.get_selection_bounds()
        if bounds:
            return self.buffer.get_text(*bounds, True)
        return ''

    def wrap(self, before, after='', placeholder=''):
        self.back_to_source()
        selection = self.selected() or placeholder
        self.buffer.begin_user_action()
        self.buffer.delete_selection(True, True)
        self.buffer.insert_at_cursor(before + selection + after)
        self.buffer.end_user_action()
        self.editor.grab_focus()

    def prefix(self, prefix, heading=False, outdent=False):
        import re
        bounds = self.buffer.get_selection_bounds()
        start, end = bounds if bounds else (self.buffer.get_iter_at_mark(self.buffer.get_insert()), self.buffer.get_iter_at_mark(self.buffer.get_insert()))
        start.set_line_offset(0)
        if bounds and end.starts_line() and end.compare(start) > 0:
            end.backward_char()
        if not end.ends_line():
            end.forward_to_line_end()
        text = self.buffer.get_text(start, end, True)
        lines = text.split('\n')
        if heading:
            lines = [re.sub(r'^#{1,6}\s+', '', s) for s in lines]
        if outdent:
            result = '\n'.join(re.sub(r'^(    |\t)', '', s) for s in lines)
        else:
            result = '\n'.join(prefix + s for s in lines)
        self.buffer.begin_user_action()
        self.buffer.delete(start, end)
        self.buffer.insert(start, result)
        self.buffer.end_user_action()
        self.back_to_source()
        self.editor.grab_focus()

    def select_language(self, lang):
        self.lang = lang
        self.code_button.set_label('{} ' + lang if lang else '```')

    def insert_code(self):
        content = self.selected()
        self.buffer.begin_user_action()
        self.buffer.delete_selection(True, True)
        self.buffer.insert_at_cursor(code_block(content, self.lang))
        if not content:
            end = self.buffer.get_iter_at_mark(self.buffer.get_insert())
            end.backward_chars(4)
            self.buffer.place_cursor(end)
        self.buffer.end_user_action()
        self.back_to_source()
        self.editor.grab_focus()

    def insert_table(self):
        def apply(value):
            try:
                rows, cols = (int(x) for x in value.lower().replace('×', 'x').split('x', 1))
                if not (1 <= rows <= 30 and 1 <= cols <= 12):
                    raise ValueError
            except ValueError:
                raise ValueError('Indiquez des dimensions comme 3x3 (1–30 lignes, 1–12 colonnes).')
            lines = ['| ' + ' | '.join('Colonne ' + str(i + 1) for i in range(cols)) + ' |',
                     '| ' + ' | '.join('---' for _ in range(cols)) + ' |']
            lines += ['| ' + ' | '.join(' ' for _ in range(cols)) + ' |' for _ in range(rows - 1)]
            self.buffer.insert_at_cursor('\n' + '\n'.join(lines) + '\n')
        self.prompt('Assistant tableau (lignes×colonnes)', '3x3', apply)

    def link(self):
        def apply(url):
            if urlparse(url).scheme not in ('http', 'https', 'mailto'):
                raise ValueError('Utilisez une URL http, https ou mailto.')
            self.wrap('[', '](<' + url.replace('>', '%3E') + '>)', 'Lien')
        self.prompt('Adresse du lien', 'https://', apply)

    def undo(self):
        if self.buffer.get_can_undo():
            self.buffer.undo()

    def redo(self):
        if self.buffer.get_can_redo():
            self.buffer.redo()

    # ---------------------------------------------------------------- search

    def show_search(self):
        self.searchbar.set_search_mode(True)
        self.back_to_source()
        self.search.grab_focus()

    def update_matches(self, *_):
        q = self.search.get_text()
        total = self.match_count(q)
        mode = 'sensible à la casse' if self.case_toggle.get_active() else 'insensible à la casse'
        self.search.set_tooltip_text(f'{total} occurrence(s) · {mode}' if q else f'Recherche littérale, {mode}')
        self.status.set_text(self.status.get_text().split('  · Recherche')[0] +
                             (f'  · Recherche : 0/{total}' if q else ''))
        self.match_counter.set_text(f'0/{total}' if q else '')
        self.highlight_matches()

    def match_count(self, q):
        if not q:
            return 0
        text = self.doc.text if self.case_toggle.get_active() else self.doc.text.casefold()
        needle = q if self.case_toggle.get_active() else q.casefold()
        return sum(1 for _ in re.finditer(re.escape(needle), text))

    def highlight_matches(self):
        start, end = self.buffer.get_bounds()
        self.buffer.remove_tag(self.match_tag, start, end)
        q = self.search.get_text() if self.searchbar.get_search_mode() else ''
        if not q:
            return
        text = self.text()
        if not self.case_toggle.get_active():
            text, q = text.casefold(), q.casefold()
        i = text.find(q)
        while i >= 0:
            self.buffer.apply_tag(self.match_tag, self.buffer.get_iter_at_offset(i),
                                  self.buffer.get_iter_at_offset(i + len(q)))
            i = text.find(q, i + len(q))

    def find_next(self, backward=False):
        q = self.search.get_text()
        if not q:
            return
        start = self.buffer.get_iter_at_mark(self.buffer.get_insert()).get_offset()
        text = self.doc.text if self.case_toggle.get_active() else self.doc.text.casefold()
        needle = q if self.case_toggle.get_active() else q.casefold()
        if backward:
            i = text.rfind(needle, 0, max(0, start - 1))
            if i < 0:
                i = text.rfind(needle)
        else:
            i = text.find(needle, start)
            if i < 0:
                i = text.find(needle)
        if i >= 0:
            a, b = self.buffer.get_iter_at_offset(i), self.buffer.get_iter_at_offset(i+len(q))
            self.buffer.select_range(b, a) if backward else self.buffer.select_range(a, b)
            total = self.match_count(q)
            before = text[:i]
            current = sum(1 for _ in re.finditer(re.escape(needle), before)) + 1
            self.search.set_tooltip_text(f'{current}/{total} occurrence(s)')
            self.match_counter.set_text(f'{current}/{total}')
            self.editor.scroll_to_iter(a, 0.1, False, 0, 0)
        else:
            self.toast('Aucune occurrence')

    def replace_one(self):
        q = self.search.get_text()
        selected = self.selected()
        matches = selected == q if self.case_toggle.get_active() else selected.casefold() == q.casefold()
        if q and matches:
            self.buffer.begin_user_action()
            self.buffer.delete_selection(True, True)
            self.buffer.insert_at_cursor(self.replacement.get_text())
            self.buffer.end_user_action()
        self.find_next()

    def replace_all(self):
        q = self.search.get_text()
        if q:
            flags = 0 if self.case_toggle.get_active() else re.IGNORECASE
            count = self.match_count(q)
            self.replace_document(re.sub(re.escape(q), self.replacement.get_text(), self.doc.text, flags=flags))
            self.toast(f'{count} remplacement(s)')

    def search_key(self, _, keyval, keycode, state):
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self.find_next(backward=bool(state & Gdk.ModifierType.SHIFT_MASK))
            return True
        return False

    def editor_key(self, _, keyval, keycode, state):
        if keyval == Gdk.KEY_Tab and not (state & Gdk.ModifierType.CONTROL_MASK):
            cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
            line = cursor.get_line()
            start = self.buffer.get_iter_at_line(line)
            end = start.copy()
            end.forward_to_line_end()
            if not re.match(r'\s*(?:[-*+]|\d+[.)])\s+', self.buffer.get_text(start, end, True)):
                return False
            self.prefix('    ' if not (state & Gdk.ModifierType.SHIFT_MASK) else '', outdent=bool(state & Gdk.ModifierType.SHIFT_MASK))
            return True
        return False

    # ---------------------------------------------------------------- folder

    def pin_folder(self, path):
        folder = str(path)
        folders = self.cfg.get_strv('pinned-folders')
        if folder not in folders:
            self.cfg.set_strv('pinned-folders', folders + [folder])
        self.select_folder(folder)

    def select_folder(self, folder):
        self.folder_popover.popdown()
        self.folder = folder
        self.current_folder = folder
        self.cfg.set_string('pinned-folder', folder)
        self.file_filter.set_text('')
        if folder:
            self.folder_expander.set_expanded(True)
        self.watch_folder()
        self.refresh_folder()
        self.refresh_pinned_list()

    def unpin(self, folder=None):
        folder = folder or self.folder
        folders = [f for f in self.cfg.get_strv('pinned-folders') if f != folder]
        self.cfg.set_strv('pinned-folders', folders)
        if folder == self.folder:
            self.select_folder(folders[0] if folders else '')
        self.toast(f'« {Path(folder).name} » détaché de Grimoire (le dossier n’est pas supprimé)')

    def reveal(self, path):
        file = Gio.File.new_for_path(str(path))
        if path.is_dir():
            Gtk.FileLauncher.new(file).launch(self, None, self.reveal_done, 'launch_finish')
        else:
            Gtk.FileLauncher.new(file).open_containing_folder(self, None, self.reveal_done,
                                                              'open_containing_folder_finish')

    def reveal_done(self, launcher, result, method):
        try:
            getattr(launcher, method)(result)
        except GLib.Error as e:
            if not e.matches(Gtk.dialog_error_quark(), Gtk.DialogError.DISMISSED):
                self.toast('Impossible d’ouvrir Fichiers : ' + e.message)

    def watch_folder(self):
        if self.folder_monitor:
            self.folder_monitor.cancel()
            self.folder_monitor = None
        if self.folder:
            try:
                self.folder_monitor = Gio.File.new_for_path(self.current_folder).monitor_directory(Gio.FileMonitorFlags.NONE, None)
                self.folder_monitor.connect('changed', lambda *_: self.refresh_folder())
            except GLib.Error:
                pass

    def refresh_folder(self):
        clear(self.files)
        self.folder_up.set_sensitive(False)
        if not self.folder:
            self.folder_title.set_subtitle('Aucun dossier épinglé')
            return
        p = Path(self.current_folder)
        self.folder_up.set_sensitive(p != Path(self.folder))
        self.folder_title.set_subtitle(p.name)
        self.folder_title.set_tooltip_text(str(p))
        try:
            paths = sorted((f for f in p.iterdir() if f.is_dir() or (f.is_file() and f.suffix.lower() in ('.md', '.markdown'))), key=lambda f: (not f.is_dir(), f.name.casefold()))
            q = self.file_filter.get_text().casefold()
            for path in paths:
                if q not in path.name.casefold():
                    continue
                row = Gtk.ListBoxRow()
                row.path = path
                row.is_folder = path.is_dir()
                box = Gtk.Box(spacing=8, margin_start=6, margin_end=6, margin_top=9, margin_bottom=9)
                box.append(Gtk.Image.new_from_icon_name('folder-symbolic' if row.is_folder else 'text-x-generic-symbolic'))
                box.append(Gtk.Label(label=path.name if row.is_folder else path.stem, xalign=0, ellipsize=Pango.EllipsizeMode.END))
                row.set_child(box)
                row.set_tooltip_text(str(path))
                self.files.append(row)
                if self.doc.path == path.resolve():
                    self.files.select_row(row)
        except OSError:
            self.folder_title.set_subtitle('Dossier indisponible')

    def sync_file_selection(self):
        self.files.unselect_all()
        index = 0
        while self.doc.path and (row := self.files.get_row_at_index(index)):
            if row.path.resolve() == self.doc.path:
                self.files.select_row(row)
                break
            index += 1

    def enter_folder(self, path):
        self.current_folder = str(path)
        self.file_filter.set_text('')
        self.watch_folder()
        self.refresh_folder()

    def parent_folder(self):
        if self.folder and Path(self.current_folder) != Path(self.folder):
            self.enter_folder(Path(self.current_folder).parent)

    def activate_file(self, _, row):
        self.activate_path(row.path)

    def activate_path(self, path):
        if path.is_dir():
            self.enter_folder(path)
            return
        self.sync_file_selection()
        if self.doc.path != path.resolve():
            self.open_tab(path)
        if self.split.get_collapsed():
            self.split.set_show_sidebar(False)

    # ----------------------------------------------------------------- misc

    def make_default(self):
        try:
            app = Gio.DesktopAppInfo.new(APP_ID + '.desktop')
            if not app:
                raise ValueError('Installez le paquet avant de choisir cette association.')
            app.set_as_default_for_type('text/markdown')
            app.set_as_default_for_extension('md')
            app.set_as_default_for_extension('markdown')
            self.toast('Grimoire est votre éditeur Markdown par défaut.')
        except (GLib.Error, ValueError) as e:
            self.error(e)

    def shortcuts(self):
        d = Adw.ShortcutsDialog()
        for title, items in [
            ('Fichiers', [('Nouveau document', '<Control>n'), ('Ouvrir', '<Control>o'),
                          ('Enregistrer', '<Control>s'), ('Enregistrer sous', '<Control><Shift>s'),
                          ('Renommer le fichier', 'F2'), ('Actualiser le dossier', 'F5'),
                          ('Fermer la fenêtre', '<Control>w')]),
            ('Édition', [('Gras', '<Control>b'), ('Italique', '<Control>i'),
                         ('Annuler', '<Control>z'), ('Rétablir', '<Control><Shift>z'),
                         ('Rechercher et remplacer', '<Control>f')]),
            ('Affichage', [('Barre latérale', 'F9'), ('Agrandir le texte', '<Control>plus'),
                           ('Réduire le texte', '<Control>minus'), ('Taille normale', '<Control>0'),
                           ('Raccourcis clavier', '<Control>question')])]:
            section = Adw.ShortcutsSection(title=title)
            for name, accel in items:
                section.add(Adw.ShortcutsItem(title=name, accelerator=accel))
            d.add(section)
        d.present(self)

    def about(self):
        d = Adw.AboutDialog(application_name='Grimoire', application_icon=APP_ID,
                            version='0.2.0', developer_name='Ogu',
                            comments='Vos textes, vos notes et vos formules.\nÉditeur Markdown local pour GNOME.',
                            license_type=Gtk.License.MIT_X11)
        d.present(self)

    def on_close(self, *_):
        if self.doc.dirty:
            self.guard(self.close)
            return True
        self.cancel_timers()
        if self.folder_monitor:
            self.folder_monitor.cancel()
        self.file_menu.unparent()
        return False


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_OPEN)

    def do_startup(self):
        Adw.Application.do_startup(self)
        self.cfg = settings()
        self.cfg.connect('changed::color-scheme', lambda *_: self.apply_color_scheme())
        self.apply_color_scheme()
        action = Gio.SimpleAction.new('preferences', None)
        action.connect('activate', lambda *_: Preferences(self.cfg).present(self.get_active_window()))
        self.add_action(action)
        self.set_accels_for_action('app.preferences', ['<Primary>comma'])

    def apply_color_scheme(self):
        schemes = {'light': Adw.ColorScheme.FORCE_LIGHT, 'dark': Adw.ColorScheme.FORCE_DARK}
        Adw.StyleManager.get_default().set_color_scheme(
            schemes.get(self.cfg.get_string('color-scheme'), Adw.ColorScheme.DEFAULT))

    def do_activate(self):
        w = self.get_active_window()
        if not w:
            w = Window(self)
        w.present()

    def do_open(self, files, n_files, hint):
        w = self.get_active_window()
        if not w:
            w = Window(self)
        for file in files:
            path = file.get_path()
            if path:
                w.open_tab(path)
        w.present()


if __name__ == '__main__':
    sys.exit(Application().run(sys.argv))
