"""Recherche d'images Wikimedia Commons et fenêtre de détail d'une image."""

import os
from pathlib import Path

from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk, Pango

from . import api

PELLICOLA_ID = "io.gitlab.shogu.Pellicola.desktop"
_textures = {}


def load_texture(url, callback):
    """callback(Gdk.Texture | None), avec cache mémoire."""
    url = api.https(url)
    if not url:
        callback(None)
        return
    if url in _textures:
        callback(_textures[url])
        return

    def done(data, err):
        tex = None
        if data and not err:
            try:
                tex = Gdk.Texture.new_from_bytes(GLib.Bytes.new(data))
                _textures[url] = tex
            except GLib.Error:
                tex = None
        callback(tex)

    api.pool_async(api.fetch_bytes, done, url)


def pellicola_available():
    try:
        return Gio.DesktopAppInfo.new(PELLICOLA_ID) is not None
    except TypeError:
        return False


class CommonsView(Gtk.Stack):
    __gsignals__ = {"open-image": (GObject.SignalFlags.RUN_FIRST, None, (object,))}

    def __init__(self):
        super().__init__(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.add_named(Adw.StatusPage(icon_name="image-x-generic-symbolic",
                                      title="Images de Wikimedia Commons",
                                      description="Tapez une recherche puis Entrée pour trouver des images en haute définition."),
                       "empty")
        spin = Adw.Spinner(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, width_request=32, height_request=32)
        self.add_named(spin, "loading")
        self.none = Adw.StatusPage(icon_name="edit-find-symbolic", title="Aucune image")
        self.add_named(self.none, "none")
        self.flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, homogeneous=True,
                                min_children_per_line=2, max_children_per_line=8,
                                row_spacing=12, column_spacing=12,
                                margin_top=18, margin_bottom=18, margin_start=18, margin_end=18,
                                valign=Gtk.Align.START)
        self.add_named(Gtk.ScrolledWindow(child=self.flow, hscrollbar_policy=Gtk.PolicyType.NEVER), "grid")
        self._token = None

    def search(self, query):
        self.set_visible_child_name("loading")
        token = self._token = object()
        api.run_async(api.commons_search, lambda r, e: self._fill(token, query, r, e), query)

    def _fill(self, token, query, results, err):
        if token is not self._token:
            return
        if err:
            self.none.set_title("Recherche impossible")
            self.none.set_description(GLib.markup_escape_text(str(err)))
            self.set_visible_child_name("none")
            return
        self.flow.remove_all()
        if not results:
            self.none.set_title("Aucune image")
            self.none.set_description(f"Rien trouvé pour « {query} ».")
            self.set_visible_child_name("none")
            return
        for info in results:
            self.flow.append(self._tile(info))
        self.set_visible_child_name("grid")

    def _tile(self, info):
        pic = Gtk.Picture(content_fit=Gtk.ContentFit.COVER, can_shrink=True,
                          width_request=200, height_request=150, css_classes=["alex-thumb"])
        pic.set_overflow(Gtk.Overflow.HIDDEN)
        load_texture(info["thumb"], lambda t: t and pic.set_paintable(t))
        label = Gtk.Label(label=info["name"], ellipsize=Pango.EllipsizeMode.MIDDLE,
                          max_width_chars=24, css_classes=["caption", "dim-label"])
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.append(pic)
        box.append(label)
        btn = Gtk.Button(child=box, css_classes=["flat"], tooltip_text=info["name"])
        btn.connect("clicked", lambda *_: self.emit("open-image", info))
        return btn


