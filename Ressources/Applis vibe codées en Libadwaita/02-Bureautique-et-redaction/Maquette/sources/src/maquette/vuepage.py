"""Page en grand : navigation page par page, recadrage et pose de texte."""

from gi.repository import Adw, Gdk, GObject, Graphene, Gsk, Gtk

RECADRER = "recadrer"
POSER_TEXTE = "poser-texte"

MARGE = 24
TRACE_MINIMUM = 4

SOUS_TITRES_APERCU = {
    "brochure-a5": "Brochure A5 : deux pages par face, à plier et agrafer au centre",
    "livret-a4": "Livret A4 : deux pages par face, à plier et agrafer au centre",
}

OUTILS = (
    (RECADRER, "maquette-rogner-symbolic", "Recadrer",
     "Trace une zone, puis choisis : la garder, la vider, ou la retirer en réduisant la page."),
    (POSER_TEXTE, "maquette-texte-symbolic", "Texte",
     "Trace le cadre du texte à écrire sur la page."),
)


def _rgba(r, g, b, a):
    """Gdk.RGBA ignore les arguments nommés : il faut affecter les champs."""
    couleur = Gdk.RGBA()
    couleur.red, couleur.green, couleur.blue, couleur.alpha = r, g, b, a
    return couleur


class VuePage(Gtk.Widget):
    """Affiche une page et permet d'y tracer une zone."""
    __gtype_name__ = "MaquetteVuePage"
    __gsignals__ = {
        "zone-tracee": (GObject.SignalFlags.RUN_LAST, None, (str, float, float, float, float)),
    }

    def __init__(self):
        super().__init__(hexpand=True, vexpand=True, focusable=True, overflow=Gtk.Overflow.HIDDEN)
        self.texture = None
        self.outil = None
        self._trace = None
        geste = Gtk.GestureDrag()
        geste.connect("drag-begin", self._debut)
        geste.connect("drag-update", self._maj)
        geste.connect("drag-end", self._fin)
        self.add_controller(geste)

    def definir_texture(self, texture):
        self.texture = texture
        self.queue_draw()

    def definir_outil(self, outil):
        self.outil = outil
        self._trace = None
        self.set_cursor_from_name("crosshair" if outil else None)
        self.queue_draw()

    def do_measure(self, _orientation, _for_size):
        return 160, 600, -1, -1

    def _rect_page(self):
        if self.texture is None:
            return None
        l, h = self.get_width() - 2 * MARGE, self.get_height() - 2 * MARGE
        tl, th = self.texture.get_width(), self.texture.get_height()
        s = min(l / tl, h / th)
        pl, ph = tl * s, th * s
        return (self.get_width() - pl) / 2, (self.get_height() - ph) / 2, pl, ph

    def _rect_trace(self):
        """Rectangle tracé, limité à la page."""
        x, y, l, h = self._rect_page()
        x0, y0, x1, y1 = self._trace
        x0, x1 = sorted((min(max(x0, x), x + l), min(max(x1, x), x + l)))
        y0, y1 = sorted((min(max(y0, y), y + h), min(max(y1, y), y + h)))
        return x0, y0, x1, y1

    def do_snapshot(self, snapshot):
        rect = self._rect_page()
        if rect is None:
            return
        x, y, l, h = rect
        zone = Graphene.Rect().init(x, y, l, h)
        arrondi = Gsk.RoundedRect()
        arrondi.init_from_rect(zone, 2)
        snapshot.append_outset_shadow(arrondi, _rgba(0, 0, 0, 0.28), 0, 2, 0, 10)
        snapshot.append_scaled_texture(self.texture, Gsk.ScalingFilter.TRILINEAR, zone)
        if self._trace is None:
            return

        x0, y0, x1, y1 = self._rect_trace()
        accent = Adw.StyleManager.get_default().get_accent_color_rgba()
        trace = Graphene.Rect().init(x0, y0, x1 - x0, y1 - y0)
        if self.outil == RECADRER:
            voile = _rgba(0, 0, 0, 0.45)
            for bx, by, bl, bh in ((x, y, l, y0 - y), (x, y1, l, y + h - y1),
                                   (x, y0, x0 - x, y1 - y0), (x1, y0, x + l - x1, y1 - y0)):
                if bl > 0 and bh > 0:
                    snapshot.append_color(voile, Graphene.Rect().init(bx, by, bl, bh))
        else:
            snapshot.append_color(_rgba(accent.red, accent.green, accent.blue, 0.18), trace)
        bord = Gsk.RoundedRect()
        bord.init_from_rect(trace, 0)
        snapshot.append_border(bord, [2, 2, 2, 2], [accent] * 4)

    def _debut(self, geste, x, y):
        if self.outil is None or self._rect_page() is None:
            geste.set_state(Gtk.EventSequenceState.DENIED)
            return
        self.grab_focus()
        self._trace = (x, y, x, y)

    def _maj(self, _geste, dx, dy):
        if self._trace is None:
            return
        x0, y0, _x1, _y1 = self._trace
        self._trace = (x0, y0, x0 + dx, y0 + dy)
        self.queue_draw()

    def _fin(self, _geste, _dx, _dy):
        if self._trace is None:
            return
        x0, y0, x1, y1 = self._rect_trace()
        outil = self.outil
        self._trace = None
        self.queue_draw()
        if x1 - x0 < TRACE_MINIMUM or y1 - y0 < TRACE_MINIMUM:
            return
        x, y, l, h = self._rect_page()
        self.emit("zone-tracee", outil, (x0 - x) / l, (y0 - y) / h, (x1 - x) / l, (y1 - y) / h)


