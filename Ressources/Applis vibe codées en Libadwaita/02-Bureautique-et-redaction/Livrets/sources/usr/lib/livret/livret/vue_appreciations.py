"""Section Appréciations : saisie à gauche, élèves et matières à droite."""

from __future__ import annotations

from gi.repository import Adw, Gio, GLib, GObject, Gtk, Pango

from . import calculs, outils
from .db import format_nombre, libelle_periode, nb_periodes, nom_complet, normaliser


# ------------------------------------------------------------------ phrases

class PopoverPhrases(Gtk.Popover):
    """Banque de phrases : recherche par mots-clés, insertion en un clic."""

    def __init__(self, fen, obtenir_eleve, inserer):
        super().__init__()
        self.fen = fen
        self.obtenir_eleve = obtenir_eleve
        self.inserer = inserer
        self.add_css_class("menu")
        boite = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                        margin_top=6, margin_bottom=6, margin_start=6, margin_end=6)
        boite.set_size_request(420, -1)
        self.recherche = Gtk.SearchEntry(placeholder_text="Rechercher par mots-clés…")
        self.recherche.connect("search-changed", lambda *_: self.remplir())
        self.recherche.connect("activate", self._premiere)
        self.recherche.connect("stop-search", lambda *_: self.popdown())
        boite.append(self.recherche)
        self.liste = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.liste.add_css_class("navigation-sidebar")
        self.liste.connect("row-activated", self._choisie)
        self.liste.set_header_func(self._entete)
        vide = Gtk.Label(label="Aucune phrase trouvée", margin_top=18, margin_bottom=18)
        vide.add_css_class("dim-label")
        self.liste.set_placeholder(vide)
        defil = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
                                   propagate_natural_height=True, max_content_height=380)
        defil.set_child(self.liste)
        boite.append(defil)
        gerer = outils.bouton("document-edit-symbolic", "_Gérer la banque de phrases…",
                              classes=("flat",), clic=self._gerer)
        boite.append(gerer)
        self.set_child(boite)
        self.connect("show", self._montre)

    def _montre(self, *_):
        self.recherche.set_text("")
        self.remplir()
        outils.focus_differe(self.recherche)

    def remplir(self):
        e = self.obtenir_eleve()
        prenom, nom = (e["prenom"], e["nom"]) if e else ("", "")
        self.liste.remove_all()
        for p in self.fen.base.phrases(self.recherche.get_text()):
            texte = calculs.developper(p["texte"], prenom, nom)
            ligne = Gtk.ListBoxRow()
            ligne.texte = texte
            ligne.categorie = p["categorie"] or "Sans catégorie"
            lab = Gtk.Label(label=texte, xalign=0, wrap=True, max_width_chars=48,
                            margin_top=4, margin_bottom=4)
            ligne.set_child(lab)
            if p["mots_cles"]:
                ligne.set_tooltip_text(f"Mots-clés : {p['mots_cles']}")
            self.liste.append(ligne)

    @staticmethod
    def _entete(ligne, avant):
        if avant is None or avant.categorie != ligne.categorie:
            lab = Gtk.Label(label=ligne.categorie, xalign=0, margin_start=6, margin_top=6)
            lab.add_css_class("caption-heading")
            lab.add_css_class("dim-label")
            ligne.set_header(lab)
        else:
            ligne.set_header(None)

    def _premiere(self, *_):
        ligne = self.liste.get_row_at_index(0)
        if ligne:
            self._choisie(self.liste, ligne)

    def _choisie(self, _liste, ligne):
        self.popdown()
        self.inserer(ligne.texte)

    def _gerer(self):
        self.popdown()
        self.fen.activate_action("win.phrases", None)


# ------------------------------------------------------------------ éditeur

