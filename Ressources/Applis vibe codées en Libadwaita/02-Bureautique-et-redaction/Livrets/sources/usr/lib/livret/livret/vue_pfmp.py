"""Section PFMP : recherche de stage, conventions, entreprises, suivis."""

from __future__ import annotations

from gi.repository import Adw, GLib, Gtk, Pango

from . import outils
from .db import CONVENTION, RECHERCHE, normaliser

ETAPE_SUIVANTE = ["Parents", "Direction", "Finaliser"]
CLES_RECHERCHE = list(RECHERCHE)  # en_cours, terminee
LIBELLES_RECHERCHE = ["Recherche en cours", "Recherche terminée"]
FILTRE_RECHERCHE = ["Recherches : toutes", "En cours", "Terminées"]
FILTRE_CONVENTION = ["Conventions : toutes", *CONVENTION, "Non finalisées"]


# ------------------------------------------------------------------ carnet

class BoutonCarnet(Gtk.MenuButton):
    """Choisir une entreprise déjà connue (carnet alimenté automatiquement)."""

    def __init__(self, fen, choisir):
        super().__init__(icon_name="x-office-address-book-symbolic", valign=Gtk.Align.CENTER,
                         tooltip_text="Choisir dans le carnet d'entreprises")
        self.add_css_class("flat")
        self.fen = fen
        self.choisir = choisir
        pop = Gtk.Popover()
        boite = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_top=6,
                        margin_bottom=6, margin_start=6, margin_end=6)
        boite.set_size_request(360, -1)
        self.recherche = Gtk.SearchEntry(placeholder_text="Rechercher une entreprise…")
        self.recherche.connect("search-changed", lambda *_: self._remplir())
        boite.append(self.recherche)
        self.liste = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.liste.add_css_class("navigation-sidebar")
        vide = Gtk.Label(label="Le carnet se remplit tout seul quand vous saisissez une entreprise.",
                         wrap=True, margin_top=12, margin_bottom=12, max_width_chars=36)
        vide.add_css_class("dim-label")
        self.liste.set_placeholder(vide)
        self.liste.connect("row-activated", self._active)
        defil = Gtk.ScrolledWindow(propagate_natural_height=True, max_content_height=320,
                                   hscrollbar_policy=Gtk.PolicyType.NEVER)
        defil.set_child(self.liste)
        boite.append(defil)
        pop.set_child(boite)
        pop.connect("show", lambda *_: (self.recherche.set_text(""), self._remplir()))
        self.set_popover(pop)

    def _remplir(self):
        self.liste.remove_all()
        for e in self.fen.base.carnet(self.recherche.get_text()):
            ligne = Gtk.ListBoxRow()
            ligne.entreprise = e
            b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin_top=4, margin_bottom=4)
            t = Gtk.Label(label=e["nom"], xalign=0, ellipsize=Pango.EllipsizeMode.END)
            t.add_css_class("heading")
            b.append(t)
            if e["adresse"]:
                a = Gtk.Label(label=e["adresse"], xalign=0, ellipsize=Pango.EllipsizeMode.END)
                a.add_css_class("dim-label")
                a.add_css_class("caption")
                b.append(a)
            ligne.set_child(b)
            self.liste.append(ligne)

    def _active(self, _l, ligne):
        self.get_popover().popdown()
        self.choisir(ligne.entreprise)


