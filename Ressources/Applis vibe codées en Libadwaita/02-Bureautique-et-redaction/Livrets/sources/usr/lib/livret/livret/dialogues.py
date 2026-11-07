"""Dialogues : classes, années, import de tableur, phrases, préférences,
répartition des suivis et visites PFMP."""

from __future__ import annotations

import os
import threading
import re
from pathlib import Path

from gi.repository import Adw, GLib, Gtk, Pango

from . import calculs, geo, outils, tableur
from .db import annee_scolaire_courante, libelle_periode, nb_periodes, nom_complet, normaliser
from .tableur import separer_nom_prenom


def _esc(t):
    return GLib.markup_escape_text(t or "")


def _liste_boxed(*lignes):
    l = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
    l.add_css_class("boxed-list")
    for r in lignes:
        l.append(r)
    return l


# ============================================================== classes

def nouvelle_classe(fen):
    aid = fen.base.annee_active()
    classes = fen.base.classes(aid)
    nom = Adw.EntryRow(title="Nom de la classe", use_markup=False)
    decoupage = Adw.ComboRow(title="Découpage", model=outils.liste_chaines(["3 trimestres", "2 semestres"]))
    reprise = Adw.ComboRow(title="Reprendre les matières de",
                           model=outils.liste_chaines(["Aucune classe", *[c["nom"] for c in classes]]))
    # Par défaut, seule la première classe suivie en PFMP l'est (prof principal d'une classe).
    pfmp = Adw.SwitchRow(title="Suivi des PFMP", subtitle="Stages, conventions et visites",
                         active=not fen.base.classes_pfmp(aid))
    lignes = [nom, decoupage] + ([reprise] if classes else []) + [pfmp]
    d = Adw.AlertDialog(heading="Nouvelle classe")
    d.set_extra_child(_liste_boxed(*lignes))
    d.add_response("annuler", "_Annuler")
    d.add_response("creer", "_Créer")
    d.set_response_appearance("creer", Adw.ResponseAppearance.SUGGESTED)
    d.set_default_response("creer")
    d.set_close_response("annuler")
    # « Créer » reste grisé tant que le nom est vide. (Le bug « un seul caractère »
    # venait d'une boucle de focus, corrigée par outils.focus_differe.)
    d.set_response_enabled("creer", False)
    nom.connect("changed", lambda r: d.set_response_enabled("creer", bool(r.get_text().strip())))
    # Entrée valide la réponse par défaut (« Créer »).
    nom.set_activates_default(True)

    def reponse(_d, r):
        if r != "creer":
            return
        i = reprise.get_selected()
        try:
            cid = fen.base.creer_classe(aid, nom.get_text(), "T" if decoupage.get_selected() == 0 else "S",
                                        matieres_de=classes[i - 1]["id"] if classes and i > 0 else None,
                                        pfmp=pfmp.get_active())
        except ValueError as e:
            outils.alerte(fen, "Classe non créée", str(e))
            return
        fen.rafraichir(selection=("appr", cid))
        ReglagesClasse(fen, cid).present(fen)
    d.connect("response", reponse)
    d.present(fen)
    outils.focus_differe(nom)


class ReglagesClasse(Adw.PreferencesDialog):
    def __init__(self, fen, classe_id):
        super().__init__(search_enabled=False, content_width=640, content_height=720)
        self.fen = fen
        self.base = fen.base
        self.classe_id = classe_id
        c = self.base.classe(classe_id)
        self.set_title(f"Classe {c['nom']}")
        page = Adw.PreferencesPage(title="Classe", icon_name="system-users-symbolic")

        g = Adw.PreferencesGroup(title="Classe")
        self.nom = Adw.EntryRow(title="Nom", text=c["nom"], show_apply_button=True, use_markup=False)
        self.nom.connect("apply", self._renommer)
        g.add(self.nom)
        self.decoupage = Adw.ComboRow(title="Découpage de l'année",
                                      model=outils.liste_chaines(["3 trimestres", "2 semestres"]))
        self.decoupage.set_selected(0 if c["decoupage"] == "T" else 1)
        self.decoupage.connect("notify::selected", self._decoupage)
        g.add(self.decoupage)
        lm = Adw.SpinRow.new_with_range(50, 3000, 10)
        lm.set_title("Limite d'une appréciation")
        lm.set_subtitle("En caractères, espaces comprises")
        lm.set_value(c["limite_matiere"])
        lm.connect("notify::value", lambda r, _p: self.base.maj_classe(classe_id, limite_matiere=int(r.get_value())))
        g.add(lm)
        lb = Adw.SpinRow.new_with_range(50, 3000, 10)
        lb.set_title("Limite du bilan général")
        lb.set_value(c["limite_bilan"])
        lb.connect("notify::value", lambda r, _p: self.base.maj_classe(classe_id, limite_bilan=int(r.get_value())))
        g.add(lb)
        pf = Adw.SwitchRow(title="Suivi des PFMP",
                           subtitle="Afficher cette classe dans la section PFMP "
                                    "(stages, conventions, répartition, visites)",
                           active=bool(c["pfmp"]))
        pf.connect("notify::active", lambda r, _p: self.base.maj_classe(classe_id, pfmp=int(r.get_active())))
        g.add(pf)
        page.add(g)

        self.g_eleves = Adw.PreferencesGroup(title="Élèves")
        importer = outils.bouton("document-open-symbolic", "_Importer…", "Importer un tableur (csv, xlsx, ods)",
                                 classes=("flat",), clic=self._importer)
        self.g_eleves.set_header_suffix(importer)
        ajout = Adw.EntryRow(title="Ajouter un élève : NOM Prénom", show_apply_button=True, use_markup=False)
        ajout.connect("apply", self._ajouter_eleve)
        ajout.connect("entry-activated", self._ajouter_eleve)
        self.g_eleves.add(ajout)
        self.lignes_eleves = []
        page.add(self.g_eleves)

        self.g_matieres = Adw.PreferencesGroup(title="Matières",
                                               description="L'ordre est celui du bulletin.")
        ajout_m = Adw.EntryRow(title="Ajouter une matière", show_apply_button=True, use_markup=False)
        ajout_m.connect("apply", self._ajouter_matiere)
        ajout_m.connect("entry-activated", self._ajouter_matiere)
        self.g_matieres.add(ajout_m)
        self.lignes_matieres = []
        page.add(self.g_matieres)

        g = Adw.PreferencesGroup()
        sup = Adw.ButtonRow(title="Supprimer la classe…", start_icon_name="user-trash-symbolic")
        sup.add_css_class("destructive-action")
        sup.connect("activated", self._supprimer)
        g.add(sup)
        page.add(g)
        self.add(page)
        self._remplir()
        self.connect("closed", lambda *_: fen.rafraichir())

    def _remplir(self):
        for r in self.lignes_eleves:
            self.g_eleves.remove(r)
        self.lignes_eleves = []
        eleves = self.base.eleves(self.classe_id)
        self.g_eleves.set_description(f"{len(eleves)} élève(s)")
        for e in eleves:
            r = Adw.ActionRow(title=nom_complet(e), use_markup=False)
            r.add_suffix(outils.bouton("document-edit-symbolic", infobulle="Modifier", classes=("flat",),
                                       clic=lambda e=e: self._modifier_eleve(e)))
            r.add_suffix(outils.bouton("user-trash-symbolic", infobulle="Supprimer", classes=("flat",),
                                       clic=lambda e=e: self._supprimer_eleve(e)))
            self.g_eleves.add(r)
            self.lignes_eleves.append(r)
        for r in self.lignes_matieres:
            self.g_matieres.remove(r)
        self.lignes_matieres = []
        matieres = self.base.matieres(self.classe_id)
        for i, m in enumerate(matieres):
            r = Adw.EntryRow(title="Matière", text=m["nom"], show_apply_button=True, use_markup=False)
            r.connect("apply", lambda r, mid=m["id"]: (self.base.renommer_matiere(mid, r.get_text()),
                                                      self.fen.toast("Matière renommée")))
            haut = outils.bouton("go-up-symbolic", infobulle="Monter", classes=("flat",),
                                 clic=lambda mid=m["id"]: self._deplacer(mid, -1))
            haut.set_sensitive(i > 0)
            bas = outils.bouton("go-down-symbolic", infobulle="Descendre", classes=("flat",),
                                clic=lambda mid=m["id"]: self._deplacer(mid, 1))
            bas.set_sensitive(i < len(matieres) - 1)
            sup = outils.bouton("user-trash-symbolic", infobulle="Supprimer", classes=("flat",),
                                clic=lambda m=m: self._supprimer_matiere(m))
            for b in (haut, bas, sup):
                b.set_valign(Gtk.Align.CENTER)
                r.add_suffix(b)
            self.g_matieres.add(r)
            self.lignes_matieres.append(r)

    def _renommer(self, r):
        try:
            self.base.maj_classe(self.classe_id, nom=r.get_text())
            self.set_title(f"Classe {r.get_text().strip()}")
            self.add_toast(Adw.Toast(title="Classe renommée"))
        except Exception as e:  # noqa: BLE001 — conflit d'unicité ou nom vide
            self.add_toast(Adw.Toast(title=_esc(f"Impossible : {e}")))

    def _decoupage(self, r, _p):
        self.base.maj_classe(self.classe_id, decoupage="T" if r.get_selected() == 0 else "S")

    def _ajouter_eleve(self, r):
        texte = " ".join(r.get_text().split())
        if not texte:
            return
        nom, prenom = separer_nom_prenom(texte)
        self.base.ajouter_eleve(self.classe_id, nom, prenom)
        r.set_text("")
        self._remplir()

    def _modifier_eleve(self, e):
        nom = Adw.EntryRow(title="Nom", text=e["nom"], use_markup=False)
        prenom = Adw.EntryRow(title="Prénom", text=e["prenom"], use_markup=False)
        d = Adw.AlertDialog(heading="Modifier l'élève")
        d.set_extra_child(_liste_boxed(nom, prenom))
        d.add_response("annuler", "_Annuler")
        d.add_response("ok", "_Enregistrer")
        d.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        d.set_default_response("ok")
        d.set_close_response("annuler")

        def rep(_d, r):
            if r == "ok" and (nom.get_text().strip() or prenom.get_text().strip()):
                self.base.maj_eleve(e["id"], nom.get_text(), prenom.get_text())
                self._remplir()
        d.connect("response", rep)
        d.present(outils.fenetre_parent(self))

    def _supprimer_eleve(self, e):
        outils.confirmer(self, f"Supprimer {nom_complet(e)} ?",
                         "Ses appréciations, bilans et informations de PFMP seront supprimés.",
                         "_Supprimer", lambda: (self.base.supprimer_eleve(e["id"]), self._remplir()))

    def _ajouter_matiere(self, r):
        if r.get_text().strip():
            self.base.ajouter_matiere(self.classe_id, r.get_text())
            r.set_text("")
            self._remplir()

    def _deplacer(self, mid, delta):
        self.base.deplacer_matiere(mid, delta)
        self._remplir()

    def _supprimer_matiere(self, m):
        outils.confirmer(self, f"Supprimer la matière {m['nom']} ?",
                         "Toutes les appréciations de cette matière seront supprimées.",
                         "_Supprimer", lambda: (self.base.supprimer_matiere(m["id"]), self._remplir()))

    def _importer(self):
        importer_tableur(self.fen, self.classe_id, None, parent=self, apres=self._remplir)

    def _supprimer(self, *_):
        c = self.base.classe(self.classe_id)

        def faire():
            self.base.sauvegarder("avant-suppression")
            self.base.supprimer_classe(self.classe_id)
            self.close()
            self.fen.toast(f"Classe {c['nom']} supprimée (une sauvegarde a été faite)")
        outils.confirmer(self, f"Supprimer la classe {c['nom']} ?",
                         "Élèves, appréciations et suivis PFMP de la classe seront supprimés. "
                         "Une sauvegarde de la base est faite juste avant.", "_Supprimer", faire)


