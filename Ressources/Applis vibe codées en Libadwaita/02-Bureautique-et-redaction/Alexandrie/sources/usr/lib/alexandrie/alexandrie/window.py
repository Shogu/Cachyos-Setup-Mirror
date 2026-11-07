"""Fenêtre principale d'Alexandrie."""

import html as _html
import json
import os
import urllib.parse

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk, Pango, WebKit  # noqa: E402

BIDI = GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE

from . import api, export, store, webpage  # noqa: E402
from .commons import CommonsView, ImageDialog, load_texture  # noqa: E402
from .mapview import MapCard, maps_available, open_in_maps, search_in_maps  # noqa: E402
from .prefs import PreferencesDialog  # noqa: E402

SPECIAL_NS = ("Catégorie:", "Portail:", "Spécial:", "Aide:", "Modèle:", "Projet:", "Wikipédia:",
              "Discussion:", "Utilisateur:", "Wikisource:", "Auteur:Index", "Vikidia:")
READING_SITES = ("wikipedia", "vikidia", "wikisource")


class Tab:
    """Un onglet de lecture : sa vue web, son article et son historique de navigation."""

    def __init__(self, win):
        self.win = win
        self.current = None          # {site, title, description, coords, qid}
        self.history, self.future = [], []
        self.toc_items = []
        self.related = []            # liens de la section « Voir aussi » (JS)
        self.similar = []            # articles proches (API)
        self.reperes_data = None     # {dates, coords} de Wikidata
        self.place = None            # lieu cité situé par clic droit {lat, lon, name, description}
        self.load_token = None
        self.fc_wired = False
        self.page = None

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.stack.add_named(Adw.StatusPage(
            icon_name=api.APP_ID, title="Alexandrie",
            description="Cherchez un article, un texte ou une image.\nCtrl+L pour aller à la recherche, "
                        "Ctrl+T pour un nouvel onglet."), "blank")
        self.stack.add_named(Adw.Spinner(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER,
                                         width_request=40, height_request=40), "loading")
        self.error_page = Adw.StatusPage(icon_name="network-error-symbolic", title="Erreur")
        self.stack.add_named(self.error_page, "error")

        self.web = WebKit.WebView(vexpand=True, hexpand=True)
        ws = self.web.get_settings()
        ws.set_javascript_can_access_clipboard(True)
        ws.set_enable_developer_extras(False)
        ws.set_enable_back_forward_navigation_gestures(False)
        ucm = self.web.get_user_content_manager()
        ucm.register_script_message_handler("alex", None)
        ucm.connect("script-message-received::alex", lambda _u, v: win._on_js(self, v))
        self.web.connect("decide-policy", win._on_policy)
        click = Gtk.GestureClick()
        click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        click.connect("pressed", lambda *_: win.suggest_pop.popdown())
        self.web.add_controller(click)
        self.stack.add_named(self.web, "article")
        self.stack.set_visible_child_name("blank")
        win._apply_web_bg(self.web)

    def run_js(self, script):
        self.web.evaluate_javascript(script, -1, None, None, None, None)

    @property
    def state(self):
        return self.stack.get_visible_child_name()


