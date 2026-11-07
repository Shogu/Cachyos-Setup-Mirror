"""Fenêtre principale : document en cours, historique, actions."""

import os
from dataclasses import replace

from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from . import dialogues, modele
from .conversion import ErreurConversion, genre_fichier
from .grille import Grille
from .modele import FORMATS_BLANCS, ISSUES_RECADRAGE, TEXTE, Page, Source
from .moteur import APERCU, NORMAL, URGENT, MotDePasseIncorrect, MotDePasseRequis, priorite_miniature
from .reglages import instantane, nouveaux_reglages
from .vuepage import POSER_TEXTE, RECADRER, PageApercu, PageGrand

TAILLE_RENDU_GRAND = 2000
PAS_ZOOM = 24
MESSAGES_ISSUE = {cle: libelle for cle, libelle, _aide in ISSUES_RECADRAGE}

# Dispositions proposées par le bouton scindé, dans l'ordre d'affichage.
DISPOSITIONS = (
    ("fidele", "assemblage fidèle"),
    ("brochure-a5", "brochure A5 sur A4"),
    ("livret-a4", "livret A4 sur A3"),
)

FILTRES = (
    ("PDF et images", ["application/pdf", "image/*"], ["*.pdf"]),
    ("Documents PDF", ["application/pdf"], ["*.pdf"]),
    ("Images", ["image/*"], []),
)


def _menu(*sections):
    menu = Gio.Menu()
    for section in sections:
        s = Gio.Menu()
        for libelle, action in section:
            s.append(libelle, action)
        menu.append_section(None, s)
    return menu


def _taille_lisible(octets):
    if octets < 1024 * 1024:
        return f"{max(1, round(octets / 1024))} Ko"
    return f"{octets / 1024 / 1024:.1f} Mo".replace(".", ",")


def _filtres(entrees):
    liste = Gio.ListStore.new(Gtk.FileFilter)
    for nom, types, motifs in entrees:
        f = Gtk.FileFilter(name=nom)
        for t in types:
            f.add_mime_type(t)
        for m in motifs:
            f.add_pattern(m)
        liste.append(f)
    return liste