# ================================================================ années

def nouvelle_annee(fen):
    base = fen.base
    actuelle = base.annee(base.annee_active())
    m = re.match(r"(\d{4})-(\d{4})", actuelle["libelle"])
    propose = f"{int(m.group(1)) + 1}-{int(m.group(2)) + 1}" if m else annee_scolaire_courante()
    lib = Adw.EntryRow(title="Année scolaire", text=propose, use_markup=False)
    reprise = Adw.SwitchRow(title="Reprendre les classes et les matières",
                            subtitle=f"Depuis {actuelle['libelle']}, sans les élèves", active=True)
    d = Adw.AlertDialog(heading="Nouvelle année scolaire",
                        body="La banque de phrases et le carnet d'entreprises sont conservés.")
    d.set_extra_child(_liste_boxed(lib, reprise))
    d.add_response("annuler", "_Annuler")
    d.add_response("ok", "_Créer")
    d.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
    d.set_default_response("ok")
    d.set_close_response("annuler")

    def rep(_d, r):
        if r != "ok":
            return
        try:
            base.creer_annee(lib.get_text(), actuelle["id"] if reprise.get_active() else None)
        except ValueError as e:
            outils.alerte(fen, "Année non créée", str(e))
            return
        fen.rafraichir(nouvelle_annee=True)
        fen.toast(f"Année {lib.get_text().strip()} créée")
    d.connect("response", rep)
    d.present(fen)


def archiver_annee(fen):
    base = fen.base
    a = base.annee(base.annee_active())
    if a["archivee"]:
        fen.toast("Cette année est déjà archivée")
        return

    def faire():
        fen.vider_attente()
        chemin = base.archiver(a["id"])
        fen.rafraichir()
        fen.toast("Année archivée : export JSON enregistré", "Voir",
                  lambda: outils.montrer_dans_dossier(fen, chemin))
    outils.confirmer(fen, f"Archiver l'année {a['libelle']} ?",
                     "L'année passe en consultation seule et un export JSON complet est enregistré "
                     "dans le dossier des archives. Vous pourrez la désarchiver plus tard.",
                     "_Archiver", faire, destructif=False)


# =========================================================== import tableur

