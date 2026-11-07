import json
import os
import shlex
import sys
import tarfile
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GtkSource", "5")
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk, GtkSource  # noqa: E402

from . import parsing  # noqa: E402

APP_ID = "io.github.fisherman.Fisherman"
VERSION = "0.3.1"

# Ordre et titres des groupes de la barre latérale.
GROUPS = [
    ("config", "Configuration"),
    ("confd", "Démarrage (conf.d)"),
    ("function", "Fonctions"),
    ("shortcut", "Alias et abréviations"),
    ("included", "Fichiers inclus"),
]
GROUP_TITLES = dict(GROUPS)
FILE_KINDS = {"config", "confd", "function", "included"}


# Ancien fichier installé par Fisherman 0.3.0 (rechargement des terminaux
# ouverts, abandonné) : retiré au démarrage s'il n'a pas été modifié.
LEGACY_HANDLER = "fisherman-reload.fish"
LEGACY_RELOAD_HANDLER_CODE = """\
# Installé par Fisherman : applique aux terminaux déjà ouverts les changements
# enregistrés dans Fisherman, en ne rejouant que ce qui doit l'être.
# Se désactive dans le menu de Fisherman (ce fichier est alors supprimé).
status is-interactive; or return

set -g __fisherman_applied 0
string match -qr '^[0-9]+$' -- "$__fisherman_reload"
and set -g __fisherman_applied $__fisherman_reload

function __fisherman_apply --on-variable __fisherman_reload
    string match -qr '^[0-9]+$' -- "$__fisherman_reload"; or return
    set -l dir $HOME/.cache
    set -q XDG_CACHE_HOME[1]; and set dir $XDG_CACHE_HOME
    set dir $dir/fisherman/reload
    test $__fisherman_reload -lt $__fisherman_applied; and set -g __fisherman_applied 0
    set -l n (math $__fisherman_applied + 1)
    while test $n -le $__fisherman_reload
        test -r $dir/$n.fish; and source $dir/$n.fish
        set n (math $n + 1)
    end
    set -g __fisherman_applied $__fisherman_reload
end
"""


def fish_config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(xdg) / "fish"


def settings_path() -> Path:
    return Path(GLib.get_user_config_dir()) / "fisherman" / "settings.json"