class Editeur(Gtk.Box):
    """Zone de saisie avec historique en lecture seule, compteur, phrases, copie."""

    def __init__(self, fen, bilan, enregistrer, terminer, copier, obtenir_eleve):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.fen = fen
        self._enregistrer = enregistrer
        self._terminer = terminer
        self._copier = copier
        self.obtenir_eleve = obtenir_eleve
        self.cible = None
        self.prefixe = ""
        self.limite = 400
        self.lecture_seule = False
        self._chargement = False
        self.retard = outils.retarder(500)

        self.titre = Gtk.Label(xalign=0, wrap=True)
        self.titre.add_css_class("title-4")
        self.append(self.titre)

        self.historique = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.append(self.historique)

        cadre = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        cadre.add_css_class("card")
        cadre.add_css_class("editeur-cadre")
        self.vue = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR, accepts_tab=False,
                                top_margin=12, bottom_margin=12, left_margin=14, right_margin=14)
        self.vue.add_css_class("editeur")
        if bilan:
            self.vue.add_css_class("bilan")
        self.tampon = self.vue.get_buffer()
        self.tampon.connect("changed", self._change)
        cadre.append(self.vue)
        self.append(cadre)

        pied = Gtk.Box(spacing=6)
        self.compteur = Gtk.Label(xalign=0, hexpand=True)
        self.compteur.add_css_class("compteur")
        self.compteur.add_css_class("caption")
        pied.append(self.compteur)
        self.bouton_phrases = Gtk.MenuButton(
            child=Adw.ButtonContent(icon_name="livret-phrases-symbolic", label="_Phrases",
                                    use_underline=True),
            tooltip_text="Insérer une phrase de la banque")
        self.bouton_phrases.set_popover(PopoverPhrases(fen, obtenir_eleve, self.inserer))
        pied.append(self.bouton_phrases)
        self.bouton_termine = Gtk.ToggleButton(
            child=Adw.ButtonContent(icon_name="object-select-symbolic", label="Terminé"),
            tooltip_text="Marquer comme terminé")
        self.bouton_termine.connect("toggled", self._bascule)
        pied.append(self.bouton_termine)
        self.bouton_copier = Gtk.Button(
            child=Adw.ButtonContent(icon_name="edit-copy-symbolic", label="Copier"))
        self.bouton_copier.add_css_class("suggested-action")
        self.bouton_copier.connect("clicked", lambda *_: self._copier(self.valeur()))
        pied.append(self.bouton_copier)
        self.append(pied)

    # ----------------------------------------------------------- données
    def charger(self, cible, titre, texte, termine, historique, limite, prefixe, lecture_seule,
                infobulle_copier=""):
        self.retard.vider()
        self._chargement = True
        self.cible = cible
        self.titre.set_text(titre)
        self.vue.update_property([Gtk.AccessibleProperty.LABEL], [titre])
        self.limite = max(1, int(limite))
        self.prefixe = prefixe if not lecture_seule else ""
        self.lecture_seule = lecture_seule
        texte = texte or ""
        if not texte.strip() and self.prefixe:
            texte = self.prefixe
        self.tampon.set_text(texte)
        self.tampon.place_cursor(self.tampon.get_end_iter())
        self.bouton_termine.set_active(bool(termine) and bool(self.valeur().strip()))
        self.vue.set_editable(not lecture_seule)
        self.vue.set_cursor_visible(not lecture_seule)
        self.bouton_phrases.set_sensitive(not lecture_seule)
        self.bouton_copier.set_tooltip_text(infobulle_copier or "Copier dans le presse-papiers")
        outils.vider(self.historique)
        for libelle, txt in historique:
            bloc = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            bloc.add_css_class("historique")
            per = Gtk.Label(label=libelle, xalign=0)
            per.add_css_class("periode")
            bloc.append(per)
            lab = Gtk.Label(label=txt, xalign=0, wrap=True, selectable=True)
            bloc.append(lab)
            self.historique.append(bloc)
        self.historique.set_visible(bool(historique))
        self._chargement = False
        self._maj()

    def valeur(self) -> str:
        debut, fin = self.tampon.get_bounds()
        return calculs.valeur_sans_prefixe_seul(self.tampon.get_text(debut, fin, False), self.prefixe)

    def vider_attente(self):
        self.retard.vider()

    def inserer(self, phrase):
        if self.lecture_seule:
            return
        e = self.obtenir_eleve()
        curseur = self.tampon.get_iter_at_mark(self.tampon.get_insert())
        avant = self.tampon.get_text(self.tampon.get_start_iter(), curseur, False)
        self.tampon.insert_at_cursor(calculs.ajuster_insertion(avant, phrase, e["prenom"] if e else ""))
        self.vue.grab_focus()

    # ---------------------------------------------------------- signaux
    def _maj(self):
        n = len(self.valeur())
        self.compteur.set_text(f"{n} / {self.limite} caractères")
        self.compteur.remove_css_class("warning")
        self.compteur.remove_css_class("error")
        self.compteur.remove_css_class("dim-label")
        if n > self.limite:
            self.compteur.add_css_class("error")
        elif n > 0.9 * self.limite:
            self.compteur.add_css_class("warning")
        else:
            self.compteur.add_css_class("dim-label")
        self.bouton_termine.set_sensitive(not self.lecture_seule and n > 0)

    def _change(self, *_):
        if self._chargement:
            return
        self._maj()
        cible = self.cible
        self.retard.planifier(lambda: self._enregistrer(cible, self.valeur()))

    def _bascule(self, b):
        if self._chargement or self.lecture_seule:
            return
        self.retard.vider()
        self._terminer(self.cible, b.get_active())


