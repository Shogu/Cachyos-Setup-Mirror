"""Mode « conseil de classe » : plein écran, lecture, saisie de la décision."""

from __future__ import annotations

from gi.repository import Adw, Gtk

from . import outils
from .db import DECISIONS, format_nombre, libelle_periode, nom_complet


class PageEleve(Gtk.ScrolledWindow):
    def __init__(self, fen, classe, eleve, periode, matieres, moyennes, lecture_seule):
        super().__init__(hscrollbar_policy=Gtk.PolicyType.NEVER, hexpand=True, vexpand=True)
        self.fen = fen
        self.base = fen.base
        self.eleve = eleve
        self.periode = periode
        self.retard = outils.retarder(600)
        dec = classe["decoupage"]
        bilans = self.base.bilans_eleve(eleve["id"])
        b = bilans.get(periode)
        appr = self.base.appreciations_eleve(eleve["id"])

        clamp = Adw.Clamp(maximum_size=1280, tightening_threshold=900)
        boite = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24,
                        margin_top=24, margin_bottom=36, margin_start=32, margin_end=32)

        # Entête : identité et moyennes
        entete = Gtk.Box(spacing=20)
        av = Adw.Avatar(size=88, show_initials=True, text=f"{eleve['prenom']} {eleve['nom']}")
        entete.append(av)
        noms = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER, hexpand=True)
        nom = Gtk.Label(label=nom_complet(eleve), xalign=0, wrap=True)
        nom.add_css_class("conseil-nom")
        noms.append(nom)
        etat = self.base.etat_eleve(eleve["id"], periode, [m["id"] for m in matieres])
        sous = Gtk.Label(xalign=0, label={"vide": "Aucune appréciation saisie",
                                          "brouillon": "Saisie incomplète",
                                          "termine": "Saisie terminée"}[etat])
        sous.add_css_class("dim-label")
        noms.append(sous)
        entete.append(noms)
        moys = moyennes.get(eleve["id"], {})
        bloc_moy = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER)
        m = Gtk.Label(label=format_nombre(moys.get(periode)), xalign=1)
        m.add_css_class("conseil-moyenne")
        bloc_moy.append(m)
        c = Gtk.Label(xalign=1, label=f"{libelle_periode(dec, periode)} · cumul annuel "
                                       f"{format_nombre(self.base.moyenne_cumulee(moys, periode))}")
        c.add_css_class("dim-label")
        c.add_css_class("numeric")
        bloc_moy.append(c)
        entete.append(bloc_moy)
        boite.append(entete)

        colonnes = Gtk.Box(spacing=28)
        gauche = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, hexpand=True)
        droite = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        droite.set_size_request(360, -1)

        # Bilan
        gauche.append(outils.titre_section("Bilan général"))
        lab = Gtk.Label(label=(b["texte"] if b and b["texte"].strip() else "—"), xalign=0, wrap=True,
                        selectable=True)
        lab.add_css_class("conseil-texte")
        cadre = Gtk.Box()
        cadre.add_css_class("card")
        lab.set_margin_top(14)
        lab.set_margin_bottom(14)
        lab.set_margin_start(16)
        lab.set_margin_end(16)
        cadre.append(lab)
        gauche.append(cadre)

        # Appréciations par matière
        gauche.append(outils.titre_section("Appréciations"))
        flux = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, homogeneous=True,
                           max_children_per_line=2, min_children_per_line=1,
                           column_spacing=12, row_spacing=12)
        for mat in matieres:
            a = appr.get((mat["id"], periode))
            carte = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            carte.add_css_class("card")
            carte.add_css_class("conseil-matiere")
            t = Gtk.Label(label=mat["nom"], xalign=0)
            t.add_css_class("heading")
            carte.append(t)
            txt = Gtk.Label(label=a["texte"] if a and a["texte"].strip() else "—", xalign=0, wrap=True,
                            selectable=True)
            txt.add_css_class("texte")
            carte.append(txt)
            flux.append(carte)
        if not matieres:
            vide = Gtk.Label(label="Aucune matière", xalign=0)
            vide.add_css_class("dim-label")
            gauche.append(vide)
        else:
            gauche.append(flux)

        # Décision
        groupe = Adw.PreferencesGroup(title="Décision du conseil")
        self.decision = Adw.ComboRow(title="Décision", model=outils.liste_chaines(DECISIONS))
        actuelle = b["decision"] if b and b["decision"] in DECISIONS else "Aucune"
        self.decision.set_selected(DECISIONS.index(actuelle))
        self.decision.connect("notify::selected", self._decision)
        groupe.add(self.decision)
        self.note = Adw.EntryRow(title="Remarque du conseil", text=(b["decision_note"] if b else "") or "")
        self.note.connect("changed", lambda *_: self.retard.planifier(self._note))
        groupe.add(self.note)
        groupe.set_sensitive(not lecture_seule)
        droite.append(groupe)
        anciennes = [(p, bilans[p]) for p in range(1, periode)
                     if p in bilans and bilans[p]["decision"] and bilans[p]["decision"] != "Aucune"]
        if anciennes:
            g = Adw.PreferencesGroup(title="Décisions précédentes")
            for p, bp in anciennes:
                r = Adw.ActionRow(title=bp["decision"], subtitle=libelle_periode(dec, p, True),
                                  use_markup=False)
                g.add(r)
            droite.append(g)

        colonnes.append(gauche)
        colonnes.append(droite)
        boite.append(colonnes)
        clamp.set_child(boite)
        self.set_child(clamp)

    def _decision(self, row, _p):
        self.base.enregistrer_bilan(self.eleve["id"], self.periode,
                                    decision=DECISIONS[row.get_selected()])

    def _note(self):
        self.base.enregistrer_bilan(self.eleve["id"], self.periode, decision_note=self.note.get_text())

    def vider_attente(self):
        self.retard.vider()