class ChampsEntreprise:
    """Lignes Adw.EntryRow liées au stage d'un élève pour une PFMP."""

    CHAMPS = [("entreprise", "Entreprise d'accueil"), ("adresse", "Adresse"),
              ("telephone", "Téléphone"), ("tuteur", "Tuteur"), ("visite_le", "Date de visite")]

    def __init__(self, fen, eleve_id, pfmp_id, apres=None, lecture_seule=False):
        self.fen = fen
        self.eleve_id = eleve_id
        self.pfmp_id = pfmp_id
        self.apres = apres
        self.retard = outils.retarder(600)
        self._chargement = True
        s = fen.base.stage(eleve_id, pfmp_id)
        self.entrees: dict[str, Adw.EntryRow] = {}
        self.lignes = []
        for cle, titre in self.CHAMPS:
            r = Adw.EntryRow(title=titre, text=s[cle] or "", use_markup=False)
            if cle == "telephone":
                r.set_input_purpose(Gtk.InputPurpose.PHONE)
            r.connect("changed", self._change)
            r.set_editable(not lecture_seule)
            self.entrees[cle] = r
            self.lignes.append(r)
        if not lecture_seule:
            self.entrees["entreprise"].add_suffix(BoutonCarnet(fen, self._depuis_carnet))
        self.bouton_itineraire = outils.bouton(
            "livret-route-symbolic", infobulle="Itinéraire vers cette adresse "
                                                 "(GNOME Cartes, sinon OpenStreetMap)",
            classes=("flat",), clic=self.itineraire)
        self.bouton_itineraire.set_valign(Gtk.Align.CENTER)
        self.entrees["adresse"].add_suffix(self.bouton_itineraire)
        tel = outils.bouton("edit-copy-symbolic", infobulle="Copier le numéro", classes=("flat",),
                            clic=lambda: self._copier_tel())
        tel.set_valign(Gtk.Align.CENTER)
        self.entrees["telephone"].add_suffix(tel)
        self.entrees["visite_le"].set_tooltip_text("Par exemple : 12/03 à 10 h")
        self._chargement = False
        self._maj()

    def _maj(self):
        self.bouton_itineraire.set_sensitive(bool(self.entrees["adresse"].get_text().strip()))

    def itineraire(self):
        outils.ouvrir_itineraire(self.entrees["adresse"], self.entrees["adresse"].get_text())

    def _copier_tel(self):
        if outils.copier(self.entrees["telephone"], self.entrees["telephone"].get_text().strip()):
            self.fen.toast("Numéro copié")

    def _change(self, *_):
        self._maj()
        if not self._chargement:
            self.retard.planifier(self.enregistrer)

    def enregistrer(self):
        if self.fen.lecture_seule():
            return
        self.fen.base.maj_stage(self.eleve_id, self.pfmp_id,
                                **{k: r.get_text().strip() for k, r in self.entrees.items()})
        if self.apres:
            self.apres()

    def _depuis_carnet(self, e):
        self._chargement = True
        self.entrees["entreprise"].set_text(e["nom"])
        self.entrees["adresse"].set_text(e["adresse"])
        self.entrees["telephone"].set_text(e["telephone"])
        if e["tuteur"] and not self.entrees["tuteur"].get_text().strip():
            self.entrees["tuteur"].set_text(e["tuteur"])
        self._chargement = False
        self._maj()
        self.retard.annuler()
        self.enregistrer()

    def vider_attente(self):
        self.retard.vider()


# ------------------------------------------------------------- lignes liste

class Etapes(Gtk.Box):
    def __init__(self):
        super().__init__(spacing=3, valign=Gtk.Align.CENTER)
        self.add_css_class("etapes")
        self.blocs = []
        for _ in CONVENTION:
            b = Gtk.Box()
            b.add_css_class("etape")
            self.blocs.append(b)
            self.append(b)

    def definir(self, n):
        for i, b in enumerate(self.blocs):
            (b.add_css_class if i <= n else b.remove_css_class)("faite")
        (self.add_css_class if n == len(CONVENTION) - 1 else self.remove_css_class)("finalisee")
        self.set_tooltip_text(f"Convention : étape {n + 1} sur {len(CONVENTION)} — {CONVENTION[n]}")