def importer_tableur(fen, classe_id, periode, parent=None, apres=None):
    def lu(chemin):
        try:
            lignes = tableur.lire(chemin)
        except tableur.ErreurTableur as e:
            outils.alerte(parent or fen, "Import impossible", str(e))
            return
        if not lignes:
            outils.alerte(parent or fen, "Import impossible", "Le fichier ne contient aucune donnée.")
            return
        DialogueImport(fen, classe_id, periode, chemin, lignes, apres).present(parent or fen)
    outils.choisir_fichier(parent or fen, "Importer la liste des élèves",
                           [("Tableurs (csv, xlsx, ods)", ["csv", "xlsx", "ods"],
                             ["text/csv", "application/vnd.oasis.opendocument.spreadsheet",
                              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"])],
                           lu)


class DialogueImport(Adw.Dialog):
    def __init__(self, fen, classe_id, periode, chemin, lignes, apres=None):
        super().__init__(title="Importer la liste des élèves", content_width=560, content_height=680)
        self.fen = fen
        self.base = fen.base
        self.classe_id = classe_id
        self.lignes = lignes
        self.apres = apres
        self.analyse = tableur.analyser(lignes)
        c = self.base.classe(classe_id)
        cols = self.analyse["colonnes"]

        vue = Adw.ToolbarView()
        entete = Adw.HeaderBar(show_end_title_buttons=False, show_start_title_buttons=False)
        entete.pack_start(outils.bouton(libelle="_Annuler", clic=self.close))
        self.bouton = outils.bouton(libelle="_Importer", classes=("suggested-action",), clic=self._importer)
        entete.pack_end(self.bouton)
        vue.add_top_bar(entete)
        page = Adw.PreferencesPage()

        g = Adw.PreferencesGroup(title="Fichier")
        g.add(Adw.ActionRow(title=Path(chemin).name, subtitle=f"{len(lignes)} lignes · classe {c['nom']}",
                            use_markup=False))
        page.add(g)

        g = Adw.PreferencesGroup(title="Colonnes", description="Détectées automatiquement ; corrigez si besoin.")
        self.c_nom = Adw.ComboRow(title="Nom (ou « NOM Prénom »)", model=outils.liste_chaines(cols))
        self.c_nom.set_selected(self.analyse["nom"] or 0)
        self.c_prenom = Adw.ComboRow(title="Prénom",
                                     model=outils.liste_chaines(["Dans la colonne du nom", *cols]))
        self.c_prenom.set_selected((self.analyse["prenom"] + 1) if self.analyse["prenom"] is not None else 0)
        self.c_moy = Adw.ComboRow(title="Moyenne générale",
                                  model=outils.liste_chaines(["Aucune", *cols]))
        self.c_moy.set_selected((self.analyse["moyenne"] + 1) if self.analyse["moyenne"] is not None else 0)
        pers = [libelle_periode(c["decoupage"], p, True) for p in range(1, nb_periodes(c["decoupage"]) + 1)]
        self.c_per = Adw.ComboRow(title="Période de la moyenne", model=outils.liste_chaines(pers))
        self.c_per.set_selected(max(0, min(len(pers) - 1, (periode or 1) - 1)))
        self.ajout = Adw.SwitchRow(title="Ajouter les élèves absents de la classe", active=True)
        for r in (self.c_nom, self.c_prenom, self.c_moy, self.c_per, self.ajout):
            g.add(r)
            r.connect("notify::selected" if isinstance(r, Adw.ComboRow) else "notify::active",
                      lambda *_: self._apercu())
        page.add(g)

        self.g_apercu = Adw.PreferencesGroup(title="Aperçu")
        self.lignes_apercu = []
        page.add(self.g_apercu)
        vue.set_content(page)
        self.set_child(vue)
        self._apercu()

    def _extraire(self):
        p = self.c_prenom.get_selected()
        m = self.c_moy.get_selected()
        return tableur.extraire(self.lignes, self.analyse["entete"], self.c_nom.get_selected(),
                                None if p == 0 else p - 1, None if m == 0 else m - 1)

    def _apercu(self):
        for r in self.lignes_apercu:
            self.g_apercu.remove(r)
        self.lignes_apercu = []
        res = self._extraire()
        existants = {normaliser(f"{e['nom']} {e['prenom']}") for e in self.base.eleves(self.classe_id)}
        nouveaux = sum(1 for n, p, _ in res if normaliser(f"{n} {p}") not in existants)
        moy = sum(1 for *_, m in res if m is not None)
        self.g_apercu.set_description(f"{len(res)} élèves lus · {nouveaux} nouveaux · {moy} moyennes")
        for nom, prenom, moyenne in res[:6]:
            r = Adw.ActionRow(title=f"{nom} {prenom}".strip(), use_markup=False)
            lab = Gtk.Label(label=f"{moyenne:.2f}".replace(".", ",") if moyenne is not None else "—")
            lab.add_css_class("numeric")
            r.add_suffix(lab)
            self.g_apercu.add(r)
            self.lignes_apercu.append(r)
        self.bouton.set_sensitive(bool(res))

    def _importer(self):
        res = self._extraire()
        periode = self.c_per.get_selected() + 1 if self.c_moy.get_selected() else None
        bilan = self.base.importer_eleves(self.classe_id, res, periode, self.ajout.get_active())
        morceaux = [f"{bilan['ajoutes']} élève(s) ajouté(s)", f"{bilan['moyennes']} moyenne(s)"]
        if bilan["ignores"]:
            morceaux.append(f"{len(bilan['ignores'])} ignoré(s)")
        self.close()
        self.fen.rafraichir()
        if self.apres:
            self.apres()
        self.fen.toast(" · ".join(morceaux))


# ========================================================= banque de phrases

class DialoguePhrases(Adw.Dialog):
    def __init__(self, fen):
        super().__init__(title="Banque de phrases", content_width=680, content_height=720)
        self.fen = fen
        self.base = fen.base
        vue = Adw.ToolbarView()
        entete = Adw.HeaderBar()
        entete.pack_start(outils.bouton("list-add-symbolic", "_Nouvelle phrase", classes=("suggested-action",),
                                        clic=lambda: self._editer(None)))
        vue.add_top_bar(entete)
        barre = Gtk.Box(margin_start=12, margin_end=12, margin_top=6, margin_bottom=6)
        self.recherche = Gtk.SearchEntry(placeholder_text="Rechercher par mots-clés, texte ou catégorie…",
                                         hexpand=True)
        self.recherche.connect("search-changed", lambda *_: self._remplir())
        barre.append(self.recherche)
        vue.add_top_bar(barre)
        defil = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        clamp = Adw.Clamp(maximum_size=760)
        self.boite = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, margin_top=12,
                             margin_bottom=24, margin_start=12, margin_end=12)
        clamp.set_child(self.boite)
        defil.set_child(clamp)
        vue.set_content(defil)
        self.set_child(vue)
        self._remplir()

    def _remplir(self):
        outils.vider(self.boite)
        aide = Gtk.Label(label="Écrivez {prénom} dans une phrase pour y insérer le prénom de l'élève. "
                               "Les mots-clés servent à la recherche.", xalign=0, wrap=True)
        aide.add_css_class("dim-label")
        aide.add_css_class("caption")
        self.boite.append(aide)
        groupes: dict = {}
        phrases = self.base.phrases(self.recherche.get_text())
        for p in phrases:
            cat = p["categorie"] or "Sans catégorie"
            if cat not in groupes:
                groupes[cat] = Adw.PreferencesGroup(title=_esc(cat))
                self.boite.append(groupes[cat])
            r = Adw.ActionRow(title=p["texte"], use_markup=False, title_lines=0)
            if p["mots_cles"]:
                r.set_subtitle(f"Mots-clés : {p['mots_cles']}")
            r.add_suffix(outils.bouton("document-edit-symbolic", infobulle="Modifier", classes=("flat",),
                                       clic=lambda p=p: self._editer(p)))
            r.add_suffix(outils.bouton("user-trash-symbolic", infobulle="Supprimer", classes=("flat",),
                                       clic=lambda p=p: self._supprimer(p)))
            groupes[cat].add(r)
        if not phrases:
            st = Adw.StatusPage(icon_name="system-search-symbolic", title="Aucune phrase trouvée")
            st.add_css_class("compact")
            self.boite.append(st)

    def _editer(self, p):
        cat = Adw.EntryRow(title="Catégorie", text=p["categorie"] if p else "", use_markup=False)
        mots = Adw.EntryRow(title="Mots-clés", text=p["mots_cles"] if p else "", use_markup=False)
        boite = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        boite.append(_liste_boxed(cat, mots))
        cadre = Gtk.Box()
        cadre.add_css_class("card")
        cadre.add_css_class("editeur-cadre")
        vue = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR, top_margin=10, bottom_margin=10,
                           left_margin=12, right_margin=12, hexpand=True, accepts_tab=False)
        vue.add_css_class("editeur")
        vue.update_property([Gtk.AccessibleProperty.LABEL], ["Texte de la phrase"])
        vue.get_buffer().set_text(p["texte"] if p else "")
        cadre.append(vue)
        boite.append(cadre)
        cats = self.base.categories_phrases()
        if cats:
            aide = Gtk.Label(label="Catégories existantes : " + ", ".join(c for c in cats if c), xalign=0,
                             wrap=True)
            aide.add_css_class("dim-label")
            aide.add_css_class("caption")
            boite.append(aide)
        d = Adw.AlertDialog(heading="Modifier la phrase" if p else "Nouvelle phrase",
                            body="{prénom} sera remplacé par le prénom de l'élève.")
        d.set_extra_child(boite)
        d.add_response("annuler", "_Annuler")
        d.add_response("ok", "_Enregistrer")
        d.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        d.set_close_response("annuler")
        tampon = vue.get_buffer()

        def maj(*_):
            d.set_response_enabled("ok", bool(tampon.get_text(*tampon.get_bounds(), False).strip()))
        tampon.connect("changed", maj)
        maj()

        def rep(_d, r):
            if r != "ok":
                return
            texte = tampon.get_text(*tampon.get_bounds(), False)
            if p:
                self.base.maj_phrase(p["id"], cat.get_text(), texte, mots.get_text())
            else:
                self.base.ajouter_phrase(cat.get_text(), texte, mots.get_text())
            self._remplir()
        d.connect("response", rep)
        d.present(outils.fenetre_parent(self))
        outils.focus_differe(vue)

    def _supprimer(self, p):
        outils.confirmer(self, "Supprimer cette phrase ?", p["texte"], "_Supprimer",
                         lambda: (self.base.supprimer_phrase(p["id"]), self._remplir()))


# ======================================================= carnet d'entreprises

class DialogueCarnet(Adw.Dialog):
    """Carnet d'entreprises : ajout, modification, suppression, itinéraire.
    Le carnet se remplit aussi tout seul quand on saisit une entreprise dans un stage."""

    def __init__(self, fen):
        super().__init__(title="Carnet d'entreprises", content_width=700, content_height=720)
        self.fen = fen
        self.base = fen.base
        self.ro = fen.lecture_seule()
        self.toasts = Adw.ToastOverlay()
        vue = Adw.ToolbarView()
        entete = Adw.HeaderBar()
        nouveau = outils.bouton("list-add-symbolic", "_Nouvelle entreprise", classes=("suggested-action",),
                                clic=lambda: self._editer(None))
        nouveau.set_sensitive(not self.ro)
        entete.pack_start(nouveau)
        vue.add_top_bar(entete)
        barre = Gtk.Box(margin_start=12, margin_end=12, margin_top=6, margin_bottom=6)
        self.recherche = Gtk.SearchEntry(placeholder_text="Rechercher une entreprise, une adresse, un tuteur…",
                                         hexpand=True)
        self.recherche.connect("search-changed", lambda *_: self._remplir())
        barre.append(self.recherche)
        vue.add_top_bar(barre)
        self.page = Adw.PreferencesPage()
        self.groupe = None
        vue.set_content(self.page)
        self.toasts.set_child(vue)
        self.set_child(self.toasts)
        self.connect("closed", lambda *_: fen.rafraichir())
        self._remplir()

    def _toast(self, texte):
        self.toasts.add_toast(Adw.Toast(title=_esc(texte)))

    def _remplir(self):
        if self.groupe is not None:
            self.page.remove(self.groupe)
        entreprises = self.base.carnet(self.recherche.get_text())
        self.groupe = Adw.PreferencesGroup(
            description=f"{len(entreprises)} entreprise(s). Le carnet se complète aussi tout seul "
                        "quand vous saisissez une entreprise dans un stage.")
        for e in entreprises:
            n = self.base.stages_entreprise(e["nom"])
            details = [x for x in (e["adresse"], e["telephone"],
                                   f"tuteur : {e['tuteur']}" if e["tuteur"] else "",
                                   f"{n} stage(s)" if n else "") if x]
            r = Adw.ActionRow(title=e["nom"], subtitle=" · ".join(details) or "Aucune information",
                              use_markup=False, subtitle_lines=2)
            itin = outils.bouton("livret-route-symbolic", infobulle="Itinéraire", classes=("flat",),
                                 clic=lambda e=e, r=r: outils.ouvrir_itineraire(r, e["adresse"]))
            itin.set_sensitive(bool(e["adresse"]))
            r.add_suffix(itin)
            for icone, info, f in (("document-edit-symbolic", "Modifier", lambda e=e: self._editer(e)),
                                   ("user-trash-symbolic", "Retirer du carnet", lambda e=e: self._supprimer(e))):
                b = outils.bouton(icone, infobulle=info, classes=("flat",), clic=f)
                b.set_sensitive(not self.ro)
                r.add_suffix(b)
            self.groupe.add(r)
        if not entreprises:
            self.groupe.add(Adw.ActionRow(title="Aucune entreprise" if not self.recherche.get_text()
                                          else "Aucune entreprise ne correspond"))
        self.page.add(self.groupe)

    def _editer(self, e):
        champs = {}
        lignes = []
        for cle, titre in (("nom", "Nom de l'entreprise"), ("adresse", "Adresse"),
                           ("telephone", "Téléphone"), ("tuteur", "Tuteur habituel")):
            r = Adw.EntryRow(title=titre, text=(e[cle] if e else "") or "", use_markup=False)
            if cle == "telephone":
                r.set_input_purpose(Gtk.InputPurpose.PHONE)
            champs[cle] = r
            lignes.append(r)
        n = self.base.stages_entreprise(e["nom"]) if e else 0
        propager = None
        if n:
            propager = Adw.SwitchRow(title=f"Mettre à jour aussi les {n} stage(s) de cette entreprise",
                                     subtitle="Nom, adresse et téléphone ; le tuteur seulement s'il était "
                                              "vide ou identique", active=True)
            lignes.append(propager)
        d = Adw.AlertDialog(heading="Modifier l'entreprise" if e else "Nouvelle entreprise")
        d.set_extra_child(_liste_boxed(*lignes))
        d.add_response("annuler", "_Annuler")
        d.add_response("ok", "_Enregistrer")
        d.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        d.set_default_response("ok")
        d.set_close_response("annuler")
        d.set_response_enabled("ok", bool(champs["nom"].get_text().strip()))
        champs["nom"].connect("changed", lambda r: d.set_response_enabled("ok", bool(r.get_text().strip())))
        for r in champs.values():
            r.set_activates_default(True)

        def rep(_d, reponse):
            if reponse != "ok":
                return
            v = {k: r.get_text() for k, r in champs.items()}
            try:
                if e:
                    faits = self.base.maj_entreprise(e["id"], v["nom"], v["adresse"], v["telephone"],
                                                     v["tuteur"], propager=bool(propager and propager.get_active()))
                    self._toast(f"Entreprise modifiée · {faits} stage(s) mis à jour" if faits
                                else "Entreprise modifiée")
                else:
                    self.base.ajouter_entreprise(v["nom"], v["adresse"], v["telephone"], v["tuteur"])
                    self._toast("Entreprise ajoutée au carnet")
            except ValueError as err:
                outils.alerte(self, "Enregistrement impossible", str(err))
                return
            self._remplir()
        d.connect("response", rep)
        d.present(self)
        outils.focus_differe(champs["nom"])

    def _supprimer(self, e):
        n = self.base.stages_entreprise(e["nom"])
        corps = ("Les stages déjà saisis gardent leurs informations." if n else
                 "Cette entreprise n'est utilisée par aucun stage.")
        if n:
            corps += " Elle reviendra dans le carnet si vous modifiez l'un de ces stages."
        outils.confirmer(self, f"Retirer « {e['nom']} » du carnet ?", corps, "_Retirer",
                         lambda: (self.base.supprimer_entreprise(e["id"]), self._remplir()))


# ============================================================== préférences

class Preferences(Adw.PreferencesDialog):
    def __init__(self, fen):
        super().__init__(search_enabled=False)
        self.fen = fen
        base = fen.base
        page = Adw.PreferencesPage(title="Saisie", icon_name="document-edit-symbolic")
        g = Adw.PreferencesGroup(title="Début des appréciations",
                                 description="Le prénom de l'élève est écrit automatiquement au début "
                                             "d'une appréciation vide.")
        auto = Adw.SwitchRow(title="Commencer par le prénom", active=base.reglage_bool("prefixe_auto", True))
        auto.connect("notify::active", lambda r, _p: base.definir_reglage("prefixe_auto", int(r.get_active())))
        g.add(auto)
        exemples = [f"Léa{s}bon trimestre…" for s in calculs.SEPARATEURS]
        sep = Adw.ComboRow(title="Forme", model=outils.liste_chaines(exemples))
        actuel = base.reglage("separateur", " ")
        sep.set_selected(calculs.SEPARATEURS.index(actuel) if actuel in calculs.SEPARATEURS else 0)
        sep.connect("notify::selected",
                    lambda r, _p: base.definir_reglage("separateur", calculs.SEPARATEURS[r.get_selected()]))
        auto.bind_property("active", sep, "sensitive", 2)  # SYNC_CREATE
        g.add(sep)
        page.add(g)
        g = Adw.PreferencesGroup(title="Nouvelles classes")
        for cle, titre, defaut in (("limite_matiere_defaut", "Limite d'une appréciation", 400),
                                   ("limite_bilan_defaut", "Limite du bilan général", 600)):
            r = Adw.SpinRow.new_with_range(50, 3000, 10)
            r.set_title(titre)
            r.set_subtitle("En caractères")
            r.set_value(int(base.reglage(cle, defaut)))
            r.connect("notify::value", lambda r, _p, cle=cle: base.definir_reglage(cle, int(r.get_value())))
            g.add(r)
        page.add(g)
        self.add(page)

        page = Adw.PreferencesPage(title="Données", icon_name="document-save-symbolic")
        g = Adw.PreferencesGroup(title="Stockage local",
                                 description="Les données restent sur cet ordinateur. Chaque modification "
                                             "est enregistrée aussitôt ; une copie de la base est faite à "
                                             "chaque démarrage (10 dernières conservées).")
        r = Adw.ActionRow(title="Base de données", subtitle=str(base.chemin), use_markup=False,
                          subtitle_selectable=True)
        r.add_suffix(outils.bouton("folder-open-symbolic", infobulle="Ouvrir le dossier", classes=("flat",),
                                   clic=lambda: outils.ouvrir_chemin(fen, base.chemin.parent)))
        g.add(r)
        n = len(list(base.dossier_sauvegardes().glob("*.db")))
        r = Adw.ActionRow(title="Sauvegardes", subtitle=f"{n} copie(s) dans {base.dossier_sauvegardes()}",
                          use_markup=False)
        r.add_suffix(outils.bouton("folder-open-symbolic", infobulle="Ouvrir le dossier", classes=("flat",),
                                   clic=lambda: outils.ouvrir_chemin(fen, base.dossier_sauvegardes())))
        g.add(r)
        page.add(g)
        g = Adw.PreferencesGroup(title="Itinéraires et distances")
        g.add(Adw.ActionRow(title="Application de cartes",
                            subtitle="GNOME Cartes" if outils.cartes_installe()
                            else "GNOME Cartes absent : OpenStreetMap dans le navigateur"))
        etab = Adw.EntryRow(title="Adresse de l'établissement (point de départ des distances)",
                            text=geo.etablissement(base), show_apply_button=True, use_markup=False)
        etab.connect("apply", lambda r: base.definir_reglage(geo.REGLAGE_ETABLISSEMENT, r.get_text().strip()))
        g.add(etab)
        page.add(g)
        self.add(page)


# ===================================================== répartition des suivis

class DialogueRepartition(Adw.Dialog):
    def __init__(self, fen, classe_id=None):
        super().__init__(title="Répartition des suivis", content_width=720, content_height=760)
        self.fen = fen
        self.base = fen.base
        self.aid = self.base.annee_active()
        self.ro = fen.lecture_seule()
        self.classes = self.base.classes_pfmp(self.aid)
        ids = [c["id"] for c in self.classes]
        self.classe_id = classe_id if classe_id in ids else (ids[0] if ids else None)

        self.toasts = Adw.ToastOverlay()
        vue = Adw.ToolbarView()
        entete = Adw.HeaderBar()
        self.bouton_pdf = outils.bouton("x-office-document-symbolic", "_Générer les PDF",
                                        "Un PDF de bilan par collègue", classes=("suggested-action",),
                                        clic=self._pdf)
        entete.pack_end(self.bouton_pdf)
        vue.add_top_bar(entete)
        self.page = Adw.PreferencesPage()
        self.groupes = []
        vue.set_content(self.page)
        self.toasts.set_child(vue)
        self.set_child(self.toasts)
        self._construire()

    def _vider(self):
        for g in self.groupes:
            self.page.remove(g)
        self.groupes = []

    def _ajouter_groupe(self, g):
        self.page.add(g)
        self.groupes.append(g)

    def _construire(self):
        self._vider()
        ens = self.base.enseignants(self.aid)

        g = Adw.PreferencesGroup(title="Équipe pédagogique",
                                 description="Les collègues de l'année, communs à toutes les classes.")
        ajout = Adw.EntryRow(title="Ajouter un collègue", show_apply_button=True, use_markup=False)
        ajout.connect("apply", self._ajouter)
        ajout.connect("entry-activated", self._ajouter)
        ajout.set_sensitive(not self.ro)
        g.add(ajout)
        for e in ens:
            r = Adw.EntryRow(title="Nom", text=e["nom"], show_apply_button=True, use_markup=False)
            r.connect("apply", lambda r, eid=e["id"]: self._renommer(eid, r.get_text()))
            sup = outils.bouton("user-trash-symbolic", infobulle="Retirer de l'équipe", classes=("flat",),
                                clic=lambda e=e: self._supprimer(e))
            sup.set_valign(Gtk.Align.CENTER)
            r.add_suffix(sup)
            r.set_sensitive(not self.ro)
            g.add(r)
        self._ajouter_groupe(g)

        if not self.classes:
            g = Adw.PreferencesGroup()
            g.add(Adw.ActionRow(title="Aucune classe suivie en PFMP",
                                subtitle="Activez « Suivi des PFMP » dans les réglages de la classe."))
            self._ajouter_groupe(g)
            self.bouton_pdf.set_sensitive(False)
            return

        c = self.base.classe(self.classe_id)
        nb = len(self.base.eleves(self.classe_id))
        g = Adw.PreferencesGroup(title="Heures par classe",
                                 description="Saisies une fois par classe et par année.")
        choix = Adw.ComboRow(title="Classe", model=outils.liste_chaines([x["nom"] for x in self.classes]))
        choix.set_selected([x["id"] for x in self.classes].index(self.classe_id))
        choix.connect("notify::selected", self._classe)
        g.add(choix)
        g.add(Adw.ActionRow(title="Élèves dans la classe", subtitle=str(nb)))
        heures = self.base.heures_classe(self.classe_id)
        for e in ens:
            r = Adw.SpinRow.new_with_range(0, 40, 0.5)
            r.set_digits(1)
            r.set_title(_esc(e["nom"]))
            r.set_subtitle(f"Heures élève hebdomadaires en {_esc(c['nom'])}")
            r.set_value(heures.get(e["id"], 0))
            r.connect("notify::value", lambda r, _p, eid=e["id"]: self._heures(eid, r.get_value()))
            r.set_sensitive(not self.ro)
            g.add(r)
        if not ens:
            g.add(Adw.ActionRow(title="Ajoutez d'abord les collègues ci-dessus."))
        self._ajouter_groupe(g)

        self.g_res = Adw.PreferencesGroup(title="Élèves à suivre",
                                          description="(heures du collègue ÷ total des heures) × nombre "
                                                      "d'élèves — calcul exact, valeur donnée à 0,1 près.")
        self.lignes_res = []
        self._ajouter_groupe(self.g_res)
        self._resultats()
        self.bouton_pdf.set_sensitive(any(self.base.heures_enseignant(e["id"]) for e in ens))

    def _resultats(self):
        for r in self.lignes_res:
            self.g_res.remove(r)
        self.lignes_res = []
        heures = self.base.heures_classe(self.classe_id)
        nb = len(self.base.eleves(self.classe_id))
        parts = calculs.repartir(heures, nb)
        noms = {e["id"]: e["nom"] for e in self.base.enseignants(self.aid)}
        total_h = sum(heures.values())
        for eid, q in sorted(parts.items(), key=lambda kv: normaliser(noms.get(kv[0], ""))):
            r = Adw.ActionRow(title=noms.get(eid, "?"), use_markup=False,
                              subtitle=f"{calculs.format_heures(heures[eid])} sur "
                                       f"{calculs.format_heures(total_h)} × {nb} élèves")
            lab = Gtk.Label(label=calculs.format_quota(q))
            lab.add_css_class("quota")
            r.add_suffix(lab)
            self.g_res.add(r)
            self.lignes_res.append(r)
        if parts:
            r = Adw.ActionRow(title="Total", subtitle="Contrôle : la somme redonne l'effectif")
            lab = Gtk.Label(label=calculs.format_quota(sum(parts.values())))
            lab.add_css_class("heading")
            r.add_suffix(lab)
            self.g_res.add(r)
            self.lignes_res.append(r)
        else:
            r = Adw.ActionRow(title="Aucune heure saisie pour cette classe")
            self.g_res.add(r)
            self.lignes_res.append(r)

    def _classe(self, r, _p):
        self.classe_id = self.classes[r.get_selected()]["id"]
        GLib.idle_add(self._construire)

    def _heures(self, eid, h):
        self.base.definir_heures(eid, self.classe_id, h)
        self._resultats()
        self.bouton_pdf.set_sensitive(True)

    def _ajouter(self, r):
        if r.get_text().strip():
            self.base.ajouter_enseignant(self.aid, r.get_text())
            GLib.idle_add(self._construire)

    def _renommer(self, eid, nom):
        try:
            self.base.renommer_enseignant(eid, nom)
            self.toasts.add_toast(Adw.Toast(title="Nom modifié"))
            GLib.idle_add(self._construire)
        except Exception as e:  # noqa: BLE001 — nom vide ou déjà pris
            self.toasts.add_toast(Adw.Toast(title=_esc(f"Impossible : {e}")))

    def _supprimer(self, e):
        outils.confirmer(self, f"Retirer {e['nom']} de l'équipe ?",
                         "Ses heures sont effacées et ses élèves suivis n'ont plus de référent.",
                         "_Retirer", lambda: (self.base.supprimer_enseignant(e["id"]),
                                              GLib.idle_add(self._construire)))

    def _pdf(self):
        exports = outils.module_exports(self)
        if exports is None:
            return
        ens = [e for e in self.base.enseignants(self.aid) if self.base.heures_enseignant(e["id"])]
        if not ens:
            return
        annee = self.base.annee(self.aid)["libelle"]

        def ecrire(dossier):
            faits = []
            try:
                for e in ens:
                    nom = re.sub(r'[\\/:*?"<>|]', "-", e["nom"])
                    chemin = os.path.join(dossier, f"Suivis PFMP {annee} - {nom}.pdf")
                    exports.bilan_suivis_pdf(self.base, self.aid, e["id"], chemin)
                    faits.append(chemin)
            except Exception as err:  # noqa: BLE001
                outils.alerte(self, "Génération interrompue", str(err))
                return
            t = Adw.Toast(title=f"{len(faits)} PDF enregistré(s)", button_label="Ouvrir le dossier")
            t.connect("button-clicked", lambda *_: outils.ouvrir_chemin(self, dossier))
            self.toasts.add_toast(t)
        outils.choisir_dossier(self, "Dossier où enregistrer les PDF", ecrire)


# ============================================================ visites PFMP

class DialogueVisites(Adw.Dialog):
    def __init__(self, fen, numero=1):
        super().__init__(title="Visites PFMP", content_width=1000, content_height=760)
        self.fen = fen
        self.base = fen.base
        self.aid = self.base.annee_active()
        self.ro = fen.lecture_seule()
        self.numero = numero
        self.ens_id = None
        self.champs = []

        self.toasts = Adw.ToastOverlay()
        vue = Adw.ToolbarView()
        entete = Adw.HeaderBar()
        self.choix = Adw.ToggleGroup(valign=Gtk.Align.CENTER)
        for n in (1, 2):
            self.choix.add(Adw.Toggle(name=str(n), label=f"PFMP {n}"))
        self.choix.set_active_name(str(numero))
        self.choix.connect("notify::active-name", self._pfmp)
        entete.pack_start(self.choix)
        entete.pack_end(outils.bouton("x-office-spreadsheet-symbolic", "_XLSX",
                                      "Exporter les visites en tableur (xlsx)", clic=self._exporter_xlsx))
        self.bouton_distances = outils.bouton(
            "mark-location-symbolic", "_Distances",
            "Distances depuis l'établissement, à vol d'oiseau (adresses localisées par OpenStreetMap)",
            clic=self._distances)
        entete.pack_start(self.bouton_distances)
        entete.pack_end(outils.bouton("x-office-document-symbolic", "_PDF",
                                      "Exporter les visites en PDF", clic=self._exporter_pdf))
        vue.add_top_bar(entete)

        paned = Gtk.Paned(position=260, shrink_start_child=False, shrink_end_child=False,
                          resize_start_child=False)
        gauche = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        gauche.append(outils.titre_section("Collègues"))
        gauche.get_first_child().add_css_class("liste-entete")
        self.liste = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.liste.add_css_class("navigation-sidebar")
        self.liste.connect("row-selected", self._choisi)
        vide = Gtk.Label(label="Aucun collègue.\nAjoutez l'équipe ci-dessous ou dans « Répartition des suivis ».",
                         wrap=True, justify=Gtk.Justification.CENTER, margin_top=18, margin_start=12,
                         margin_end=12)
        vide.add_css_class("dim-label")
        self.liste.set_placeholder(vide)
        defil = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        defil.set_child(self.liste)
        gauche.append(defil)
        ajout = Adw.EntryRow(title="Ajouter un collègue", show_apply_button=True, use_markup=False)
        ajout.connect("apply", self._ajouter_ens)
        ajout.connect("entry-activated", self._ajouter_ens)
        ajout.set_sensitive(not self.ro)
        l = _liste_boxed(ajout)
        l.set_margin_start(8)
        l.set_margin_end(8)
        l.set_margin_bottom(8)
        gauche.append(l)
        paned.set_start_child(gauche)
        self.droite = Adw.Bin()
        paned.set_end_child(self.droite)
        vue.set_content(paned)
        self.toasts.set_child(vue)
        self.set_child(self.toasts)
        self.connect("closed", self._ferme)
        self._remplir_ens()

    def _ferme(self, *_):
        for c in self.champs:
            c.vider_attente()
        self.fen.rafraichir()

    def _exporter_pdf(self):
        exports = outils.module_exports(self)
        if exports is None:
            return
        annee = self.base.annee(self.aid)["libelle"]
        nom = f"Visites PFMP {self.numero} — {annee}.pdf"

        def ecrire(chemin):
            try:
                exports.visites_pdf(self.base, self.aid, self.numero, chemin)
            except Exception as err:  # noqa: BLE001
                outils.alerte(self, "Export impossible", str(err))
                return
            t = Adw.Toast(title="PDF des visites enregistré", button_label="Ouvrir")
            t.connect("button-clicked", lambda *_: outils.ouvrir_chemin(self, chemin))
            self.toasts.add_toast(t)
        outils.enregistrer_fichier(self, "Exporter les visites en PDF", nom,
                                   [("Document PDF", ["pdf"], ["application/pdf"])], ecrire)

    def _exporter_xlsx(self):
        exports = outils.module_exports(self)
        if exports is None:
            return
        annee = self.base.annee(self.aid)["libelle"]
        nom = f"Visites PFMP {self.numero} — {annee}.xlsx"

        def ecrire(chemin):
            try:
                exports.visites_xlsx(self.base, self.aid, self.numero, chemin)
            except Exception as err:  # noqa: BLE001
                outils.alerte(self, "Export impossible", str(err))
                return
            t = Adw.Toast(title="Tableur des visites enregistré", button_label="Ouvrir")
            t.connect("button-clicked", lambda *_: outils.ouvrir_chemin(self, chemin))
            self.toasts.add_toast(t)
        outils.enregistrer_fichier(self, "Exporter les visites (xlsx)", nom,
                                   [("Classeur Excel", ["xlsx"],
                                     ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"])],
                                   ecrire)

    def pfmp_id(self):
        return self.base.pfmp_id(self.aid, self.numero)

    def _remplir_ens(self):
        garde = self.ens_id
        self.liste.remove_all()
        choisie = None
        stages = self.base.stages(self.aid, self.pfmp_id())
        for e in self.base.enseignants(self.aid):
            n = sum(1 for s in stages if s["enseignant_id"] == e["id"])
            ligne = Gtk.ListBoxRow()
            ligne.ens_id = e["id"]
            b = Gtk.Box(spacing=8, margin_top=6, margin_bottom=6)
            b.append(Gtk.Label(label=e["nom"], xalign=0, hexpand=True, ellipsize=Pango.EllipsizeMode.END))
            c = Gtk.Label(label=str(n))
            c.add_css_class("dim-label")
            c.add_css_class("numeric")
            b.append(c)
            ligne.set_child(b)
            self.liste.append(ligne)
            if e["id"] == garde:
                choisie = ligne
        choisie = choisie or self.liste.get_row_at_index(0)
        if choisie:
            self.liste.select_row(choisie)
        else:
            self.droite.set_child(Adw.StatusPage(icon_name="livret-visites-symbolic",
                                                 title="Aucun collègue",
                                                 description="Ajoutez les collègues de l'équipe à gauche."))

    def _choisi(self, _l, ligne):
        if ligne is None:
            return
        for c in self.champs:
            c.vider_attente()
        self.ens_id = ligne.ens_id
        self._page()

    def _page(self):
        ens = next((e for e in self.base.enseignants(self.aid) if e["id"] == self.ens_id), None)
        if ens is None:
            return
        suivis = self.base.suivis(self.ens_id, self.pfmp_id())
        page = Adw.PreferencesPage()
        # Repère : quota calculé par la répartition des suivis
        from .exports import bilan_suivis
        _lignes, quota = bilan_suivis(self.base, self.aid, self.ens_id)
        desc = f"{len(suivis)} élève(s) attribué(s)"
        if quota:
            desc += f" · à suivre selon la répartition : {calculs.format_quota(quota)}"
        g = Adw.PreferencesGroup(title=_esc(f"{ens['nom']} — PFMP {self.numero}"), description=_esc(desc))
        ajout = outils.bouton("list-add-symbolic", "_Ajouter des élèves…", classes=("flat",),
                              clic=self._choisir_eleves)
        ajout.set_sensitive(not self.ro)
        g.set_header_suffix(ajout)
        self.champs = []
        for s in suivis:
            km = geo.format_km(geo.distance_km(self.base, s["adresse"]))
            r = Adw.ExpanderRow(title=f"{s['nom']} {s['prenom']}", use_markup=False,
                                subtitle=" · ".join(x for x in (s["classe_nom"], s["entreprise"], km) if x))
            r.set_subtitle_lines(1)
            champs = ChampsEntreprise(self.fen, s["eleve_id"], s["pfmp_id"], lecture_seule=self.ro)
            champs.apres = (lambda r=r, s=s, ch=champs: r.set_subtitle(
                " · ".join(x for x in (s["classe_nom"], ch.entrees["entreprise"].get_text().strip()) if x)))
            itin = outils.bouton("livret-route-symbolic", infobulle="Itinéraire", classes=("flat",),
                                 clic=champs.itineraire)
            itin.set_valign(Gtk.Align.CENTER)
            itin.set_sensitive(bool(s["adresse"]))
            champs.entrees["adresse"].connect("changed", lambda e, b=itin: b.set_sensitive(bool(e.get_text().strip())))
            r.add_suffix(itin)
            for l in champs.lignes:
                r.add_row(l)
            retirer = Adw.ButtonRow(title="Retirer de ses suivis", start_icon_name="list-remove-symbolic")
            retirer.connect("activated", lambda _b, s=s: self._retirer(s))
            retirer.set_sensitive(not self.ro)
            r.add_row(retirer)
            self.champs.append(champs)
            g.add(r)
        if not suivis:
            g.add(Adw.ActionRow(title="Aucun élève attribué",
                                subtitle="« Ajouter des élèves » pour constituer la tournée."))
        page.add(g)
        self.droite.set_child(page)

    # ------------------------------------------------------------- distances
    def _toast(self, texte):
        self.toasts.add_toast(Adw.Toast(title=_esc(texte), timeout=5))

    def _distances(self):
        if not geo.etablissement(self.base):
            self._demander_etablissement()
            return
        adresses = geo.a_localiser(self.base, [s["adresse"] for s in
                                               self.base.stages(self.aid, self.pfmp_id())])
        if not adresses:
            self._page()
            self._toast("Distances à jour")
            return
        if self.base.reglage_bool("geo_accepte"):
            self._lancer_geo(adresses)
            return

        def accepter():
            self.base.definir_reglage("geo_accepte", 1)
            self._lancer_geo(adresses)
        outils.confirmer(self, "Localiser les adresses ?",
                         "L'adresse de l'établissement et celles des lieux de stage sont envoyées au "
                         "service OpenStreetMap (Nominatim) pour être placées sur la carte. Aucun nom "
                         "d'élève n'est transmis, et chaque adresse n'est envoyée qu'une fois.",
                         "_Localiser", accepter, destructif=False)

    def _demander_etablissement(self):
        champ = Adw.EntryRow(title="Adresse de l'établissement", use_markup=False,
                             text=geo.etablissement(self.base))
        champ.set_activates_default(True)
        d = Adw.AlertDialog(heading="Point de départ",
                            body="Les distances sont calculées depuis l'établissement. "
                                 "Vous pourrez modifier cette adresse dans les préférences.")
        d.set_extra_child(_liste_boxed(champ))
        d.add_response("annuler", "_Annuler")
        d.add_response("ok", "_Enregistrer")
        d.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        d.set_default_response("ok")
        d.set_close_response("annuler")

        def rep(_d, r):
            if r == "ok" and champ.get_text().strip():
                self.base.definir_reglage(geo.REGLAGE_ETABLISSEMENT, champ.get_text().strip())
                self._distances()
        d.connect("response", rep)
        d.present(self)
        outils.focus_differe(champ)

    def _lancer_geo(self, adresses):
        self.bouton_distances.set_sensitive(False)
        self._toast(f"Localisation de {len(adresses)} adresse(s)… "
                    f"(environ {max(1, round(len(adresses) * geo.DELAI))} s)")

        def travail():
            res, err = geo.localiser_tout(adresses)
            GLib.idle_add(self._geo_fini, res, err)
        threading.Thread(target=travail, daemon=True).start()

    def _geo_fini(self, res, err):
        for adresse, coord in res.items():
            geo.memoriser(self.base, adresse, coord)
        self.bouton_distances.set_sensitive(True)
        introuvables = sum(1 for c in res.values() if c is None)
        if err is not None:
            self._toast(f"Réseau indisponible : {len(res)} adresse(s) traitée(s) avant l'erreur")
        elif introuvables:
            self._toast(f"{len(res) - introuvables} adresse(s) localisée(s), {introuvables} introuvable(s) : "
                        "vérifiez leur écriture (rue, code postal, ville)")
        else:
            self._toast(f"{len(res)} adresse(s) localisée(s)")
        self._page()
        return GLib.SOURCE_REMOVE

    def _retirer(self, s):
        self.base.maj_stage(s["eleve_id"], s["pfmp_id"], enseignant_id=None)
        self._remplir_ens()

    def _pfmp(self, groupe, _p):
        if groupe.get_active_name():
            for c in self.champs:
                c.vider_attente()
            self.numero = int(groupe.get_active_name())
            self._remplir_ens()

    def _ajouter_ens(self, r):
        if r.get_text().strip():
            self.ens_id = self.base.ajouter_enseignant(self.aid, r.get_text())
            r.set_text("")
            self._remplir_ens()

    def _choisir_eleves(self):
        stages = self.base.stages(self.aid, self.pfmp_id())
        noms = {e["id"]: e["nom"] for e in self.base.enseignants(self.aid)}
        d = Adw.Dialog(title="Ajouter des élèves", content_width=480, content_height=640)
        vue = Adw.ToolbarView()
        entete = Adw.HeaderBar(show_end_title_buttons=False, show_start_title_buttons=False)
        entete.pack_start(outils.bouton(libelle="_Annuler", clic=d.close))
        valider = outils.bouton(libelle="_Ajouter", classes=("suggested-action",))
        entete.pack_end(valider)
        vue.add_top_bar(entete)
        recherche = Gtk.SearchEntry(placeholder_text="Rechercher…", margin_start=12, margin_end=12,
                                    margin_top=6, margin_bottom=6)
        vue.add_top_bar(recherche)
        liste = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        liste.add_css_class("boxed-list")
        coches = {}
        for s in stages:
            if s["enseignant_id"] == self.ens_id:
                continue
            morceaux = [s["classe_nom"]]
            if s["entreprise"]:
                morceaux.append(s["entreprise"])
            if s["adresse"]:
                morceaux.append(s["adresse"])
            if s["enseignant_id"] in noms:
                morceaux.append(f"suivi par {noms[s['enseignant_id']]}")
            r = Adw.ActionRow(title=f"{s['nom']} {s['prenom']}", use_markup=False,
                              subtitle=" · ".join(morceaux))
            c = Gtk.CheckButton(valign=Gtk.Align.CENTER)
            r.add_prefix(c)
            r.set_activatable_widget(c)
            r.cle = normaliser(f"{s['nom']} {s['prenom']} {s['classe_nom']}")
            coches[s["eleve_id"]] = c
            liste.append(r)
        liste.set_filter_func(lambda r: all(m in r.cle for m in normaliser(recherche.get_text()).split()))
        recherche.connect("search-changed", lambda *_: liste.invalidate_filter())
        defil = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True)
        clamp = Adw.Clamp(margin_top=6, margin_bottom=18, margin_start=12, margin_end=12)
        clamp.set_child(liste)
        defil.set_child(clamp)
        vue.set_content(defil)
        d.set_child(vue)

        def ok():
            pid = self.pfmp_id()
            n = 0
            for eid, c in coches.items():
                if c.get_active():
                    self.base.maj_stage(eid, pid, enseignant_id=self.ens_id)
                    n += 1
            d.close()
            self._remplir_ens()
            if n:
                self.toasts.add_toast(Adw.Toast(title=f"{n} élève(s) ajouté(s)"))
        valider.connect("clicked", lambda *_: ok())
        d.present(outils.fenetre_parent(self))


from .vue_pfmp import ChampsEntreprise  # noqa: E402  (import tardif : évite un cycle)


# ==================================== import des commentaires des collègues

_TABLEURS = [("Tableurs (csv, xlsx, ods)", ["csv", "xlsx", "ods"],
              ["text/csv", "application/vnd.oasis.opendocument.spreadsheet",
               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"])]


def importer_commentaires(fen, classe_id, periode):
    def lu(chemin):
        try:
            lignes = tableur.lire(chemin)
        except tableur.ErreurTableur as e:
            outils.alerte(fen, "Import impossible", str(e))
            return
        if not lignes:
            outils.alerte(fen, "Import impossible", "Le fichier ne contient aucune donnée.")
            return
        analyse = tableur.analyser_commentaires(lignes)
        if not analyse["format"]:
            outils.alerte(fen, "Import impossible",
                          "Aucune discipline n'a été reconnue.\n\n"
                          "Deux dispositions sont acceptées :\n"
                          "• une colonne « Discipline » et une colonne « Commentaire » "
                          "(et éventuellement « Moyenne ») ;\n"
                          "• une colonne par discipline, par exemple « Mathématiques » ou "
                          "« Mathématiques (moyenne) ».")
            return
        DialogueImportCommentaires(fen, classe_id, periode, chemin, lignes, analyse).present(fen)
    outils.choisir_fichier(fen, "Importer les commentaires des collègues", _TABLEURS, lu)


class DialogueImportCommentaires(Adw.Dialog):
    def __init__(self, fen, classe_id, periode, chemin, lignes, analyse):
        super().__init__(title="Commentaires des collègues", content_width=640,
                         content_height=740)
        self.fen = fen
        self.base = fen.base
        self.classe_id = classe_id
        self.analyse = analyse
        self.lignes_fichier = lignes
        self.classe = self.base.classe(classe_id)

        vue = Adw.ToolbarView()
        entete = Adw.HeaderBar(show_end_title_buttons=False, show_start_title_buttons=False)
        entete.pack_start(outils.bouton(libelle="_Annuler", clic=self.close))
        self.bouton = outils.bouton(libelle="_Importer", classes=("suggested-action",),
                                    clic=self._importer)
        entete.pack_end(self.bouton)
        vue.add_top_bar(entete)
        page = Adw.PreferencesPage()

        g = Adw.PreferencesGroup(title="Fichier")
        g.add(Adw.ActionRow(title=Path(chemin).name,
                            subtitle=f"{len(lignes)} lignes · classe {self.classe['nom']}",
                            use_markup=False))
        g.add(Adw.ActionRow(title="Disposition reconnue",
                            subtitle="une ligne par élève et par discipline"
                                     if analyse["format"] == "long" else
                                     f"une colonne par discipline ({len(analyse['disciplines'])})"))
        page.add(g)

        pers = [libelle_periode(self.classe["decoupage"], p, True)
                for p in range(1, nb_periodes(self.classe["decoupage"]) + 1)]
        g = Adw.PreferencesGroup(title="Destination")
        self.c_per = Adw.ComboRow(title="Période", model=outils.liste_chaines(pers))
        self.c_per.set_selected(max(0, min(len(pers) - 1, (periode or 1) - 1)))
        g.add(self.c_per)
        page.add(g)

        g = Adw.PreferencesGroup(title="Options")
        self.creer = Adw.SwitchRow(title="Créer les disciplines manquantes", active=True)
        self.creer.connect("notify::active", lambda *_: self._apercu())
        g.add(self.creer)
        self.ajouter = Adw.SwitchRow(title="Ajouter les élèves absents de la classe", active=True)
        g.add(self.ajouter)
        self.calculer = Adw.SwitchRow(title="Calculer la moyenne générale",
                                      subtitle="Moyenne des notes de disciplines, si aucune n'est "
                                               "encore enregistrée pour la période", active=True)
        g.add(self.calculer)
        page.add(g)

        self.g_apercu = Adw.PreferencesGroup(title="Aperçu")
        self.lignes_apercu = []
        page.add(self.g_apercu)
        vue.set_content(page)
        self.set_child(vue)
        self._apercu()

    def _extraire(self):
        return tableur.extraire_commentaires(self.lignes_fichier, self.analyse)

    def _apercu(self):
        for r in self.lignes_apercu:
            self.g_apercu.remove(r)
        self.lignes_apercu = []
        res = self._extraire()
        disciplines = sorted({d for _, _, d, _, _ in res})
        commentaires = sum(1 for *_, c in res if c)
        notes = sum(1 for *_, n, _ in res if n is not None)
        self.g_apercu.set_description(
            f"{len(res)} appréciations · {len(disciplines)} discipline(s) · "
            f"{commentaires} commentaire(s) · {notes} note(s)")
        for nom, prenom, discipline, note, commentaire in res[:8]:
            r = Adw.ActionRow(title=f"{nom} {prenom}".strip(),
                              subtitle=_esc(f"{discipline} · {commentaire or '—'}"[:90]),
                              use_markup=True)
            lab = Gtk.Label(label=f"{note:.2f}".replace(".", ",") if note is not None else "—")
            lab.add_css_class("numeric")
            lab.set_valign(Gtk.Align.CENTER)
            r.add_suffix(lab)
            self.g_apercu.add(r)
            self.lignes_apercu.append(r)
        self.bouton.set_sensitive(bool(res))

    def _importer(self):
        res = self._extraire()
        bilan = self.base.importer_commentaires(
            self.classe_id, self.c_per.get_selected() + 1, res,
            ajouter_absents=self.ajouter.get_active(),
            creer_matieres=self.creer.get_active(),
            calculer_moyennes=self.calculer.get_active())
        morceaux = [f"{bilan['commentaires']} commentaire(s)"]
        if bilan["disciplines"]:
            morceaux.append(f"{bilan['disciplines']} discipline(s) créée(s)")
        if bilan["ajoutes"]:
            morceaux.append(f"{bilan['ajoutes']} élève(s) ajouté(s)")
        if bilan["notes"]:
            morceaux.append(f"{bilan['notes']} note(s)")
        if bilan["moyennes_generales"]:
            morceaux.append(f"{bilan['moyennes_generales']} moyenne(s) générale(s)")
        if bilan["ignores"]:
            morceaux.append(f"{len(bilan['ignores'])} ignoré(s)")
        self.close()
        self.fen.rafraichir()
        self.fen.toast("Import : " + " · ".join(morceaux))


# ============================================== toutes les commandes

class DialogueCommandes(Adw.Dialog):
    """Toutes les commandes de l'application, groupées par thème, classées par
    ordre alphabétique, avec un champ de recherche."""

    def __init__(self, fen):
        super().__init__(title="Toutes les commandes", content_width=680, content_height=780)
        self.fen = fen
        vue = Adw.ToolbarView()
        entete = Adw.HeaderBar(show_end_title_buttons=False, show_start_title_buttons=False)
        entete.pack_start(outils.bouton(libelle="_Fermer", clic=self.close))
        vue.add_top_bar(entete)

        self.recherche = Gtk.SearchEntry(placeholder_text="Rechercher une commande…",
                                         margin_start=12, margin_end=12, margin_top=6,
                                         margin_bottom=6)
        vue.add_top_bar(self.recherche)

        self.liste = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.liste.add_css_class("boxed-list")
        self.liste.set_header_func(self._entete)
        self.liste.set_filter_func(self._filtre)
        for theme, libelle, action, actif in self._commandes():
            r = Adw.ActionRow(title=libelle, activatable=actif, use_markup=False)
            r.theme = theme
            r.cle = normaliser(f"{theme} {libelle}")
            r.action = action
            if actif:
                r.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            else:
                r.set_sensitive(False)
            r.connect("activated", self._lancer)
            self.liste.append(r)
        self.recherche.connect("search-changed", lambda *_: self.liste.invalidate_filter())

        defil = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True)
        clamp = Adw.Clamp(maximum_size=620, margin_top=6, margin_bottom=18,
                          margin_start=12, margin_end=12)
        clamp.set_child(self.liste)
        defil.set_child(clamp)
        vue.set_content(defil)
        self.set_child(vue)

    def _commandes(self):
        f, a, p = self.fen, self.fen.vue_appr, self.fen.vue_pfmp
        modifiable = not f.lecture_seule()
        classe = a.classe is not None
        cmds = [
            ("Année scolaire", "Archiver l'année…", lambda: archiver_annee(f), modifiable),
            ("Année scolaire", "Désarchiver l'année", f.desarchiver, f.lecture_seule()),
            ("Année scolaire", "Nouvelle année scolaire…", lambda: nouvelle_annee(f), modifiable),
            ("Application", "À propos", lambda: f.activate_action("app.about", None), True),
            ("Application", "Préférences…", lambda: f.activate_action("app.preferences", None), True),
            ("Application", "Quitter", lambda: f.activate_action("app.quit", None), True),
            ("Appréciations", "Conseil de classe (plein écran)", a.ouvrir_conseil, classe),
            ("Appréciations", "Importer les commentaires des collègues…",
             a.importer_commentaires, modifiable and classe),
            ("Appréciations", "Importer un tableur (élèves, moyennes)…", a.importer,
             modifiable and classe),
            ("Appréciations", "Réglages de la classe…", a.reglages, modifiable and classe),
            ("Appréciations", "Récapitulatif ODS de l'année…", a.exporter_ods, classe),
            ("Appréciations", "Récapitulatif PDF de la période…", a.exporter_pdf, classe),
            ("Classes et élèves", "Nouvelle classe…", lambda: nouvelle_classe(f), modifiable),
            ("Données", "Exporter toutes les données (JSON)…", f.exporter_json, True),
            ("Données", "Importer des données (JSON)…", f.importer_json, modifiable),
            ("Données", "Tout exporter (tableurs)…", f.tout_exporter, True),
            ("PFMP", "Carnet d'entreprises…", f.ouvrir_carnet, True),
            ("PFMP", "Dates des PFMP…", p.dates, modifiable),
            ("PFMP", "Répartition des suivis…", p.repartition, True),
            ("PFMP", "Visites PFMP…", p.visites, True),
            ("Phrases", "Banque de phrases…", f.ouvrir_phrases, True),
        ]
        for c in f.base.classes(f.base.annee_active()):
            cmds.append(("Classes et élèves", f"Modifier la classe {c['nom']} (élèves, matières, réglages)…",
                         lambda cid=c["id"]: f.modifier_classe(cid), modifiable))
        # Par thème, puis par ordre alphabétique (sans tenir compte des accents)
        return sorted(cmds, key=lambda x: (normaliser(x[0]), normaliser(x[1])))

    def _lancer(self, row):
        self.close()
        row.action()

    @staticmethod
    def _entete(row, avant):
        if avant is None or avant.theme != row.theme:
            lab = Gtk.Label(label=row.theme, xalign=0, margin_start=8,
                            margin_top=14 if avant else 4, margin_bottom=4)
            lab.add_css_class("heading")
            row.set_header(lab)
        else:
            row.set_header(None)

    def _filtre(self, row):
        mots = normaliser(self.recherche.get_text()).split()
        return all(m in row.cle for m in mots)