class PageApercu(Adw.NavigationPage):
    """Aperçu du document final, page par page, sans outil ni modification."""
    __gtype_name__ = "MaquettePageApercu"
    __gsignals__ = {
        "naviguer": (GObject.SignalFlags.RUN_LAST, None, (int,)),
    }

    def __init__(self):
        super().__init__(title="Aperçu", tag="apercu")
        self.vue = VuePage()
        self.vue.set_focusable(False)
        self.index = 0
        self._infos = []
        self._source = {}
        self.titre = Adw.WindowTitle(title="Aperçu")

        self.precedente = Gtk.Button(icon_name="go-previous-symbolic", tooltip_text="Page précédente (←)")
        self.precedente.connect("clicked", lambda _b: self._bouger(-1))
        self.suivante = Gtk.Button(icon_name="go-next-symbolic", tooltip_text="Page suivante (→)")
        self.suivante.connect("clicked", lambda _b: self._bouger(1))

        barre = Gtk.CenterBox(margin_top=6, margin_bottom=6, margin_start=6, margin_end=6)
        barre.set_start_widget(self.precedente)
        barre.set_end_widget(self.suivante)
        barre.add_css_class("toolbar")

        vue = Adw.ToolbarView(content=self.vue)
        vue.add_top_bar(Adw.HeaderBar(title_widget=self.titre))
        vue.add_bottom_bar(barre)
        self.set_child(vue)

        raccourcis = Gtk.ShortcutController(scope=Gtk.ShortcutScope.LOCAL)
        for touches, delta in (("Left|Page_Up|BackSpace", -1), ("Right|Page_Down|space", 1)):
            raccourcis.add_shortcut(Gtk.Shortcut(trigger=Gtk.ShortcutTrigger.parse_string(touches),
                                                 action=Gtk.CallbackAction.new(self._raccourci, delta)))
        self.add_controller(raccourcis)

    def charger(self, infos, imposition):
        """infos : [(largeur, hauteur, rotation)] du document construit."""
        from .modele import Page, Source
        from .moteur import APERCU
        self._infos = list(infos)
        self._source = {APERCU: Source(APERCU, "aperçu", "", "pdf", self._infos)}
        self._pages = [Page(-1 - i, APERCU, i) for i in range(len(self._infos))]
        self.index = 0
        self.titre.set_subtitle(SOUS_TITRES_APERCU.get(imposition, ""))

    def page_a(self, index):
        if not 0 <= index < len(self._pages):
            return None, len(self._pages)
        self.index = index
        return self._pages[index], len(self._pages)

    def montrer_numero(self, numero, total):
        mot = "feuille" if self.titre.get_subtitle() else "page"
        self.titre.set_title(f"{mot.capitalize()} {numero} sur {total}")
        self.precedente.set_sensitive(numero > 1)
        self.suivante.set_sensitive(numero < total)

    def _bouger(self, delta):
        cible = self.index + delta
        if 0 <= cible < len(self._pages):
            self.emit("naviguer", cible)

    def _raccourci(self, _widget, _args, delta):
        self._bouger(delta)
        return True