class LigneStage(Adw.ActionRow):
    def __init__(self, vue, s, avec_classe, lecture_seule):
        super().__init__(use_markup=False, activatable=True, title=f"{s['nom']} {s['prenom']}")
        self.vue = vue
        self.s = s
        self.lecture_seule = lecture_seule
        self.compact = vue.compact
        self._chargement = True
        self.set_subtitle(self._sous_titre(avec_classe))
        self.set_subtitle_lines(1)
        self.set_title_lines(1)

        self.recherche = Gtk.DropDown(model=outils.liste_chaines(LIBELLES_RECHERCHE),
                                      valign=Gtk.Align.CENTER, tooltip_text="Recherche de stage")
        self.recherche.set_selected(CLES_RECHERCHE.index(s["recherche"]))
        self.recherche.set_size_request(190, -1)
        self.recherche.connect("notify::selected", self._recherche)
        self.recherche.update_property([Gtk.AccessibleProperty.LABEL], ["Recherche de stage"])
        self.add_suffix(self.recherche)

        self.etapes = Etapes()
        self.add_suffix(self.etapes)
        self.convention = Gtk.DropDown(model=outils.liste_chaines(CONVENTION), valign=Gtk.Align.CENTER,
                                       tooltip_text="Convention de stage")
        self.convention.set_selected(s["convention"])
        self.convention.set_size_request(185, -1)
        self.convention.connect("notify::selected", self._convention)
        self.convention.update_property([Gtk.AccessibleProperty.LABEL], ["Convention"])
        self.add_suffix(self.convention)
        self.suivant = Gtk.Button(valign=Gtk.Align.CENTER)
        self.suivant.add_css_class("flat")
        self.suivant.set_size_request(118, -1)
        self.suivant.connect("clicked", lambda *_: self._avancer())
        self.suivant.set_valign(Gtk.Align.CENTER)
        self.add_suffix(self.suivant)
        self._maj()
        self.compacter(vue.compact)
        self._chargement = False

    def compacter(self, compact):
        """Fenêtre étroite : on garde l'essentiel (nom, recherche, convention)."""
        self.compact = compact
        self.recherche.set_size_request(-1 if compact else 190, -1)
        self.convention.set_size_request(-1 if compact else 185, -1)
        self._maj()

    def _sous_titre(self, avec_classe):
        s = self.s
        morceaux = []
        if avec_classe:
            morceaux.append(s["classe_nom"])
        morceaux.append(s["entreprise"] or "Entreprise non renseignée")
        if s["enseignant_nom"]:
            morceaux.append(f"suivi : {s['enseignant_nom']}")
        return " · ".join(morceaux)

    @staticmethod
    def _montrer(widget, oui):
        """Masque sans retirer la place occupée : les colonnes restent alignées d'une
        ligne à l'autre, que la convention soit commencée ou non."""
        widget.set_opacity(1 if oui else 0)
        widget.set_can_target(oui)
        widget.set_can_focus(oui)
        widget.update_state([Gtk.AccessibleState.HIDDEN], [not oui])

    def _maj(self):
        terminee = self.s["recherche"] == "terminee"
        # Recherche terminée : le sélecteur est grisé (on peut la rouvrir depuis la fiche « Élève »).
        self.recherche.set_sensitive(not self.lecture_seule and not terminee)
        # La convention ne commence qu'une fois la recherche terminée : sinon,
        # ni chemin bleu, ni sélecteur, ni bouton « étape suivante ».
        n = self.convention.get_selected()
        fin = n >= len(CONVENTION) - 1
        self.etapes.definir(n)
        self.etapes.set_visible(not self.compact)
        self._montrer(self.etapes, terminee)
        self._montrer(self.convention, terminee)
        self.convention.set_sensitive(not self.lecture_seule)
        self.suivant.set_visible(not self.compact)
        self._montrer(self.suivant, terminee and not fin)
        self.suivant.set_sensitive(not self.lecture_seule)
        if not fin:
            self.suivant.set_child(Adw.ButtonContent(icon_name="go-next-symbolic",
                                                     label=ETAPE_SUIVANTE[n]))
            self.suivant.set_tooltip_text(f"Convention : passer à « {CONVENTION[n + 1]} »")

    def _recherche(self, dd, _p):
        if self._chargement:
            return
        self.s["recherche"] = CLES_RECHERCHE[dd.get_selected()]
        self.vue.base.maj_stage(self.s["eleve_id"], self.s["pfmp_id"], recherche=self.s["recherche"])
        self._maj()
        self.vue.apres_modif()

    def _convention(self, dd, _p):
        self._maj()
        if self._chargement:
            return
        self.s["convention"] = dd.get_selected()
        self.vue.base.maj_stage(self.s["eleve_id"], self.s["pfmp_id"], convention=self.s["convention"])
        self.vue.apres_modif()

    def _avancer(self):
        n = self.convention.get_selected()
        if n < len(CONVENTION) - 1:
            self.convention.set_selected(n + 1)


# --------------------------------------------------------------------- vue