class FenetreMaquette(Adw.ApplicationWindow):
    __gtype_name__ = "MaquetteFenetre"

    def __init__(self, application, moteur):
        super().__init__(application=application, title="Maquette", default_width=1100, default_height=760)
        self.moteur = moteur
        self.reglages = nouveaux_reglages()
        self.sources: dict[int, Source] = {}
        self.pages: tuple = ()
        self.etat_enregistre: tuple = ()
        self._annuler: list = []
        self._refaire: list = []
        self._occupations = 0
        self._uid_grand = None
        self._cle_grand = None
        self._fermeture_confirmee = False
        self._fermer_apres_enregistrement = False
        self._confirmation = None

        self._construire()
        self._creer_actions()
        self.reglages.connect("changed", self._sur_reglage)
        self.connect("close-request", self._sur_fermeture)
        self._rafraichir()

    # ================================================== construction
    def _construire(self):
        self.titre = Adw.WindowTitle(title="Maquette")
        entete = Adw.HeaderBar(title_widget=self.titre)

        inserer = Gtk.MenuButton(
            icon_name="list-add-symbolic",
            menu_model=_menu([("Des fichiers…", "win.inserer-fichiers"), ("Une page blanche", "win.page-blanche")]),
            tooltip_text="Insérer (Ctrl+O)\n"
                         "Des PDF ou des images, après la sélection.\n"
                         "Un document ODT ou DOCX est à exporter en PDF depuis son éditeur.")
        entete.pack_start(inserer)
        historique = Gtk.Box()
        historique.add_css_class("linked")
        historique.append(Gtk.Button(icon_name="edit-undo-symbolic", action_name="win.annuler", tooltip_text="Annuler (Ctrl+Z)"))
        historique.append(Gtk.Button(icon_name="edit-redo-symbolic", action_name="win.refaire",
                                     tooltip_text="Rétablir (Ctrl+Maj+Z)"))
        entete.pack_start(historique)

        menu_principal = _menu(
            [("Nouvelle fenêtre", "app.nouvelle-fenetre")],
            [("Préférences", "app.preferences"), ("Raccourcis clavier", "app.raccourcis"),
             ("À propos de Maquette", "app.a-propos")])
        entete.pack_end(Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu_principal, primary=True,
                                       tooltip_text="Menu principal"))
        # Pas de classe « suggested-action » : elle fusionne les deux moitiés du
        # bouton scindé en un seul bloc coloré et lui fait perdre son aspect natif.
        enregistrer = Adw.SplitButton(
            icon_name="document-save-symbolic", action_name="win.enregistrer",
            tooltip_text="Enregistrer sous… (Ctrl+S)",
            dropdown_tooltip="Disposition des pages et aperçu",
            menu_model=self._menu_enregistrement())
        entete.pack_end(enregistrer)
        self.indicateur = Adw.Spinner(visible=False, tooltip_text="Traitement en cours…")
        entete.pack_end(self.indicateur)

        menu_contextuel = _menu(
            [("Afficher en grand", "win.afficher")],
            [("Pivoter à gauche", "win.pivoter-gauche"), ("Pivoter à droite", "win.pivoter-droite"),
             ("Rétablir la page d'origine", "win.reinitialiser")],
            [("Insérer une page blanche après", "win.page-blanche"), ("Insérer des fichiers après…", "win.inserer-fichiers")],
            [("Extraire vers un nouveau fichier…", "win.extraire"), ("Supprimer", "win.supprimer")])
        self.grille = Grille(menu_contextuel, self._demander_rendu)
        self.grille.connect("deplacer", self._sur_deplacer)
        self.grille.connect("deposer-fichiers", lambda _g, fichiers, index: self.ajouter_fichiers(fichiers, index))
        self.grille.connect("activer", lambda _g, uid: self._ouvrir_grand(uid))
        self.grille.connect("selection-changee", lambda _g: self._maj_selection())

        bouton_ouvrir = Gtk.Button(label="Ouvrir des fichiers…", halign=Gtk.Align.CENTER,
                                   action_name="win.inserer-fichiers")
        bouton_ouvrir.add_css_class("pill")
        bouton_ouvrir.add_css_class("suggested-action")
        vide = Adw.StatusPage(icon_name="io.gitlab.shogu.Maquette-symbolic", title="Aucun document",
                              description="Glisse ici des PDF ou des images.\n"
                                          "Un document ODT ou DOCX est à exporter en PDF depuis son éditeur.",
                              child=bouton_ouvrir)
        cible = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        cible.connect("drop", lambda _c, liste, _x, _y: self.ajouter_fichiers(liste.get_files()) or True)
        vide.add_controller(cible)

        self.pile = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.pile.add_named(vide, "vide")
        self.pile.add_named(self.grille, "grille")

        self.compte_selection = Gtk.Label()
        self.barre_selection = Gtk.ActionBar(revealed=False)
        self.barre_selection.pack_start(self.compte_selection)
        for icone, bulle, action in (("object-rotate-left-symbolic", "Pivoter à gauche (Ctrl+←)", "win.pivoter-gauche"),
                                     ("object-rotate-right-symbolic", "Pivoter à droite (Ctrl+→)", "win.pivoter-droite")):
            self.barre_selection.pack_start(Gtk.Button(icon_name=icone, action_name=action, tooltip_text=bulle))
        supprimer = Gtk.Button(icon_name="user-trash-symbolic", action_name="win.supprimer",
                               tooltip_text="Supprimer les pages choisies (Suppr)")
        supprimer.add_css_class("destructive-action")
        self.barre_selection.pack_end(supprimer)
        self.barre_selection.pack_end(Gtk.Button(
            icon_name="maquette-extraire-symbolic", action_name="win.extraire",
            tooltip_text="Extraire la sélection vers un nouveau fichier (Ctrl+E)"))

        vue = Adw.ToolbarView(content=self.pile)
        vue.add_top_bar(entete)
        vue.add_bottom_bar(self.barre_selection)

        self.page_apercu = PageApercu()
        self.page_apercu.connect("naviguer", lambda _p, i: self._montrer_apercu(i))

        self.page_grand = PageGrand()
        self.page_grand.connect("naviguer", self._sur_naviguer)
        self.page_grand.vue.connect("zone-tracee", self._sur_zone)
        self.page_grand.connect("hidden", self._sur_grand_cache)

        self.navigation = Adw.NavigationView()
        self.navigation.add(Adw.NavigationPage(title="Maquette", tag="grille", child=vue))
        self.toasts = Adw.ToastOverlay(child=self.navigation)
        self.set_content(self.toasts)

    @staticmethod
    def _menu_enregistrement():
        """Menu du bouton scindé : aperçu, puis les dispositions."""
        menu = Gio.Menu()
        apercu = Gio.Menu()
        apercu.append("Aperçu du résultat…", "win.apercu")
        menu.append_section(None, apercu)
        dispositions = Gio.Menu()
        for cle, libelle in DISPOSITIONS:
            element = Gio.MenuItem.new(f"Enregistrer en {libelle}…", None)
            element.set_action_and_target_value("win.enregistrer-ainsi", GLib.Variant("s", cle))
            dispositions.append_item(element)
        menu.append_section("Disposition des pages", dispositions)
        return menu

    def _creer_actions(self):
        for nom, rappel in (
            ("inserer-fichiers", lambda *_: self._choisir_fichiers()),
            ("page-blanche", lambda *_: self._inserer_page_blanche()),
            ("enregistrer", lambda *_: self._enregistrer_sous(extraction=False)),
            ("apercu", lambda *_: self._ouvrir_apercu()),
            ("extraire", lambda *_: self._enregistrer_sous(extraction=True)),
            ("annuler", lambda *_: self._historique(self._annuler, self._refaire)),
            ("refaire", lambda *_: self._historique(self._refaire, self._annuler)),
            ("pivoter-gauche", lambda *_: self._pivoter(270)),
            ("pivoter-droite", lambda *_: self._pivoter(90)),
            ("reinitialiser", lambda *_: self._reinitialiser()),
            ("supprimer", lambda *_: self._supprimer()),
            ("tout-selectionner", lambda *_: self.grille.selectionner([p.uid for p in self.pages])),
            ("afficher", lambda *_: self._afficher_selection()),
            ("recadrer", lambda *_: self._outil_sur_page(RECADRER)),
            ("texte", lambda *_: self._outil_sur_page(POSER_TEXTE)),
            ("zoom-plus", lambda *_: self._zoom(PAS_ZOOM)),
            ("zoom-moins", lambda *_: self._zoom(-PAS_ZOOM)),
            ("fermer", lambda *_: self.close()),
        ):
            action = Gio.SimpleAction.new(nom, None)
            action.connect("activate", rappel)
            self.add_action(action)
        avec_disposition = Gio.SimpleAction.new("enregistrer-ainsi", GLib.VariantType("s"))
        avec_disposition.connect(
            "activate", lambda _a, cible: self._enregistrer_sous(extraction=False, imposition=cible.get_string()))
        self.add_action(avec_disposition)

    # ============================================================ état
    def _modifie(self):
        return self.pages != self.etat_enregistre

    def _changer(self, pages, selection=None):
        self._annuler.append(self.pages)
        self._refaire.clear()
        self.pages = tuple(pages)
        self._rafraichir(selection)

    def _historique(self, depuis, vers):
        if not depuis:
            return
        vers.append(self.pages)
        self.pages = depuis.pop()
        self._rafraichir()

    def _rafraichir(self, selection=None):
        self.grille.synchroniser(self.pages, self.sources, self.reglages)
        if selection is not None:
            self.grille.selectionner(selection, focus=self.navigation.get_visible_page() is not self.page_grand)
        self.pile.set_visible_child_name("grille" if self.pages else "vide")

        nom = self._nom_document()
        n = len(self.pages)
        self.titre.set_title(nom or "Maquette")
        sous_titre = "" if not n else (f"{n} page" if n == 1 else f"{n} pages")
        if n and self._modifie():
            sous_titre += " · modifié"
        self.titre.set_subtitle(sous_titre)
        self.set_title(f"{nom} — Maquette" if nom else "Maquette")

        self.lookup_action("annuler").set_enabled(bool(self._annuler))
        self.lookup_action("refaire").set_enabled(bool(self._refaire))
        for nom_action in ("enregistrer", "tout-selectionner", "apercu", "enregistrer-ainsi"):
            self.lookup_action(nom_action).set_enabled(bool(self.pages))
        self._maj_selection()
        if self._uid_grand is not None:
            self._maj_grand()

    def _maj_selection(self):
        n = len(self._cibles())
        for nom in ("pivoter-gauche", "pivoter-droite", "reinitialiser", "supprimer",
                    "extraire", "afficher", "recadrer", "texte"):
            self.lookup_action(nom).set_enabled(n > 0)
        sel = len(self.grille.selection())
        self.barre_selection.set_revealed(sel > 0)
        self.compte_selection.set_label("1 page sélectionnée" if sel == 1 else f"{sel} pages sélectionnées")

    def _sur_reglage(self, _reglages, cle):
        if cle in ("taille-miniatures", "numeros", "couleur-source"):
            self.grille.synchroniser(self.pages, self.sources, self.reglages)

    def _occuper(self, delta):
        self._occupations += delta
        self.indicateur.set_visible(self._occupations > 0)

    def _toast(self, titre, annulable=False):
        toast = Adw.Toast(title=titre, timeout=4)
        if annulable:
            toast.set_button_label("Annuler")
            toast.set_action_name("win.annuler")
        self.toasts.add_toast(toast)
        return toast

    def _nom_document(self):
        for page in self.pages:
            if page.source is not None:
                return os.path.splitext(self.sources[page.source].nom)[0]
        return ""

    def _index(self, uid):
        return next(i for i, p in enumerate(self.pages) if p.uid == uid)

    def _cibles(self):
        """Pages visées par une action : la page en grand, sinon la sélection."""
        if self._uid_grand is not None:
            return [self._uid_grand]
        return self.grille.selection()

    def _position_insertion(self):
        sel = self._cibles()
        if not sel:
            return len(self.pages)
        return max(self._index(u) for u in sel) + 1

    # ========================================================== rendu
    @staticmethod
    def _texture(resultat):
        largeur, hauteur, pas, octets = resultat
        return Gdk.MemoryTexture.new(largeur, hauteur, Gdk.MemoryFormat.R8G8B8, GLib.Bytes.new(octets), pas)

    def _demander_rendu(self, carte, page, largeur, hauteur, rang):
        cle = carte.cle_voulue

        def recu(resultat):
            if carte.cle_voulue == cle:
                carte.afficher(self._texture(resultat))
        self.moteur.soumettre(self.moteur.rendre, page, largeur, hauteur, priorite=priorite_miniature(rang),
                              rappel=recu, voulu=lambda: carte.cle_voulue == cle)

    # ===================================================== fichiers
    def _choisir_fichiers(self):
        dialogue = Gtk.FileDialog(title="Insérer des fichiers", filters=_filtres(FILTRES), modal=True)
        position = self._position_insertion()

        def choisi(d, resultat):
            try:
                fichiers = d.open_multiple_finish(resultat)
            except GLib.Error:
                return
            self.ajouter_fichiers(list(fichiers), position)
        dialogue.open_multiple(self, None, choisi)

    def ajouter_fichiers(self, fichiers, position=None):
        if position is None:
            position = self._position_insertion()
        a_traiter, refuses = [], []
        for f in fichiers:
            chemin = f.get_path()
            genre = genre_fichier(chemin) if chemin else None
            if genre is None:
                refuses.append(f.get_basename())
            else:
                a_traiter.append((chemin, genre))
        if refuses:
            self._toast("Format non pris en charge : " + ", ".join(refuses))
        if not a_traiter:
            return
        reglages = instantane(self.reglages)
        images = sum(1 for _c, g in a_traiter if g == "image")
        if images and self.reglages.get_boolean("images-demander"):
            def repondu(choix):
                if choix is not None:
                    self._ouvrir_suivant(a_traiter, position, dict(reglages, **choix), [])
            dialogues.demander_mise_en_page_images(self, self.reglages, images, repondu)
            return
        self._ouvrir_suivant(a_traiter, position, reglages, [])

    def _ouvrir_suivant(self, file, position, reglages, nouvelles, mot_de_passe=None):
        """Ouvre les fichiers un par un, puis insère toutes leurs pages d'un coup."""
        if not file:
            self._inserer_pages(nouvelles, position)
            return
        chemin, genre = file[0]
        id_source = modele.nouvel_id_source()
        self._occuper(1)

        def ouvert(infos):
            self._occuper(-1)
            couleur = len({s.couleur for s in self.sources.values()})
            source = Source(id_source, os.path.basename(chemin), chemin, genre, infos, couleur)
            self.sources[id_source] = source
            nouvelles.extend(Page(modele.nouvel_uid(), id_source, i) for i in range(len(infos)))
            self._ouvrir_suivant(file[1:], position, reglages, nouvelles)

        def echec(erreur):
            self._occuper(-1)
            if isinstance(erreur, (MotDePasseRequis, MotDePasseIncorrect)):
                def repondu(mdp):
                    if mdp is None:
                        self._ouvrir_suivant(file[1:], position, reglages, nouvelles)
                    else:
                        self._ouvrir_suivant(file, position, reglages, nouvelles, mdp)
                dialogues.demander_mot_de_passe(self, chemin, isinstance(erreur, MotDePasseIncorrect), repondu)
                return
            if isinstance(erreur, ErreurConversion):
                self._toast(str(erreur))
            else:
                self._toast(f"Impossible d'ouvrir « {os.path.basename(chemin)} »")
            self._ouvrir_suivant(file[1:], position, reglages, nouvelles)

        self.moteur.soumettre(self.moteur.ouvrir, id_source, chemin, genre, reglages, mot_de_passe,
                              priorite=NORMAL, rappel=ouvert, erreur=echec)

    def _inserer_pages(self, nouvelles, position):
        if not nouvelles:
            return
        position = min(position, len(self.pages))
        uids = [p.uid for p in nouvelles]
        if not self.pages and not self._annuler:
            self.pages = tuple(nouvelles)
            self.etat_enregistre = self.pages
            self._rafraichir()
            return
        self._changer(self.pages[:position] + tuple(nouvelles) + self.pages[position:], selection=uids)
        n = len(nouvelles)
        self._toast("1 page insérée" if n == 1 else f"{n} pages insérées", annulable=True)

    # ===================================================== opérations
    def _sur_deplacer(self, _grille, uids, index):
        glissees = set(uids)
        deplacees = [p for p in self.pages if p.uid in glissees]
        avant = sum(1 for p in self.pages[:index] if p.uid in glissees)
        restantes = [p for p in self.pages if p.uid not in glissees]
        index -= avant
        nouvel_ordre = restantes[:index] + deplacees + restantes[index:]
        if [p.uid for p in nouvel_ordre] != [p.uid for p in self.pages]:
            self._changer(nouvel_ordre, selection=uids)

    def _pivoter(self, degres):
        cibles = set(self._cibles())
        self._changer([replace(p, rotation=(p.rotation + degres) % 360) if p.uid in cibles else p for p in self.pages],
                      selection=list(cibles))

    def _reinitialiser(self):
        cibles = set(self._cibles())
        pages = [replace(p, rotation=0, ops=()) if p.uid in cibles else p for p in self.pages]
        if pages != list(self.pages):
            self._changer(pages, selection=list(cibles))

    def _supprimer(self):
        cibles = set(self._cibles())
        if not cibles:
            return
        premier = min(self._index(u) for u in cibles)
        restantes = [p for p in self.pages if p.uid not in cibles]
        voisine = [restantes[min(premier, len(restantes) - 1)].uid] if restantes else []
        self._changer(restantes, selection=voisine)
        n = len(cibles)
        self._toast("1 page supprimée" if n == 1 else f"{n} pages supprimées", annulable=True)

    def _inserer_page_blanche(self):
        position = self._position_insertion()
        cle = self.reglages.get_string("format-page-blanche")
        if cle == "voisine" and self.pages:
            voisine = self.pages[max(0, position - 1)]
            taille = modele.taille_affichee(voisine, self.sources)
        else:
            taille = FORMATS_BLANCS.get(cle, modele.A4)
        page = Page(modele.nouvel_uid(), None, blanche=(round(taille[0], 2), round(taille[1], 2)))
        self._changer(self.pages[:position] + (page,) + self.pages[position:], selection=[page.uid])

    def _zoom(self, pas):
        taille = self.reglages.get_int("taille-miniatures")
        self.reglages.set_int("taille-miniatures", min(400, max(96, taille + pas)))

    # ================================================== page en grand
    def _ouvrir_grand(self, uid):
        self._uid_grand = uid
        self._cle_grand = None
        self.page_grand.vue.definir_texture(None)
        if self.navigation.get_visible_page() is not self.page_grand:
            self.navigation.push(self.page_grand)
        self._maj_grand()
        self.page_grand.vue.grab_focus()

    def _outil_sur_page(self, outil):
        """Ouvre la page en grand, outil déjà choisi."""
        cibles = self._cibles()
        if not cibles:
            return
        if self._uid_grand is None:
            self._ouvrir_grand(cibles[0])
        self.page_grand.choisir_outil(outil)

    def _afficher_selection(self):
        cibles = self._cibles()
        if cibles:
            self._ouvrir_grand(cibles[0])

    def _sur_grand_cache(self, _page):
        uid = self._uid_grand
        self._uid_grand = None
        self._cle_grand = None
        if uid is not None and any(p.uid == uid for p in self.pages):
            self.grille.selectionner([uid], focus=True)
        self._maj_selection()

    def _maj_grand(self):
        if not any(p.uid == self._uid_grand for p in self.pages):
            self._uid_grand = None
            self.navigation.pop()
            return
        i = self._index(self._uid_grand)
        page = self.pages[i]
        source = self.sources.get(page.source)
        sous_titre = f"{source.nom} — page {page.index + 1}" if source else "Page blanche"
        self.page_grand.montrer(i + 1, len(self.pages), sous_titre)
        self._maj_selection()
        cle = page.cle_rendu()
        if cle == self._cle_grand:
            return
        self._cle_grand = cle
        taille = TAILLE_RENDU_GRAND

        def recu(resultat):
            if self._cle_grand == cle:
                self.page_grand.vue.definir_texture(self._texture(resultat))
        self.moteur.soumettre(self.moteur.rendre, page, taille, taille, priorite=URGENT, rappel=recu)

    def _sur_naviguer(self, _page, delta):
        if self._uid_grand is None:
            return
        i = self._index(self._uid_grand) + delta
        if 0 <= i < len(self.pages):
            self._uid_grand = self.pages[i].uid
            self.grille.selectionner([self._uid_grand])
            self._maj_grand()

    def _sur_zone(self, _vue, outil, fu0, fv0, fu1, fv1):
        """Une zone vient d'être tracée : recadrage à trois issues, ou texte."""
        page = self.pages[self._index(self._uid_grand)]
        if outil == RECADRER:
            dialogues.choisir_issue_recadrage(
                self, lambda issue: self._appliquer_zone(page, issue, (fu0, fv0, fu1, fv1)))
        else:
            dialogues.saisir_texte(
                self, self.reglages,
                lambda texte, taille, couleur: self._appliquer_zone(
                    page, TEXTE, (fu0, fv0, fu1, fv1),
                    contenu=texte, taille=taille, couleur=couleur))

    def _appliquer_zone(self, page, genre, fractions, **mise_en_forme):
        op = modele.zone_depuis_affichage(page, self.sources, genre, *fractions, **mise_en_forme)
        if op is None:
            self._toast("Zone trop petite, ou page entière")
            return
        if not any(p.uid == page.uid for p in self.pages):
            return
        self._changer([replace(p, ops=p.ops + (op,)) if p.uid == page.uid else p for p in self.pages])
        self.page_grand.choisir_outil(None)
        self._toast("Texte ajouté" if genre == TEXTE else MESSAGES_ISSUE[genre], annulable=True)

    # =================================================== enregistrement
    def _enregistrer_sous(self, extraction, imposition=None):
        if extraction:
            cibles = set(self._cibles())
            pages = [p for p in self.pages if p.uid in cibles]
        else:
            pages = list(self.pages)
        if not pages:
            return
        if extraction:
            imposition = "fidele"
        nom = self._nom_document() or "document"
        suffixe = "-extrait" if extraction else self.reglages.get_string("suffixe-nom")
        dialogue = Gtk.FileDialog(title="Extraire les pages" if extraction else "Enregistrer sous", modal=True,
                                  initial_name=f"{nom}{suffixe}.pdf", filters=_filtres(FILTRES[1:2]))
        dossier = self._dossier_propose()
        if dossier:
            dialogue.set_initial_folder(Gio.File.new_for_path(dossier))

        def choisi(d, resultat):
            try:
                fichier = d.save_finish(resultat)
            except GLib.Error:
                self._fermer_apres_enregistrement = False
                return
            chemin = fichier.get_path()
            if not chemin.lower().endswith(".pdf"):
                chemin += ".pdf"
            originaux = {os.path.realpath(s.chemin) for s in self.sources.values() if s.genre == "pdf"}
            if os.path.realpath(chemin) in originaux:
                dialogues.confirmer(
                    self, "Remplacer le fichier d'origine ?",
                    f"« {os.path.basename(chemin)} » fait partie des fichiers ouverts. "
                    "Il sera remplacé par le nouveau document ; l'ancienne version sera perdue.",
                    "Remplacer", lambda: self._ecrire(pages, chemin, extraction, imposition))
            else:
                self._ecrire(pages, chemin, extraction, imposition)
        dialogue.save(self, None, choisi)

    def _dossier_propose(self):
        choix = self.reglages.get_string("dossier-propose")
        dernier = self.reglages.get_string("dernier-dossier")
        fixe = self.reglages.get_string("dossier-fixe")
        if choix == "fixe" and os.path.isdir(fixe):
            return fixe
        if choix == "dernier" and os.path.isdir(dernier):
            return dernier
        for page in self.pages:
            if page.source is not None:
                return os.path.dirname(self.sources[page.source].chemin)
        return dernier if os.path.isdir(dernier) else None

    def _ecrire(self, pages, chemin, extraction, imposition=None):
        pages = tuple(pages)
        genres = {sid: s.genre for sid, s in self.sources.items()}
        reglages = self._reglages_sortie(imposition)
        self._occuper(1)

        def fait(octets):
            self._occuper(-1)
            self.reglages.set_string("dernier-dossier", os.path.dirname(chemin))
            if not extraction:
                self.etat_enregistre = pages
                self._rafraichir()
            toast = self._toast(f"Enregistré : {os.path.basename(chemin)} ({_taille_lisible(octets)})")
            toast.set_button_label("Ouvrir")
            toast.connect("button-clicked", lambda _t: self._lancer(chemin))
            if self.reglages.get_boolean("ouvrir-apres"):
                self._lancer(chemin)
            if self._fermer_apres_enregistrement and not extraction:
                self._fermeture_confirmee = True
                self.close()

        def echec(erreur):
            self._occuper(-1)
            self._fermer_apres_enregistrement = False
            dialogues.signaler_erreur(self, "Échec de l'enregistrement",
                                      f"« {os.path.basename(chemin)} » n'a pas pu être écrit.\n\n{erreur}")

        self.moteur.soumettre(self.moteur.enregistrer, pages, chemin, reglages, genres,
                              priorite=URGENT, rappel=fait, erreur=echec)

    def _reglages_sortie(self, imposition=None):
        reglages = instantane(self.reglages)
        if imposition is not None:
            reglages["imposition"] = imposition
        return reglages

    def _ouvrir_apercu(self):
        """Montre le document final, imposition comprise, sans rien écrire."""
        if not self.pages:
            return
        pages = tuple(self.pages)
        genres = {sid: s.genre for sid, s in self.sources.items()}
        self._occuper(1)

        def pret(infos):
            self._occuper(-1)
            if not infos:
                return
            self.page_apercu.charger(infos, self._reglages_sortie()["imposition"])
            if self.navigation.get_visible_page() is not self.page_apercu:
                self.navigation.push(self.page_apercu)
            self._montrer_apercu(0)

        def echec(erreur):
            self._occuper(-1)
            dialogues.signaler_erreur(self, "Aperçu impossible", str(erreur))

        self.moteur.soumettre(self.moteur.construire_apercu, pages, self._reglages_sortie(), genres,
                              priorite=URGENT, rappel=pret, erreur=echec)

    def _montrer_apercu(self, index):
        page, total = self.page_apercu.page_a(index)
        if page is None:
            return
        self.page_apercu.montrer_numero(index + 1, total)
        taille = TAILLE_RENDU_GRAND

        def recu(resultat):
            if self.page_apercu.index == index:
                self.page_apercu.vue.definir_texture(self._texture(resultat))
        self.page_apercu.vue.definir_texture(None)
        self.moteur.soumettre(self.moteur.rendre, page, taille, taille, priorite=URGENT, rappel=recu)

    def _lancer(self, chemin):
        Gtk.FileLauncher.new(Gio.File.new_for_path(chemin)).launch(self, None, None, None)

    # ======================================================= fermeture
    def _sur_fermeture(self, _fenetre):
        if (self._fermeture_confirmee or not self._modifie()
                or not self.reglages.get_boolean("confirmer-fermeture")):
            self.moteur.soumettre(self.moteur.liberer, list(self.sources) + [APERCU], priorite=NORMAL)
            return False
        if self._confirmation is not None:          # fermeture redemandée : une seule suffit
            self._confirmation.present(self)
            return True
        dialogue = Adw.AlertDialog(heading="Enregistrer les modifications ?",
                                   body="Le document a été modifié. Sans enregistrement, les changements seront perdus.")
        dialogue.add_response("annuler", "Annuler")
        dialogue.add_response("fermer", "Fermer sans enregistrer")
        dialogue.add_response("enregistrer", "Enregistrer sous…")
        dialogue.set_response_appearance("fermer", Adw.ResponseAppearance.DESTRUCTIVE)
        dialogue.set_response_appearance("enregistrer", Adw.ResponseAppearance.SUGGESTED)
        dialogue.set_default_response("enregistrer")
        dialogue.set_close_response("annuler")

        def repondu(_d, reponse):
            self._confirmation = None
            if reponse == "fermer":
                self._fermeture_confirmee = True
                self.close()
            elif reponse == "enregistrer":
                self._fermer_apres_enregistrement = True
                self._enregistrer_sous(extraction=False)
        dialogue.connect("response", repondu)
        self._confirmation = dialogue
        ouvert = self.get_visible_dialog()
        if ouvert is None:
            dialogue.present(self)
        else:
            # Un dialogue déjà ouvert masquerait la confirmation : on le referme,
            # puis on présente au tour de boucle suivant, sinon rien ne s'affiche.
            ouvert.force_close()
            GLib.idle_add(dialogue.present, self)
        return True
