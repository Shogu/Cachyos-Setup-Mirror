"""Grille des miniatures : le document final, page par page.

La grille ne connaît ni le moteur ni l'historique : elle affiche les pages
qu'on lui donne, demande leur rendu via `demander_rendu` et signale les
gestes (déplacement, dépôt de fichiers, activation).
"""

from gi.repository import Gdk, Gio, GLib, GObject, Graphene, Gtk

from . import modele

RATIO_BOITE = 1.414          # A4 portrait tient pile dans une boîte carrée
MARGE_DEFILEMENT = 48        # px près du bord où le glisser fait défiler
PREFIXE_GLISSER = "maquette-pages:"


class CartePage(Gtk.FlowBoxChild):
    __gtype_name__ = "MaquetteCartePage"

    def __init__(self, uid):
        super().__init__()
        self.uid = uid
        self.page = None
        self.cle_voulue = None
        self.add_css_class("carte-page")

        self.image = Gtk.Picture(content_fit=Gtk.ContentFit.FILL, can_shrink=True)
        self.image.add_css_class("miniature")
        self.repere = Gtk.Box(halign=Gtk.Align.END, valign=Gtk.Align.START, visible=False,
                              tooltip_text="Page modifiée")
        self.repere.add_css_class("repere-modifie")
        self.badge = Gtk.Image(halign=Gtk.Align.START, valign=Gtk.Align.END, visible=False, pixel_size=12)
        self.badge.add_css_class("badge-conversion")

        surimpression = Gtk.Overlay(halign=Gtk.Align.CENTER, child=self.image)
        surimpression.add_overlay(self.repere)
        surimpression.add_overlay(self.badge)

        self.bande = Gtk.Box(halign=Gtk.Align.CENTER, margin_top=4)
        self.bande.add_css_class("bande-source")

        self.cadre = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.END)
        self.cadre.append(surimpression)
        self.cadre.append(self.bande)
        conteneur = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.END)
        conteneur.append(self.cadre)

        self.numero = Gtk.Label(margin_top=6)
        self.numero.add_css_class("caption")
        self.numero.add_css_class("numeric")
        self.numero.add_css_class("dim-label")

        boite = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.zone = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.END)
        self.zone.append(conteneur)
        boite.append(self.zone)
        boite.append(self.numero)
        self.set_child(boite)

    def configurer(self, numero, page, sources, boite, avec_numero, avec_bande):
        self.page = page
        l, h = modele.taille_affichee(page, sources)
        s = boite / max(l, h)
        lp, hp = max(8, round(l * s)), max(8, round(h * s))
        self.zone.set_size_request(boite, boite)
        self.image.set_size_request(lp, hp)
        self.bande.set_size_request(lp, -1)

        self.numero.set_label(str(numero))
        self.numero.set_visible(avec_numero)
        self.repere.set_visible(page.modifiee)

        source = sources.get(page.source)
        self.bande.set_visible(avec_bande and source is not None)
        for i in range(6):
            self.bande.remove_css_class(f"source-{i}")
        if source is not None:
            self.bande.add_css_class(f"source-{source.couleur % 6}")
        if source is not None and source.convertie:
            self.badge.set_from_icon_name("maquette-image-symbolic")
            self.badge.set_tooltip_text(f"Image « {source.nom} » mise en page")
            self.badge.set_visible(True)
        else:
            self.badge.set_visible(False)
        tip = f"Page {numero}"
        if source is not None:
            tip += f" — {source.nom}, page {page.index + 1}"
        elif page.blanche:
            tip += " — page blanche"
        self.image.set_tooltip_text(tip)
        return lp, hp

    def afficher(self, texture):
        self.image.set_paintable(texture)