class PageGrand(Adw.NavigationPage):
    """Page de navigation « page en grand »."""
    __gtype_name__ = "MaquettePageGrand"
    __gsignals__ = {
        "naviguer": (GObject.SignalFlags.RUN_LAST, None, (int,)),
    }

    def __init__(self):
        super().__init__(title="Page", tag="page")
        self.vue = VuePage()
        self.titre = Adw.WindowTitle()

        entete = Adw.HeaderBar(title_widget=self.titre)
        for icone, action, bulle in (
                ("maquette-reinitialiser-symbolic", "win.reinitialiser", "Rétablir la page d'origine"),
                ("object-rotate-right-symbolic", "win.pivoter-droite", "Pivoter à droite (Ctrl+→)"),
                ("object-rotate-left-symbolic", "win.pivoter-gauche", "Pivoter à gauche (Ctrl+←)")):
            entete.pack_end(Gtk.Button(icon_name=icone, action_name=action, tooltip_text=bulle))

        self.consigne = Gtk.Label(wrap=True, justify=Gtk.Justification.CENTER)
        self.consigne.add_css_class("consigne-outil")
        self.revele_consigne = Gtk.Revealer(child=self.consigne, valign=Gtk.Align.START,
                                            halign=Gtk.Align.CENTER, margin_top=12,
                                            transition_type=Gtk.RevealerTransitionType.CROSSFADE)
        surimpression = Gtk.Overlay(child=self.vue)
        surimpression.add_overlay(self.revele_consigne)

        self.precedente = Gtk.Button(icon_name="go-previous-symbolic", tooltip_text="Page précédente (←)")
        self.precedente.connect("clicked", lambda _b: self.emit("naviguer", -1))
        self.suivante = Gtk.Button(icon_name="go-next-symbolic", tooltip_text="Page suivante (→)")
        self.suivante.connect("clicked", lambda _b: self.emit("naviguer", 1))

        outils = Gtk.Box(spacing=6)
        self._boutons = {}
        for genre, icone, libelle, consigne in OUTILS:
            bouton = Gtk.ToggleButton(child=Adw.ButtonContent(icon_name=icone, label=libelle, can_shrink=True),
                                      tooltip_text=consigne)
            bouton.connect("toggled", self._outil_bascule, genre)
            outils.append(bouton)
            self._boutons[genre] = bouton

        barre = Gtk.CenterBox(margin_top=6, margin_bottom=6, margin_start=6, margin_end=6)
        barre.set_start_widget(self.precedente)
        barre.set_center_widget(outils)
        barre.set_end_widget(self.suivante)
        barre.add_css_class("toolbar")

        vue = Adw.ToolbarView(content=surimpression)
        vue.add_top_bar(entete)
        vue.add_bottom_bar(barre)
        self.set_child(vue)

        raccourcis = Gtk.ShortcutController(scope=Gtk.ShortcutScope.LOCAL)
        for touches, delta in (("Left|Page_Up|BackSpace", -1), ("Right|Page_Down|space", 1)):
            raccourcis.add_shortcut(Gtk.Shortcut(trigger=Gtk.ShortcutTrigger.parse_string(touches),
                                                 action=Gtk.CallbackAction.new(self._raccourci_navigation, delta)))
        self.add_controller(raccourcis)
        self.connect("hidden", lambda _p: self.choisir_outil(None))

    def _raccourci_navigation(self, _widget, _args, delta):
        self.emit("naviguer", delta)
        return True

    def _outil_bascule(self, bouton, genre):
        if bouton.get_active():
            self.choisir_outil(genre)
        elif self.vue.outil == genre:
            self.choisir_outil(None)

    def choisir_outil(self, genre):
        for g, bouton in self._boutons.items():
            if bouton.get_active() != (g == genre):
                bouton.set_active(g == genre)
        self.vue.definir_outil(genre)
        consigne = next((c for g, _i, _l, c in OUTILS if g == genre), None)
        if consigne:
            self.consigne.set_label(consigne)
        self.revele_consigne.set_reveal_child(consigne is not None)

    def montrer(self, numero, total, sous_titre):
        self.titre.set_title(f"Page {numero} sur {total}")
        self.titre.set_subtitle(sous_titre)
        self.precedente.set_sensitive(numero > 1)
        self.suivante.set_sensitive(numero < total)
