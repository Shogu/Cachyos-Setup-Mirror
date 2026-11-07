import os

from gi.repository import Adw, Gdk, Gio, GLib, Gtk, WebKit

import opencode
import state
from config import (
    APP_ID, APP_NAME, BASE_URL, NEW_SESSION_URI, SESSION_ROUTE, VERSION,
    WEBKIT_DATA_DIR, CACHE_DIR, is_local, session_uri,
)
from notifier import Notifier
from server import Server

DARK_BACKGROUND = "#1d1d20"
LIGHT_BACKGROUND = "#ffffff"
ZOOM_STEP = 0.1
ZOOM_MIN = 0.3
ZOOM_MAX = 3.0

SHORTCUTS = (
    ("<Control>t", "Nouvelle session"),
    ("<Control>r", "Recharger"),
    ("<Alt>Home", "Reconnecter"),
    ("<Control>plus", "Zoom avant"),
    ("<Control>minus", "Zoom arrière"),
    ("<Control>0", "Zoom 100 %"),
    ("F11", "Plein écran"),
    ("<Control>question", "Raccourcis clavier"),
    ("<Control>q", "Quitter"),
)


def rgba(spec):
    color = Gdk.RGBA()
    color.parse(spec)
    return color


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=APP_NAME)
        self._connecting = False
        self._pairing = False
        saved = state.load()
        self._server_key = saved.get("server_key")
        self.set_default_size(saved.get("width", 1180), saved.get("height", 820))
        if saved.get("maximized"):
            self.maximize()

        os.makedirs(WEBKIT_DATA_DIR, exist_ok=True)
        os.makedirs(CACHE_DIR, exist_ok=True)
        network_session = WebKit.NetworkSession.new(WEBKIT_DATA_DIR, CACHE_DIR)

        self.server = Server(network_session)
        self.notifier = Notifier(self, self.server)

        self.webview = WebKit.WebView(network_session=network_session, hexpand=True, vexpand=True)
        self.webview.connect("load-changed", self.on_load_changed)
        self.webview.connect("load-failed", self.on_load_failed)
        self.webview.connect("notify::uri", self.on_uri)
        self.webview.connect("notify::title", self.on_page_title)
        self.webview.connect("decide-policy", self.on_decide_policy)
        self.webview.connect("context-menu", self.on_context_menu)
        self.webview.connect("create", self.on_create)

        self.style_manager = Adw.StyleManager.get_default()
        self.style_manager.connect("notify::dark", self.on_dark_changed)
        self.on_dark_changed(self.style_manager)

        self.set_content(self._build_content())
        self._add_actions()
        self.connect("close-request", self.on_close_request)

        self.connect_and_load()

    # -- construction -----------------------------------------------------

    def _build_content(self):
        self.status_page = Adw.StatusPage(icon_name="network-error-symbolic")
        retry = Gtk.Button(label="Réessayer", halign=Gtk.Align.CENTER, action_name="win.reconnect")
        retry.add_css_class("pill")
        retry.add_css_class("suggested-action")
        self.status_page.set_child(retry)

        spinner = Adw.Spinner(width_request=48, height_request=48, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.stack.add_named(spinner, "loading")
        self.stack.add_named(self.webview, "content")
        self.stack.add_named(self.status_page, "error")

        self.window_title = Adw.WindowTitle(title=APP_NAME)
        header = Adw.HeaderBar(title_widget=self.window_title)
        header.pack_start(Gtk.Button(
            icon_name="tab-new-symbolic", tooltip_text="Nouvelle session (Ctrl+T)", action_name="win.new-session",
        ))
        header.pack_end(Gtk.MenuButton(
            icon_name="open-menu-symbolic", tooltip_text="Menu principal", primary=True, menu_model=self._build_menu(),
        ))

        toolbar = Adw.ToolbarView(content=self.stack)
        toolbar.add_top_bar(header)
        return toolbar

    def _build_menu(self):
        menu = Gio.Menu()
        sessions = Gio.Menu()
        sessions.append("Nouvelle session", "win.new-session")
        sessions.append("Recharger", "win.reload")
        sessions.append("Reconnecter", "win.reconnect")
        menu.append_section(None, sessions)

        view = Gio.Menu()
        view.append("Zoom avant", "win.zoom-in")
        view.append("Zoom arrière", "win.zoom-out")
        view.append("Zoom 100 %", "win.zoom-reset")
        view.append("Plein écran", "win.fullscreen")
        menu.append_section(None, view)

        app = Gio.Menu()
        app.append("Raccourcis clavier", "win.shortcuts")
        app.append("À propos de Perceptron", "win.about")
        menu.append_section(None, app)
        return menu

    def _add_actions(self):
        for name, callback in (
            ("new-session", lambda *_: self.webview.load_uri(NEW_SESSION_URI)),
            ("reload", lambda *_: self.webview.reload()),
            ("reconnect", lambda *_: self.connect_and_load()),
            ("zoom-in", lambda *_: self.zoom_by(ZOOM_STEP)),
            ("zoom-out", lambda *_: self.zoom_by(-ZOOM_STEP)),
            ("zoom-reset", lambda *_: self.webview.set_zoom_level(1.0)),
            ("fullscreen", self.on_fullscreen),
            ("shortcuts", self.on_shortcuts),
            ("about", self.on_about),
        ):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

    # -- connexion --------------------------------------------------------

    def connect_and_load(self):
        if self._connecting:
            return
        self._connecting = True
        self.stack.set_visible_child_name("loading")
        opencode.connect(self.on_connected)

    def on_connected(self, link):
        self._connecting = False
        if link is None:
            self.show_error(
                "OpenCode introuvable",
                "Ni le PATH de la session ni ~/.opencode/bin ne contiennent la commande « opencode ».",
            )
            return
        self._pairing = True
        uri = link or BASE_URL
        self.webview.load_uri(uri)

    # -- webkit -----------------------------------------------------------

    def on_load_changed(self, web, event):
        if not self._pairing:
            return
        if event != WebKit.LoadEvent.FINISHED:
            return
        self._pairing = False
        self.stack.set_visible_child_name("content")
        self.server.start()

    def on_load_failed(self, web, _event, uri, error):
        if not self._pairing:
            return False
        if error.matches(WebKit.NetworkError.quark(), WebKit.NetworkError.CANCELLED):
            return False
        self._pairing = False
        self.show_error("Service OpenCode injoignable", "Pas de réponse sur %s\n%s" % (BASE_URL, error.message))
        return True

    def on_uri(self, web, _pspec):
        match = SESSION_ROUTE.search(web.get_uri() or "")
        if match and match.group(1) != self._server_key:
            self._server_key = match.group(1)
            state.save({**state.load(), "server_key": self._server_key})

    def on_page_title(self, web, _pspec):
        title = web.get_title()
        if title:
            self.window_title.set_subtitle(title)

    def on_decide_policy(self, web, decision, decision_type):
        if decision_type not in (WebKit.PolicyDecisionType.NAVIGATION_ACTION, WebKit.PolicyDecisionType.NEW_WINDOW_ACTION):
            return False
        uri = decision.get_navigation_action().get_request().get_uri()
        if is_local(uri) or not uri.startswith(("http:", "https:", "mailto:")):
            return False
        decision.ignore()
        Gtk.UriLauncher.new(uri).launch(self)
        return True

    def on_context_menu(self, web, context_menu, hit_test_result):
        # WebKit 6.0 : 3 paramètres (pas de « event »)
        DOMINATED = (
            WebKit.ContextMenuAction.OPEN_LINK,
            WebKit.ContextMenuAction.OPEN_LINK_IN_NEW_WINDOW,
            WebKit.ContextMenuAction.DOWNLOAD_LINK_TO_DISK,
        )
        to_remove = [item for item in context_menu.get_items() if item.get_stock_action() in DOMINATED]
        for item in to_remove:
            context_menu.remove(item)

        if hit_test_result.context_is_link():
            link_uri = hit_test_result.get_link_uri()
            if link_uri and not is_local(link_uri):
                open_item = WebKit.ContextMenuItem.new_from_stock_action(WebKit.ContextMenuAction.OPEN_LINK)
                open_item.set_label("Ouvrir dans le navigateur")
                context_menu.prepend(open_item)
        return False

    def on_create(self, web, navigation_action):
        uri = navigation_action.get_request().get_uri()
        if uri and not is_local(uri):
            Gtk.UriLauncher.new(uri).launch(self)
        return None

    # -- actions ----------------------------------------------------------

    def show_session(self, session_id):
        self.present()
        if self._server_key:
            self.webview.load_uri(session_uri(self._server_key, session_id))

    def send_to_new_session(self, title, text):
        self.server.request_json("POST", "/api/session", {}, lambda info: self._on_prompt_session(info, title, text))

    def _on_prompt_session(self, info, title, text):
        if not info or not info.get("id"):
            self._alert("Session impossible à créer", "OpenCode n’a pas répondu à la création de session.")
            return
        path = "/api/session/" + GLib.Uri.escape_string(info["id"], None, False)
        if title:
            self.server.request_json("PATCH", path, {"title": title}, lambda _data: None)
        self.server.request_json("POST", path + "/prompt", {"text": text}, self._on_prompt_sent)
        if self._server_key:
            self.show_session(info["id"])
        else:
            self.webview.load_uri(BASE_URL)

    def _on_prompt_sent(self, data):
        if data is None:
            self._alert("Envoi impossible", "La session est créée mais OpenCode a refusé le message.")

    def _alert(self, heading, body):
        dialog = Adw.AlertDialog(heading=heading, body=body)
        dialog.add_response("ok", "OK")
        dialog.present(self)

    def show_error(self, title, description):
        self.status_page.set_title(title)
        self.status_page.set_description(description)
        self.stack.set_visible_child_name("error")

    def on_dark_changed(self, style_manager, *_):
        color = rgba(DARK_BACKGROUND if style_manager.get_dark() else LIGHT_BACKGROUND)
        self.webview.set_background_color(color)

    def zoom_by(self, step):
        level = min(max(self.webview.get_zoom_level() + step, ZOOM_MIN), ZOOM_MAX)
        self.webview.set_zoom_level(level)

    def on_fullscreen(self, *_):
        if self.is_fullscreen():
            self.unfullscreen()
        else:
            self.fullscreen()

    def on_shortcuts(self, *_):
        section = Adw.ShortcutsSection(title="Général")
        for accelerator, title in SHORTCUTS:
            section.add(Adw.ShortcutsItem(title=title, accelerator=accelerator))
        dialog = Adw.ShortcutsDialog()
        dialog.add(section)
        dialog.present(self)

    def on_about(self, *_):
        Adw.AboutDialog(
            application_name=APP_NAME,
            application_icon=APP_ID,
            version=VERSION,
            comments="Interface GTK4/libadwaita pour OpenCode",
            developer_name="ogu",
            website="https://gitlab.com/ogu/opencode-gtk",
            license_type=Gtk.License.MIT_X11,
        ).present(self)

    def on_close_request(self, *_):
        import os as _os
        width, height = self.get_default_size()
        state.save({
            **state.load(),
            "width": width,
            "height": height,
            "maximized": self.is_maximized(),
        })
        self.notifier.destroy()
        self.server.destroy()
        _os._exit(0)