class AlexWindow(Adw.ApplicationWindow):
    # L'état de lecture appartient à l'onglet actif.
    tab = property(lambda self: self._tab_of(self.tabview.get_selected_page()))
    current = property(lambda self: self.tab.current if self.tab else None)
    history = property(lambda self: self.tab.history if self.tab else [])
    future = property(lambda self: self.tab.future if self.tab else [])
    toc_items = property(lambda self: self.tab.toc_items if self.tab else [])
    load_token = property(lambda self: self.tab.load_token if self.tab else None)
    web = property(lambda self: self.tab.web if self.tab else None)

    def __init__(self, app):
        super().__init__(application=app, title="Alexandrie")
        self.settings = app.settings
        self.favorites = store.Favorites()
        self.basket = store.Basket()
        self.recent = store.History()
        self.site = "wikipedia"
        self._tabs = {}
        self.toc_rows = {}
        self._map_shown = None
        self.summary_cache = {}
        self.ctx = {}
        self.hover_href = None
        self.search_token = None
        self.pending_pdf = None
        self._suppress_search = False
        self._switching = False
        self._shown_title = None
        self.commons_query = None

        self.set_default_size(self.settings.get_int("window-width"), self.settings.get_int("window-height"))
        self.set_size_request(360, 420)
        self.connect("close-request", self._save_size)

        self._build_actions()
        self._build_ui()
        self.settings.connect("changed", self._on_setting)
        self.basket.connect("changed", lambda *_: self._refresh_basket())
        self.favorites.connect("changed", lambda *_: self._refresh_favorites())
        Adw.StyleManager.get_default().connect("notify::dark", self._on_dark)
        self._refresh_basket()
        self._refresh_favorites()
        self._update_nav()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        self.toasts = Adw.ToastOverlay()
        self.set_content(self.toasts)
        tv = Adw.ToolbarView()
        self.toasts.set_child(tv)

        header = Adw.HeaderBar()
        tv.add_top_bar(header)
        tv.add_top_bar(self._build_findbar())

        self.side_btn = Gtk.ToggleButton(icon_name="sidebar-show-symbolic", tooltip_text="Barre latérale (F9)")
        header.pack_start(self.side_btn)
        nav = Gtk.Box(css_classes=["linked"])
        self.back_btn = Gtk.Button(icon_name="go-previous-symbolic", tooltip_text="Précédent (Alt+←)",
                                   action_name="win.back")
        self.fwd_btn = Gtk.Button(icon_name="go-next-symbolic", tooltip_text="Suivant (Alt+→)",
                                  action_name="win.forward")
        nav.append(self.back_btn)
        nav.append(self.fwd_btn)
        header.pack_start(nav)
        header.pack_start(Gtk.Button(icon_name="tab-new-symbolic", tooltip_text="Nouvel onglet (Ctrl+T)",
                                     action_name="win.new-tab"))
        self.sources = Adw.ToggleGroup(css_classes=["round"], valign=Gtk.Align.CENTER)
        self.sources.connect("notify::active-name", self._on_source)
        header.pack_start(self.sources)

        self.entry = Gtk.SearchEntry(placeholder_text="Rechercher dans Wikipédia", hexpand=True)
        self.entry.connect("search-changed", self._on_search_changed)
        self.entry.connect("activate", self._on_search_activate)
        self.entry.connect("stop-search", lambda *_: self.suggest_pop.popdown())
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_entry_key)
        self.entry.add_controller(keys)
        header.set_title_widget(Adw.Clamp(maximum_size=440, child=self.entry, hexpand=True))
        self._build_suggestions()

        menu = Gio.Menu()
        sec = Gio.Menu()
        sec.append("Copier l'article entier", "win.copy-article")
        sec.append("Exporter l'article en PDF…", "win.export-pdf")
        sec.append("Ouvrir dans le navigateur", "win.open-browser")
        menu.append_section(None, sec)
        sec2 = Gio.Menu()
        widths = Gio.Menu()
        widths.append("Normale", "win.reading-width::normal")
        widths.append("Large", "win.reading-width::wide")
        widths.append("Pleine largeur", "win.reading-width::full")
        sec.append_submenu("Largeur du texte", widths)
        sec2.append("Préférences", "win.preferences")
        sec2.append("Raccourcis clavier", "win.shortcuts")
        sec2.append("À propos d'Alexandrie", "app.about")
        menu.append_section(None, sec2)
        header.pack_end(Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu,
                                       primary=True, tooltip_text="Menu principal"))
        self.reperes_btn = Gtk.ToggleButton(icon_name="mark-location-symbolic", tooltip_text="Repères : dates, lieu et articles liés",
                                            sensitive=False)
        header.pack_end(self.reperes_btn)

        bbtn = self.basket_btn = Gtk.ToggleButton(tooltip_text="Afficher ou masquer le panier (Ctrl+B)")
        self._basket_sync = False
        ov = Gtk.Overlay(child=Gtk.Image(icon_name="alexandrie-basket-symbolic"))
        self.badge = Gtk.Label(css_classes=["alex-badge"], halign=Gtk.Align.END, valign=Gtk.Align.START)
        ov.add_overlay(self.badge)
        bbtn.set_child(ov)
        bbtn.connect("toggled", self._on_basket_toggled)
        header.pack_end(bbtn)

        self.find_btn = Gtk.ToggleButton(icon_name="edit-find-symbolic",
                                         tooltip_text="Rechercher dans l'article (Ctrl+F)", sensitive=False)
        self.find_btn.bind_property("active", self.findbar, "search-mode-enabled", BIDI)

        self.fav_btn = Gtk.MenuButton(icon_name="non-starred-symbolic", tooltip_text="Favori (Ctrl+D)",
                                      sensitive=False)
        self._build_fav_popover()
        header.pack_end(self.fav_btn)
        header.pack_end(self.find_btn)

        # Panneaux : barre latérale redimensionnable (Gtk.Paned) / contenu / Repères (droite)
        self.inner = Adw.OverlaySplitView(sidebar_position=Gtk.PackType.END, show_sidebar=False,
                                          min_sidebar_width=250, max_sidebar_width=360)
        self.sidebar = self._build_sidebar()
        self.sidebar.add_css_class("sidebar-pane")
        self.sidebar.set_size_request(250, -1)
        self.paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL, start_child=self.sidebar,
                               end_child=self.inner, resize_start_child=False, shrink_start_child=False,
                               shrink_end_child=False)
        self.paned.set_position(self.settings.get_int("sidebar-width"))
        tv.set_content(self.paned)
        self.side_btn.bind_property("active", self.sidebar, "visible", BIDI)
        self.reperes_btn.bind_property("active", self.inner, "show-sidebar", BIDI)

        self.inner.set_content(self._build_content())
        self.inner.set_sidebar(self._build_reperes())

        bp = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 1050sp"))
        bp.add_setter(self.inner, "collapsed", True)
        self.add_breakpoint(bp)

        self._rebuild_sources()
        self.side_btn.set_active(True)
        self.sidebar.connect("notify::visible", self._sync_basket_btn)
        self.side_tabs.connect("notify::active-name", self._sync_basket_btn)
        self.new_tab()

    def _build_findbar(self):
        self.findbar = Gtk.SearchBar(show_close_button=True)
        box = Gtk.Box(spacing=6)
        self.find_entry = Gtk.SearchEntry(placeholder_text="Rechercher dans l'article", width_chars=28)
        self.find_entry.connect("search-changed", self._find_changed)
        self.find_entry.connect("activate", lambda *_: self._find_step(1))
        self.find_entry.connect("next-match", lambda *_: self._find_step(1))
        self.find_entry.connect("previous-match", lambda *_: self._find_step(-1))
        self.find_entry.connect("stop-search", lambda *_: self.findbar.set_search_mode(False))
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._find_key)
        self.find_entry.add_controller(keys)
        nav = Gtk.Box(css_classes=["linked"])
        prev = Gtk.Button(icon_name="go-up-symbolic", tooltip_text="Occurrence précédente (Maj+Entrée)")
        prev.connect("clicked", lambda *_: self._find_step(-1))
        nxt = Gtk.Button(icon_name="go-down-symbolic", tooltip_text="Occurrence suivante (Entrée)")
        nxt.connect("clicked", lambda *_: self._find_step(1))
        nav.append(prev)
        nav.append(nxt)
        self.find_count = Gtk.Label(css_classes=["dim-label", "numeric"], width_chars=14, xalign=0)
        box.append(self.find_entry)
        box.append(nav)
        box.append(self.find_count)
        self.findbar.set_child(box)
        self.findbar.connect_entry(self.find_entry)
        self.findbar.connect("notify::search-mode-enabled", self._find_mode)
        return self.findbar

    def _find_controller(self):
        tab = self.tab
        if not tab:
            return None
        fc = tab.web.get_find_controller()
        if not tab.fc_wired:
            fc.connect("counted-matches", lambda _fc, n, t=tab: t is self.tab and self._find_show(n))
            fc.connect("found-text", lambda _fc, n, t=tab: t is self.tab and self._find_show(n))
            fc.connect("failed-to-find-text", lambda *_, t=tab: t is self.tab and self._find_show(0))
            tab.fc_wired = True
        return fc

    def _find_show(self, n):
        text = self.find_entry.get_text()
        if not text:
            self.find_count.set_label("")
            self.find_entry.remove_css_class("error")
            return
        self.find_count.set_label("Aucun résultat" if n == 0 else f"{n} résultat{'s' if n > 1 else ''}")
        (self.find_entry.add_css_class if n == 0 else self.find_entry.remove_css_class)("error")

    def _find_changed(self, entry):
        fc = self._find_controller()
        if fc is None:
            return
        text = entry.get_text()
        if not text:
            fc.search_finish()
            self._find_show(0)
            return
        opts = WebKit.FindOptions.CASE_INSENSITIVE | WebKit.FindOptions.WRAP_AROUND
        fc.count_matches(text, opts, 9999)
        fc.search(text, opts, 9999)

    def _find_step(self, direction):
        if not self.find_entry.get_text():
            return
        fc = self._find_controller()
        if fc:
            (fc.search_next if direction > 0 else fc.search_previous)()

    def _find_key(self, _c, keyval, _code, state):
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and state & Gdk.ModifierType.SHIFT_MASK:
            self._find_step(-1)
            return True
        return False

    def _find_mode(self, bar, _p):
        if bar.get_search_mode():
            self.find_entry.grab_focus()
            self.find_entry.select_region(0, -1)
            if self.find_entry.get_text():
                self._find_changed(self.find_entry)
        else:
            fc = self._find_controller()
            if fc:
                fc.search_finish()
            self.find_count.set_label("")
            if self.web:
                self.web.grab_focus()

    def _find_open(self):
        if self.content.get_visible_child_name() != "tabs" or not self.tab or self.tab.state != "article":
            self.entry.grab_focus()
            return
        self.findbar.set_search_mode(True)

    def _build_sidebar(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.side_tabs = Adw.ToggleGroup(margin_top=8, margin_bottom=8, margin_start=8, margin_end=8)
        self.side_stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, vexpand=True)
        self.side_tabs.connect("notify::active-name",
                               lambda g, _p: g.get_active_name() and self.side_stack.set_visible_child_name(g.get_active_name()))
        box.append(self.side_tabs)
        box.append(self.side_stack)

        # Sommaire
        self.toc_list = Gtk.ListBox(css_classes=["navigation-sidebar"])
        self.toc_list.connect("row-activated", lambda _l, row: self.run_js(f"alexScrollTo({json.dumps(row.toc_id)})"))
        self.toc_stack = Gtk.Stack()
        self.toc_stack.add_named(Adw.StatusPage(icon_name="view-list-symbolic", title="Sommaire",
                                                description="Le plan de l'article s'affiche ici.",
                                                css_classes=["compact"]), "empty")
        self.toc_stack.add_named(Gtk.ScrolledWindow(child=self.toc_list, vexpand=True), "list")
        self.side_stack.add_named(self.toc_stack, "sommaire")

        # Favoris
        fav = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.tag_flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, row_spacing=4, column_spacing=4,
                                    margin_start=8, margin_end=8, margin_bottom=6, max_children_per_line=12)
        self.tag_filter = set()
        fav.append(self.tag_flow)
        self.fav_list = Gtk.ListBox(css_classes=["navigation-sidebar"])
        self.fav_list.connect("row-activated", lambda _l, row: self.open_article(row.fav["site"], row.fav["title"]))
        self.fav_stack = Gtk.Stack(vexpand=True)
        self.fav_stack.add_named(Adw.StatusPage(icon_name="starred-symbolic", title="Vos favoris",
                                                description="Ajoutez un article avec l'étoile et classez-le avec vos propres tags.",
                                                css_classes=["compact"]), "empty")
        self.fav_stack.add_named(Gtk.ScrolledWindow(child=self.fav_list), "list")
        fav.append(self.fav_stack)
        self.side_stack.add_named(fav, "favoris")

        # Panier
        pan = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.basket_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.MULTIPLE,
                                       css_classes=["navigation-sidebar"])
        sc = Gtk.ShortcutController(scope=Gtk.ShortcutScope.LOCAL)
        sc.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("<Control>c"),
                                         Gtk.CallbackAction.new(lambda *_: self.copy_basket() or True)))
        sc.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("<Control>a"),
                                         Gtk.CallbackAction.new(lambda *_: self.basket_list.select_all() or True)))
        sc.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("Delete"),
                                         Gtk.CallbackAction.new(lambda *_: self._remove_selected() or True)))
        self.basket_list.add_controller(sc)
        self.basket_stack = Gtk.Stack(vexpand=True)
        self.basket_stack.add_named(Adw.StatusPage(
            icon_name="alexandrie-basket-symbolic", title="Panier d'extraits",
            description="Sélectionnez un passage, une image ou une date puis « Ajouter au panier ».",
            css_classes=["compact"]), "empty")
        self.basket_stack.add_named(Gtk.ScrolledWindow(child=self.basket_list), "list")
        pan.append(self.basket_stack)

        bottom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_top=6,
                         margin_bottom=10, margin_start=10, margin_end=10)
        src_list = Gtk.ListBox(css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE)
        num_row = Adw.SwitchRow(title="Numéroter les documents", subtitle="Document 1, 2… avec légende")
        self.settings.bind("basket-numbered", num_row, "active", Gio.SettingsBindFlags.DEFAULT)
        src_row = Adw.SwitchRow(title="Ajouter la source")
        self.settings.bind("basket-source", src_row, "active", Gio.SettingsBindFlags.DEFAULT)
        src_list.append(num_row)
        src_list.append(src_row)
        bottom.append(src_list)
        btns = Gtk.Box(spacing=6, homogeneous=True)
        copy = Gtk.Button(label="Copier", css_classes=["suggested-action"],
                          tooltip_text="Copier la sélection, ou tout le panier (Ctrl+C)")
        copy.connect("clicked", lambda *_: self.copy_basket())
        pdf = Gtk.Button(label="PDF…", tooltip_text="Exporter la fiche en PDF")
        pdf.connect("clicked", lambda *_: self.export_basket())
        bmenu = Gio.Menu()
        bmenu.append("Tout sélectionner", "win.basket-select-all")
        bmenu.append("Copier en texte brut", "win.basket-copy-plain")
        bmenu.append("Retirer la sélection", "win.basket-remove")
        more = Gtk.MenuButton(icon_name="view-more-symbolic", menu_model=bmenu, tooltip_text="Plus")
        clear = Gtk.Button(label="Vider", css_classes=["destructive-action"], tooltip_text="Vider le panier")
        clear.connect("clicked", lambda *_: self._confirm_clear())
        btns.append(copy)
        btns.append(pdf)
        btns.append(clear)
        addmenu = Gio.Menu()
        addmenu.append("Titre de partie", "win.basket-add-block::heading")
        addmenu.append("Consigne", "win.basket-add-block::instruction")
        addmenu.append("Note", "win.basket-add-block::note")
        add = Gtk.MenuButton(icon_name="list-add-symbolic", menu_model=addmenu,
                             tooltip_text="Ajouter un titre, une consigne ou une note")
        bx = Gtk.Box(spacing=6)
        bx.append(add)
        bx.append(btns)
        btns.set_hexpand(True)
        bx.append(more)
        bottom.append(bx)
        pan.append(bottom)
        self.side_stack.add_named(pan, "panier")
        self._rebuild_side_tabs()
        return box

    def _build_content(self):
        self.content = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.tabview = Adw.TabView(vexpand=True)
        self.tabview.connect("notify::selected-page", self._on_tab_switched)
        self.tabview.connect("close-page", self._on_close_page)
        self.tabbar = Adw.TabBar(view=self.tabview, autohide=True)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(self.tabbar)
        box.append(self.tabview)
        self.content.add_named(box, "tabs")

        self.commons = CommonsView()
        self.commons.connect("open-image", lambda _v, info: ImageDialog(self, info=info).present(self))
        self.content.add_named(self.commons, "commons")
        self.content.set_visible_child_name("tabs")

        # Popovers posés sur la vue web de l'onglet actif (re-parentés au changement d'onglet)
        self.hover_pop = Gtk.Popover(autohide=False, has_arrow=True, can_focus=False,
                                     position=Gtk.PositionType.BOTTOM, css_classes=["alex-preview"])
        self.def_pop = Gtk.Popover(position=Gtk.PositionType.BOTTOM)
        self.ctx_pop = Gtk.PopoverMenu(has_arrow=False, halign=Gtk.Align.START)
        self._popover_host = None
        return self.content

    # ------------------------------------------------------------ Onglets
    def _tab_of(self, page):
        return self._tabs.get(page.get_child()) if page else None

    def new_tab(self, select=True):
        tab = Tab(self)
        # Enregistré avant l'ajout : le premier onglet est sélectionné pendant append().
        self._tabs[tab.stack] = tab
        parent = self.tabview.get_selected_page()
        page = self.tabview.append(tab.stack) if select or parent is None else self.tabview.add_page(tab.stack, parent)
        page.set_title("Nouvel onglet")
        tab.page = page
        if select:
            self.tabview.set_selected_page(page)
        self._attach_popovers()
        return tab

    def _attach_popovers(self):
        """Les popovers d'article suivent la vue web de l'onglet actif."""
        web = self.web
        for pop in (self.hover_pop, self.def_pop, self.ctx_pop):
            if pop.get_parent() is web:
                continue
            pop.popdown()
            if pop.get_parent() is not None:
                pop.unparent()
            if web is not None:
                pop.set_parent(web)

    def _on_close_page(self, view, page):
        tab = self._tab_of(page)
        if tab:
            for pop in (self.hover_pop, self.def_pop, self.ctx_pop):
                if pop.get_parent() is tab.web:
                    pop.popdown()
                    pop.unparent()
            tab.load_token = None
        view.close_page_finish(page, True)
        if tab:
            self._tabs.pop(tab.stack, None)
        if view.get_n_pages() == 0:
            self.new_tab()
            self.entry.set_text("")
            self.entry.grab_focus()
        return Gdk.EVENT_STOP

    def close_tab(self):
        page = self.tabview.get_selected_page()
        if page:
            self.tabview.close_page(page)

    def _on_tab_switched(self, *_):
        tab = self.tab
        if not tab:
            return
        self._attach_popovers()
        self.findbar.set_search_mode(False)
        cur = tab.current
        self.set_title(f"{cur['title']} — Alexandrie" if cur else "Alexandrie")
        self._suppress_search = True
        self._shown_title = cur["title"] if cur else None
        self.entry.set_text(cur["title"] if cur else "")
        self._suppress_search = False
        if cur and cur["site"] != self.site and self.content.get_visible_child_name() == "tabs":
            self._select_source(cur["site"])
        self._render_toc(tab)
        self._render_reperes(tab)
        self._update_nav()
        self._update_fav_button()

    def _show_state(self, tab, name):
        tab.stack.set_visible_child_name(name)
        if tab.page:
            tab.page.set_loading(name == "loading")
        if tab is self.tab:
            self.content.set_visible_child_name("tabs")

    def _build_reperes(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, margin_top=12,
                      margin_bottom=12, margin_start=12, margin_end=12)
        self.dates_group = Adw.PreferencesGroup(title="Dates clés",
                                                description="Cliquez une date pour l'ajouter au panier.")
        self.date_rows = []
        box.append(self.dates_group)
        self.map_card = MapCard(self)
        box.append(self.map_card)
        self.related_group = Adw.PreferencesGroup(title="Voir aussi")
        self.related_rows = []
        box.append(self.related_group)
        return Gtk.ScrolledWindow(child=box, hscrollbar_policy=Gtk.PolicyType.NEVER)

    def _build_suggestions(self):
        self.suggest_list = Gtk.ListBox(css_classes=["navigation-sidebar"])
        self.suggest_list.connect("row-activated", lambda _l, row: hasattr(row, "title") and
                                  self.open_article(getattr(row, "site", self.site), row.title))
        sw = Gtk.ScrolledWindow(child=self.suggest_list, propagate_natural_height=True,
                                max_content_height=420, width_request=420,
                                hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.suggest_pop = Gtk.Popover(child=sw, autohide=False, has_arrow=False, halign=Gtk.Align.START,
                                       position=Gtk.PositionType.BOTTOM)
        self.suggest_pop.set_parent(self.entry)
        focus = Gtk.EventControllerFocus()
        focus.connect("leave", lambda *_: GLib.timeout_add(150, self._maybe_hide_suggestions))
        focus.connect("enter", self._on_entry_focus)
        self.entry.add_controller(focus)

    def _maybe_hide_suggestions(self):
        if not (self._entry_focused() or self.suggest_list.get_focus_child()):
            self.suggest_pop.popdown()
        return False

    def _build_fav_popover(self):
        pop = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=6, margin_bottom=6,
                      margin_start=6, margin_end=6, width_request=300)
        self.fav_title = Gtk.Label(xalign=0, css_classes=["heading"])
        box.append(self.fav_title)
        lb = Gtk.ListBox(css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE)
        self.fav_entry = Adw.EntryRow(title="Tags, séparés par des virgules")
        self.fav_entry.connect("entry-activated", lambda *_: self._save_fav())
        lb.append(self.fav_entry)
        box.append(lb)
        self.fav_tag_flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=6,
                                        row_spacing=4, column_spacing=4)
        box.append(self.fav_tag_flow)
        btns = Gtk.Box(spacing=6, halign=Gtk.Align.END)
        self.fav_remove = Gtk.Button(label="Retirer", css_classes=["destructive-action"])
        self.fav_remove.connect("clicked", self._remove_fav)
        save = Gtk.Button(label="Enregistrer", css_classes=["suggested-action"])
        save.connect("clicked", lambda *_: self._save_fav())
        btns.append(self.fav_remove)
        btns.append(save)
        box.append(btns)
        pop.set_child(box)
        pop.connect("show", self._fill_fav_popover)
        self.fav_btn.set_popover(pop)
        self.fav_pop = pop

    # ------------------------------------------------------------ Actions
    def _build_actions(self):
        def add(name, cb, accels=None):
            a = Gio.SimpleAction.new(name, None)
            a.connect("activate", lambda *_: cb())
            self.add_action(a)
            if accels:
                self.get_application().set_accels_for_action(f"win.{name}", accels)
            return a

        add("back", self.go_back, ["<Alt>Left", "<Alt>KP_Left"])
        add("forward", self.go_forward, ["<Alt>Right"])
        add("focus-search", lambda: self.entry.grab_focus(), ["<Control>l", "<Control>k"])
        add("find", self._find_open, ["<Control>f"])
        self.add_action(self.settings.create_action("reading-width"))
        add("toggle-sidebar", lambda: self.side_btn.set_active(not self.side_btn.get_active()), ["F9"])
        add("preferences", lambda: PreferencesDialog(self.settings).present(self), ["<Control>comma"])
        add("shortcuts", self._show_shortcuts, ["<Control>question"])
        add("copy-article", lambda: self._request_article("copy"), ["<Control><Shift>a"])
        add("export-pdf", self.export_article, ["<Control>p"])
        add("favorite", lambda: self.current and self.fav_btn.popup(), ["<Control>d"])
        add("open-browser", self._open_browser)
        add("show-basket", lambda: self.basket_btn.set_active(not self.basket_btn.get_active()), ["<Control>b"])
        add("basket-select-all", lambda: self.basket_list.select_all())
        add("basket-copy-plain", lambda: self.copy_basket(plain=True))
        add("basket-remove", self._remove_selected)
        add("basket-clear", self._confirm_clear)
        add("ctx-copy-rich", lambda: self._ctx_copy(False))
        add("ctx-copy-plain", lambda: self._ctx_copy(True))
        add("ctx-add-text", self._ctx_add_text)
        add("ctx-add-image", self._ctx_add_image)
        add("ctx-image", lambda: self.ctx.get("img", {}).get("file") and
            ImageDialog(self, file_title=self.ctx["img"]["file"]).present(self))
        add("ctx-map-app", self._ctx_map_app)
        add("ctx-map-panel", self._ctx_map_panel)
        add("ctx-open-tab", lambda: self.ctx.get("link") and self._open_link(self.ctx["link"]["href"], new_tab=True))
        add("new-tab", self._new_tab_focus, ["<Control>t"])
        add("close-tab", self.close_tab, ["<Control>w"])
        blk = Gio.SimpleAction.new("basket-add-block", GLib.VariantType.new("s"))
        blk.connect("activate", lambda _a, v: self._edit_block(None, v.get_string()))
        self.add_action(blk)
        add("ctx-define", lambda: self.ctx.get("word") and self.run_js(f"alexDefineAt({json.dumps(self.ctx['word'])})"))

    # ------------------------------------------------------------ Outils
    def toast(self, text, button=None, callback=None):
        t = Adw.Toast(title=text, timeout=3)
        if button:
            t.set_button_label(button)
            t.connect("button-clicked", lambda *_: callback())
        self.toasts.add_toast(t)

    def run_js(self, script):
        if self.tab:
            self.tab.run_js(script)

    def _run_js_all(self, script):
        for tab in self._tabs.values():
            tab.run_js(script)

    def _new_tab_focus(self):
        self.new_tab()
        if self.content.get_visible_child_name() != "tabs":
            self._select_source("wikipedia" if self.site == "commons" else self.site)
            self.content.set_visible_child_name("tabs")
        self.entry.set_text("")
        self.entry.grab_focus()

    def set_clipboard(self, text, html=None):
        data = text.encode("utf-8")
        providers = [Gdk.ContentProvider.new_for_bytes("text/plain;charset=utf-8", GLib.Bytes.new(data)),
                     Gdk.ContentProvider.new_for_bytes("text/plain", GLib.Bytes.new(data))]
        if html:
            doc = f'<html><head><meta charset="utf-8"></head><body>{html}</body></html>'
            providers.insert(0, Gdk.ContentProvider.new_for_bytes("text/html", GLib.Bytes.new(doc.encode("utf-8"))))
        self.get_clipboard().set_content(Gdk.ContentProvider.new_union(providers))

    def _basket_shown(self):
        return self.sidebar.get_visible() and self.side_tabs.get_active_name() == "panier"

    def _on_basket_toggled(self, btn):
        if self._basket_sync:
            return
        if btn.get_active():
            self.show_sidebar_page("panier")
        else:
            self.side_btn.set_active(False)

    def _sync_basket_btn(self, *_):
        self._basket_sync = True
        self.basket_btn.set_active(self._basket_shown())
        self._basket_sync = False

    def show_sidebar_page(self, name):
        if name == "sommaire" and not self.settings.get_boolean("show-toc"):
            return
        self.side_btn.set_active(True)
        self.side_tabs.set_active_name(name)

    def _point(self, x, y, w=1, h=1):
        r = Gdk.Rectangle()
        r.x, r.y, r.width, r.height = int(x), int(y), max(1, int(w)), max(1, int(h))
        return r

    def _save_size(self, *_):
        w, h = self.get_default_size()
        if self.sidebar.get_visible():
            self.settings.set_int("sidebar-width", self.paned.get_position())
        if not self.is_maximized():
            self.settings.set_int("window-width", w)
            self.settings.set_int("window-height", h)
        return False

    def _apply_web_bg(self, web):
        dark = Adw.StyleManager.get_default().get_dark()
        c = Gdk.RGBA()
        c.parse("#1d1d20" if dark else "#ffffff")
        web.set_background_color(c)

    def _on_dark(self, *_):
        for tab in self._tabs.values():
            self._apply_web_bg(tab.web)
        self._run_js_all(f"window.alexSetDark && alexSetDark({json.dumps(Adw.StyleManager.get_default().get_dark())})")

    # ------------------------------------------------------- Sources & onglets
    SOURCES = [
        ("wikipedia", "Encyclopédie", "Articles de Wikipédia", None),
        ("vikidia", "Vikidia", "Vikidia, l'encyclopédie des 8-13 ans : articles plus courts et plus simples",
         "enable-vikidia"),
        ("wikisource", "Textes", "Œuvres et documents historiques de Wikisource", "enable-wikisource"),
        ("commons", "Images", "Images en haute définition de Wikimedia Commons", "enable-commons"),
    ]
    PLACEHOLDERS = {"wikipedia": "Rechercher dans l'encyclopédie", "vikidia": "Rechercher dans Vikidia",
                    "wikisource": "Rechercher un texte", "commons": "Rechercher des images"}

    def _rebuild_sources(self):
        want = [w for w in self.SOURCES if w[3] is None or self.settings.get_boolean(w[3])]
        names = [w[0] for w in want]
        active = self.site if self.site in names else "wikipedia"
        self._switching = True
        self.sources.remove_all()
        for name, label, tip, _key in want:
            self.sources.add(Adw.Toggle(name=name, label=label, tooltip=tip))
        self.sources.set_visible(len(want) > 1)
        self.sources.set_active_name(active)
        self._switching = False

    def _select_source(self, name):
        """Change l'onglet de source sans relancer de recherche."""
        self._switching = True
        self.sources.set_active_name(name)
        self._switching = False
        self.site = self.sources.get_active_name() or name

    def _rebuild_side_tabs(self):
        current = self.side_tabs.get_active_name()
        self.side_tabs.remove_all()
        tabs = []
        if self.settings.get_boolean("show-toc"):
            tabs.append(("sommaire", "Sommaire"))
        tabs += [("favoris", "Favoris"), ("panier", "Panier")]
        for name, label in tabs:
            self.side_tabs.add(Adw.Toggle(name=name, label=label))
        self.side_tabs.set_active_name(current if current in dict(tabs) else tabs[0][0])

    def _on_source(self, group, _p):
        name = group.get_active_name()
        if not name:
            return
        self.site = name
        self.suggest_pop.popdown()
        self.entry.set_placeholder_text(self.PLACEHOLDERS[name])
        if self._switching:
            return
        # On reprend la recherche en cours dans la nouvelle source.
        query = self.entry.get_text().strip()
        if name == "commons":
            self.content.set_visible_child_name("commons")
            if query and query != self.commons_query:
                self.commons_query = query
                self.commons.search(query)
            return
        self.content.set_visible_child_name("tabs")
        cur = self.current
        if cur and cur["site"] == name and (not query or query == cur["title"]):
            return
        if query:
            self.open_article(name, query)

    def _on_setting(self, settings, key):
        if key in ("enable-wikisource", "enable-commons", "enable-vikidia"):
            self._rebuild_sources()
        elif key == "show-toc":
            self._rebuild_side_tabs()
        elif key == "reading-width":
            self._run_js_all(f"window.alexSetWidth && alexSetWidth({json.dumps(settings.get_string(key))})")
        elif key == "copy-format":
            self._run_js_all(f"window.alexSetCopyMode && alexSetCopyMode({json.dumps(settings.get_string(key))})")
        elif key in ("link-preview", "dictionary", "hide-references"):
            if self.current:
                self.open_article(self.current["site"], self.current["title"], push=False)
        elif key in ("show-key-dates", "show-map", "maps-button", "reperes-auto", "show-related"):
            if self.tab and self.current:
                self._load_reperes(self.tab)
        elif key == "search-history" and not settings.get_boolean(key):
            self.suggest_pop.popdown()

    # ------------------------------------------------------------ Recherche et historique
    def _history_on(self):
        return self.settings.get_boolean("search-history")

    def _on_search_changed(self, entry):
        text = entry.get_text().strip()
        if self._suppress_search or (text and text == self._shown_title):
            self.suggest_pop.popdown()
            return
        if self.site == "commons":
            self.suggest_pop.popdown()
            return
        if len(text) < 2:
            self._show_suggestions(None, [], None, history_only=True)
            return
        token = self.search_token = object()
        site = self.site
        api.run_async(api.search_titles, lambda r, e: self._show_suggestions(token, r, e), site, text)

    def _on_entry_focus(self, *_):
        if not self.entry.get_text().strip() and self.site != "commons":
            self._show_suggestions(None, [], None, history_only=True)

    def _history_row(self, h):
        sub = h.get("description") or ""
        if h["site"] != self.site:
            sub = api.SITE_LABELS.get(h["site"], "") + (" · " + sub if sub else "")
        row = Adw.ActionRow(title=h["title"], subtitle=sub, activatable=True, use_markup=False, subtitle_lines=1)
        row.title, row.site = h["title"], h["site"]
        row.add_prefix(Gtk.Image(icon_name="document-open-recent-symbolic"))
        rm = Gtk.Button(icon_name="window-close-symbolic", valign=Gtk.Align.CENTER,
                        css_classes=["flat", "circular"], tooltip_text="Retirer de l'historique")
        rm.connect("clicked", lambda *_: self._forget(h))
        row.add_suffix(rm)
        return row

    def _forget(self, h):
        self.recent.remove(h["site"], h["title"])
        text = self.entry.get_text().strip()
        if len(text) < 2:
            self._show_suggestions(None, [], None, history_only=True)
        else:
            self._on_search_changed(self.entry)

    def _clear_history(self):
        self.recent.clear()
        self.suggest_pop.popdown()
        self.toast("Historique effacé")

    def _show_suggestions(self, token, results, err, history_only=False):
        if not history_only and (token is not self.search_token or err):
            return
        if self.tab and self.tab.state == "loading":
            return
        text = self.entry.get_text().strip()
        self.suggest_list.remove_all()
        hist = []
        if self._history_on():
            hist = self.recent.items[:10] if not text else self.recent.matching(text, limit=3)
        titles = set()
        for h in hist:
            self.suggest_list.append(self._history_row(h))
            titles.add((h["site"], h["title"]))
        for res in results or []:
            if (self.site, res["title"]) in titles:
                continue
            row = Adw.ActionRow(title=res["title"], subtitle=res["description"], activatable=True,
                                use_markup=False, subtitle_lines=1)
            row.title, row.site = res["title"], self.site
            if res.get("thumb"):
                pic = Gtk.Picture(content_fit=Gtk.ContentFit.COVER, width_request=36, height_request=36,
                                  can_shrink=True, valign=Gtk.Align.CENTER)
                pic.set_overflow(Gtk.Overflow.HIDDEN)
                pic.add_css_class("alex-thumb")
                load_texture(res["thumb"], lambda t, p=pic: t and p.set_paintable(t))
                row.add_prefix(pic)
            else:
                row.add_prefix(Gtk.Image(icon_name="text-x-generic-symbolic", pixel_size=24))
            self.suggest_list.append(row)
        if hist and not text:
            clear = Gtk.Button(label="Effacer l'historique", css_classes=["flat"], halign=Gtk.Align.CENTER,
                               margin_top=4, margin_bottom=4)
            clear.connect("clicked", lambda *_: self._clear_history())
            r = Gtk.ListBoxRow(child=clear, activatable=False, selectable=False)
            self.suggest_list.append(r)
        if (hist or results) and self._entry_focused():
            self.suggest_pop.popup()
        else:
            self.suggest_pop.popdown()

    def _entry_focused(self):
        return self.entry.has_focus() or self.entry.get_focus_child() is not None

    def _on_entry_key(self, _c, keyval, _code, _state):
        if keyval == Gdk.KEY_Down and self.suggest_pop.get_visible():
            row = self.suggest_list.get_row_at_index(0)
            if row:
                row.grab_focus()
                return True
        return False

    def _on_search_activate(self, entry):
        text = entry.get_text().strip()
        self.search_token = None  # ignore les suggestions encore en route
        if not text:
            return
        self.suggest_pop.popdown()
        if self.site == "commons":
            self.commons_query = text
            self.commons.search(text)
            return
        self.open_article(self.site, text)

    # ------------------------------------------------------------ Navigation
    def open_article(self, site, title, push=True, new_tab=False, background=False):
        self.suggest_pop.popdown()
        self.hover_pop.popdown()
        if site not in READING_SITES:
            site = "wikipedia"
        tab = self.new_tab(select=not background) if (new_tab or not self.tab) else self.tab
        if push and tab.current and (tab.current["site"], tab.current["title"]) != (site, title):
            tab.history.append((tab.current["site"], tab.current["title"]))
            tab.future.clear()
        if tab is self.tab:
            if self.site != site:
                self._select_source(site)
            self.content.set_visible_child_name("tabs")
        if tab.page:
            tab.page.set_title(title)
        self._show_state(tab, "loading")
        token = tab.load_token = object()
        api.run_async(api.load_article, lambda r, e: self._on_article(tab, token, r, e), site, title)

    def _on_article(self, tab, token, data, err):
        if token is not tab.load_token or tab.stack.get_parent() is None:
            return
        active = tab is self.tab
        if err:
            if isinstance(err, api.NotFound):
                tab.error_page.set_icon_name("edit-find-symbolic")
                tab.error_page.set_title("Article introuvable")
                tab.error_page.set_description(f"Aucune page ne correspond à « {GLib.markup_escape_text(str(err))} ».")
            else:
                tab.error_page.set_icon_name("network-error-symbolic")
                tab.error_page.set_title("Connexion impossible")
                tab.error_page.set_description(GLib.markup_escape_text(str(err)))
            self._show_state(tab, "error")
            if tab.page:
                tab.page.set_title("Erreur")
            if active:
                self._update_nav()
            return
        s = data["summary"]
        tab.current = {"site": data["site"], "title": data["title"], "description": s.get("description", ""),
                       "coords": s.get("coords"), "qid": s.get("qid")}
        tab.toc_items, tab.related, tab.similar, tab.reperes_data, tab.place = [], [], [], None, None
        if tab.page:
            tab.page.set_title(data["title"])
            tab.page.set_tooltip(f"{data['title']} — {api.SITE_LABELS[data['site']]}")
        if self._history_on():
            self.recent.add(data["site"], data["title"], tab.current["description"])
        page = webpage.build(
            api.SITES[data["site"]], data["title"], tab.current["description"], data["body"],
            dark=Adw.StyleManager.get_default().get_dark(),
            hide_refs=self.settings.get_boolean("hide-references"),
            copy_mode=self.settings.get_string("copy-format"),
            link_preview=self.settings.get_boolean("link-preview"),
            dictionary=self.settings.get_boolean("dictionary"),
            width=self.settings.get_string("reading-width"))
        tab.web.load_html(page, f"https://{api.SITES[data['site']]}/wiki/")
        self._show_state(tab, "article")
        if active:
            self.set_title(f"{data['title']} — Alexandrie")
            self._suppress_search = True
            self._shown_title = data["title"]
            self.entry.set_text(data["title"])
            self.entry.set_position(-1)
            self._suppress_search = False
            self.findbar.set_search_mode(False)
            self._render_toc(tab)
            self._update_nav()
            self._update_fav_button()
        self._load_reperes(tab)

    def _on_policy(self, _web, decision, dtype):
        # Les clics sont gérés en JS ; on bloque toute navigation imprévue.
        if dtype == WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            action = decision.get_navigation_action()
            if action.get_navigation_type() == WebKit.NavigationType.LINK_CLICKED:
                decision.ignore()
                self._open_link(action.get_request().get_uri())
                return True
        elif dtype == WebKit.PolicyDecisionType.NEW_WINDOW_ACTION:
            decision.ignore()
            return True
        return False

    def go_back(self):
        if self.history and self.current:
            self.future.append((self.current["site"], self.current["title"]))
            self.open_article(*self.history.pop(), push=False)

    def go_forward(self):
        if self.future and self.current:
            self.history.append((self.current["site"], self.current["title"]))
            self.open_article(*self.future.pop(), push=False)

    def _update_nav(self):
        self.lookup_action("back").set_enabled(bool(self.history))
        self.lookup_action("forward").set_enabled(bool(self.future))
        has = self.current is not None
        for name in ("copy-article", "export-pdf", "open-browser", "favorite"):
            self.lookup_action(name).set_enabled(has)
        self.fav_btn.set_sensitive(has)
        self.find_btn.set_sensitive(has)

    def _open_browser(self):
        if self.current:
            Gtk.UriLauncher(uri=api.page_url(self.current["site"], self.current["title"])).launch(self, None, None, None)

    def _site_enabled(self, site):
        key = {"wikisource": "enable-wikisource", "vikidia": "enable-vikidia"}.get(site)
        return key is None or self.settings.get_boolean(key)

    def _open_link(self, href, new_tab=False):
        u = urllib.parse.urlparse(href)
        site = api.HOST_TO_SITE.get(u.netloc)
        if site and u.path.startswith("/wiki/"):
            title = urllib.parse.unquote(u.path[6:]).replace("_", " ")
            if title.startswith(("Fichier:", "File:", "Image:")):
                ImageDialog(self, file_title=title).present(self)
                return
            if self._site_enabled(site) and not title.startswith(SPECIAL_NS):
                if u.fragment and self.current and title == self.current["title"] and not new_tab:
                    self.run_js(f"alexScrollTo({json.dumps(u.fragment)})")
                else:
                    self.open_article(site, title, new_tab=new_tab, background=new_tab)
                    if new_tab:
                        self.toast(f"« {title} » ouvert dans un nouvel onglet")
                return
        if u.scheme in ("http", "https", "mailto"):
            Gtk.UriLauncher(uri=href).launch(self, None, None, None)

    # ------------------------------------------------------------ Repères
    def _load_reperes(self, tab):
        tab.reperes_data, tab.similar = None, []
        token = tab.load_token
        if tab is self.tab:
            self._render_reperes(tab)
        cur = tab.current
        if not cur:
            return
        want_dates = self.settings.get_boolean("show-key-dates")
        want_map = self.settings.get_boolean("show-map")

        def got(r, _e):
            if token is tab.load_token:
                tab.reperes_data = r or {}
                if tab is self.tab:
                    self._render_reperes(tab, auto_open=True)

        if cur.get("qid") and (want_dates or (want_map and not cur.get("coords"))):
            api.run_async(api.fetch_wikidata, got, cur["qid"])
        else:
            got({}, None)
        if self.settings.get_boolean("show-related") and cur["site"] == "wikipedia":
            def sim(r, _e):
                if token is tab.load_token and r:
                    tab.similar = r
                    if tab is self.tab:
                        self._render_reperes(tab)
            api.run_async(api.related, sim, cur["site"], cur["title"])

    def _render_reperes(self, tab, auto_open=False):
        for r in self.date_rows:
            self.dates_group.remove(r)
        for r in self.related_rows:
            self.related_group.remove(r)
        self.date_rows, self.related_rows = [], []
        cur = tab.current
        data = tab.reperes_data or {}
        dates = data.get("dates", []) if (cur and self.settings.get_boolean("show-key-dates")) else []
        for d in dates:
            row = Adw.ActionRow(title=d["date"], subtitle=d["label"], activatable=True, use_markup=False,
                                tooltip_text="Ajouter au panier")
            row.add_suffix(Gtk.Image(icon_name="list-add-symbolic"))
            row.connect("activated", lambda _r, d=d: self._add_date(d))
            self.dates_group.add(row)
            self.date_rows.append(row)
        self.dates_group.set_visible(bool(dates))

        coords = (cur or {}).get("coords") or data.get("coords")
        place = tab.place
        has_map = bool(cur and (coords or place)) and self.settings.get_boolean("show-map")
        if has_map:
            if place:   # lieu cité, situé par clic droit
                key = (place["lat"], place["lon"], place["name"])
                args = (place["lat"], place["lon"], place["name"], place.get("description"), f"Lieu : {place['name']}")
            else:
                key = (coords["lat"], coords["lon"], cur["title"])
                args = (coords["lat"], coords["lon"], cur["title"], cur.get("description"), "Lieu")
            if key != self._map_shown:
                self.map_card.show(*args[:4], heading=args[4])
                self._map_shown = key
        self.map_card.set_visible(has_map)

        rel = []
        if cur and self.settings.get_boolean("show-related"):
            seen = {cur["title"]}
            for t in [r["title"] for r in tab.related] + list(tab.similar):
                if t not in seen:
                    seen.add(t)
                    rel.append(t)
        for title in rel[:16]:
            row = Adw.ActionRow(title=title, activatable=True, use_markup=False,
                                tooltip_text="Ouvrir (clic du milieu : nouvel onglet)")
            row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
            row.connect("activated", lambda _r, t=title, s=cur["site"]: self.open_article(s, t))
            mid = Gtk.GestureClick(button=2)
            mid.connect("pressed", lambda *_a, t=title, s=cur["site"]: self.open_article(
                s, t, new_tab=True, background=True))
            row.add_controller(mid)
            self.related_group.add(row)
            self.related_rows.append(row)
        self.related_group.set_visible(bool(rel))

        self.reperes_btn.set_sensitive(bool(dates or has_map or rel))
        if not (dates or has_map or rel):
            self.reperes_btn.set_active(False)
        elif auto_open and (dates or has_map) and self.settings.get_boolean("reperes-auto"):
            self.reperes_btn.set_active(True)

    def _add_date(self, d):
        cur = self.current
        if not cur:
            return
        ok = self.basket.add({"kind": "date", "date": d["date"], "label": d["label"], "sort": d.get("sort"),
                              "source_title": cur["title"], "site": cur["site"],
                              "url": api.page_url(cur["site"], cur["title"]), "license": api.LICENSE})
        self.toast(f"« {d['date']} » ajouté au panier" if ok else "Déjà dans le panier")

    # ------------------------------------------------------------ Messages JS
    TAB_MESSAGES = ("toc", "toc-active", "related")

    def _on_js(self, tab, value):
        try:
            msg = json.loads(value.to_string())
        except (ValueError, TypeError):
            return
        kind = msg.get("type", "")
        if kind in self.TAB_MESSAGES:
            getattr(self, "_js_" + kind.replace("-", "_"))(tab, msg)
            return
        if tab is not self.tab:
            return
        self._attach_popovers()
        handler = getattr(self, "_js_" + kind.replace("-", "_"), None)
        if handler:
            handler(msg)

    def _js_ready(self, _m):
        pass

    def _js_toc(self, tab, m):
        tab.toc_items = m["items"]
        if tab is self.tab:
            self._render_toc(tab)

    def _render_toc(self, tab):
        self.toc_list.remove_all()
        self.toc_rows = {}
        for it in tab.toc_items:
            lab = Gtk.Label(label=it["text"], xalign=0, ellipsize=Pango.EllipsizeMode.END,
                            margin_start=0 if it["level"] == 2 else 14)
            if it["level"] == 3:
                lab.add_css_class("dim-label")
            row = Gtk.ListBoxRow(child=lab, tooltip_text=it["text"])
            row.toc_id = it["id"]
            self.toc_rows[it["id"]] = row
            self.toc_list.append(row)
        self.toc_stack.set_visible_child_name("list" if tab.toc_items else "empty")

    def _js_toc_active(self, tab, m):
        if tab is self.tab:
            row = self.toc_rows.get(m["id"])
            if row:
                self.toc_list.select_row(row)

    def _js_related(self, tab, m):
        tab.related = m.get("items", [])
        if tab is self.tab:
            self._render_reperes(tab)

    def _js_link(self, m):
        self._open_link(m["href"], new_tab=bool(m.get("newtab")))

    def _js_open_file(self, m):
        ImageDialog(self, file_title=m["file"]).present(self)

    def _js_copied(self, m):
        self.toast("Copié (texte mis en forme)" if m["mode"] == "rich" else "Copié (texte brut)")

    # Aperçu au survol
    def _js_hover(self, m):
        href = m["href"]
        self.hover_href = href
        u = urllib.parse.urlparse(href)
        site = api.HOST_TO_SITE.get(u.netloc)
        if not site or not u.path.startswith("/wiki/"):
            return
        title = urllib.parse.unquote(u.path[6:]).replace("_", " ")
        rect = self._point(m["x"], m["y"], m["w"], m["h"])
        key = (site, title)
        if key in self.summary_cache:
            self._show_preview(href, rect, self.summary_cache[key])
            return

        def done(res, err):
            if res and not err:
                self.summary_cache[key] = res
                self._show_preview(href, rect, res)

        api.run_async(api.fetch_summary, done, site, title)

    def _show_preview(self, href, rect, s):
        if href != self.hover_href or not s.get("extract"):
            return
        box = Gtk.Box(spacing=12, margin_top=6, margin_bottom=6, margin_start=6, margin_end=6)
        if s.get("thumb"):
            pic = Gtk.Picture(content_fit=Gtk.ContentFit.COVER, width_request=96, height_request=96,
                              can_shrink=True, valign=Gtk.Align.START, css_classes=["alex-thumb"])
            pic.set_overflow(Gtk.Overflow.HIDDEN)
            load_texture(s["thumb"], lambda t: t and pic.set_paintable(t))
            box.append(pic)
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        col.append(Gtk.Label(label=s["title"], xalign=0, wrap=True, css_classes=["heading"], max_width_chars=44))
        if s.get("description"):
            col.append(Gtk.Label(label=s["description"], xalign=0, wrap=True, max_width_chars=48,
                                 css_classes=["dim-label", "caption"]))
        col.append(Gtk.Label(label=s["extract"], xalign=0, wrap=True, lines=7, max_width_chars=52,
                             ellipsize=Pango.EllipsizeMode.END))
        box.append(col)
        self.hover_pop.set_child(box)
        self.hover_pop.set_pointing_to(rect)
        self.hover_pop.popup()

    def _js_hover_end(self, _m):
        self.hover_href = None
        self.hover_pop.popdown()

    # Wiktionnaire
    def _js_define(self, m):
        self.hover_pop.popdown()
        word = m["word"]
        self.def_word = word
        self.def_rect = self._point(m["x"], m["y"], m["w"], m["h"])
        spin = Gtk.Box(spacing=8, margin_top=8, margin_bottom=8, margin_start=8, margin_end=8)
        spin.append(Adw.Spinner())
        spin.append(Gtk.Label(label=f"« {word} » dans le Wiktionnaire…"))
        self.def_pop.set_child(spin)
        self.def_pop.set_pointing_to(self.def_rect)
        self.def_pop.popup()

        def done(res, err):
            if self.def_word != word:
                return
            if err or not res or not res[1]:
                self._js_definition({"word": word, "items": []})
                return
            w, html = res
            self.def_word = w
            self.run_js(f"alexParseDefinition({json.dumps(w)}, {json.dumps(html)})")

        api.run_async(api.fetch_wiktionary, done, word)

    def _js_definition(self, m):
        word = m["word"]
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_top=8, margin_bottom=8,
                      margin_start=8, margin_end=8, width_request=320)
        box.append(Gtk.Label(label=word, xalign=0, css_classes=["title-4"]))
        if not m["items"]:
            box.append(Gtk.Label(label="Pas de définition en français.", xalign=0, css_classes=["dim-label"]))
        for it in m["items"]:
            box.append(Gtk.Label(label=it["pos"], xalign=0, css_classes=["heading", "accent"]))
            for i, d in enumerate(it["defs"], 1):
                line = Gtk.Box(spacing=6)
                line.append(Gtk.Label(label=f"{i}. {d}", xalign=0, wrap=True, max_width_chars=46,
                                      selectable=True, hexpand=True))
                add = Gtk.Button(icon_name="alexandrie-glossary-symbolic", valign=Gtk.Align.START,
                                 css_classes=["flat", "circular"], tooltip_text="Ajouter au glossaire du panier")
                add.connect("clicked", lambda _b, w=word, p=it["pos"], d=d: self._add_term(w, p, d))
                line.append(add)
                box.append(line)
        link = Gtk.LinkButton(uri=f"https://fr.wiktionary.org/wiki/{api.quote_title(word)}",
                              label="Ouvrir dans le Wiktionnaire", halign=Gtk.Align.START)
        box.append(link)
        sw = Gtk.ScrolledWindow(child=box, propagate_natural_height=True, max_content_height=420,
                                hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.def_pop.set_child(sw)
        self.def_pop.set_pointing_to(self.def_rect)
        self.def_pop.popup()

    def _add_term(self, word, pos, definition):
        ok = self.basket.add({"kind": "term", "word": word, "pos": pos, "definition": definition,
                              "source_title": f"{word} (Wiktionnaire)",
                              "url": f"https://fr.wiktionary.org/wiki/{api.quote_title(word)}",
                              "license": api.LICENSE})
        self.toast(f"« {word} » ajouté au glossaire" if ok else "Déjà dans le glossaire")

    # Menu contextuel
    def _js_context(self, m):
        self.ctx = m
        self.hover_pop.popdown()
        menu = Gio.Menu()
        if m.get("sel"):
            s = Gio.Menu()
            first, second = (("Copier (texte mis en forme)", "win.ctx-copy-rich"),
                             ("Copier (texte brut)", "win.ctx-copy-plain"))
            if self.settings.get_string("copy-format") == "plain":
                first, second = second, first
            s.append(*first)
            s.append(*second)
            s.append("Ajouter au panier", "win.ctx-add-text")
            menu.append_section(None, s)
        if m.get("link"):
            s = Gio.Menu()
            s.append("Ouvrir dans un nouvel onglet", "win.ctx-open-tab")
            menu.append_section(None, s)
        if m.get("word") and self.settings.get_boolean("dictionary"):
            s = Gio.Menu()
            s.append(f"Définir « {m['word']} »", "win.ctx-define")
            menu.append_section(None, s)
        self.ctx["place"] = place = self._place_from_ctx(m)
        want_panel = self.settings.get_boolean("show-map")
        want_app = self.settings.get_boolean("maps-button") and maps_available()
        if place and (want_panel or want_app):
            s = Gio.Menu()
            label = place["label"] if len(place["label"]) <= 32 else place["label"][:31] + "…"
            if want_panel:
                s.append(f"Situer « {label} » sur la carte", "win.ctx-map-panel")
            if want_app:
                s.append(f"Ouvrir « {label} » dans Cartes", "win.ctx-map-app")
            menu.append_section(None, s)
        if m.get("img"):
            s = Gio.Menu()
            s.append("Ajouter l'image au panier", "win.ctx-add-image")
            if m["img"].get("file"):
                s.append("Voir l'image en grand", "win.ctx-image")
            menu.append_section(None, s)
        s = Gio.Menu()
        s.append("Copier l'article entier", "win.copy-article")
        s.append("Exporter en PDF…", "win.export-pdf")
        menu.append_section(None, s)
        self.ctx_pop.set_menu_model(menu)
        self.ctx_pop.set_pointing_to(self._point(m["x"], m["y"]))
        self.ctx_pop.popup()

    def _place_from_ctx(self, m):
        link = m.get("link")
        if link:
            u = urllib.parse.urlparse(link["href"])
            if api.HOST_TO_SITE.get(u.netloc) in ("wikipedia", "vikidia") and u.path.startswith("/wiki/"):
                title = urllib.parse.unquote(u.path[6:]).replace("_", " ")
                if not title.startswith(SPECIAL_NS) and ":" not in title:
                    return {"title": title, "label": link.get("text") or title}
        text = (m.get("seltext") or "").strip()
        if text and len(text) <= 60 and len(text.split()) <= 6:
            return {"title": text, "label": text}
        return None

    def _locate(self, then):
        place = self.ctx.get("place")
        if not place:
            return

        def done(res, err):
            try:
                then(place, None if err else res)
            except Exception as e:  # noqa: BLE001
                self.toast(f"Carte indisponible : {e}")

        api.run_async(api.locate, done, place["title"])

    def _ctx_map_panel(self):
        tab = self.tab

        def show(place, res):
            if not res:
                self.toast(f"Lieu introuvable : {place['label']}")
                return
            if tab is None or tab.current is None:
                return
            tab.place = {"lat": res["lat"], "lon": res["lon"], "name": res["name"],
                         "description": res.get("description", "")}
            if tab is self.tab:
                self._render_reperes(tab)
                self.reperes_btn.set_active(True)

        self._locate(show)

    def _ctx_map_app(self):
        def open_(place, res):
            if res:
                open_in_maps(self, res["lat"], res["lon"])
            else:
                search_in_maps(self, place["label"])

        self._locate(open_)

    def _ctx_copy(self, plain):
        sel = self.ctx.get("sel")
        if sel:
            self.set_clipboard(sel["text"], None if plain else sel["html"])
            self.toast("Copié (texte brut)" if plain else "Copié (texte mis en forme)")

    def _ctx_add_text(self):
        sel = self.ctx.get("sel")
        if sel and self.current:
            cur = self.current
            ok = self.basket.add({"kind": "text", "html": sel["html"], "text": sel["text"],
                                  "source_title": cur["title"], "site": cur["site"],
                                  "url": api.page_url(cur["site"], cur["title"]), "license": api.LICENSE})
            self.toast("Extrait ajouté au panier" if ok else "Déjà dans le panier")

    def _ctx_add_image(self):
        img = self.ctx.get("img")
        if img and self.current:
            cur = self.current
            ok = self.basket.add({"kind": "image", "src": img["src"], "caption": img.get("caption", ""),
                                  "file": (img.get("file") or "").split(":", 1)[-1], "source_title": cur["title"],
                                  "site": cur["site"], "url": api.page_url(cur["site"], cur["title"]),
                                  "license": api.LICENSE})
            self.toast("Image ajoutée au panier" if ok else "Déjà dans le panier")

    # Article entier
    def _request_article(self, purpose, opts=None):
        if self.current:
            self.run_js(f"alexGetArticle({json.dumps(purpose)}, {json.dumps(opts or {})})")

    def _js_article(self, m):
        cur = self.current
        if not cur:
            return
        if m["purpose"] == "copy":
            esc = _html.escape
            html = f"<h1>{esc(cur['title'])}</h1>{m['html']}"
            self.set_clipboard(f"{cur['title']}\n\n{m['text']}", html)
            self.toast("Article copié")
        elif m["purpose"] == "pdf" and self.pending_pdf:
            path, opts = self.pending_pdf
            self.pending_pdf = None
            credit = None
            if opts["source"]:
                credit = f"Source : {cur['title']} — {api.page_url(cur['site'], cur['title'])} ({api.LICENSE})"
            doc = export.article_document(cur["title"], cur.get("description"), m["full"],
                                          self.toc_items if opts["toc"] else None, credit)
            self._write_pdf(doc, path, f"https://{api.SITES[cur['site']]}/wiki/")

    # ------------------------------------------------------------ Export PDF
    def export_article(self):
        if not self.current:
            return
        dlg = Adw.AlertDialog(heading="Exporter l'article en PDF",
                              body="Mise en page propre, sans menus ; les liens deviennent du texte normal.")
        lb = Gtk.ListBox(css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE)
        r_img = Adw.SwitchRow(title="Inclure les images", active=self.settings.get_boolean("pdf-images"))
        r_toc = Adw.SwitchRow(title="Inclure le sommaire", active=self.settings.get_boolean("pdf-toc"))
        r_src = Adw.SwitchRow(title="Ajouter la source", active=self.settings.get_boolean("basket-source"))
        for r in (r_img, r_toc, r_src):
            lb.append(r)
        dlg.set_extra_child(lb)
        dlg.add_response("cancel", "Annuler")
        dlg.add_response("export", "Exporter…")
        dlg.set_response_appearance("export", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("export")

        def on_resp(_d, resp):
            if resp != "export":
                return
            opts = {"images": r_img.get_active(), "toc": r_toc.get_active(), "source": r_src.get_active()}
            self._ask_pdf_path(self.current["title"], lambda path: self._export_article_to(path, opts))

        dlg.connect("response", on_resp)
        dlg.present(self)

    def _export_article_to(self, path, opts):
        self.pending_pdf = (path, opts)
        self._request_article("pdf", {"images": opts["images"]})

    def export_basket(self):
        if not self.basket.items:
            self.toast("Le panier est vide")
            return
        dlg = Adw.AlertDialog(heading="Exporter le panier en PDF", body="Une fiche élève, dans l'ordre du panier.")
        lb = Gtk.ListBox(css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE)
        r_title = Adw.EntryRow(title="Titre de la fiche (facultatif)")
        r_num = Adw.SwitchRow(title="Numéroter les documents", active=self.settings.get_boolean("basket-numbered"))
        r_src = Adw.SwitchRow(title="Ajouter la source", active=self.settings.get_boolean("basket-source"))
        lb.append(r_title)
        lb.append(r_num)
        lb.append(r_src)
        dlg.set_extra_child(lb)
        dlg.add_response("cancel", "Annuler")
        dlg.add_response("export", "Exporter…")
        dlg.set_response_appearance("export", Adw.ResponseAppearance.SUGGESTED)

        def on_resp(_d, resp):
            if resp != "export":
                return
            title = r_title.get_text().strip()
            html, _plain = store.render(self.basket.items, r_src.get_active(), title or None,
                                        numbered=r_num.get_active())
            doc = export.wrap(html, title or "Fiche")
            self._ask_pdf_path(title or "fiche", lambda path: self._write_pdf(doc, path, "https://fr.wikipedia.org/wiki/"))

        dlg.connect("response", on_resp)
        dlg.present(self)

    def _ask_pdf_path(self, name, then):
        safe = "".join(c for c in name if c not in '/\\:*?"<>|').strip() or "export"
        fd = Gtk.FileDialog(initial_name=f"{safe}.pdf")
        f = Gtk.FileFilter(name="PDF")
        f.add_mime_type("application/pdf")
        store_ = Gio.ListStore.new(Gtk.FileFilter)
        store_.append(f)
        fd.set_filters(store_)

        def done(dlg, res):
            try:
                gfile = dlg.save_finish(res)
            except GLib.Error:
                return
            then(gfile.get_path())

        fd.save(self, None, done)

    def _write_pdf(self, doc, path, base):
        self.toast("Création du PDF…")

        def done(_r, err):
            if err:
                self.toast(f"Échec de l'export : {err}")
                return
            self.toast(f"PDF enregistré : {os.path.basename(path)}", "Ouvrir",
                       lambda: Gtk.FileLauncher(file=Gio.File.new_for_path(path)).launch(self, None, None, None))

        api.run_async(export.write_pdf, done, doc, path, base)

    # ------------------------------------------------------------ Panier
    def _refresh_basket(self):
        items = self.basket.items
        self.badge.set_label(str(len(items)))
        self.badge.set_visible(bool(items))
        self.basket_list.remove_all()
        for idx, it in enumerate(items):
            self.basket_list.append(self._basket_row(idx, it))
        self.basket_stack.set_visible_child_name("list" if items else "empty")

    def _basket_row(self, idx, it):
        row = Adw.ActionRow(title=store.item_label(it), subtitle=store.item_subtitle(it), use_markup=False,
                            title_lines=3, subtitle_lines=1)
        row.add_prefix(Gtk.Image(icon_name="alexandrie-drag-symbolic", css_classes=["dim-label"]))
        if it["kind"] == "image":
            pic = Gtk.Picture(content_fit=Gtk.ContentFit.COVER, width_request=36, height_request=36,
                              can_shrink=True, valign=Gtk.Align.CENTER, css_classes=["alex-thumb"])
            pic.set_overflow(Gtk.Overflow.HIDDEN)
            load_texture(it["src"], lambda t: t and pic.set_paintable(t))
            row.add_prefix(pic)
        else:
            icon = {"date": "alexandrie-calendar-symbolic", "term": "alexandrie-glossary-symbolic",
                    "block": {"heading": "alexandrie-heading-symbolic",
                              "instruction": "alexandrie-instruction-symbolic"}.get(it.get("style"),
                                                                                   "alexandrie-note-symbolic"),
                    }.get(it["kind"], "alexandrie-excerpt-symbolic")
            row.add_prefix(Gtk.Image(icon_name=icon))
        if it["kind"] == "block":
            ed = Gtk.Button(icon_name="document-edit-symbolic", valign=Gtk.Align.CENTER, css_classes=["flat"],
                            tooltip_text="Modifier")
            ed.connect("clicked", lambda *_: self._edit_block(idx, it.get("style")))
            row.add_suffix(ed)
        rm = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER, css_classes=["flat"],
                        tooltip_text="Retirer")
        rm.connect("clicked", lambda *_: self.basket.remove(idx))
        row.add_suffix(rm)

        drag = Gtk.DragSource(actions=Gdk.DragAction.MOVE)
        drag.connect("prepare", lambda *_: Gdk.ContentProvider.new_for_value(str(idx)))
        drag.connect("drag-begin", lambda src, _d: src.set_icon(Gtk.WidgetPaintable.new(row), 0, 0))
        row.add_controller(drag)
        drop = Gtk.DropTarget.new(str, Gdk.DragAction.MOVE)
        drop.connect("drop", lambda _t, value, *_: GLib.idle_add(lambda: self.basket.move(int(value), idx)) or True)
        row.add_controller(drop)
        return row

    def _edit_block(self, idx, style):
        """Crée (idx=None) ou modifie un bloc libre : titre de partie, consigne ou note."""
        labels = {"heading": "Titre de partie", "instruction": "Consigne", "note": "Note"}
        style = style if style in labels else "note"
        existing = self.basket.items[idx] if idx is not None and idx < len(self.basket.items) else None
        dlg = Adw.AlertDialog(heading=("Modifier : " if existing else "Ajouter : ") + labels[style].lower())
        buf = Gtk.TextBuffer(text=existing.get("text", "") if existing else "")
        tv = Gtk.TextView(buffer=buf, wrap_mode=Gtk.WrapMode.WORD_CHAR, top_margin=8, bottom_margin=8,
                          left_margin=8, right_margin=8, accepts_tab=False)
        frame = Gtk.Frame(child=Gtk.ScrolledWindow(child=tv, min_content_height=60 if style == "heading" else 120,
                                                    min_content_width=360,
                                                    hscrollbar_policy=Gtk.PolicyType.NEVER))
        dlg.set_extra_child(frame)
        dlg.add_response("cancel", "Annuler")
        dlg.add_response("ok", "Enregistrer" if existing else "Ajouter")
        dlg.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("ok")

        def on_resp(_d, resp):
            text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False).strip()
            if resp != "ok" or not text:
                return
            if existing:
                self.basket.update(idx, text=text)
                return
            sel = sorted(r.get_index() for r in self.basket_list.get_selected_rows())
            self.basket.add({"kind": "block", "style": style, "text": text})
            if sel:  # inséré juste avant la première ligne sélectionnée
                self.basket.move(len(self.basket.items) - 1, sel[0])

        dlg.connect("response", on_resp)
        dlg.present(self)
        GLib.idle_add(lambda: tv.grab_focus() and False)

    def _selected_items(self):
        rows = self.basket_list.get_selected_rows()
        if not rows:
            return list(self.basket.items)
        idxs = sorted(r.get_index() for r in rows)
        return [self.basket.items[i] for i in idxs]

    def copy_basket(self, plain=False):
        items = self._selected_items()
        if not items:
            self.toast("Le panier est vide")
            return
        html, text = store.render(items, self.settings.get_boolean("basket-source"),
                                  numbered=self.settings.get_boolean("basket-numbered"))
        self.set_clipboard(text, None if plain else html)
        n = len(items)
        self.toast(f"{n} élément{'s' if n > 1 else ''} copié{'s' if n > 1 else ''} — prêt à coller")

    def _remove_selected(self):
        idxs = sorted((r.get_index() for r in self.basket_list.get_selected_rows()), reverse=True)
        for i in idxs:
            del self.basket.items[i]
        if idxs:
            self.basket._commit()

    def _confirm_clear(self):
        if not self.basket.items:
            return
        dlg = Adw.AlertDialog(heading="Vider le panier ?", body="Tous les extraits seront retirés.")
        dlg.add_response("cancel", "Annuler")
        dlg.add_response("clear", "Vider")
        dlg.set_response_appearance("clear", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.connect("response", lambda _d, r: r == "clear" and self.basket.clear())
        dlg.present(self)

    # ------------------------------------------------------------ Favoris
    def _update_fav_button(self):
        fav = self.current and self.favorites.find(self.current["site"], self.current["title"])
        self.fav_btn.set_icon_name("starred-symbolic" if fav else "non-starred-symbolic")

    def _fill_fav_popover(self, *_):
        if not self.current:
            return
        fav = self.favorites.find(self.current["site"], self.current["title"])
        self.fav_title.set_label("Modifier le favori" if fav else "Ajouter aux favoris")
        self.fav_entry.set_text(", ".join(fav["tags"]) if fav else "")
        self.fav_remove.set_visible(bool(fav))
        self.fav_tag_flow.remove_all()
        for tag in self.favorites.all_tags():
            b = Gtk.Button(label=tag, css_classes=["alex-tag"])
            b.connect("clicked", lambda _b, t=tag: self._append_tag(t))
            self.fav_tag_flow.append(b)

    def _append_tag(self, tag):
        tags = [t.strip() for t in self.fav_entry.get_text().split(",") if t.strip()]
        if tag not in tags:
            tags.append(tag)
        self.fav_entry.set_text(", ".join(tags))

    def _save_fav(self):
        if not self.current:
            return
        self.favorites.set(self.current["site"], self.current["title"], self.fav_entry.get_text().split(","))
        self.fav_pop.popdown()
        self._update_fav_button()
        self.toast("Favori enregistré")

    def _remove_fav(self, *_):
        if self.current:
            self.favorites.remove(self.current["site"], self.current["title"])
            self.fav_pop.popdown()
            self._update_fav_button()

    def _refresh_favorites(self):
        tags = self.favorites.all_tags()
        self.tag_filter &= set(tags)
        self.tag_flow.remove_all()
        for tag in tags:
            b = Gtk.ToggleButton(label=tag, active=tag in self.tag_filter, css_classes=["alex-tag"])
            b.connect("toggled", lambda btn, t=tag: self._toggle_tag(t, btn.get_active()))
            self.tag_flow.append(b)
        self.tag_flow.set_visible(bool(tags))
        self.fav_list.remove_all()
        shown = [f for f in self.favorites.items if self.tag_filter <= set(f["tags"])]
        for f in shown:
            sub = " · ".join(f["tags"])
            if f["site"] != "wikipedia":
                sub = (api.SITE_LABELS[f["site"]] + (" · " + sub if sub else ""))
            row = Adw.ActionRow(title=f["title"], subtitle=sub, activatable=True, use_markup=False)
            row.fav = f
            rm = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER, css_classes=["flat"],
                            tooltip_text="Retirer des favoris")
            rm.connect("clicked", lambda _b, f=f: self.favorites.remove(f["site"], f["title"]))
            row.add_suffix(rm)
            self.fav_list.append(row)
        self.fav_stack.set_visible_child_name("list" if shown else "empty")
        self._update_fav_button()

    def _toggle_tag(self, tag, on):
        (self.tag_filter.add if on else self.tag_filter.discard)(tag)
        self._refresh_favorites()

    # ------------------------------------------------------------ Raccourcis
    def _show_shortcuts(self):
        rows = [
            ("Ctrl+L", "Aller à la recherche"), ("Ctrl+F", "Rechercher dans l'article"),
            ("Ctrl+T", "Nouvel onglet"), ("Ctrl+W", "Fermer l'onglet"),
            ("Ctrl+Tab / Ctrl+Maj+Tab", "Onglet suivant / précédent"),
            ("Clic du milieu ou Ctrl+clic", "Ouvrir un lien dans un nouvel onglet"),
            ("Alt+← / Alt+→", "Précédent / suivant"),
            ("F9", "Barre latérale"), ("Ctrl+D", "Favori"), ("Ctrl+B", "Panier"),
            ("Ctrl+C", "Copier la sélection (format par défaut)"), ("Ctrl+Maj+C", "Copier dans l'autre format"),
            ("Ctrl+A puis Ctrl+C (dans le panier)", "Copier tout le panier"),
            ("Suppr (dans le panier)", "Retirer la sélection"),
            ("Ctrl+Maj+A", "Copier l'article entier"), ("Ctrl+P", "Exporter l'article en PDF"),
            ("Ctrl+,", "Préférences"), ("Double-clic sur un mot", "Définition du Wiktionnaire"),
        ]
        dlg = Adw.Dialog(title="Raccourcis clavier", content_width=460)
        tv = Adw.ToolbarView()
        tv.add_top_bar(Adw.HeaderBar())
        page = Adw.PreferencesPage()
        grp = Adw.PreferencesGroup()
        for k, d in rows:
            r = Adw.ActionRow(title=d, use_markup=False)
            r.add_suffix(Gtk.Label(label=k, css_classes=["dim-label", "monospace"]))
            grp.add(r)
        page.add(grp)
        tv.set_content(page)
        dlg.set_child(tv)
        dlg.present(self)