class Grille(Gtk.ScrolledWindow):
    __gtype_name__ = "MaquetteGrille"
    __gsignals__ = {
        "deplacer": (GObject.SignalFlags.RUN_LAST, None, (object, int)),
        "deposer-fichiers": (GObject.SignalFlags.RUN_LAST, None, (object, int)),
        "activer": (GObject.SignalFlags.RUN_LAST, None, (int,)),
        "selection-changee": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, menu_contextuel: Gio.MenuModel, demander_rendu):
        super().__init__(hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True)
        self._demander_rendu = demander_rendu
        self._cartes: dict[int, CartePage] = {}
        self._ordre: list[CartePage] = []
        self._indicateur = None
        self._vitesse_defilement = 0
        self._source_defilement = 0

        self.flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.MULTIPLE, activate_on_single_click=False,
                                homogeneous=True, valign=Gtk.Align.START, max_children_per_line=500,
                                row_spacing=6, column_spacing=6, margin_top=18, margin_bottom=18,
                                margin_start=18, margin_end=18)
        self.flow.add_css_class("grille-pages")
        self.flow.connect("child-activated", lambda _f, c: self.emit("activer", c.uid))
        self.flow.connect("selected-children-changed", lambda _f: self.emit("selection-changee"))
        self.set_child(self.flow)

        self._menu = Gtk.PopoverMenu.new_from_model(menu_contextuel)
        self._menu.set_has_arrow(False)
        self._menu.set_halign(Gtk.Align.START)
        self._menu.set_parent(self.flow)

        clic = Gtk.GestureClick(button=0)
        clic.connect("pressed", self._sur_clic)
        self.flow.add_controller(clic)

        cible = Gtk.DropTarget.new(GObject.TYPE_NONE, Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
        cible.set_gtypes([Gdk.FileList, GObject.TYPE_STRING])
        cible.connect("motion", self._sur_survol)
        cible.connect("leave", self._sur_sortie)
        cible.connect("drop", self._sur_depot)
        self.flow.add_controller(cible)

        defil = Gtk.EventControllerScroll(flags=Gtk.EventControllerScrollFlags.VERTICAL)
        defil.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        defil.connect("scroll", self._sur_molette)
        self.add_controller(defil)

        raccourcis = Gtk.ShortcutController(scope=Gtk.ShortcutScope.LOCAL)
        raccourcis.add_shortcut(Gtk.Shortcut(trigger=Gtk.ShortcutTrigger.parse_string("Delete"),
                                             action=Gtk.NamedAction.new("win.supprimer")))
        raccourcis.add_shortcut(Gtk.Shortcut(trigger=Gtk.ShortcutTrigger.parse_string("Escape"),
                                             action=Gtk.CallbackAction.new(self._tout_deselectionner)))
        self.flow.add_controller(raccourcis)

    def do_dispose(self):
        if self._source_defilement:
            GLib.Source.remove(self._source_defilement)
            self._source_defilement = 0
        if self._menu is not None:
            self._menu.unparent()
            self._menu = None
        Gtk.ScrolledWindow.do_dispose(self)

    # -------------------------------------------------------- contenu
    def synchroniser(self, pages, sources, reglages):
        boite = round(reglages.get_int("taille-miniatures") * RATIO_BOITE)
        avec_numero = reglages.get_boolean("numeros")
        avec_bande = reglages.get_boolean("couleur-source")
        echelle = self.get_scale_factor()
        selection = set(self.selection())

        cartes, ordre = {}, []
        for rang, page in enumerate(pages):
            carte = self._cartes.get(page.uid)
            if carte is None:
                carte = self._nouvelle_carte(page.uid)
            cartes[page.uid] = carte
            ordre.append(carte)
            lp, hp = carte.configurer(rang + 1, page, sources, boite, avec_numero, avec_bande)
            cle = (page.cle_rendu(), lp * echelle, hp * echelle)
            if carte.cle_voulue != cle:
                carte.cle_voulue = cle
                self._demander_rendu(carte, page, lp * echelle, hp * echelle, rang)

        if [c.uid for c in ordre] != [c.uid for c in self._ordre]:
            for carte in self._ordre:
                self.flow.remove(carte)
            for carte in ordre:
                self.flow.append(carte)
        self._cartes, self._ordre = cartes, ordre
        self.selectionner([u for u in selection if u in cartes])

    def _nouvelle_carte(self, uid):
        carte = CartePage(uid)
        source = Gtk.DragSource(actions=Gdk.DragAction.MOVE)
        source.connect("prepare", self._preparer_glisser, carte)
        source.connect("drag-begin", self._debut_glisser, carte)
        carte.add_controller(source)
        return carte

    def selection(self) -> list[int]:
        return [c.uid for c in self._ordre if c.is_selected()]

    def selectionner(self, uids, focus=False):
        uids = set(uids)
        for carte in self._ordre:
            if carte.uid in uids and not carte.is_selected():
                self.flow.select_child(carte)
            elif carte.uid not in uids and carte.is_selected():
                self.flow.unselect_child(carte)
        if focus:
            for carte in self._ordre:
                if carte.uid in uids:
                    carte.grab_focus()
                    break

    def _tout_deselectionner(self, *_args):
        self.flow.unselect_all()
        return True

    # --------------------------------------------------------- souris
    def _sur_clic(self, geste, _n, x, y):
        carte = self.flow.get_child_at_pos(x, y)
        if carte is None:
            self.flow.unselect_all()
            return
        if geste.get_current_button() != Gdk.BUTTON_SECONDARY:
            return
        if not carte.is_selected():
            self.flow.unselect_all()
            self.flow.select_child(carte)
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = int(x), int(y), 1, 1
        self._menu.set_pointing_to(rect)
        self._menu.popup()

    def _sur_molette(self, controleur, _dx, dy):
        if not controleur.get_current_event_state() & Gdk.ModifierType.CONTROL_MASK:
            return False
        self.activate_action("win.zoom-moins" if dy > 0 else "win.zoom-plus", None)
        return True

    # ------------------------------------------------ glisser-déposer
    def _preparer_glisser(self, _source, _x, _y, carte):
        if not carte.is_selected():
            self.flow.unselect_all()
            self.flow.select_child(carte)
        texte = PREFIXE_GLISSER + ",".join(str(u) for u in self.selection())
        return Gdk.ContentProvider.new_for_value(GObject.Value(GObject.TYPE_STRING, texte))

    def _debut_glisser(self, source, _drag, carte):
        largeur = carte.image.get_width()
        source.set_icon(Gtk.WidgetPaintable.new(carte.image), largeur // 2, 12)

    def _index_insertion(self, x, y):
        """Position d'insertion sous le pointeur, et la carte à marquer."""
        if not self._ordre:
            return 0, None, None
        rangees = {}
        for i, carte in enumerate(self._ordre):
            ok, b = carte.compute_bounds(self.flow)
            if ok:
                rangees.setdefault(round(b.get_y()), []).append((i, carte, b))
        if not rangees:
            return len(self._ordre), None, None

        def distance(ligne):
            b = ligne[0][2]
            haut, bas = b.get_y(), b.get_y() + b.get_height()
            return 0 if haut <= y <= bas else min(abs(y - haut), abs(y - bas))
        ligne = min(rangees.values(), key=distance)
        for i, carte, b in ligne:
            if x < b.get_x() + b.get_width() / 2:
                return i, carte, "insertion-avant"
        i, carte, _b = ligne[-1]
        return i + 1, carte, "insertion-apres"

    def _marquer(self, carte, classe):
        if self._indicateur is not None:
            ancienne, ancienne_classe = self._indicateur
            ancienne.remove_css_class(ancienne_classe)
        self._indicateur = (carte, classe) if carte is not None else None
        if carte is not None:
            carte.add_css_class(classe)

    def _sur_survol(self, cible, x, y):
        _i, carte, classe = self._index_insertion(x, y)
        self._marquer(carte, classe)
        self._defiler_pres_du_bord(x, y)
        interne = cible.get_current_drop().get_drag() is not None
        return Gdk.DragAction.MOVE if interne else Gdk.DragAction.COPY

    def _sur_sortie(self, _cible):
        self._marquer(None, None)
        self._arreter_defilement()

    def _sur_depot(self, _cible, valeur, x, y):
        index, _c, _cl = self._index_insertion(x, y)
        self._marquer(None, None)
        self._arreter_defilement()
        if isinstance(valeur, Gdk.FileList):
            self.emit("deposer-fichiers", valeur.get_files(), index)
            return True
        if isinstance(valeur, str) and valeur.startswith(PREFIXE_GLISSER):
            uids = [int(u) for u in valeur[len(PREFIXE_GLISSER):].split(",") if u]
            self.emit("deplacer", uids, index)
            return True
        if isinstance(valeur, str):
            fichiers = [Gio.File.new_for_uri(l.strip()) for l in valeur.splitlines() if l.startswith("file://")]
            if fichiers:
                self.emit("deposer-fichiers", fichiers, index)
                return True
        return False

    def _defiler_pres_du_bord(self, x, y):
        ok, point = self.flow.compute_point(self, Graphene.Point().init(x, y))
        if not ok:
            return
        hauteur = self.get_height()
        if point.y < MARGE_DEFILEMENT:
            self._vitesse_defilement = -(MARGE_DEFILEMENT - point.y) / 2
        elif point.y > hauteur - MARGE_DEFILEMENT:
            self._vitesse_defilement = (point.y - hauteur + MARGE_DEFILEMENT) / 2
        else:
            self._arreter_defilement()
            return
        if not self._source_defilement:
            self._source_defilement = GLib.timeout_add(16, self._pas_defilement)

    def _pas_defilement(self):
        adj = self.get_vadjustment()
        adj.set_value(adj.get_value() + self._vitesse_defilement)
        return GLib.SOURCE_CONTINUE

    def _arreter_defilement(self):
        if self._source_defilement:
            GLib.Source.remove(self._source_defilement)
            self._source_defilement = 0