class ImageDialog(Adw.Dialog):
    """Image en grand, crédits, téléchargement, panier, Pellicola."""

    def __init__(self, window, info=None, file_title=None):
        super().__init__(title="Image", content_width=820, content_height=680)
        self.win = window
        self.info = None
        tv = Adw.ToolbarView()
        self.header = Adw.HeaderBar()
        tv.add_top_bar(self.header)
        self.set_child(tv)

        self.stack = Gtk.Stack()
        self.stack.add_named(Adw.Spinner(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER,
                                         width_request=32, height_request=32), "loading")
        self.error = Adw.StatusPage(icon_name="image-missing-symbolic", title="Image indisponible")
        self.stack.add_named(self.error, "error")

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                       margin_top=6, margin_bottom=18, margin_start=18, margin_end=18)
        self.picture = Gtk.Picture(content_fit=Gtk.ContentFit.CONTAIN, can_shrink=True, vexpand=True)
        body.append(self.picture)
        self.caption = Gtk.Label(wrap=True, xalign=0, lines=3, ellipsize=Pango.EllipsizeMode.END, selectable=True)
        self.credit = Gtk.Label(wrap=True, xalign=0, css_classes=["dim-label", "caption"], selectable=True)
        body.append(self.caption)
        body.append(self.credit)

        bar = Gtk.Box(spacing=8, halign=Gtk.Align.END)
        page_btn = Gtk.Button(label="Page Commons")
        page_btn.connect("clicked", self._open_page)
        self.pell_btn = Gtk.Button(label="Ouvrir dans Pellicola")
        self.pell_btn.connect("clicked", self._pellicola)
        self.pell_btn.set_visible(pellicola_available() and window.settings.get_boolean("pellicola-button"))
        dl = Gtk.Button(label="Télécharger…")
        dl.connect("clicked", self._download)
        add = Gtk.Button(label="Ajouter au panier", css_classes=["suggested-action"])
        add.connect("clicked", self._add)
        for b in (page_btn, self.pell_btn, dl, add):
            bar.append(b)
        body.append(bar)
        self.stack.add_named(body, "image")
        tv.set_content(self.stack)

        if info:
            # La vignette de recherche est petite : on recharge en 1280 px.
            file_title = info["title"]
        api.run_async(api.commons_file, self._loaded, file_title)

    def _loaded(self, info, err):
        if err or not info:
            self.error.set_description("Ce fichier n'est pas sur Wikimedia Commons." if isinstance(err, api.NotFound)
                                       else GLib.markup_escape_text(str(err)))
            self.stack.set_visible_child_name("error")
            return
        self.info = info
        self.set_title(info["name"])
        self.caption.set_label(info["description"] or info["name"])
        dims = f"{info['width']} × {info['height']} px" if info.get("width") else ""
        self.credit.set_label(" · ".join(x for x in (info["author"], info["license"], dims) if x))
        load_texture(info["thumb"], lambda t: t and self.picture.set_paintable(t))
        self.stack.set_visible_child_name("image")

    def _open_page(self, *_):
        if self.info and self.info.get("page"):
            Gtk.UriLauncher(uri=self.info["page"]).launch(self.win, None, None, None)

    def _add(self, *_):
        if not self.info:
            return
        i = self.info
        self.win.basket.add({
            "kind": "image", "src": i["thumb"], "caption": i["description"][:300] or i["name"],
            "file": i["name"], "source_title": i["title"], "url": i["page"],
            "license": i["license"], "author": i["author"],
        })
        self.win.toast("Image ajoutée au panier")

    def _download(self, *_):
        if not self.info:
            return
        dlg = Gtk.FileDialog(initial_name=self.info["name"])
        dlg.save(self.win, None, self._download_to)

    def _download_to(self, dlg, res):
        try:
            gfile = dlg.save_finish(res)
        except GLib.Error:
            return
        path = gfile.get_path()
        self.win.toast("Téléchargement en cours…")

        def done(_r, err):
            if err:
                self.win.toast(f"Échec du téléchargement : {err}")
            else:
                self.win.toast(f"Image enregistrée : {os.path.basename(path)}")

        api.run_async(api.download_to, done, self.info["url"], path)

    def _pellicola(self, *_):
        if not self.info:
            return
        cache = Path(GLib.get_user_cache_dir()) / "alexandrie" / "images"
        cache.mkdir(parents=True, exist_ok=True)
        path = str(cache / self.info["name"])
        self.win.toast("Préparation de l'image pour Pellicola…")

        def done(_r, err):
            if err:
                self.win.toast(f"Échec du téléchargement : {err}")
                return
            app = Gio.DesktopAppInfo.new(PELLICOLA_ID)
            if app:
                app.launch([Gio.File.new_for_path(path)], None)

        if os.path.exists(path):
            done(path, None)
        else:
            api.run_async(api.download_to, done, self.info["url"], path)
