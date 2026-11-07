"""Fenêtre principale : barre latérale (Appréciations, PFMP) et contenu."""

from __future__ import annotations

from gi.repository import Adw, Gio, GLib, Gtk, Pango

from . import APP_ID, dialogues, outils, tableur
from .db import CONVENTION
from .vue_appreciations import VueAppreciations
from .vue_pfmp import VuePfmp


class LigneNav(Gtk.ListBoxRow):
    def __init__(self, section, classe_id, libelle, icone):
        super().__init__()
        self.section = section
        self.classe_id = classe_id
        boite = Gtk.Box(spacing=10, margin_top=2, margin_bottom=2)
        boite.append(Gtk.Image.new_from_icon_name(icone))
        boite.append(Gtk.Label(label=libelle, xalign=0, hexpand=True, ellipsize=Pango.EllipsizeMode.END))
        self.compteur = Gtk.Label()
        self.compteur.add_css_class("dim-label")
        self.compteur.add_css_class("caption")
        self.compteur.add_css_class("numeric")
        boite.append(self.compteur)
        self.set_child(boite)


class FenetrePrincipale(Adw.ApplicationWindow):
    def __init__(self, app, base):
        super().__init__(application=app, title="Livret", icon_name=APP_ID)
        self.base = base
        self._chargement = False
        self.set_default_size(int(base.reglage("largeur", 1280)), int(base.reglage("hauteur", 820)))
        # Taille minimale explicite : indispensable pour que les points de rupture s'appliquent.
        self.set_size_request(600, 480)
        if base.reglage_bool("maximisee"):
            self.maximize()

        self.toasts = Adw.ToastOverlay()
        self.split = Adw.NavigationSplitView(min_sidebar_width=220, max_sidebar_width=300)

        # ---------------------------------------------------- barre latérale
        lat = Adw.ToolbarView()
        entete = Adw.HeaderBar()
        self.annees = Gtk.DropDown(tooltip_text="Année scolaire")
        self.annees.add_css_class("flat")
        self.annees.connect("notify::selected", self._annee_changee)
        entete.set_title_widget(self.annees)
        menu = Gio.Menu()
        s = Gio.Menu()
        # Sous-menu « Modifier » : toutes les éditions en un seul endroit
        # (classes, élèves et matières, PFMP, équipe, phrases…). Reconstruit par
        # _maj_menu_modifier() quand la liste des classes change.
        self.menu_modifier = Gio.Menu()
        s.append_submenu("_Modifier", self.menu_modifier)
        s.append("Toutes les _commandes…", "win.commandes")
        menu.append_section(None, s)
        s = Gio.Menu()
        s.append("Nouvelle _classe…", "win.nouvelle-classe")
        s.append("Nouvelle _année scolaire…", "win.nouvelle-annee")
        s.append("A_rchiver l'année…", "win.archiver")
        menu.append_section(None, s)
        s = Gio.Menu()
        s.append("_Tout exporter (tableurs)…", "win.tout-exporter")
        s.append("_Exporter toutes les données (JSON)…", "win.export-json")
        s.append("_Importer des données (JSON)…", "win.import-json")
        menu.append_section(None, s)
        s = Gio.Menu()
        s.append("_Préférences", "app.preferences")
        s.append("Journal d'_erreurs", "app.journal")
        s.append("_À propos de Livret", "app.about")
        menu.append_section(None, s)
        entete.pack_end(Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu,
                                       primary=True, tooltip_text="Menu principal"))
        lat.add_top_bar(entete)
        self.nav = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.nav.add_css_class("navigation-sidebar")
        self.nav.set_header_func(self._entete_section)
        self.nav.connect("row-selected", self._nav_choisie)
        defil = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True)
        defil.set_child(self.nav)
        lat.set_content(defil)
        bas = Gtk.Box(margin_start=6, margin_end=6, margin_top=6, margin_bottom=6)
        b = outils.bouton("list-add-symbolic", "Nouvelle _classe", classes=("flat",),
                          clic=lambda: self.activate_action("win.nouvelle-classe", None))
        b.set_hexpand(True)
        bas.append(b)
        lat.add_bottom_bar(bas)
        self.split.set_sidebar(Adw.NavigationPage(title="Livret", child=lat))

        # ---------------------------------------------------------- contenu
        self.pile = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, hhomogeneous=False,
                              vhomogeneous=False)
        vide = Adw.ToolbarView()
        vide.add_top_bar(Adw.HeaderBar(show_title=False))
        st = Adw.StatusPage(icon_name=f"{APP_ID}-symbolic", title="Bienvenue dans Livret",
                            description="Commencez par créer une classe. Les données restent sur cet "
                                        "ordinateur et sont enregistrées automatiquement.")
        st.set_child(outils.bouton("list-add-symbolic", "Nouvelle _classe…", classes=("pill", "suggested-action"),
                                   clic=lambda: self.activate_action("win.nouvelle-classe", None)))
        vide.set_content(st)
        self.pile.add_named(vide, "vide")
        self.vue_appr = VueAppreciations(self)
        self.pile.add_named(self.vue_appr, "appr")
        self.vue_pfmp = VuePfmp(self)
        self.pile.add_named(self.vue_pfmp, "pfmp")
        self.page_contenu = Adw.NavigationPage(title="Livret", child=self.pile)
        self.split.set_content(self.page_contenu)

        self.toasts.set_child(self.split)
        self.set_content(self.toasts)

        # Un seul point de rupture est actif à la fois (le dernier qui correspond) :
        # le plus étroit reprend donc aussi les réglages du plus large.
        moyen = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 1100sp"))
        etroit = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 760sp"))
        for bp in (moyen, etroit):
            bp.add_setter(self.vue_appr.split, "collapsed", True)
            bp.add_setter(self.vue_pfmp.selecteur, "policy", Adw.ViewSwitcherPolicy.NARROW)
        etroit.add_setter(self.split, "collapsed", True)
        etroit.connect("apply", lambda *_: self.vue_pfmp.definir_compact(True))
        etroit.connect("unapply", lambda *_: self.vue_pfmp.definir_compact(False))
        self.add_breakpoint(moyen)
        self.add_breakpoint(etroit)

        self._actions()
        self.connect("close-request", self._fermeture)
        self.rafraichir()

    # ---------------------------------------------------------- actions
    def _actions(self):
        for nom, f in (("nouvelle-classe", lambda: dialogues.nouvelle_classe(self)),
                       ("nouvelle-annee", lambda: dialogues.nouvelle_annee(self)),
                       ("archiver", lambda: dialogues.archiver_annee(self)),
                       ("phrases", self.ouvrir_phrases),
                       ("tout-exporter", self.tout_exporter),
                       ("commandes", self.ouvrir_commandes),
                       ("export-json", self.exporter_json),
                       ("import-json", self.importer_json)):
            a = Gio.SimpleAction.new(nom, None)
            a.connect("activate", lambda _a, _p, f=f: f())
            self.add_action(a)
        # Éditions du sous-menu « Modifier »
        for nom, f in (("carnet", self.ouvrir_carnet),
                       ("dates-pfmp", lambda: self.vue_pfmp.dates()),
                       ("repartition", lambda: self.vue_pfmp.repartition()),
                       ("visites", lambda: self.vue_pfmp.visites())):
            a = Gio.SimpleAction.new(nom, None)
            a.connect("activate", lambda _a, _p, f=f: f())
            self.add_action(a)
        a = Gio.SimpleAction.new("modifier-classe", GLib.VariantType.new("x"))
        a.connect("activate", lambda _a, p: self.modifier_classe(p.get_int64()))
        self.add_action(a)

    def ouvrir_carnet(self):
        self.vider_attente()
        dialogues.DialogueCarnet(self).present(self)

    def modifier_classe(self, classe_id):
        """Réglages, élèves et matières d'une classe."""
        if self.lecture_seule():
            self.toast("Année archivée : consultation seule")
            return
        if self.base.classe(classe_id) is None:
            return
        self.vider_attente()
        dialogues.ReglagesClasse(self, classe_id).present(self)

    def _maj_menu_modifier(self):
        """Toutes les éditions possibles, groupées par thème, classées par ordre alphabétique."""
        m = self.menu_modifier
        m.remove_all()
        aid = self.base.annee_active()
        s = Gio.Menu()
        for c in self.base.classes(aid):
            item = Gio.MenuItem.new(f"{c['nom']} : élèves, matières, réglages…", None)
            item.set_action_and_target_value("win.modifier-classe", GLib.Variant.new_int64(c["id"]))
            s.append_item(item)
        s.append("Nouvelle classe…", "win.nouvelle-classe")
        m.append_section("Classes", s)
        s = Gio.Menu()
        s.append("Carnet d'entreprises (adresses, téléphones, tuteurs)…", "win.carnet")
        s.append("Dates des PFMP…", "win.dates-pfmp")
        s.append("Équipe pédagogique et heures (répartition des suivis)…", "win.repartition")
        s.append("Visites : élèves suivis, entreprises, tuteurs…", "win.visites")
        m.append_section("PFMP", s)
        s = Gio.Menu()
        s.append("Banque de phrases…", "win.phrases")
        m.append_section("Appréciations", s)
        s = Gio.Menu()
        s.append("Adresse de l'établissement, saisie, données…", "app.preferences")
        s.append("Nouvelle année scolaire…", "win.nouvelle-annee")
        m.append_section("Établissement et année", s)

    def ouvrir_phrases(self):
        self.vider_attente()
        d = dialogues.DialoguePhrases(self)
        d.present(self)

    def exporter_json(self):
        self.vider_attente()
        nom = f"Livret {GLib.DateTime.new_now_local().format('%Y-%m-%d')}.json"

        def ecrire(chemin):
            try:
                self.base.exporter_json(chemin)
            except OSError as e:
                outils.alerte(self, "Export impossible", str(e))
                return
            self.toast("Données exportées. Ce fichier contient des données d'élèves : rangez-le en lieu sûr.")
        outils.enregistrer_fichier(self, "Exporter toutes les données", nom,
                                   [("Export Livret (JSON)", ["json"], ["application/json"])], ecrire)

    def tout_exporter(self):
        self.vider_attente()
        aid = self.base.annee_active()

        def choisir(dossier):
            try:
                faits = tableur.exporter_donnees(self.base, aid, dossier)
            except OSError as e:
                outils.alerte(self, "Export impossible", str(e))
                return
            self.toast(f"{len(faits)} classeur(s) exporté(s). Ils contiennent des données "
                       "d'élèves : rangez-les en lieu sûr.",
                       "Ouvrir le dossier", lambda: outils.ouvrir_chemin(self, dossier))
        outils.choisir_dossier(self, "Choisir le dossier de destination", choisir)

    def ouvrir_commandes(self):
        self.vider_attente()
        dialogues.DialogueCommandes(self).present(self)

    def importer_json(self):
        self.vider_attente()

        def lire(chemin):
            def faire():
                try:
                    self.base.importer_json(chemin)
                except (ValueError, OSError) as e:
                    outils.alerte(self, "Import impossible", str(e))
                    return
                self.rafraichir(nouvelle_annee=True)
                self.toast("Données importées (l'ancienne base a été sauvegardée)")
            outils.confirmer(self, "Remplacer toutes les données ?",
                             "Le contenu du fichier remplace toutes les données actuelles. "
                             "Une sauvegarde de la base actuelle est faite juste avant.",
                             "_Remplacer", faire)
        outils.choisir_fichier(self, "Importer des données",
                               [("Export Livret (JSON)", ["json"], ["application/json"])], lire)

    def desarchiver(self):
        def faire():
            self.base.archiver_annee(self.base.annee_active(), False)
            self.rafraichir()
            self.toast("L'année est de nouveau modifiable")
        outils.confirmer(self, "Désarchiver l'année ?", "L'année redevient modifiable.",
                         "_Désarchiver", faire, destructif=False)

    # ------------------------------------------------------------ état
    def lecture_seule(self) -> bool:
        return self.base.annee_archivee(self.base.annee_active())

    def toast(self, titre, bouton=None, rappel=None):
        t = Adw.Toast(title=GLib.markup_escape_text(titre), timeout=4)
        if bouton and rappel:
            t.set_button_label(bouton)
            t.connect("button-clicked", lambda *_: rappel())
        self.toasts.add_toast(t)

    def vider_attente(self):
        self.vue_appr.vider_attente()
        self.vue_pfmp.vider_attente()

    # -------------------------------------------------------- navigation
    def rafraichir(self, selection=None, nouvelle_annee=False):
        """Reconstruit la barre latérale et recharge la vue affichée."""
        self.vider_attente()
        courante = self.nav.get_selected_row()
        if selection is None and courante is not None and not nouvelle_annee:
            selection = (courante.section, courante.classe_id)
        if selection is None:
            sec = self.base.reglage("nav_section", "appr")
            cid = self.base.reglage("nav_classe")
            selection = (sec, int(cid) if cid and cid != "None" else None)
        aid = self.base.annee_active()
        self._chargement = True
        annees = self.base.annees()
        self._ids_annees = [a["id"] for a in annees]
        self.annees.set_model(outils.liste_chaines(
            [a["libelle"] + (" (archivée)" if a["archivee"] else "") for a in annees]))
        self.annees.set_selected(self._ids_annees.index(aid))
        self.nav.remove_all()
        classes = self.base.classes(aid)
        for c in classes:
            self.nav.append(LigneNav("appr", c["id"], c["nom"], "document-edit-symbolic"))
        # PFMP : uniquement les classes dont on suit les stages (réglage de la classe),
        # sans entrée « Toutes les classes ».
        for c in self.base.classes_pfmp(aid):
            self.nav.append(LigneNav("pfmp", c["id"], c["nom"], "system-users-symbolic"))
        self._maj_menu_modifier()
        ro = self.lecture_seule()
        for nom in ("modifier-classe", "dates-pfmp", "nouvelle-classe"):
            self.lookup_action(nom).set_enabled(not ro)
        self._chargement = False
        self.maj_compteurs()
        cible = None
        i = 0
        while (l := self.nav.get_row_at_index(i)) is not None:
            if (l.section, l.classe_id) == tuple(selection):
                cible = l
            i += 1
        if cible is None:
            cible = self.nav.get_row_at_index(0)
        if cible is None:
            self.pile.set_visible_child_name("vide")
            self.page_contenu.set_title("Livret")
            return
        if cible is courante:
            self._afficher(cible)
        else:
            self.nav.select_row(cible)

    def maj_compteurs(self):
        aid = self.base.annee_active()
        etats_par_classe = {}
        stages = None
        i = 0
        while (l := self.nav.get_row_at_index(i)) is not None:
            i += 1
            if l.section == "appr":
                c = self.base.classe(l.classe_id)
                if c is None:
                    continue
                per = self.base.reglage(f"periode_{c['id']}", "1")
                etats = etats_par_classe.get(c["id"]) or self.base.etats_classe(c["id"], int(per))
                faits = sum(1 for e in etats.values() if e == "termine")
                l.compteur.set_text(f"{faits}/{len(etats)}" if etats else "")
                l.set_tooltip_text(f"{faits} élèves terminés sur {len(etats)}")
            else:
                if stages is None:
                    stages = self.base.stages(aid, self.base.pfmp_id(aid, self.vue_pfmp.numero))
                ceux = [s for s in stages if l.classe_id is None or s["classe_id"] == l.classe_id]
                fin = sum(1 for s in ceux if s["convention"] == len(CONVENTION) - 1)
                l.compteur.set_text(f"{fin}/{len(ceux)}" if ceux else "")
                l.set_tooltip_text(f"Conventions finalisées (PFMP {self.vue_pfmp.numero}) : "
                                   f"{fin} sur {len(ceux)}")

    @staticmethod
    def _entete_section(ligne, avant):
        if avant is None or avant.section != ligne.section:
            lab = Gtk.Label(label="Appréciations" if ligne.section == "appr" else "PFMP", xalign=0,
                            margin_start=8, margin_top=12 if avant else 6, margin_bottom=4)
            lab.add_css_class("heading")
            ligne.set_header(lab)
        else:
            ligne.set_header(None)

    def _nav_choisie(self, _l, ligne):
        if ligne is None or self._chargement:
            return
        self._afficher(ligne)
        self.split.set_show_content(True)

    def _afficher(self, ligne):
        self.vider_attente()
        self.base.definir_reglage("nav_section", ligne.section)
        self.base.definir_reglage("nav_classe", ligne.classe_id)
        if ligne.section == "appr":
            self.pile.set_visible_child_name("appr")
            self.vue_appr.afficher_classe(ligne.classe_id)
            self.page_contenu.set_title("Appréciations")
        else:
            self.pile.set_visible_child_name("pfmp")
            self.vue_pfmp.afficher(ligne.classe_id, "classe")
            self.page_contenu.set_title("PFMP")

    def _annee_changee(self, dd, _p):
        if self._chargement:
            return
        i = dd.get_selected()
        if 0 <= i < len(self._ids_annees):
            self.vider_attente()
            self.base.choisir_annee(self._ids_annees[i])
            GLib.idle_add(lambda: self.rafraichir(nouvelle_annee=True) and False)

    def _fermeture(self, *_):
        self.vider_attente()
        largeur, hauteur = self.get_default_size()
        self.base.definir_reglage("maximisee", int(self.is_maximized()))
        if not self.is_maximized():
            self.base.definir_reglage("largeur", largeur)
            self.base.definir_reglage("hauteur", hauteur)
        return False