# --------------------------------------------------------------------- vue

def rendre_visible(liste: Gtk.ListBox, ligne: Gtk.ListBoxRow):
    """Fait défiler la liste pour montrer la ligne, sans lui donner le focus."""
    defil = liste.get_ancestor(Gtk.ScrolledWindow)
    ok, rect = ligne.compute_bounds(liste)
    if not defil or not ok:
        return
    adj = defil.get_vadjustment()
    haut, bas = rect.get_y(), rect.get_y() + rect.get_height()
    if haut < adj.get_value():
        adj.set_value(haut)
    elif bas > adj.get_value() + adj.get_page_size():
        adj.set_value(bas - adj.get_page_size())


class LigneEleve(Gtk.ListBoxRow):
    def __init__(self, eleve):
        super().__init__()
        self.id = eleve["id"]
        self.cle = normaliser(nom_complet(eleve))
        boite = Gtk.Box(spacing=10, margin_top=6, margin_bottom=6)
        self.pastille = outils.pastille()
        boite.append(self.pastille)
        self.nom = Gtk.Label(label=nom_complet(eleve), xalign=0, hexpand=True,
                             ellipsize=Pango.EllipsizeMode.END)
        boite.append(self.nom)
        self.cumul = Gtk.Label()
        self.cumul.add_css_class("moyenne")
        self.cumul.add_css_class("cumul")
        boite.append(self.cumul)
        self.moyenne = Gtk.Label(width_chars=4, xalign=1)
        self.moyenne.add_css_class("moyenne")
        boite.append(self.moyenne)
        self.set_child(boite)

    def definir(self, etat, moyenne, cumul):
        outils.definir_pastille(self.pastille, etat)
        self.moyenne.set_text(format_nombre(moyenne))
        self.cumul.set_text(f"cumul {format_nombre(cumul)}" if cumul is not None else "")
        self.moyenne.set_tooltip_text("Moyenne générale de la période")
        self.cumul.set_tooltip_text("Moyenne cumulée de l'année")


class LigneMatiere(Gtk.ListBoxRow):
    def __init__(self, matiere):
        super().__init__()
        self.id = matiere["id"]
        self.cle = normaliser(matiere["nom"])
        boite = Gtk.Box(spacing=10, margin_top=6, margin_bottom=6)
        self.pastille = outils.pastille()
        boite.append(self.pastille)
        boite.append(Gtk.Label(label=matiere["nom"], xalign=0, hexpand=True, ellipsize=Pango.EllipsizeMode.END))
        self.note = Gtk.Label(xalign=1)
        self.note.add_css_class("numeric")
        self.note.add_css_class("dim-label")
        boite.append(self.note)
        self.set_child(boite)

    def definir_note(self, note):
        self.note.set_text(format_nombre(note) if note is not None else "")
        self.note.set_tooltip_text("Moyenne de la discipline (importée)" if note is not None else None)


