"""Application : fenêtres, actions globales, raccourcis."""

import os
import sys

from . import VERSION
from gi.repository import Adw, Gdk, Gio, Gtk

from .fenetre import FenetreMaquette
from .moteur import Moteur
from .preferences import Preferences
from .reglages import ID_APPLI

DOSSIER = os.path.dirname(os.path.abspath(__file__))
# Lancée depuis les sources, l'appli trouve ses icônes dans data/ ; installée,
# elles sont dans /usr/share/icons/hicolor que GTK consulte déjà.
ICONES_SOURCES = os.path.join(os.path.dirname(DOSSIER), "data", "icons")

RACCOURCIS = {
    "win.inserer-fichiers": ["<Control>o"],
    "win.page-blanche": ["<Control>b"],
    "win.enregistrer": ["<Control>s", "<Control><Shift>s"],
    "win.apercu": ["<Control>p"],
    "win.extraire": ["<Control>e"],
    "win.annuler": ["<Control>z"],
    "win.refaire": ["<Control><Shift>z", "<Control>y"],
    "win.pivoter-gauche": ["<Control>Left"],
    "win.pivoter-droite": ["<Control>Right"],
    "win.tout-selectionner": ["<Control>a"],
    "win.recadrer": ["<Control>r"],
    "win.texte": ["<Control>t"],
    "win.zoom-plus": ["<Control>plus", "<Control>equal", "<Control>KP_Add"],
    "win.zoom-moins": ["<Control>minus", "<Control>KP_Subtract"],
    "win.fermer": ["<Control>w"],
    "app.nouvelle-fenetre": ["<Control>n"],
    "app.preferences": ["<Control>comma"],
    "app.raccourcis": ["<Control>question"],
    "app.quitter": ["<Control>q"],
}

AIDE_RACCOURCIS = (
    ("Document", (
        ("Insérer des fichiers", "<Control>o"),
        ("Insérer une page blanche", "<Control>b"),
        ("Enregistrer sous", "<Control>s"),
        ("Aperçu du résultat", "<Control>p"),
        ("Extraire la sélection", "<Control>e"),
        ("Annuler", "<Control>z"),
        ("Rétablir", "<Control><Shift>z"),
    )),
    ("Pages", (
        ("Tout sélectionner", "<Control>a"),
        ("Supprimer la sélection", "Delete"),
        ("Pivoter à gauche", "<Control>Left"),
        ("Pivoter à droite", "<Control>Right"),
        ("Afficher en grand", "Return"),
        ("Recadrer", "<Control>r"),
        ("Écrire sur la page", "<Control>t"),
        ("Agrandir ou réduire les miniatures", "<Control>plus <Control>minus"),
    )),
    ("Page en grand", (
        ("Recadrer", "<Control>r"),
        ("Écrire sur la page", "<Control>t"),
        ("Page précédente", "Left"),
        ("Page suivante", "Right"),
        ("Revenir à la grille", "Escape"),
    )),
    ("Général", (
        ("Nouvelle fenêtre", "<Control>n"),
        ("Préférences", "<Control>comma"),
        ("Fermer la fenêtre", "<Control>w"),
        ("Quitter", "<Control>q"),
    )),
)


class Application(Adw.Application):
    __gtype_name__ = "MaquetteApplication"

    def __init__(self):
        super().__init__(application_id=ID_APPLI, flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.moteur = None

    def do_startup(self):
        Adw.Application.do_startup(self)
        self.moteur = Moteur()
        affichage = Gdk.Display.get_default()
        style = Gtk.CssProvider()
        style.load_from_path(os.path.join(DOSSIER, "style.css"))
        Gtk.StyleContext.add_provider_for_display(affichage, style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        if os.path.isdir(ICONES_SOURCES):
            Gtk.IconTheme.get_for_display(affichage).add_search_path(ICONES_SOURCES)

        for nom, rappel in (("nouvelle-fenetre", lambda *_: self._nouvelle_fenetre().present()),
                            ("preferences", lambda *_: self._preferences()),
                            ("raccourcis", lambda *_: self._raccourcis()),
                            ("a-propos", lambda *_: self._a_propos()),
                            ("quitter", lambda *_: self._quitter())):
            action = Gio.SimpleAction.new(nom, None)
            action.connect("activate", rappel)
            self.add_action(action)
        for action, touches in RACCOURCIS.items():
            self.set_accels_for_action(action, touches)

    def do_activate(self):
        (self.get_active_window() or self._nouvelle_fenetre()).present()

    def do_open(self, fichiers, _n, _indice):
        fenetre = self.get_active_window()
        if fenetre is None or fenetre.pages:
            fenetre = self._nouvelle_fenetre()
        fenetre.present()
        fenetre.ajouter_fichiers(list(fichiers))

    def _nouvelle_fenetre(self):
        return FenetreMaquette(self, self.moteur)

    def _preferences(self):
        fenetre = self.get_active_window()
        Preferences(fenetre.reglages).present(fenetre)

    def _raccourcis(self):
        dialogue = Adw.ShortcutsDialog()
        for titre, entrees in AIDE_RACCOURCIS:
            section = Adw.ShortcutsSection(title=titre)
            for libelle, touches in entrees:
                section.add(Adw.ShortcutsItem.new(libelle, touches))
            dialogue.add(section)
        dialogue.present(self.get_active_window())

    def _a_propos(self):
        Adw.AboutDialog(
            application_name="Maquette", application_icon=ID_APPLI, version=VERSION, developer_name="Shogu",
            comments="Assembler et préparer des documents PDF : fusionner, réordonner, pivoter, "
                     "recadrer, écrire sur une page, insérer des images, composer des livrets.",
            license_type=Gtk.License.AGPL_3_0,
        ).present(self.get_active_window())

    def _quitter(self):
        for fenetre in list(self.get_windows()):
            fenetre.close()


def main(argv=None):
    return Application().run(sys.argv if argv is None else argv)