def load_settings() -> dict:
    try:
        return json.loads(settings_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_settings(data: dict):
    try:
        path = settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass


class FishItem(GObject.Object):
    """Une ligne de la barre latérale : un fichier, ou un alias/une abbr."""

    def __init__(self, path: Path, kind: str, text: str = "", shortcut=None):
        super().__init__()
        self.path = path
        self.kind = kind
        self.text = text  # contenu mis en cache (recherche, description)
        self.shortcut: parsing.Shortcut | None = shortcut
        self.number = 0
        self.readonly = not os.access(path, os.W_OK)
        self.overridden = False  # alias d'un paquet redéfini par l'utilisateur
        self.description = None
        if kind == "function":
            self.description = parsing.function_description(text, path.stem)

    @property
    def name(self) -> str:
        if self.shortcut is not None:
            return self.shortcut.name
        if self.kind in ("function", "confd") and self.path.suffix == ".fish":
            return self.path.stem
        return self.path.name

    @property
    def line(self) -> int | None:
        return self.shortcut.line if self.shortcut is not None else None

    @property
    def key(self):
        return (self.kind, str(self.path), self.line)

    def matches(self, query: str) -> bool:
        q = query.casefold()
        if q in self.name.casefold():
            return True
        if self.shortcut is not None:
            return q in self.shortcut.value.casefold()
        return q in self.text.casefold()


class GroupHeader(FishItem):
    """En-tête cliquable d'un groupe (pliable)."""

    def __init__(self, group: str):
        GObject.Object.__init__(self)
        self.kind = "header"
        self.group = group
        self.path = Path()
        self.text = ""
        self.shortcut = None
        self.number = 0
        self.readonly = True
        self.overridden = False
        self.description = None

    @property
    def name(self) -> str:
        return GROUP_TITLES[self.group]

    @property
    def key(self):
        return ("header", self.group, None)

    def matches(self, query: str) -> bool:
        return False


class FishermanWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app, title="Fisherman")
        self.set_default_size(1060, 700)
        self.set_icon_name(APP_ID)

        self.settings = load_settings()
        self.current: FishItem | None = None  # fichier ouvert dans l'éditeur
        self.selected_key = None  # ligne sélectionnée (fichier ou alias)
        self.query = ""
        self.counts: dict[str, int] = {}
        self.collapsed: set[str] = set(self.settings.get("collapsed", []))
        self.visible_counts: dict[str, int] = {}
        self.dirty = False
        self.loading = False
        self.dir_monitors = []
        self.file_monitor = None
        self.refresh_source_id = 0
        self.reload_source_id = 0

        self._build_ui()
        self._setup_actions()
        self._remove_legacy_reload()
        self._populate()
        self._setup_file_monitors()
        self.connect("close-request", self._on_close_request)

    # ---------- UI ----------
    def _build_ui(self):
        self.store = Gio.ListStore(item_type=FishItem)
        self.filter = Gtk.CustomFilter.new(self._filter_func)
        self.filter_model = Gtk.FilterListModel(model=self.store, filter=self.filter)

        self.listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.listbox.add_css_class("navigation-sidebar")
        self.listbox.bind_model(self.filter_model, self._create_row)
        self.listbox.connect("row-selected", self._on_row_selected)
        self.listbox.connect("row-activated", self._on_row_activated)

        sidebar_scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True)
        sidebar_scroll.set_child(self.listbox)

        self.empty_search = Adw.StatusPage(
            icon_name="edit-find-symbolic",
            title="Aucun résultat",
            vexpand=True,
        )
        self.empty_search.add_css_class("compact")
        self.sidebar_stack = Gtk.Stack(vexpand=True)
        self.sidebar_stack.add_named(sidebar_scroll, "list")
        self.sidebar_stack.add_named(self.empty_search, "empty")

        sidebar_header = Adw.HeaderBar()
        sidebar_header.add_css_class("flat")
        # Barre latérale compacte : pas de titre central.
        sidebar_header.set_title_widget(Gtk.Box())
        sidebar_header.set_show_end_title_buttons(False)

        add_menu = Gio.Menu()
        add_menu.append("Nouvelle fonction", "win.new-function")
        add_menu.append("Nouveau fichier de démarrage (conf.d)", "win.new-confd")
        add_btn = Gtk.MenuButton(
            icon_name="list-add-symbolic",
            tooltip_text="Ajouter",
            menu_model=add_menu,
        )
        sidebar_header.pack_start(add_btn)

        self.delete_btn = Gtk.Button(
            icon_name="user-trash-symbolic",
            tooltip_text="Supprimer le fichier sélectionné",
            sensitive=False,
        )
        self.delete_btn.add_css_class("destructive-action")
        self.delete_btn.connect("clicked", self._on_delete_button_clicked)
        sidebar_header.pack_end(self.delete_btn)

        menu = Gio.Menu()
        sort_section = Gio.Menu()
        sort_section.append("Trier par nom", "win.sort::name")
        sort_section.append("Trier par date de modification", "win.sort::date")
        menu.append_section(None, sort_section)
        io_section = Gio.Menu()
        io_section.append("Exporter la configuration…", "win.export")
        io_section.append("Importer une configuration…", "win.import")
        menu.append_section(None, io_section)
        about_section = Gio.Menu()
        about_section.append("À propos de Fisherman", "app.about")
        menu.append_section(None, about_section)
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu)
        sidebar_header.pack_end(menu_btn)

        # Recherche globale (noms, contenu des fichiers, alias et abbr)
        self.global_search = Gtk.SearchEntry(
            placeholder_text="Rechercher partout (Ctrl+K)",
            hexpand=True,
        )
        self.global_search.connect("search-changed", self._on_global_search_changed)
        self.global_search.connect("activate", self._on_global_search_activate)
        self.global_search.connect("stop-search", lambda e: e.set_text(""))
        search_box = Gtk.Box(margin_start=8, margin_end=8, margin_bottom=6)
        search_box.append(self.global_search)

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, width_request=250)
        sidebar.append(sidebar_header)
        sidebar.append(search_box)
        sidebar.append(self.sidebar_stack)

        # Éditeur
        self.buffer = GtkSource.Buffer()
        lm = GtkSource.LanguageManager.get_default()
        self.buffer.set_language(lm.get_language("fish"))
        self.buffer.set_highlight_syntax(True)
        self.buffer.connect("changed", self._on_buffer_changed)

        self.view = GtkSource.View(buffer=self.buffer)
        self.view.set_monospace(True)
        self.view.set_show_line_numbers(True)
        self.view.set_highlight_current_line(True)
        self.view.set_auto_indent(True)
        self.view.set_indent_width(4)
        self.view.set_insert_spaces_instead_of_tabs(True)
        self.view.set_tab_width(4)
        self.view.set_left_margin(8)
        self.view.set_top_margin(8)
        self.view.set_sensitive(False)

        style_mgr = Adw.StyleManager.get_default()
        style_mgr.connect("notify::dark", lambda *_: self._apply_scheme())
        self._apply_scheme()

        # Recherche native dans l'éditeur
        self.search_settings = GtkSource.SearchSettings(wrap_around=True)
        self.search_context = GtkSource.SearchContext.new(self.buffer, self.search_settings)
        self.search_context.set_highlight(True)

        self.search_entry = Gtk.SearchEntry(placeholder_text="Rechercher dans le fichier…")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("activate", self._on_search_next)
        self.search_entry.connect(
            "stop-search", lambda *_: self.search_bar.set_search_mode(False)
        )

        search_prev = Gtk.Button(icon_name="go-up-symbolic", tooltip_text="Occurrence précédente")
        search_prev.connect("clicked", self._on_search_prev)
        search_next = Gtk.Button(icon_name="go-down-symbolic", tooltip_text="Occurrence suivante")
        search_next.connect("clicked", self._on_search_next)
        search_nav = Gtk.Box(spacing=0, css_classes=["linked"])
        search_nav.append(search_prev)
        search_nav.append(search_next)

        search_inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        search_inner.append(self.search_entry)
        search_inner.append(search_nav)

        self.search_bar = Gtk.SearchBar()
        self.search_bar.set_child(search_inner)
        self.search_bar.connect_entry(self.search_entry)
        self.search_bar.set_key_capture_widget(self.view)

        editor_scroll = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        editor_scroll.set_child(self.view)
        self.editor_scroll = editor_scroll

        self.content_header = Adw.HeaderBar()
        self.content_title = Adw.WindowTitle(title="Aucun fichier", subtitle="")
        self.content_header.set_title_widget(self.content_title)
        self.content_header.set_show_start_title_buttons(False)

        search_toggle = Gtk.ToggleButton(
            icon_name="edit-find-symbolic", tooltip_text="Rechercher dans le fichier (Ctrl+F)"
        )
        self.search_bar.bind_property(
            "search-mode-enabled",
            search_toggle,
            "active",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
        )
        self.content_header.pack_start(search_toggle)

        self.try_btn = Gtk.Button(
            icon_name="media-playback-start-symbolic",
            tooltip_text="Essayer dans un terminal (Ctrl+E)",
            sensitive=False,
        )
        self.try_btn.connect("clicked", lambda *_: self._try_current())
        self.content_header.pack_start(self.try_btn)

        self.save_btn = Gtk.Button(
            icon_name="document-save-symbolic",
            tooltip_text="Enregistrer (Ctrl+S)",
            sensitive=False,
        )
        self.save_btn.connect("clicked", lambda *_: self.save())
        self.content_header.pack_end(self.save_btn)

        self.indent_btn = Gtk.Button(
            icon_name="format-indent-more-symbolic",
            tooltip_text="Reformater avec fish_indent (Ctrl+Maj+I)",
            sensitive=False,
        )
        self.indent_btn.connect("clicked", lambda *_: self._reformat())
        self.content_header.pack_end(self.indent_btn)

        self.readonly_banner = Adw.Banner(
            title="Fichier fourni par un paquet : lecture seule.",
            revealed=False,
        )
        self.readonly_banner.connect("button-clicked", lambda *_: self._redefine_shortcut())

        self.toast_overlay = Adw.ToastOverlay()

        self.status = Adw.StatusPage(
            icon_name=APP_ID,
            title="Fisherman",
            description="Sélectionnez un fichier, un alias ou une fonction dans la barre latérale.",
        )
        self.stack = Gtk.Stack(vexpand=True, hexpand=True)
        self.stack.add_named(self.status, "empty")
        self.stack.add_named(editor_scroll, "editor")
        self.toast_overlay.set_child(self.stack)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        content.append(self.content_header)
        content.append(self.readonly_banner)
        content.append(self.search_bar)
        content.append(self.toast_overlay)

        paned = Gtk.Paned(
            orientation=Gtk.Orientation.HORIZONTAL,
            position=280,
            shrink_start_child=False,
            shrink_end_child=False,
        )
        paned.set_start_child(sidebar)
        paned.set_end_child(content)
        self.set_content(paned)

    def _setup_actions(self):
        app = self.get_application()

        def add(name, callback, accels=None):
            action = Gio.SimpleAction(name=name)
            action.connect("activate", lambda *_: callback())
            self.add_action(action)
            if accels:
                app.set_accels_for_action(f"win.{name}", accels)

        add("save", self.save, ["<Control>s"])
        add("find", self._toggle_search, ["<Control>f"])
        add("global-search", self._focus_global_search, ["<Control>k"])
        add("reformat", self._reformat, ["<Control><Shift>i"])
        add("try", self._try_current, ["<Control>e"])
        add("new-function", lambda: self._show_new_dialog("function"))
        add("new-confd", lambda: self._show_new_dialog("confd"))
        add("export", self._export)
        add("import", self._import)

        sort_mode = self.settings.get("sort", "name")
        if sort_mode not in ("name", "date"):
            sort_mode = "name"
        sort_action = Gio.SimpleAction.new_stateful(
            "sort", GLib.VariantType.new("s"), GLib.Variant("s", sort_mode)
        )
        sort_action.connect("activate", self._on_sort_changed)
        self.add_action(sort_action)

    # ---------- Barre latérale ----------
    def _filter_func(self, item: FishItem) -> bool:
        if item.kind == "header":
            if self.query:
                return self.visible_counts.get(item.group, 0) > 0
            # Sans recherche, les alias et abbr ne sont pas listés.
            return item.group != "shortcut" and self.counts.get(item.group, 0) > 0
        if self.query:
            return item.matches(self.query)
        return item.kind != "shortcut" and item.kind not in self.collapsed

    def _create_header_row(self, item: GroupHeader) -> Gtk.Widget:
        total = self.counts.get(item.group, 0)
        if self.query:
            count = f"{self.visible_counts.get(item.group, 0)} / {total}"
        else:
            count = str(total)
        box = Gtk.Box(spacing=6, margin_start=6, margin_end=6)
        title = Gtk.Label(
            label=f"{item.name} — {count}",
            xalign=0,
            hexpand=True,
            css_classes=["heading", "dim-label"],
        )
        box.append(title)
        row = Gtk.ListBoxRow(selectable=False, activatable=not self.query, child=box)
        if not self.query:
            folded = item.group in self.collapsed
            chevron = Gtk.Image.new_from_icon_name(
                "pan-end-symbolic" if folded else "pan-down-symbolic"
            )
            chevron.add_css_class("dim-label")
            box.append(chevron)
            row.set_tooltip_text("Déplier" if folded else "Replier")
        first = self.filter_model.get_n_items() > 0 and self.filter_model.get_item(0) is item
        row.set_margin_top(0 if first else 8)
        row.item = item
        return row

    def _on_row_activated(self, _listbox, row):
        item = getattr(row, "item", None)
        if item is None or item.kind != "header" or self.query:
            return
        if item.group in self.collapsed:
            self.collapsed.discard(item.group)
        else:
            self.collapsed.add(item.group)
        self.settings["collapsed"] = sorted(self.collapsed)
        save_settings(self.settings)
        self._refilter()

    def _refilter(self):
        self._recount_visible()
        self.filter.changed(Gtk.FilterChange.DIFFERENT)
        # Recrée les lignes (compteurs, chevrons, ligne trouvée en sous-titre).
        n = self.store.get_n_items()
        self.store.items_changed(0, n, n)
        self._reselect_current()

    def _create_row(self, item: FishItem) -> Gtk.Widget:
        if item.kind == "header":
            return self._create_header_row(item)
        row = Adw.ActionRow(title=item.name, activatable=True)
        row.set_use_markup(False)
        row.set_title_lines(1)
        row.set_subtitle_lines(1)

        icons = {
            "config": "emblem-system-symbolic",
            "confd": "system-run-symbolic",
            "function": "utilities-terminal-symbolic",
            "included": "changes-prevent-symbolic",
        }
        if item.shortcut is not None:
            icon = "insert-link-symbolic" if item.shortcut.kind == "alias" else "insert-text-symbolic"
        else:
            icon = icons.get(item.kind, "text-x-generic-symbolic")
        # add_prefix() ajoute à gauche : l'icône d'abord, puis le numéro devant.
        row.add_prefix(Gtk.Image.new_from_icon_name(icon))
        number = Gtk.Label(
            label=str(item.number),
            width_chars=3,
            xalign=1,
            css_classes=["dim-label", "numeric", "caption"],
        )
        row.add_prefix(number)

        subtitle = ""
        if item.kind == "config":
            subtitle = "Configuration principale"
        elif item.kind == "confd":
            subtitle = "Chargé au démarrage de fish"
        elif item.kind == "function":
            subtitle = item.description or "Sans description"
        elif item.kind == "included":
            subtitle = "Lecture seule" if item.readonly else str(item.path.parent)
        elif item.shortcut is not None:
            subtitle = item.shortcut.value
            label = item.shortcut.kind + ("\nremplacé" if item.overridden else "")
            tag = Gtk.Label(
                label=label,
                justify=Gtk.Justification.RIGHT,
                css_classes=["dim-label", "caption"],
            )
            row.add_suffix(tag)
            tip = f"{item.path.name}, ligne {item.shortcut.line}"
            if item.overridden:
                tip += "\nRedéfini dans votre configuration : c'est votre version qui compte."
            row.set_tooltip_text(tip)

        # Résultat trouvé dans le contenu : montrer la ligne concernée.
        if self.query and item.kind in FILE_KINDS and self.query.casefold() not in item.name.casefold():
            hit = parsing.first_match_line(item.text, self.query)
            if hit is not None:
                subtitle = f"l. {hit[0]} : {hit[1]}"
        row.set_subtitle(subtitle)
        row.item = item
        context_click = Gtk.GestureClick()
        context_click.set_button(3)
        context_click.connect("pressed", self._on_row_context_menu, row)
        row.add_controller(context_click)
        return row

    def _on_row_context_menu(self, gesture, _n_press, x, y, row):
        item = row.item
        if item.kind not in FILE_KINDS:
            return
        # Sélectionner sans passer par _on_row_selected : un clic droit ne doit ni
        # charger le fichier dans l'éditeur ni ouvrir le dialogue de sauvegarde.
        self.listbox.handler_block_by_func(self._on_row_selected)
        try:
            self.listbox.select_row(row)
            self.delete_btn.set_sensitive(
                item.kind in ("function", "confd") and not item.readonly
            )
        finally:
            self.listbox.handler_unblock_by_func(self._on_row_selected)

        # Menu construit à la main : des boutons reliés directement à leur rappel,
        # sans passer par des actions résolues dans l'arbre des widgets. Avec un
        # Gio.Menu, le popover était détaché avant que l'action ne soit activée et
        # les entrées restaient sans effet.
        popover = Gtk.Popover()
        popover.set_has_arrow(False)
        popover.set_halign(Gtk.Align.START)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_top(4)
        box.set_margin_bottom(4)
        box.set_margin_start(4)
        box.set_margin_end(4)

        def add_entry(label, callback, enabled=True):
            button = Gtk.Button(label=label)
            button.add_css_class("flat")
            button.set_halign(Gtk.Align.FILL)
            button.get_child().set_halign(Gtk.Align.START)
            button.set_sensitive(enabled)

            def on_clicked(_button):
                popover.popdown()
                # Après la fermeture, hors de la boucle du clic.
                GLib.idle_add(lambda: callback(item) and False)

            button.connect("clicked", on_clicked)
            box.append(button)

        add_entry("Ouvrir le dossier contenant le fichier", self._open_item_folder)
        add_entry("Renommer le fichier…", self._show_rename_dialog, self._can_rename(item))

        popover.set_child(box)
        popover.set_parent(row)
        point = Gdk.Rectangle()
        point.x, point.y, point.width, point.height = int(x), int(y), 1, 1
        popover.set_pointing_to(point)
        popover.connect("closed", lambda widget: GLib.idle_add(widget.unparent))
        popover.popup()

    def _context_item(self):
        """Ligne sélectionnée, clic droit compris : sa sélection est posée sans
        repasser par _on_row_selected."""
        row = self.listbox.get_selected_row()
        return getattr(row, "item", None)

    def _open_context_folder(self):
        item = self._context_item()
        if item is not None:
            self._open_item_folder(item)

    def _rename_context_item(self):
        item = self._context_item()
        if item is not None:
            self._show_rename_dialog(item)

    def _open_item_folder(self, item: FishItem):
        folder = item.path.parent.resolve()

        def fallback(reason=""):
            # Dernier recours : xdg-open sur le dossier.
            try:
                Gio.Subprocess.new(
                    ["xdg-open", str(folder)], Gio.SubprocessFlags.STDERR_SILENCE
                )
            except GLib.Error as e:
                self._toast(f"Impossible d’ouvrir le dossier : {reason or e.message}")

        launcher = Gtk.FileLauncher.new(Gio.File.new_for_path(str(item.path.resolve())))

        def done(source, result):
            try:
                source.open_containing_folder_finish(result)
            except GLib.Error as e:
                fallback(e.message)

        launcher.open_containing_folder(self, None, done)

    @staticmethod
    def _can_rename(item: FishItem) -> bool:
        return (
            not item.readonly
            and item.path.is_file()
            and os.access(item.path.parent, os.W_OK)
        )

    def _show_rename_dialog(self, item: FishItem):
        if not self._can_rename(item):
            self._toast("Ce fichier ne peut pas être renommé")
            return

        dialog = Adw.Dialog()
        dialog.set_title(f"Renommer « {item.path.name} »")
        dialog.set_content_width(440)
        dialog.set_content_height(190)

        header = Adw.HeaderBar()
        cancel = Gtk.Button(label="Annuler")
        cancel.connect("clicked", lambda *_: dialog.close())
        rename = Gtk.Button(label="Renommer")
        rename.add_css_class("suggested-action")
        header.pack_start(cancel)
        header.pack_end(rename)
        header.set_show_start_title_buttons(False)
        header.set_show_end_title_buttons(False)

        entry = Adw.EntryRow(title="Nouveau nom")
        entry.set_text(item.path.name)
        fields = Gtk.ListBox(css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE)
        fields.append(entry)
        body = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_top=18,
            margin_bottom=18,
            margin_start=18,
            margin_end=18,
        )
        body.append(fields)
        body.append(
            Gtk.Label(
                label="Le fichier restera dans le même dossier.",
                xalign=0,
                css_classes=["dim-label", "caption"],
            )
        )
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.append(header)
        content.append(body)
        dialog.set_child(content)

        def apply_rename(*_):
            new_name = entry.get_text()
            invalid_name = (
                not new_name
                or new_name in (".", "..")
                or Path(new_name).name != new_name
            )
            if invalid_name:
                entry.add_css_class("error")
                self._toast("Nom de fichier invalide")
                return
            entry.remove_css_class("error")
            if new_name == item.path.name:
                dialog.close()
                return
            if self._rename_file(item, new_name):
                dialog.close()

        rename.connect("clicked", apply_rename)
        entry.connect("entry-activated", apply_rename)
        dialog.present(self)
        entry.grab_focus()
        entry.select_region(0, -1)

    def _rename_file(self, item: FishItem, new_name: str) -> bool:
        old_path = item.path
        invalid_name = (
            not new_name
            or new_name in (".", "..")
            or Path(new_name).name != new_name
        )
        if invalid_name:
            self._toast("Nom de fichier invalide")
            return False
        target = old_path.with_name(new_name)
        if not self._can_rename(item):
            self._toast("Ce fichier ne peut pas être renommé")
            return False
        if target.exists() or target.is_symlink():
            self._toast(f"« {new_name} » existe déjà")
            return False
        try:
            old_path.rename(target)
        except OSError as e:
            self._toast(f"Impossible de renommer {old_path.name} : {e.strerror}")
            return False

        if self.current is not None and self.current.path == old_path:
            self.current.path = target
        if self.selected_key is not None and self.selected_key[1] == str(old_path):
            self.selected_key = (
                self.selected_key[0],
                str(target),
                *self.selected_key[2:],
            )
        self._populate()
        if self.current is not None and self.current.path == target:
            self._monitor_current_file()
            self._update_title()
        self._toast(f"{old_path.name} renommé en {new_name}")
        return True

    def _rows(self):
        i = 0
        while True:
            row = self.listbox.get_row_at_index(i)
            if row is None:
                return
            yield row
            i += 1

    def _on_global_search_changed(self, entry):
        self.query = entry.get_text().strip()
        self._refilter()
        empty = self.filter_model.get_n_items() == 0 and self.store.get_n_items() > 0
        self.empty_search.set_description(
            f"Rien ne correspond à « {self.query} »." if self.query else None
        )
        self.sidebar_stack.set_visible_child_name("empty" if empty else "list")

    def _recount_visible(self):
        self._recount_visible_for([self.store.get_item(i) for i in range(self.store.get_n_items())])

    def _on_global_search_activate(self, _entry):
        for row in self._rows():
            if row.item.kind != "header":
                self.listbox.select_row(row)
                self.view.grab_focus()
                return

    def _focus_global_search(self):
        self.global_search.grab_focus()
        self.global_search.select_region(0, -1)

    def _on_sort_changed(self, action, value):
        action.set_state(value)
        self.settings["sort"] = value.get_string()
        save_settings(self.settings)
        self._populate()

    # ---------- Nouveau fichier ----------
    def _show_new_dialog(self, kind: str):
        is_function = kind == "function"
        folder = "functions" if is_function else "conf.d"
        dialog = Adw.Dialog()
        dialog.set_title("Ajouter une fonction" if is_function else "Ajouter un fichier de démarrage")
        dialog.set_content_width(760)
        dialog.set_content_height(520)

        header = Adw.HeaderBar()
        cancel = Gtk.Button(label="Annuler")
        cancel.connect("clicked", lambda *_: dialog.close())
        create = Gtk.Button(label="Créer")
        create.add_css_class("suggested-action")
        header.pack_start(cancel)
        header.pack_end(create)
        header.set_show_start_title_buttons(False)
        header.set_show_end_title_buttons(False)

        name_row = Adw.EntryRow(title="Nom de la fonction" if is_function else "Nom du fichier")
        name_row.set_show_apply_button(False)
        name_row.add_css_class("property")
        name_list = Gtk.ListBox(css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE)
        name_list.append(name_row)

        code_buffer = GtkSource.Buffer()
        code_buffer.set_language(GtkSource.LanguageManager.get_default().get_language("fish"))
        code_buffer.set_highlight_syntax(True)
        code_buffer.set_style_scheme(self.buffer.get_style_scheme())
        code_view = GtkSource.View(buffer=code_buffer)
        code_view.set_monospace(True)
        code_view.set_show_line_numbers(True)
        code_view.set_auto_indent(True)
        code_view.set_indent_width(4)
        code_view.set_insert_spaces_instead_of_tabs(True)
        code_view.set_tab_width(4)
        code_view.set_left_margin(8)
        code_view.set_top_margin(8)
        code_scroll = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        code_scroll.set_child(code_view)

        hint = Gtk.Label(
            label=f"Le fichier sera créé dans ~/.config/fish/{folder}/",
            xalign=0,
            wrap=True,
            css_classes=["dim-label", "caption"],
        )
        if is_function:
            extra = "Laissez le code vide pour partir d'un modèle avec description."
        else:
            extra = "Fish charge ce fichier à chaque démarrage, avant config.fish."
        hint2 = Gtk.Label(label=extra, xalign=0, wrap=True, css_classes=["dim-label", "caption"])

        name_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        name_box.set_margin_top(18)
        name_box.set_margin_start(18)
        name_box.set_margin_end(18)
        name_box.append(name_list)
        name_box.append(hint)
        name_box.append(hint2)

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL, position=270)
        paned.set_start_child(name_box)
        paned.set_end_child(code_scroll)
        paned.set_shrink_start_child(False)
        paned.set_shrink_end_child(False)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.append(header)
        content.append(paned)
        dialog.set_child(content)

        def valid(name: str) -> bool:
            if not name:
                return False
            if is_function:
                return name.replace("_", "a").replace("-", "a").isalnum() and not name[0].isdigit()
            return all(c.isalnum() or c in "-_." for c in name) and not name.startswith(".")

        def create_file(*_):
            name = name_row.get_text().strip()
            if name.endswith(".fish"):
                name = name[:-5]
            if not valid(name):
                name_row.add_css_class("error")
                self._toast("Nom invalide")
                return
            name_row.remove_css_class("error")
            target_dir = fish_config_dir() / folder
            path = target_dir / f"{name}.fish"
            if path.exists():
                self._toast(f"« {name}.fish » existe déjà")
                return
            code = code_buffer.get_text(*code_buffer.get_bounds(), True)
            if is_function and not code.strip():
                code = f"function {name} --description ''\n    \nend\n"
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
                path.write_text(code, encoding="utf-8")
            except OSError as e:
                self._toast(f"Impossible de créer {name}.fish : {e.strerror}")
                return
            dialog.close()
            self._populate()
            self._toast(f"{name}.fish créé")
            self._select_key((kind, str(path), None))

        create.connect("clicked", create_file)
        name_row.connect("entry-activated", create_file)
        dialog.present(self)
        name_row.grab_focus()

    def _apply_scheme(self):
        dark = Adw.StyleManager.get_default().get_dark()
        sm = GtkSource.StyleSchemeManager.get_default()
        scheme = sm.get_scheme("Adwaita-dark" if dark else "Adwaita")
        if scheme is None:
            scheme = sm.get_scheme("classic-dark" if dark else "classic")
        if scheme is not None:
            self.buffer.set_style_scheme(scheme)

    # ---------- Dialogues ----------
    def _alert(self, heading, body, responses, callback, default=None, extra=None):
        """responses : liste de (id, libellé, apparence ou None)."""
        dlg = Adw.AlertDialog(heading=heading, body=body)
        for rid, label, appearance in responses:
            dlg.add_response(rid, label)
            if appearance is not None:
                dlg.set_response_appearance(rid, appearance)
        if default:
            dlg.set_default_response(default)
        dlg.set_close_response(responses[0][0])
        if extra is not None:
            dlg.set_extra_child(extra)
        dlg.connect("response", lambda _d, r: callback(r))
        dlg.present(self)
        return dlg

    # ---------- Shell ----------
    def _remove_legacy_reload(self):
        """Retire ce que Fisherman 0.3.0 avait installé pour recharger les
        terminaux ouverts, si l'utilisateur ne l'a pas modifié."""
        handler = fish_config_dir() / "conf.d" / LEGACY_HANDLER
        try:
            if handler.is_file() and handler.read_text(encoding="utf-8") == LEGACY_RELOAD_HANDLER_CODE:
                handler.unlink()
        except OSError:
            pass
        folder = Path(GLib.get_user_cache_dir()) / "fisherman" / "reload"
        if folder.is_dir():
            for f in folder.iterdir():
                if f.is_file() and (f.name == "seq" or (f.suffix == ".fish" and f.stem.isdigit())):
                    try:
                        f.unlink()
                    except OSError:
                        pass
            try:
                folder.rmdir()
            except OSError:
                pass

    def _terminal_command(self, fish_init: str) -> list[str] | None:
        fish_cmd = ["fish", "-C", fish_init]
        candidates = [
            ("ptyxis", ["ptyxis", "--new-window", "--"]),
            ("kgx", ["kgx", "--"]),
            ("gnome-terminal", ["gnome-terminal", "--"]),
            ("xdg-terminal-exec", ["xdg-terminal-exec"]),
        ]
        for program, prefix in candidates:
            if GLib.find_program_in_path(program):
                return prefix + fish_cmd
        return None

    def _try_current(self):
        item = self.current
        if item is None:
            return
        start, end = self.buffer.get_bounds()
        text = self.buffer.get_text(start, end, True)
        runtime = Path(GLib.get_user_runtime_dir()) / "fisherman"
        try:
            runtime.mkdir(parents=True, exist_ok=True)
            tmp = runtime / f"essai-{item.path.stem}.fish"
            tmp.write_text(text, encoding="utf-8")
        except OSError as e:
            self._toast(f"Impossible de préparer l'essai : {e.strerror}")
            return
        source = f"source {shlex.quote(str(tmp))}"

        def launch(init: str):
            argv = self._terminal_command(init)
            if argv is None:
                self._toast("Aucun terminal trouvé (Ptyxis, Console, GNOME Terminal)")
                return
            try:
                Gio.Subprocess.new(argv, Gio.SubprocessFlags.NONE)
            except GLib.Error as e:
                self._toast(f"Impossible d'ouvrir le terminal : {e.message}")

        if item.kind != "function":
            launch(source)
            return

        name = item.path.stem
        args_row = Adw.EntryRow(title="Arguments (facultatif)")
        args_list = Gtk.ListBox(css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE)
        args_list.append(args_row)

        def on_response(response):
            if response == "load":
                launch(source)
            elif response == "run":
                args = args_row.get_text().strip()
                launch(f"{source}; and {name}" + (f" {args}" if args else ""))

        dlg = self._alert(
            f"Essayer « {name} »",
            "Un terminal s'ouvre avec la version affichée dans l'éditeur, "
            "même non enregistrée. Votre configuration n'est pas modifiée.",
            [
                ("cancel", "Annuler", None),
                ("load", "Charger seulement", None),
                ("run", "Lancer", Adw.ResponseAppearance.SUGGESTED),
            ],
            on_response,
            default="run",
            extra=args_list,
        )

        def run_from_entry(*_):
            dlg.close()  # « Annuler » côté dialogue : sans effet
            on_response("run")

        args_row.connect("entry-activated", run_from_entry)
        GLib.idle_add(lambda: args_row.grab_focus() and False)

    def _reformat(self):
        if self.current is None or self.current.readonly:
            return
        start, end = self.buffer.get_bounds()
        text = self.buffer.get_text(start, end, True)
        new = parsing.indent(text)
        if new is None:
            self._toast("fish_indent a échoué : vérifiez la syntaxe")
            return
        if new == text:
            self._toast("Le code est déjà bien formaté")
            return
        line = self.buffer.get_iter_at_mark(self.buffer.get_insert()).get_line()
        self.buffer.begin_user_action()
        self.buffer.delete(start, end)
        self.buffer.insert(self.buffer.get_start_iter(), new)
        self.buffer.end_user_action()
        self._goto_line(line + 1, select=False)
        self._toast("Code reformaté (Ctrl+Z pour annuler)")

    # ---------- Suppression ----------
    def _on_delete_button_clicked(self, _button):
        row = self.listbox.get_selected_row()
        if row is None or not hasattr(row, "item"):
            return
        self._confirm_delete(row.item)

    def _confirm_delete(self, item: FishItem):
        self._alert(
            f"Supprimer « {item.name} » ?",
            f"Le fichier sera définitivement supprimé de « {item.path.parent} ».",
            [
                ("cancel", "Annuler", None),
                ("delete", "Supprimer", Adw.ResponseAppearance.DESTRUCTIVE),
            ],
            lambda r: self._delete_confirmed(r, item),
            default="cancel",
        )

    def _delete_confirmed(self, response, item):
        if response != "delete":
            return
        if self.current is not None and self.current.path == item.path and self.dirty:
            self.dirty = False
        self._delete_file(item)

    def _delete_file(self, item: FishItem):
        try:
            item.path.unlink()
        except OSError as e:
            self._toast(f"Impossible de supprimer {item.name} : {e.strerror}")
            return
        if self.current is not None and self.current.path == item.path:
            self._clear_editor()
        self._populate()
        self._toast(f"{item.name} supprimé")

    def _clear_editor(self):
        self.current = None
        self.selected_key = None
        self.dirty = False
        self.loading = True
        self.buffer.set_text("")
        self.loading = False
        self.view.set_sensitive(False)
        self.stack.set_visible_child_name("empty")
        self._update_title()
        self._monitor_current_file()

    # ---------- Alias fournis par un paquet ----------
    def _redefine_shortcut(self):
        row = self.listbox.get_selected_row()
        if row is None or row.item.shortcut is None:
            return
        item = row.item
        config = fish_config_dir() / "config.fish"
        if self.current is not None and self.current.path == config and self.dirty:
            self._toast("Enregistrez d'abord config.fish")
            return
        sc = item.shortcut
        addition = f"\n# Redéfini depuis {item.path.name} (ligne {sc.line})\n{sc.text.strip()}\n"
        try:
            existing = config.read_text(encoding="utf-8") if config.exists() else ""
            if existing and not existing.endswith("\n"):
                addition = "\n" + addition
            with config.open("a", encoding="utf-8") as fh:
                fh.write(addition)
        except OSError as e:
            self._toast(f"Impossible de modifier config.fish : {e.strerror}")
            return
        self._populate()
        total = len(config.read_text(encoding="utf-8").splitlines())
        target = None
        for i in range(self.store.get_n_items()):
            candidate = self.store.get_item(i)
            if (
                candidate.shortcut is not None
                and candidate.path == config
                and candidate.shortcut.line == total
            ):
                target = candidate
        self._open(target or self._file_item_for(config))
        self._toast(f"« {sc.name} » recopié dans config.fish : modifiez-le là")

    # ---------- Surveillance des fichiers ----------
    def _setup_file_monitors(self):
        self._clear_dir_monitors()
        cfg_dir = fish_config_dir()
        for path in (cfg_dir, cfg_dir / "functions", cfg_dir / "conf.d"):
            try:
                path.mkdir(parents=True, exist_ok=True)
                monitor = Gio.File.new_for_path(str(path)).monitor_directory(
                    Gio.FileMonitorFlags.WATCH_MOVES, None
                )
                monitor.connect("changed", self._on_directory_changed)
                self.dir_monitors.append(monitor)
            except (GLib.Error, OSError):
                pass

    def _clear_dir_monitors(self):
        for monitor in self.dir_monitors:
            monitor.cancel()
        self.dir_monitors.clear()

    def _monitor_current_file(self):
        if self.file_monitor is not None:
            self.file_monitor.cancel()
            self.file_monitor = None
        if self.current is None:
            return
        try:
            self.file_monitor = Gio.File.new_for_path(str(self.current.path)).monitor_file(
                Gio.FileMonitorFlags.WATCH_MOVES, None
            )
            self.file_monitor.connect("changed", self._on_current_file_changed)
        except GLib.Error:
            self.file_monitor = None

    def _on_directory_changed(self, *_):
        if self.refresh_source_id:
            GLib.source_remove(self.refresh_source_id)
        self.refresh_source_id = GLib.timeout_add(150, self._refresh_file_list)

    def _refresh_file_list(self):
        self.refresh_source_id = 0
        self._populate()
        return GLib.SOURCE_REMOVE

    def _on_current_file_changed(self, _monitor, _file, _other_file, event_type):
        if event_type not in (
            Gio.FileMonitorEvent.CHANGED,
            Gio.FileMonitorEvent.CHANGES_DONE_HINT,
            Gio.FileMonitorEvent.CREATED,
            Gio.FileMonitorEvent.MOVED_IN,
        ):
            return
        if self.dirty:
            return
        if self.reload_source_id:
            GLib.source_remove(self.reload_source_id)
        self.reload_source_id = GLib.timeout_add(120, self._reload_current_file)

    def _reload_current_file(self):
        self.reload_source_id = 0
        if self.current is not None and not self.dirty and self.current.path.exists():
            line = self.buffer.get_iter_at_mark(self.buffer.get_insert()).get_line()
            self._load(self.current)
            self._goto_line(line + 1, select=False)
        return GLib.SOURCE_REMOVE

    # ---------- Données ----------
    @staticmethod
    def _read(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def _sorted(self, paths):
        if self.settings.get("sort") == "date":
            def mtime(p):
                try:
                    return p.stat().st_mtime
                except OSError:
                    return 0
            return sorted(paths, key=mtime, reverse=True)
        return sorted(paths, key=lambda p: p.name.lower())

    def _populate(self):
        cfg_dir = fish_config_dir()
        config = cfg_dir / "config.fish"
        func_dir = cfg_dir / "functions"
        confd_dir = cfg_dir / "conf.d"

        functions = self._sorted(func_dir.glob("*.fish")) if func_dir.is_dir() else []
        confd = self._sorted(confd_dir.glob("*.fish")) if confd_dir.is_dir() else []
        included = []
        if config.exists():
            included = parsing.find_sources(config, cfg_dir, set(functions) | set(confd))

        groups: dict[str, list[FishItem]] = {kind: [] for kind, _ in GROUPS}
        if config.exists():
            groups["config"].append(FishItem(config, "config", self._read(config)))
        for p in confd:
            groups["confd"].append(FishItem(p, "confd", self._read(p)))
        for p in functions:
            groups["function"].append(FishItem(p, "function", self._read(p)))
        for p in included:
            groups["included"].append(FishItem(p, "included", self._read(p)))

        # Alias et abbr : config.fish, puis conf.d, puis fichiers inclus.
        user_names = set()
        for item in groups["config"] + groups["confd"] + groups["included"]:
            for sc in parsing.parse_shortcuts(item.text):
                entry = FishItem(item.path, "shortcut", shortcut=sc)
                if item.kind == "included":
                    entry.overridden = (sc.kind, sc.name) in user_names
                else:
                    user_names.add((sc.kind, sc.name))
                groups["shortcut"].append(entry)

        items: list[FishItem] = []
        self.counts = {}
        for kind, _ in GROUPS:
            items.append(GroupHeader(kind))
            for index, item in enumerate(groups[kind], start=1):
                item.number = index
                items.append(item)
            self.counts[kind] = len(groups[kind])

        self._recount_visible_for(items)
        self.store.splice(0, self.store.get_n_items(), items)

        if not any(self.counts.values()):
            self.status.set_description(f"Aucun fichier fish trouvé dans {cfg_dir}.")

        # Le fichier ouvert a pu changer d'état (lecture seule, suppression…)
        if self.current is not None:
            for item in items:
                if item.kind in FILE_KINDS and item.path == self.current.path:
                    self.current = item
                    break
        self._reselect_current()

    def _recount_visible_for(self, items):
        """Nombre d'éléments correspondant à la recherche, par groupe."""
        counts: dict[str, int] = {}
        for item in items:
            if item.kind == "header":
                continue
            if self.query and not item.matches(self.query):
                continue
            counts[item.kind] = counts.get(item.kind, 0) + 1
        self.visible_counts = counts

    def _file_item_for(self, path: Path) -> FishItem:
        for i in range(self.store.get_n_items()):
            item = self.store.get_item(i)
            if item.kind in FILE_KINDS and item.path == path:
                return item
        return FishItem(path, "included", self._read(path))

    def _load(self, item: FishItem) -> bool:
        self.loading = True
        try:
            text = item.path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            self._toast(f"Impossible de lire {item.name} : {e.strerror}")
            self.loading = False
            return False
        self.buffer.begin_irreversible_action()
        self.buffer.set_text(text)
        self.buffer.end_irreversible_action()
        self.buffer.place_cursor(self.buffer.get_start_iter())
        self.current = item
        self.dirty = False
        self.loading = False
        self.view.set_sensitive(True)
        self.view.set_editable(not item.readonly)
        self.stack.set_visible_child_name("editor")
        self._update_title()
        self._monitor_current_file()
        return True

    def _update_title(self):
        item = self.current
        if item is None:
            self.content_title.set_title("Aucun fichier")
            self.content_title.set_subtitle("")
            self.save_btn.set_sensitive(False)
            self.indent_btn.set_sensitive(False)
            self.try_btn.set_sensitive(False)
            self.readonly_banner.set_revealed(False)
            return
        title = item.path.stem if item.kind in ("function", "confd") else item.path.name
        self.content_title.set_title(("• " if self.dirty else "") + title)
        subtitle = str(item.path.parent)
        if item.readonly:
            subtitle += " — lecture seule"
        self.content_title.set_subtitle(subtitle)
        self.save_btn.set_sensitive(self.dirty and not item.readonly)
        self.indent_btn.set_sensitive(not item.readonly)
        self.try_btn.set_sensitive(True)
        self._update_banner()

    def _update_banner(self):
        item = self.current
        if item is None or not item.readonly:
            self.readonly_banner.set_revealed(False)
            return
        row = self.listbox.get_selected_row()
        selected = row.item if row is not None else None
        if selected is not None and selected.shortcut is not None and selected.path == item.path:
            self.readonly_banner.set_title(
                f"Fichier fourni par un paquet : « {selected.shortcut.name} » "
                "ne peut pas être modifié ici."
            )
            self.readonly_banner.set_button_label("Redéfinir dans config.fish")
        else:
            self.readonly_banner.set_title(
                "Fichier fourni par un paquet : lecture seule. "
                "Une mise à jour écraserait les modifications."
            )
            self.readonly_banner.set_button_label(None)
        self.readonly_banner.set_revealed(True)

    def _goto_line(self, line: int, select: bool = True):
        line = max(1, min(line, self.buffer.get_line_count()))
        ok, start = self.buffer.get_iter_at_line(line - 1)
        if not ok:
            return
        end = start.copy()
        if not end.ends_line():
            end.forward_to_line_end()
        if select:
            self.buffer.select_range(start, end)
        else:
            self.buffer.place_cursor(start)
        GLib.idle_add(self._scroll_to_cursor)

    def _scroll_to_cursor(self):
        self._reveal_iter(self.buffer.get_iter_at_mark(self.buffer.get_insert()))
        return GLib.SOURCE_REMOVE

    def _reveal_iter(self, it):
        """Fait défiler jusqu'à `it` sans décaler l'éditeur à l'horizontale
        tant que la ligne tient dans la largeur visible."""
        rect = self.view.get_iter_location(it)
        vadj = self.editor_scroll.get_vadjustment()
        hadj = self.editor_scroll.get_hadjustment()
        top, page = vadj.get_value(), vadj.get_page_size()
        if rect.y < top or rect.y + rect.height > top + page:
            vadj.set_value(max(0.0, rect.y - page * 0.3))
        hpage = hadj.get_page_size()
        if rect.x + rect.width + 40 < hpage:
            hadj.set_value(0.0)
        elif rect.x < hadj.get_value() or rect.x > hadj.get_value() + hpage - 40:
            hadj.set_value(max(0.0, rect.x - hpage * 0.5))

    def save(self, on_done=None) -> bool:
        """Enregistre après vérification de syntaxe.

        Renvoie True si le fichier est écrit tout de suite. En cas d'erreur de
        syntaxe, propose de corriger ou d'enregistrer quand même ; `on_done`
        est alors appelé après l'écriture forcée.
        """
        if self.current is None or not self.dirty:
            return True
        if self.current.readonly:
            self._toast("Fichier en lecture seule")
            return False
        start, end = self.buffer.get_bounds()
        text = self.buffer.get_text(start, end, True)
        error = parsing.check_syntax(text)
        if error is not None:
            line, message = error
            self._goto_line(line)

            def on_response(response):
                if response == "force" and self._write(text) and on_done is not None:
                    on_done()

            self._alert(
                f"Erreur de syntaxe à la ligne {line}",
                f"{message}\n\nLa ligne est sélectionnée dans l'éditeur.",
                [
                    ("fix", "Corriger", None),
                    ("force", "Enregistrer quand même", Adw.ResponseAppearance.DESTRUCTIVE),
                ],
                on_response,
                default="fix",
            )
            return False
        return self._write(text)

    def _write(self, text: str) -> bool:
        item = self.current
        try:
            item.path.write_text(text, encoding="utf-8")
        except OSError as e:
            self._toast(f"Échec de l'enregistrement : {e.strerror}")
            return False
        self.dirty = False
        self._update_title()
        self._toast(f"{item.path.name} enregistré")
        return True

    def _toast(self, msg: str):
        self.toast_overlay.add_toast(Adw.Toast(title=msg, timeout=3))

    # ---------- Recherche dans le fichier ----------
    def _toggle_search(self):
        enabled = not self.search_bar.get_search_mode()
        self.search_bar.set_search_mode(enabled)
        if enabled:
            self.search_entry.grab_focus()

    def _on_search_changed(self, entry):
        self.search_settings.set_search_text(entry.get_text() or None)

    def _on_search_next(self, *_):
        self._search_move(forward=True)

    def _on_search_prev(self, *_):
        self._search_move(forward=False)

    def _search_move(self, forward: bool):
        if not self.search_settings.get_search_text():
            return
        it = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        if forward:
            found, start, end, _wrapped = self.search_context.forward(it)
        else:
            found, start, end, _wrapped = self.search_context.backward(it)
        if found:
            self.buffer.select_range(start, end)
            GLib.idle_add(self._scroll_to_cursor)

    def _search_in_file(self, query: str):
        """Reporte la recherche globale dans la recherche du fichier."""
        self.search_entry.set_text(query)
        self.search_settings.set_search_text(query)
        self.search_bar.set_search_mode(True)
        self.buffer.place_cursor(self.buffer.get_start_iter())
        self._search_move(forward=True)

    # ---------- Signaux ----------
    def _on_buffer_changed(self, *_):
        if self.loading or self.current is None:
            return
        if not self.dirty:
            self.dirty = True
            self._update_title()

    def _on_row_selected(self, _listbox, row):
        if row is None:
            self.delete_btn.set_sensitive(False)
            return
        item = row.item
        self.delete_btn.set_sensitive(item.kind in ("function", "confd") and not item.readonly)
        if item.key == self.selected_key:
            return
        target = item.path
        if self.current is not None and target == self.current.path:
            self.selected_key = item.key
            self._after_open(item)
            return
        if self.dirty:
            self._reselect_current()

            def proceed():
                self._open(item)

            self._ask_save(proceed, proceed)
            return
        self._open(item)

    def _open(self, item: FishItem):
        file_item = item if item.kind in FILE_KINDS else self._file_item_for(item.path)
        if not self._load(file_item):
            return
        self.selected_key = item.key
        self._reselect_current()
        self._after_open(item)

    def _after_open(self, item: FishItem):
        if item.shortcut is not None:
            if self.query:
                self.search_entry.set_text(self.query)
                self.search_settings.set_search_text(self.query)
            self._goto_line(item.shortcut.line)
        elif self.query and self.query.casefold() in item.text.casefold():
            self._search_in_file(self.query)
        self._update_banner()

    def _select_key(self, key):
        # Déplie le groupe de l'élément s'il est replié.
        group = key[0] if key else None
        if group in self.collapsed and not self.query:
            self.collapsed.discard(group)
            self.settings["collapsed"] = sorted(self.collapsed)
            save_settings(self.settings)
            self._refilter()
        for row in self._rows():
            if row.item.key == key:
                self.listbox.select_row(row)
                return

    def _reselect_current(self):
        if self.selected_key is None:
            return
        self.listbox.handler_block_by_func(self._on_row_selected)
        try:
            target = None
            for row in self._rows():
                if row.item.key == self.selected_key:
                    target = row
                    break
            if target is None and self.current is not None:
                for row in self._rows():
                    if row.item.kind in FILE_KINDS and row.item.path == self.current.path:
                        target = row
                        break
            if target is not None:
                if self.listbox.get_selected_row() is not target:
                    self.listbox.select_row(target)
                self.delete_btn.set_sensitive(
                    target.item.kind in ("function", "confd") and not target.item.readonly
                )
            else:
                self.listbox.unselect_all()
        finally:
            self.listbox.handler_unblock_by_func(self._on_row_selected)

    def _on_close_request(self, *_):
        if not self.dirty:
            return False
        self._ask_save(on_saved=self.destroy, on_discard=self.destroy)
        return True

    def _ask_save(self, on_saved, on_discard):
        name = self.current.path.name if self.current else ""

        def handle(choice: str):
            if choice == "save":
                if self.save(on_done=on_saved):
                    on_saved()
            elif choice == "discard":
                self.dirty = False
                on_discard()

        self._alert(
            "Enregistrer les modifications ?",
            f"Le fichier « {name} » contient des modifications non enregistrées.",
            [
                ("cancel", "Annuler", None),
                ("discard", "Ignorer", Adw.ResponseAppearance.DESTRUCTIVE),
                ("save", "Enregistrer", Adw.ResponseAppearance.SUGGESTED),
            ],
            handle,
            default="save",
        )

    # ---------- Export / import ----------
    def _export(self):
        dialog = Gtk.FileDialog(
            title="Exporter la configuration fish",
            initial_name=f"fish-config-{time.strftime('%Y-%m-%d')}.tar.gz",
        )
        dialog.save(self, None, self._on_export_chosen)

    def _on_export_chosen(self, dialog, result):
        try:
            gfile = dialog.save_finish(result)
        except GLib.Error:
            return
        if gfile is None:
            return
        cfg_dir = fish_config_dir()
        files = []
        if (cfg_dir / "config.fish").is_file():
            files.append(cfg_dir / "config.fish")
        for sub in ("conf.d", "functions"):
            folder = cfg_dir / sub
            if folder.is_dir():
                files.extend(sorted(p for p in folder.glob("*.fish") if p.is_file()))
        try:
            with tarfile.open(gfile.get_path(), "w:gz") as tar:
                for path in files:
                    tar.add(path, arcname=str(path.relative_to(cfg_dir)), recursive=False)
        except (OSError, tarfile.TarError) as e:
            self._toast(f"Échec de l'export : {e}")
            return
        self._toast(f"{len(files)} fichiers exportés vers {gfile.get_basename()}")

    def _import(self):
        filters = Gio.ListStore(item_type=Gtk.FileFilter)
        archive = Gtk.FileFilter(name="Archives (.tar.gz)")
        archive.add_pattern("*.tar.gz")
        archive.add_pattern("*.tgz")
        filters.append(archive)
        dialog = Gtk.FileDialog(title="Importer une configuration fish", filters=filters)
        dialog.open(self, None, self._on_import_chosen)

    @staticmethod
    def _import_target(name: str) -> str | None:
        parts = [p for p in Path(name).parts if p not in (".", "")]
        if parts and parts[0] == "fish":
            parts = parts[1:]
        if any(p == ".." or p.startswith("/") for p in parts):
            return None
        if parts == ["config.fish"]:
            return "config.fish"
        if len(parts) == 2 and parts[0] in ("functions", "conf.d") and parts[1].endswith(".fish"):
            return "/".join(parts)
        return None

    def _on_import_chosen(self, dialog, result):
        try:
            gfile = dialog.open_finish(result)
        except GLib.Error:
            return
        if gfile is None:
            return
        cfg_dir = fish_config_dir()
        entries: dict[str, bytes] = {}
        try:
            with tarfile.open(gfile.get_path(), "r:*") as tar:
                for member in tar.getmembers():
                    if not member.isfile():
                        continue
                    target = self._import_target(member.name)
                    if target is None:
                        continue
                    fh = tar.extractfile(member)
                    if fh is not None:
                        entries[target] = fh.read()
        except (OSError, tarfile.TarError) as e:
            self._toast(f"Archive illisible : {e}")
            return
        if not entries:
            self._toast("Aucun fichier fish reconnu dans cette archive")
            return
        conflicts = []
        for rel, data in entries.items():
            dest = cfg_dir / rel
            if dest.exists() and dest.read_bytes() != data:
                conflicts.append(rel)

        def write(only_new: bool):
            written = 0
            for rel, data in entries.items():
                dest = cfg_dir / rel
                if dest.exists() and (only_new or dest.read_bytes() == data):
                    continue
                try:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(data)
                    written += 1
                except OSError:
                    continue
            self._populate()
            s_ = "s" if written > 1 else ""
            self._toast(f"{written} fichier{s_} importé{s_}")

        if not conflicts:
            body = f"{len(entries)} fichier{'s' if len(entries) > 1 else ''}, aucun ne remplace un fichier existant."
            responses = [
                ("cancel", "Annuler", None),
                ("all", "Importer", Adw.ResponseAppearance.SUGGESTED),
            ]
        else:
            listing = ", ".join(conflicts[:8]) + (" …" if len(conflicts) > 8 else "")
            verb = "remplacerait votre version" if len(conflicts) == 1 else "remplaceraient vos versions"
            body = f"{len(entries)} fichiers. {len(conflicts)} {verb} actuelle{'s' if len(conflicts) > 1 else ''} : {listing}"
            responses = [
                ("cancel", "Annuler", None),
                ("new", "Seulement les nouveaux", Adw.ResponseAppearance.SUGGESTED),
                ("all", "Tout remplacer", Adw.ResponseAppearance.DESTRUCTIVE),
            ]

        def on_response(response):
            if response == "all":
                write(only_new=False)
            elif response == "new":
                write(only_new=True)

        self._alert("Importer la configuration ?", body, responses, on_response, default="cancel")


class FishermanApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        about = Gio.SimpleAction(name="about")
        about.connect("activate", self._on_about)
        self.add_action(about)
        quit_action = Gio.SimpleAction(name="quit")
        quit_action.connect("activate", lambda *_: self._quit())
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<Control>q"])

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = FishermanWindow(self)
        win.present()

    def _quit(self):
        win = self.props.active_window
        if win:
            win.close()
        else:
            self.quit()

    def _on_about(self, *_):
        comments = "Éditeur de config.fish, de conf.d, des alias, abbr et fonctions fish."
        about = Adw.AboutDialog(
            application_name="Fisherman",
            application_icon=APP_ID,
            developer_name="Ugo Trevisiol",
            version=VERSION,
            comments=comments,
            license_type=Gtk.License.GPL_3_0,
            website="https://fishshell.com",
        )
        about.present(self.props.active_window)


def main() -> int:
    app = FishermanApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