class VueAppreciations(Adw.Bin):
    def __init__(self, fen):
        super().__init__()
        self.fen = fen
        self.base = fen.base
        self.classe = None
        self.periode = 1
        self.eleve = None
        self.matiere = None
        self.lignes_eleves: dict[int, LigneEleve] = {}
        self.lignes_matieres: dict[int, LigneMatiere] = {}
        self._chargement = False

        self._actions()
        vue = Adw.ToolbarView()
        entete = Adw.HeaderBar()
        self.titre = Adw.WindowTitle(title="Appréciations")
        entete.set_title_widget(self.titre)
        self.periodes = Adw.ToggleGroup(valign=Gtk.Align.CENTER, tooltip_text="Période")
        self.periodes.connect("notify::active-name", self._periode_changee)
        entete.pack_start(self.periodes)

        self.bouton_panneau = Gtk.ToggleButton(icon_name="sidebar-show-right-symbolic",
                                               tooltip_text="Élèves et matières", active=True)
        entete.pack_end(self.bouton_panneau)
        menu = Gio.Menu()
        sec = Gio.Menu()
        sec.append("_Importer un tableur (élèves, moyennes)…", "appr.importer")
        sec.append("_Importer les commentaires des collègues…", "appr.importer-commentaires")
        menu.append_section(None, sec)
        sec = Gio.Menu()
        sec.append("Récapitulatif _PDF de la période…", "appr.export-pdf")
        sec.append("Récapitulatif _ODS de l'année…", "appr.export-ods")
        menu.append_section(None, sec)
        sec = Gio.Menu()
        sec.append("_Réglages de la classe…", "appr.reglages")
        menu.append_section(None, sec)
        entete.pack_end(Gtk.MenuButton(icon_name="view-more-symbolic", menu_model=menu,
                                       tooltip_text="Classe : import, export, réglages"))
        self.bouton_conseil = outils.bouton("livret-conseil-symbolic", "_Conseil",
                                            "Mode conseil de classe, plein écran (F11)",
                                            clic=self.ouvrir_conseil)
        entete.pack_end(self.bouton_conseil)
        vue.add_top_bar(entete)

        self.banniere = Adw.Banner(title="Année archivée : consultation seule",
                                   button_label="_Désarchiver")
        self.banniere.connect("button-clicked", lambda *_: self.fen.desarchiver())
        vue.add_top_bar(self.banniere)

        prog = Gtk.Box(spacing=12)
        prog.add_css_class("progression")
        self.barre = Gtk.ProgressBar(hexpand=True, valign=Gtk.Align.CENTER)
        prog.append(self.barre)
        self.texte_prog = Gtk.Label()
        self.texte_prog.add_css_class("caption")
        self.texte_prog.add_css_class("numeric")
        prog.append(self.texte_prog)
        vue.add_top_bar(prog)

        self.split = Adw.OverlaySplitView(sidebar_position=Gtk.PackType.END,
                                          min_sidebar_width=250, max_sidebar_width=380,
                                          sidebar_width_fraction=0.32)
        self.split.bind_property("show-sidebar", self.bouton_panneau, "active",
                                 GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        self.split.set_sidebar(self._panneau_listes())
        self.split.set_content(self._zone_saisie())
        vue.set_content(self.split)
        self.set_child(vue)

        raccourcis = Gtk.ShortcutController(propagation_phase=Gtk.PropagationPhase.CAPTURE)
        for touche, action in (("<Alt>Down", "appr.eleve-suivant"), ("<Alt>Up", "appr.eleve-precedent"),
                               ("<Alt>Right", "appr.matiere-suivante"),
                               ("<Alt>Left", "appr.matiere-precedente"),
                               ("<Control><Shift>c", "appr.copier-appreciation"),
                               ("<Control><Shift>b", "appr.copier-bilan"),
                               ("<Control>f", "appr.rechercher"),
                               ("F11", "appr.conseil")):
            raccourcis.add_shortcut(Gtk.Shortcut(trigger=Gtk.ShortcutTrigger.parse_string(touche),
                                                 action=Gtk.NamedAction.new(action)))
        self.add_controller(raccourcis)

    # ---------------------------------------------------------- construction
    def _actions(self):
        groupe = Gio.SimpleActionGroup()
        for nom, f in (("importer", self.importer), ("export-pdf", self.exporter_pdf),
                       ("export-ods", self.exporter_ods), ("reglages", self.reglages),
                       ("importer-commentaires", self.importer_commentaires),
                       ("rechercher", lambda: self.recherche.grab_focus()),
                       ("eleve-suivant", lambda: self._naviguer_eleve(1)),
                       ("eleve-precedent", lambda: self._naviguer_eleve(-1)),
                       ("matiere-suivante", lambda: self._naviguer_matiere(1)),
                       ("matiere-precedente", lambda: self._naviguer_matiere(-1)),
                       ("copier-appreciation", lambda: self._copier(self.ed_appr, "appreciation")),
                       ("copier-bilan", lambda: self._copier(self.ed_bilan, "bilan")),
                       ("conseil", self.ouvrir_conseil)):
            a = Gio.SimpleAction.new(nom, None)
            a.connect("activate", lambda _a, _p, f=f: f())
            groupe.add_action(a)
        self.groupe = groupe
        self.insert_action_group("appr", groupe)

    def _panneau_listes(self):
        boite = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.recherche = Gtk.SearchEntry(placeholder_text="Rechercher un élève ou une matière…",
                                         margin_start=8, margin_end=8, margin_bottom=6,
                                         tooltip_text="Filtrer les listes (Ctrl+F)")
        self.recherche.connect("search-changed", lambda *_: self._filtrer())
        boite.append(self.recherche)
        paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL, wide_handle=True,
                          resize_start_child=True, resize_end_child=True,
                          shrink_start_child=False, shrink_end_child=False)
        self.liste_eleves = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.liste_eleves.add_css_class("navigation-sidebar")
        self.liste_eleves.connect("row-selected", self._eleve_choisi)
        self.liste_eleves.update_property([Gtk.AccessibleProperty.LABEL], ["Élèves"])
        self.entete_eleves = outils.titre_section("Élèves")
        paned.set_start_child(self._bloc_liste(self.entete_eleves, self.liste_eleves))
        self.liste_matieres = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.liste_matieres.add_css_class("navigation-sidebar")
        self.liste_matieres.connect("row-selected", self._matiere_choisie)
        self.liste_matieres.update_property([Gtk.AccessibleProperty.LABEL], ["Matières"])
        vide = Gtk.Label(label="Aucune matière", margin_top=12, margin_bottom=12)
        vide.add_css_class("dim-label")
        self.liste_matieres.set_placeholder(vide)
        self.entete_matieres = outils.titre_section("Matières")
        paned.set_end_child(self._bloc_liste(self.entete_matieres, self.liste_matieres))
        paned.set_position(420)
        boite.append(paned)
        return boite

    def _filtrer(self):
        """Filtre les listes d'élèves et de matières sur le texte recherché."""
        if self.classe is None:
            return
        mots = normaliser(self.recherche.get_text()).split()
        premier = None
        n_e = 0
        for ligne in self.lignes_eleves.values():
            visible = all(m in ligne.cle for m in mots)
            ligne.set_visible(visible)
            if visible:
                n_e += 1
                premier = premier or ligne
        n_m = 0
        for ligne in self.lignes_matieres.values():
            visible = all(m in ligne.cle for m in mots)
            ligne.set_visible(visible)
            n_m += visible
        total_e, total_m = len(self.lignes_eleves), len(self.lignes_matieres)
        self.entete_eleves.set_text(f"Élèves ({n_e}/{total_e})" if mots else f"Élèves ({total_e})")
        self.entete_matieres.set_text(f"Matières ({n_m}/{total_m})" if mots else f"Matières ({total_m})")
        courant = self.liste_eleves.get_selected_row()
        if courant is not None and not courant.get_visible() and premier is not None:
            self._chargement = True
            self.liste_eleves.select_row(premier)
            self._chargement = False
            self._eleve_choisi(self.liste_eleves, premier, force=True)

    @staticmethod
    def _bloc_liste(titre, liste):
        boite = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        titre.add_css_class("liste-entete")
        boite.append(titre)
        defil = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        defil.set_size_request(-1, 120)
        defil.set_child(liste)
        boite.append(defil)
        return boite

    def _zone_saisie(self):
        self.pile = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, hhomogeneous=False)
        statut = Adw.StatusPage(icon_name="system-users-symbolic", title="Aucun élève",
                                description="Importez la liste de la classe depuis un tableur "
                                            "(csv, xlsx, ods) ou ajoutez les élèves un par un.")
        boutons = Gtk.Box(spacing=12, halign=Gtk.Align.CENTER)
        boutons.append(outils.bouton("document-open-symbolic", "_Importer un tableur…",
                                     classes=("pill", "suggested-action"), clic=self.importer))
        boutons.append(outils.bouton("list-add-symbolic", "_Ajouter des élèves…",
                                     classes=("pill",), clic=self.reglages))
        statut.set_child(boutons)
        self.pile.add_named(statut, "vide")

        defil = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        clamp = Adw.Clamp(maximum_size=880, tightening_threshold=640)
        boite = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24,
                        margin_top=18, margin_bottom=24, margin_start=18, margin_end=18)

        entete = Gtk.Box(spacing=14)
        self.avatar = Adw.Avatar(size=52, show_initials=True)
        entete.append(self.avatar)
        noms = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER, hexpand=True)
        self.nom_eleve = Gtk.Label(xalign=0, wrap=True)
        self.nom_eleve.add_css_class("title-2")
        noms.append(self.nom_eleve)
        self.moyennes_eleve = Gtk.Label(xalign=0)
        self.moyennes_eleve.add_css_class("dim-label")
        self.moyennes_eleve.add_css_class("numeric")
        noms.append(self.moyennes_eleve)
        entete.append(noms)
        nav = Gtk.Box(valign=Gtk.Align.CENTER)
        nav.add_css_class("linked")
        nav.append(outils.bouton("go-up-symbolic", infobulle="Élève précédent (Alt+↑)",
                                 clic=lambda: self._naviguer_eleve(-1)))
        nav.append(outils.bouton("go-down-symbolic", infobulle="Élève suivant (Alt+↓)",
                                 clic=lambda: self._naviguer_eleve(1)))
        entete.append(nav)
        boite.append(entete)

        self.ed_appr = Editeur(self.fen, False, self._enregistrer_appr, self._terminer_appr,
                               lambda t: self._copier_texte(t, "appreciation"), lambda: self.eleve)
        boite.append(self.ed_appr)
        self.sans_matiere = Gtk.Box(spacing=12)
        self.sans_matiere.add_css_class("card")
        lab = Gtk.Label(label="Aucune matière dans cette classe.", xalign=0, hexpand=True,
                        margin_start=16, margin_top=14, margin_bottom=14)
        self.sans_matiere.append(lab)
        b = outils.bouton("list-add-symbolic", "Ajouter des _matières…", clic=self.reglages)
        b.set_valign(Gtk.Align.CENTER)
        b.set_margin_end(12)
        self.sans_matiere.append(b)
        boite.append(self.sans_matiere)

        self.ed_bilan = Editeur(self.fen, True, self._enregistrer_bilan, self._terminer_bilan,
                                lambda t: self._copier_texte(t, "bilan"), lambda: self.eleve)
        boite.append(self.ed_bilan)

        clamp.set_child(boite)
        defil.set_child(clamp)
        self.pile.add_named(defil, "saisie")
        return self.pile

    # ---------------------------------------------------------- chargement
    def vider_attente(self):
        self.ed_appr.vider_attente()
        self.ed_bilan.vider_attente()

    def afficher_classe(self, classe_id):
        self.vider_attente()
        if self.classe is None or self.classe["id"] != classe_id:
            self.eleve = self.matiere = None
        self.classe = self.base.classe(classe_id)
        if self.classe is None:
            return
        n = nb_periodes(self.classe["decoupage"])
        try:
            self.periode = min(n, max(1, int(self.base.reglage(f"periode_{classe_id}", 1))))
        except ValueError:
            self.periode = 1
        self._chargement = True
        self.periodes.remove_all()
        for p in range(1, n + 1):
            self.periodes.add(Adw.Toggle(name=str(p), label=libelle_periode(self.classe["decoupage"], p),
                                         tooltip=libelle_periode(self.classe["decoupage"], p, True)))
        self.periodes.set_active_name(str(self.periode))
        self._chargement = False
        annee = self.base.annee(self.classe["annee_id"])
        self.titre.set_title(self.classe["nom"])
        self.titre.set_subtitle(f"Appréciations · {annee['libelle']}")
        ro = self.fen.lecture_seule()
        self.banniere.set_revealed(ro)
        self.bouton_conseil.set_sensitive(True)
        for nom in ("importer", "reglages"):
            self.groupe.lookup_action(nom).set_enabled(not ro)
        self.recharger()

    def recharger(self):
        """Recharge les listes en gardant l'élève et la matière sélectionnés."""
        if self.classe is None:
            return
        self.vider_attente()
        self.classe = self.base.classe(self.classe["id"])
        if self.classe is None:
            return
        eleves = self.base.eleves(self.classe["id"])
        matieres = self.base.matieres(self.classe["id"])
        garde_e = self.eleve["id"] if self.eleve else None
        garde_m = self.matiere["id"] if self.matiere else None
        self._chargement = True
        self.liste_eleves.remove_all()
        self.lignes_eleves.clear()
        for e in eleves:
            l = LigneEleve(e)
            self.lignes_eleves[e["id"]] = l
            self.liste_eleves.append(l)
        self.liste_matieres.remove_all()
        self.lignes_matieres.clear()
        for m in matieres:
            l = LigneMatiere(m)
            self.lignes_matieres[m["id"]] = l
            self.liste_matieres.append(l)
        self._chargement = False
        self.entete_eleves.set_text(f"Élèves ({len(eleves)})")
        self.pile.set_visible_child_name("saisie" if eleves else "vide")
        self._maj_etats_eleves()
        if not eleves:
            self.eleve = None
            self._maj_progression({})
            return
        le = self.lignes_eleves.get(garde_e) or self.liste_eleves.get_row_at_index(0)
        lm = self.lignes_matieres.get(garde_m) or self.liste_matieres.get_row_at_index(0)
        self._chargement = True
        self.liste_matieres.select_row(lm)
        self.matiere = next((m for m in matieres if lm and m["id"] == lm.id), None)
        self._chargement = False
        self.liste_eleves.select_row(le)
        self._eleve_choisi(self.liste_eleves, le, force=True)
        self._filtrer()

    def _maj_etats_eleves(self):
        etats = self.base.etats_classe(self.classe["id"], self.periode)
        moyennes = self.base.moyennes_classe(self.classe["id"])
        for eid, ligne in self.lignes_eleves.items():
            m = moyennes.get(eid, {})
            ligne.definir(etats.get(eid, "vide"), m.get(self.periode),
                          self.base.moyenne_cumulee(m, self.periode) if len(m) > 1 or self.periode > 1 else None)
        self._maj_progression(etats)

    def _maj_progression(self, etats):
        total = len(etats)
        faits = sum(1 for e in etats.values() if e == "termine")
        self.barre.set_fraction(faits / total if total else 0)
        self.texte_prog.set_text(f"{faits} / {total} élèves terminés")
        self.fen.maj_compteurs()

    def _maj_etats_matieres(self):
        if not self.eleve:
            return
        appr = self.base.appreciations_eleve(self.eleve["id"])
        for mid, ligne in self.lignes_matieres.items():
            a = appr.get((mid, self.periode))
            outils.definir_pastille(ligne.pastille, "vide" if a is None else
                                    ("vide" if not a["texte"].strip() else
                                     "termine" if a["termine"] else "brouillon"))
            ligne.definir_note(a["moyenne"] if a is not None else None)

    def _maj_entete(self):
        e = self.eleve
        self.nom_eleve.set_text(nom_complet(e))
        self.avatar.set_text(f"{e['prenom']} {e['nom']}")
        moys = self.base.moyennes_classe(self.classe["id"]).get(e["id"], {})
        per = libelle_periode(self.classe["decoupage"], self.periode)
        cumul = self.base.moyenne_cumulee(moys, self.periode)
        self.moyennes_eleve.set_text(f"Moyenne {per} : {format_nombre(moys.get(self.periode))}"
                                     f"   ·   cumul annuel : {format_nombre(cumul)}")

    def _prefixe(self):
        if not self.eleve or not self.base.reglage_bool("prefixe_auto", True):
            return ""
        return calculs.prefixe(self.eleve["prenom"], self.base.reglage("separateur", " "))

    def _charger_editeurs(self):
        ro = self.fen.lecture_seule()
        e = self.eleve
        dec = self.classe["decoupage"]
        if self.matiere:
            self.ed_appr.set_visible(True)
            self.sans_matiere.set_visible(False)
            appr = self.base.appreciations_eleve(e["id"])
            a = appr.get((self.matiere["id"], self.periode))
            hist = [(libelle_periode(dec, p, True), appr[(self.matiere["id"], p)]["texte"])
                    for p in range(1, self.periode)
                    if (self.matiere["id"], p) in appr and appr[(self.matiere["id"], p)]["texte"].strip()]
            self.ed_appr.charger((e["id"], self.matiere["id"], self.periode),
                                 f"Appréciation — {self.matiere['nom']}",
                                 a["texte"] if a else "", a["termine"] if a else 0, hist,
                                 self.classe["limite_matiere"], self._prefixe(), ro,
                                 "Copier l'appréciation (Ctrl+Maj+C)")
        else:
            self.ed_appr.cible = None
            self.ed_appr.set_visible(False)
            self.sans_matiere.set_visible(not ro)
        bilans = self.base.bilans_eleve(e["id"])
        b = bilans.get(self.periode)
        hist = [(libelle_periode(dec, p, True), bilans[p]["texte"]) for p in range(1, self.periode)
                if p in bilans and bilans[p]["texte"].strip()]
        self.ed_bilan.charger((e["id"], self.periode), "Bilan général",
                              b["texte"] if b else "", b["termine"] if b else 0, hist,
                              self.classe["limite_bilan"], self._prefixe(), ro,
                              "Copier le bilan général (Ctrl+Maj+B)")

    # ---------------------------------------------------------- sélection
    def _eleve_choisi(self, _liste, ligne, force=False):
        if ligne is None or (self._chargement and not force):
            return
        self.vider_attente()
        self.eleve = self.base.eleve(ligne.id)
        if self.eleve is None:
            return
        self._maj_entete()
        self._maj_etats_matieres()
        self._charger_editeurs()

    def _matiere_choisie(self, _liste, ligne):
        if ligne is None or self._chargement or not self.eleve:
            return
        self.vider_attente()
        self.matiere = next((m for m in self.base.matieres(self.classe["id"]) if m["id"] == ligne.id), None)
        self._charger_editeurs()

    def _periode_changee(self, groupe, _p):
        if self._chargement or not self.classe:
            return
        nom = groupe.get_active_name()
        if not nom:
            return
        self.vider_attente()
        self.periode = int(nom)
        self.base.definir_reglage(f"periode_{self.classe['id']}", self.periode)
        self._maj_etats_eleves()
        if self.eleve:
            self._maj_entete()
            self._maj_etats_matieres()
            self._charger_editeurs()

    def _naviguer_eleve(self, delta):
        ligne = self.liste_eleves.get_selected_row()
        if ligne is None:
            return
        suivante = self.liste_eleves.get_row_at_index(ligne.get_index() + delta)
        if suivante:
            self.liste_eleves.select_row(suivante)
            rendre_visible(self.liste_eleves, suivante)

    def _naviguer_matiere(self, delta):
        ligne = self.liste_matieres.get_selected_row()
        if ligne is None:
            return
        suivante = self.liste_matieres.get_row_at_index(ligne.get_index() + delta)
        if suivante:
            self.liste_matieres.select_row(suivante)
            rendre_visible(self.liste_matieres, suivante)

    # ---------------------------------------------------------- écriture
    def _apres_ecriture(self, eleve_id):
        self._maj_etats_eleves()
        if self.eleve and self.eleve["id"] == eleve_id:
            self._maj_etats_matieres()

    def _enregistrer_appr(self, cible, texte):
        if not cible or self.fen.lecture_seule():
            return
        eid, mid, per = cible
        self.base.enregistrer_appreciation(eid, mid, per, texte=texte)
        self._apres_ecriture(eid)

    def _terminer_appr(self, cible, termine):
        if not cible or self.fen.lecture_seule():
            return
        eid, mid, per = cible
        self.base.enregistrer_appreciation(eid, mid, per, texte=self.ed_appr.valeur(), termine=termine)
        self._apres_ecriture(eid)

    def _enregistrer_bilan(self, cible, texte):
        if not cible or self.fen.lecture_seule():
            return
        eid, per = cible
        self.base.enregistrer_bilan(eid, per, texte=texte)
        self._apres_ecriture(eid)

    def _terminer_bilan(self, cible, termine):
        if not cible or self.fen.lecture_seule():
            return
        eid, per = cible
        self.base.enregistrer_bilan(eid, per, texte=self.ed_bilan.valeur(), termine=termine)
        self._apres_ecriture(eid)

    def _copier(self, editeur, quoi):
        if editeur.get_visible() and editeur.cible:
            self._copier_texte(editeur.valeur(), quoi)

    def _copier_texte(self, texte, quoi):
        if not outils.copier(self, texte):
            self.fen.toast("Rien à copier : le texte est vide")
            return
        if quoi == "bilan":
            self.fen.toast("Bilan général copié")
        else:
            self.fen.toast(f"Appréciation de {self.matiere['nom']} copiée" if self.matiere
                           else "Appréciation copiée")

    # ---------------------------------------------------------- actions
    def ouvrir_conseil(self):
        if not self.classe:
            return
        self.vider_attente()
        from .vue_conseil import FenetreConseil
        FenetreConseil(self.fen, self.classe["id"], self.periode,
                       eleve_id=self.eleve["id"] if self.eleve else None).present()

    def importer(self):
        if not self.classe or self.fen.lecture_seule():
            return
        from .dialogues import importer_tableur
        importer_tableur(self.fen, self.classe["id"], self.periode)

    def importer_commentaires(self):
        if not self.classe or self.fen.lecture_seule():
            return
        self.vider_attente()
        from .dialogues import importer_commentaires
        importer_commentaires(self.fen, self.classe["id"], self.periode)

    def reglages(self):
        if not self.classe or self.fen.lecture_seule():
            return
        self.vider_attente()
        from .dialogues import ReglagesClasse
        ReglagesClasse(self.fen, self.classe["id"]).present(self.fen)

    def exporter_pdf(self):
        if not self.classe:
            return
        self.vider_attente()
        exports = outils.module_exports(self.fen)
        if exports is None:
            return
        per = libelle_periode(self.classe["decoupage"], self.periode)
        nom = f"Conseil {self.classe['nom']} {per}.pdf".replace("/", "-")

        def ecrire(chemin):
            try:
                exports.recap_classe_pdf(self.base, self.classe["id"], self.periode, chemin)
            except Exception as err:  # noqa: BLE001 — erreur d'écriture montrée à l'utilisateur
                outils.alerte(self.fen, "Export impossible", str(err))
                return
            self.fen.toast("Récapitulatif PDF enregistré", "Ouvrir",
                           lambda: outils.ouvrir_chemin(self.fen, chemin))
        outils.enregistrer_fichier(self.fen, "Exporter le récapitulatif PDF", nom,
                                   [("Document PDF", ["pdf"], ["application/pdf"])], ecrire)

    def exporter_ods(self):
        if not self.classe:
            return
        self.vider_attente()
        exports = outils.module_exports(self.fen)
        if exports is None:
            return
        nom = f"Appréciations {self.classe['nom']}.ods".replace("/", "-")

        def ecrire(chemin):
            try:
                exports.recap_classe_ods(self.base, self.classe["id"], chemin)
            except Exception as err:  # noqa: BLE001
                outils.alerte(self.fen, "Export impossible", str(err))
                return
            self.fen.toast("Récapitulatif ODS enregistré", "Ouvrir",
                           lambda: outils.ouvrir_chemin(self.fen, chemin))
        outils.enregistrer_fichier(self.fen, "Exporter le récapitulatif ODS", nom,
                                   [("Classeur OpenDocument", ["ods"],
                                     ["application/vnd.oasis.opendocument.spreadsheet"])], ecrire)