class VuePfmp(Adw.Bin):
    def __init__(self, fen):
        super().__init__()
        self.fen = fen
        self.base = fen.base
        self.numero = 1
        self.classe_id = None
        self.eleve_id = None
        self._chargement = False
        self.champs_fiche: list[ChampsEntreprise] = []
        self.compact = False
        self.lignes: list[LigneStage] = []

        vue = Adw.ToolbarView()
        entete = Adw.HeaderBar()
        self.choix_pfmp = Adw.ToggleGroup(valign=Gtk.Align.CENTER, tooltip_text="Période de PFMP")
        for n in (1, 2):
            self.choix_pfmp.add(Adw.Toggle(name=str(n), label=f"PFMP {n}"))
        self.choix_pfmp.set_active_name("1")
        self.choix_pfmp.connect("notify::active-name", self._pfmp_change)
        entete.pack_start(self.choix_pfmp)
        self.pile = Adw.ViewStack()
        self.selecteur = Adw.ViewSwitcher(stack=self.pile, policy=Adw.ViewSwitcherPolicy.WIDE)
        entete.set_title_widget(self.selecteur)
        entete.pack_end(outils.bouton("x-office-calendar-symbolic", infobulle="Dates des PFMP",
                                      clic=self.dates))
        vue.add_top_bar(entete)

        self.banniere = Adw.Banner(title="Année archivée : consultation seule",
                                   button_label="_Désarchiver")
        self.banniere.connect("button-clicked", lambda *_: self.fen.desarchiver())
        vue.add_top_bar(self.banniere)

        filtres = Gtk.Box(spacing=8, margin_start=12, margin_end=12, margin_top=6, margin_bottom=6)
        self.recherche = Gtk.SearchEntry(placeholder_text="Rechercher un élève ou une entreprise…",
                                         hexpand=True)
        self.recherche.connect("search-changed", lambda *_: self.recharger())
        filtres.append(self.recherche)
        self.filtre_recherche = Gtk.DropDown(model=outils.liste_chaines(FILTRE_RECHERCHE),
                                             tooltip_text="Filtrer par recherche de stage")
        self.filtre_recherche.connect("notify::selected", lambda *_: self.recharger())
        filtres.append(self.filtre_recherche)
        self.filtre_convention = Gtk.DropDown(model=outils.liste_chaines(FILTRE_CONVENTION),
                                              tooltip_text="Filtrer par état de la convention")
        self.filtre_convention.connect("notify::selected", lambda *_: self.recharger())
        filtres.append(self.filtre_convention)
        vue.add_top_bar(filtres)

        # Page « Classe »
        self.titre_classe = Gtk.Label(xalign=0)
        self.titre_classe.add_css_class("title-3")
        self.liste_classe = self._liste_boxed()
        self.pile.add_titled_with_icon(self._page_defilante(self.titre_classe, self.liste_classe),
                                       "classe", "Classe", "system-users-symbolic")
        # Page « Élève »
        self.pile.add_titled_with_icon(self._page_eleve(), "eleve", "Élève", "avatar-default-symbolic")
        self.pile.connect("notify::visible-child-name", lambda *_: self.recharger())

        vue.set_content(self.pile)

        barre = Gtk.ActionBar()
        self.stats = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END)
        self.stats.add_css_class("caption")
        self.stats.add_css_class("numeric")
        barre.pack_start(self.stats)
        self.bouton_visites = outils.bouton("livret-visites-symbolic", "_Visites PFMP",
                                            "Élèves suivis par chaque collègue, entreprises, itinéraires",
                                            clic=self.visites)
        barre.pack_end(self.bouton_visites)
        self.bouton_repartition = outils.bouton("livret-repartition-symbolic", "_Répartition des suivis",
                                                "Calcul au prorata des heures et PDF par collègue",
                                                clic=self.repartition)
        barre.pack_end(self.bouton_repartition)
        vue.add_bottom_bar(barre)
        self.set_child(vue)

    # --------------------------------------------------------- construction
    @staticmethod
    def _liste_boxed():
        l = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, valign=Gtk.Align.START)
        l.add_css_class("boxed-list")
        vide = Gtk.Label(label="Aucun élève ne correspond", margin_top=18, margin_bottom=18)
        vide.add_css_class("dim-label")
        l.set_placeholder(vide)
        return l

    @staticmethod
    def _page_defilante(titre, contenu):
        defil = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True)
        clamp = Adw.Clamp(maximum_size=1100, tightening_threshold=800)
        boite = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_top=18,
                        margin_bottom=24, margin_start=12, margin_end=12)
        if titre:
            boite.append(titre)
        boite.append(contenu)
        clamp.set_child(boite)
        defil.set_child(clamp)
        return defil

    def _page_eleve(self):
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL, position=300,
                          shrink_start_child=False, shrink_end_child=False, resize_start_child=False)
        self.liste_eleves = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.liste_eleves.add_css_class("navigation-sidebar")
        self.liste_eleves.connect("row-selected", self._eleve_choisi)
        self.liste_eleves.set_header_func(self._entete_classe)
        defil = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        defil.set_size_request(240, -1)
        defil.set_child(self.liste_eleves)
        paned.set_start_child(defil)
        self.fiche_conteneur = Adw.Bin()
        self.fiche_conteneur.set_child(Adw.StatusPage(icon_name="avatar-default-symbolic",
                                                      title="Choisissez un élève"))
        paned.set_end_child(self.fiche_conteneur)
        return paned

    @staticmethod
    def _entete_classe(ligne, avant):
        if avant is None or avant.classe != ligne.classe:
            lab = Gtk.Label(label=ligne.classe, xalign=0, margin_start=8, margin_top=8)
            lab.add_css_class("caption-heading")
            lab.add_css_class("dim-label")
            ligne.set_header(lab)
        else:
            ligne.set_header(None)

    # ------------------------------------------------------------ données
    def annee_id(self):
        return self.base.annee_active()

    def pfmp_id(self):
        return self.base.pfmp_id(self.annee_id(), self.numero)

    def afficher(self, classe_id=None, page=None):
        """Affiche la PFMP de la classe (la vue d'ensemble « toutes » a été retirée)."""
        if classe_id is not None:
            self.classe_id = classe_id
        ro = self.fen.lecture_seule()
        self.banniere.set_revealed(ro)
        self.bouton_repartition.set_sensitive(True)
        self.bouton_visites.set_sensitive(True)
        self._chargement = True
        self.pile.set_visible_child_name(page if page in ("classe", "eleve") else "classe")
        self._chargement = False
        self.recharger()

    def definir_compact(self, compact):
        self.compact = compact
        for l in self.lignes:
            l.compacter(compact)

    def _filtrer(self, stages):
        q = normaliser(self.recherche.get_text()).split()
        fr = self.filtre_recherche.get_selected()
        fc = self.filtre_convention.get_selected()
        res = []
        for s in stages:
            if q:
                foin = normaliser(f"{s['nom']} {s['prenom']} {s['entreprise']} {s['classe_nom']} "
                                  f"{s['enseignant_nom']}")
                if not all(m in foin for m in q):
                    continue
            if fr == 1 and s["recherche"] != "en_cours":
                continue
            if fr == 2 and s["recherche"] != "terminee":
                continue
            if 1 <= fc <= len(CONVENTION) and s["convention"] != fc - 1:
                continue
            if fc == len(CONVENTION) + 1 and s["convention"] == len(CONVENTION) - 1:
                continue
            res.append(s)
        return res

    def recharger(self):
        if self._chargement:
            return
        page = self.pile.get_visible_child_name()
        ro = self.fen.lecture_seule()
        tous = self.base.stages(self.annee_id(), self.pfmp_id())
        self.lignes = []
        self.filtre_recherche.set_visible(page != "eleve")
        self.filtre_convention.set_visible(page != "eleve")
        if page == "classe":
            classes = {c["id"]: c for c in self.base.classes_pfmp(self.annee_id())}
            if self.classe_id not in classes:
                self.classe_id = next(iter(classes), None)
            nom = classes[self.classe_id]["nom"] if self.classe_id else "Aucune classe"
            self.titre_classe.set_text(f"{nom} — PFMP {self.numero}")
            ceux = [s for s in tous if s["classe_id"] == self.classe_id]
            visibles = self._filtrer(ceux)
            self.liste_classe.remove_all()
            for s in visibles:
                l = LigneStage(self, s, False, ro)
                l.connect("activated", self._vers_fiche)
                self.lignes.append(l)
                self.liste_classe.append(l)
            self._stats(ceux, visibles)
        else:
            self._remplir_eleves(tous)
            self._stats(tous, tous)

    def _stats(self, ensemble, visibles):
        n = len(ensemble)
        trouv = sum(1 for s in ensemble if s["recherche"] == "terminee")
        fin = sum(1 for s in ensemble if s["convention"] == len(CONVENTION) - 1)
        filtre = f" · {len(visibles)} affichés" if len(visibles) != n else ""
        self.stats.set_text(f"{n} élèves · recherche terminée : {trouv}/{n} · "
                            f"conventions finalisées : {fin}/{n}{filtre}")

    def apres_modif(self):
        """Après un changement dans une ligne : stats et compteurs, sans reconstruire la liste."""
        tous = self.base.stages(self.annee_id(), self.pfmp_id())
        if self.pile.get_visible_child_name() == "classe":
            tous = [s for s in tous if s["classe_id"] == self.classe_id]
        self._stats(tous, self._filtrer(tous))
        self.fen.maj_compteurs()

    def _vers_fiche(self, ligne):
        self.eleve_id = ligne.s["eleve_id"]
        self.pile.set_visible_child_name("eleve")

    # ------------------------------------------------------------- fiche
    def _remplir_eleves(self, tous):
        q = normaliser(self.recherche.get_text()).split()
        self._chargement = True
        self.liste_eleves.remove_all()
        choisie = None
        for s in tous:
            if q and not all(m in normaliser(f"{s['nom']} {s['prenom']} {s['entreprise']} "
                                              f"{s['classe_nom']}") for m in q):
                continue
            ligne = Gtk.ListBoxRow()
            ligne.eleve_id = s["eleve_id"]
            ligne.classe = s["classe_nom"]
            b = Gtk.Box(spacing=8, margin_top=4, margin_bottom=4)
            b.append(Gtk.Label(label=f"{s['nom']} {s['prenom']}", xalign=0, hexpand=True,
                               ellipsize=Pango.EllipsizeMode.END))
            et = Etapes()
            et.definir(s["convention"])
            b.append(et)
            ligne.set_child(b)
            self.liste_eleves.append(ligne)
            if s["eleve_id"] == self.eleve_id:
                choisie = ligne
        self._chargement = False
        if choisie is None:
            choisie = self.liste_eleves.get_row_at_index(0)
        if choisie:
            self.liste_eleves.select_row(choisie)
            self._eleve_choisi(self.liste_eleves, choisie, force=True)
        else:
            self.fiche_conteneur.set_child(Adw.StatusPage(icon_name="avatar-default-symbolic",
                                                          title="Aucun élève"))

    def _eleve_choisi(self, _l, ligne, force=False):
        if ligne is None or (self._chargement and not force):
            return
        for c in self.champs_fiche:
            c.vider_attente()
        self.eleve_id = ligne.eleve_id
        self.fiche_conteneur.set_child(self._fiche(ligne.eleve_id))

    def _fiche(self, eleve_id):
        e = self.base.eleve(eleve_id)
        c = self.base.classe(e["classe_id"])
        ro = self.fen.lecture_seule()
        page = Adw.PreferencesPage()
        tete = Adw.PreferencesGroup()
        boite = Gtk.Box(spacing=14)
        boite.append(Adw.Avatar(size=56, show_initials=True, text=f"{e['prenom']} {e['nom']}"))
        noms = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER)
        t = Gtk.Label(label=f"{e['nom']} {e['prenom']}", xalign=0)
        t.add_css_class("title-2")
        noms.append(t)
        cl = Gtk.Label(label=c["nom"], xalign=0)
        cl.add_css_class("dim-label")
        noms.append(cl)
        boite.append(noms)
        tete.add(boite)
        page.add(tete)
        ens = self.base.enseignants(self.annee_id())
        self.champs_fiche = []
        for p in self.base.pfmps(self.annee_id()):
            s = self.base.stage(eleve_id, p["id"])
            dates = f"Du {p['debut']} au {p['fin']}" if p["debut"] and p["fin"] else "Dates non renseignées"
            g = Adw.PreferencesGroup(title=f"PFMP {p['numero']}", description=dates)
            rech = Adw.ComboRow(title="Recherche de stage",
                                model=outils.liste_chaines(["En cours", "Terminée"]))
            rech.set_selected(CLES_RECHERCHE.index(s["recherche"]))
            conv = Adw.ComboRow(title="Convention", model=outils.liste_chaines(CONVENTION))
            conv.set_selected(s["convention"])

            def _conv_active(terminee, conv=conv, ro=ro):
                # La convention ne commence qu'une fois la recherche terminée.
                conv.set_sensitive(not ro and terminee)

            def _rech_change(r, _p, pid=p["id"], maj=_conv_active):
                cle = CLES_RECHERCHE[r.get_selected()]
                maj(cle == "terminee")
                self._maj_fiche(eleve_id, pid, recherche=cle)
            rech.connect("notify::selected", _rech_change)
            g.add(rech)
            conv.connect("notify::selected", lambda r, _p, pid=p["id"]: self._maj_fiche(
                eleve_id, pid, convention=r.get_selected()))
            g.add(conv)
            _conv_active(s["recherche"] == "terminee")
            prof = Adw.ComboRow(title="Professeur référent",
                                model=outils.liste_chaines(["Aucun", *[x["nom"] for x in ens]]))
            ids = [None, *[x["id"] for x in ens]]
            prof.set_selected(ids.index(s["enseignant_id"]) if s["enseignant_id"] in ids else 0)
            prof.connect("notify::selected", lambda r, _p, pid=p["id"]: self._maj_fiche(
                eleve_id, pid, enseignant_id=ids[r.get_selected()]))
            g.add(prof)
            champs = ChampsEntreprise(self.fen, eleve_id, p["id"], apres=self.fen.maj_compteurs,
                                      lecture_seule=ro)
            self.champs_fiche.append(champs)
            for r in champs.lignes:
                g.add(r)
            for r in (rech, prof):
                r.set_sensitive(not ro)
            page.add(g)
        return page

    def _maj_fiche(self, eleve_id, pfmp_id, **champs):
        if self.fen.lecture_seule():
            return
        self.base.maj_stage(eleve_id, pfmp_id, **champs)
        self.fen.maj_compteurs()
        if "convention" in champs:
            ligne = self.liste_eleves.get_selected_row()
            if ligne and pfmp_id == self.pfmp_id():
                et = ligne.get_child().get_last_child()
                et.definir(champs["convention"])

    def vider_attente(self):
        for c in self.champs_fiche:
            c.vider_attente()

    # ----------------------------------------------------------- actions
    def _pfmp_change(self, groupe, _p):
        nom = groupe.get_active_name()
        if nom:
            self.vider_attente()
            self.numero = int(nom)
            self.recharger()

    def dates(self):
        if self.fen.lecture_seule():
            return
        pfmps = self.base.pfmps(self.annee_id())
        liste = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        liste.add_css_class("boxed-list")
        entrees = []
        for p in pfmps:
            d = Adw.EntryRow(title=f"PFMP {p['numero']} — début", text=p["debut"])
            f = Adw.EntryRow(title=f"PFMP {p['numero']} — fin", text=p["fin"])
            liste.append(d)
            liste.append(f)
            entrees.append((p["id"], d, f))
        d = Adw.AlertDialog(heading="Dates des PFMP",
                            body="Les deux périodes valent pour toutes les classes de l'année. "
                                 "Format libre, par exemple 12/01/2027.")
        d.set_extra_child(liste)
        d.add_response("annuler", "_Annuler")
        d.add_response("ok", "_Enregistrer")
        d.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        d.set_default_response("ok")
        d.set_close_response("annuler")

        def reponse(_d, r):
            if r == "ok":
                for pid, de, fi in entrees:
                    self.base.maj_pfmp(pid, de.get_text(), fi.get_text())
                self.recharger()
        d.connect("response", reponse)
        d.present(self.fen)

    def repartition(self):
        self.vider_attente()
        from .dialogues import DialogueRepartition
        DialogueRepartition(self.fen, self.classe_id).present(self.fen)

    def visites(self):
        self.vider_attente()
        from .dialogues import DialogueVisites
        DialogueVisites(self.fen, self.numero).present(self.fen)