class FenetreConseil(Adw.Window):
    def __init__(self, fen, classe_id, periode, eleve_id=None):
        super().__init__(transient_for=fen, modal=False, default_width=1200, default_height=800)
        self.fen = fen
        base = fen.base
        classe = base.classe(classe_id)
        self.set_title(f"Conseil de classe — {classe['nom']}")
        eleves = base.eleves(classe_id)
        matieres = base.matieres(classe_id)
        moyennes = base.moyennes_classe(classe_id)
        ro = fen.lecture_seule()

        vue = Adw.ToolbarView(top_bar_style=Adw.ToolbarStyle.RAISED)
        entete = Adw.HeaderBar(show_end_title_buttons=False)
        self.titre = Adw.WindowTitle(title=f"Conseil de classe — {classe['nom']}",
                                     subtitle=libelle_periode(classe["decoupage"], periode, True))
        entete.set_title_widget(self.titre)
        nav = Gtk.Box()
        nav.add_css_class("linked")
        nav.append(outils.bouton("go-previous-symbolic", infobulle="Élève précédent (Page précédente)",
                                 clic=lambda: self._aller(-1)))
        nav.append(outils.bouton("go-next-symbolic", infobulle="Élève suivant (Page suivante)",
                                 clic=lambda: self._aller(1)))
        entete.pack_start(nav)
        self.position = Gtk.Label()
        self.position.add_css_class("numeric")
        entete.pack_start(self.position)
        entete.pack_end(outils.bouton("view-restore-symbolic", "_Quitter le mode conseil",
                                      "Quitter (Échap)", clic=self.close))
        vue.add_top_bar(entete)

        self.carrousel = Adw.Carousel(allow_scroll_wheel=False, allow_long_swipes=False,
                                      hexpand=True, vexpand=True)
        self.pages = []
        for e in eleves:
            p = PageEleve(fen, classe, e, periode, matieres, moyennes, ro)
            self.pages.append(p)
            self.carrousel.append(p)
        self.carrousel.connect("page-changed", lambda *_: self._maj_position())
        if eleves:
            vue.set_content(self.carrousel)
            points = Adw.CarouselIndicatorLines(carousel=self.carrousel, margin_bottom=8)
            vue.add_bottom_bar(points)
        else:
            vue.set_content(Adw.StatusPage(icon_name="system-users-symbolic", title="Aucun élève"))
        self.set_content(vue)

        raccourcis = Gtk.ShortcutController(scope=Gtk.ShortcutScope.MANAGED)
        for touches, f in (("Page_Down", lambda *_: self._aller(1)),
                           ("Page_Up", lambda *_: self._aller(-1)),
                           ("<Alt>Right", lambda *_: self._aller(1)),
                           ("<Alt>Left", lambda *_: self._aller(-1)),
                           ("Escape", lambda *_: self.close())):
            raccourcis.add_shortcut(Gtk.Shortcut(trigger=Gtk.ShortcutTrigger.parse_string(touches),
                                                 action=Gtk.CallbackAction.new(self._rappel(f))))
        self.add_controller(raccourcis)
        self.connect("close-request", self._fermeture)
        self.fullscreen()
        if eleve_id is not None:
            for i, e in enumerate(eleves):
                if e["id"] == eleve_id:
                    self.connect("map", lambda *_ , i=i: self.carrousel.scroll_to(self.pages[i], False))
                    break
        self._maj_position()

    @staticmethod
    def _rappel(f):
        def cb(*_):
            f()
            return True
        return cb

    def _index(self):
        return round(self.carrousel.get_position()) if self.pages else 0

    def _aller(self, delta):
        if not self.pages:
            return
        i = max(0, min(len(self.pages) - 1, self._index() + delta))
        self.pages[self._index()].vider_attente()
        self.carrousel.scroll_to(self.pages[i], True)

    def _maj_position(self):
        n = len(self.pages)
        self.position.set_text(f"{self._index() + 1} / {n}" if n else "")

    def _fermeture(self, *_):
        for p in self.pages:
            p.vider_attente()
        self.fen.rafraichir()
        return False
