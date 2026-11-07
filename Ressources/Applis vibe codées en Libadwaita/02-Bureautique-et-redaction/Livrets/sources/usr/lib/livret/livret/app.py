"""Point d'entrée de Livret."""

from __future__ import annotations

import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from . import APP_ID, VERSION  # noqa: E402
from .db import Base, dossier_donnees  # noqa: E402

ICI = Path(__file__).resolve().parent


def journal_erreurs() -> Path:
    return dossier_donnees() / "journal-erreurs.log"


def _installer_journal():
    """Écrit toute exception non rattrapée dans un fichier lisible.

    Une exception levée dans un gestionnaire de signal GTK n'apparaît nulle
    part dans l'interface : sans ce journal, un bouton qui « ne fait rien »
    ne laisse aucune trace exploitable."""
    def ecrire(type_, valeur, trace):
        try:
            chemin = journal_erreurs()
            chemin.parent.mkdir(parents=True, exist_ok=True)
            with open(chemin, "a", encoding="utf-8") as f:
                f.write(f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S} =====\n")
                traceback.print_exception(type_, valeur, trace, file=f)
        except OSError:
            pass
        traceback.print_exception(type_, valeur, trace)

    sys.excepthook = ecrire
    threading.excepthook = lambda a: ecrire(a.exc_type, a.exc_value, a.exc_traceback)



def _chercher_icones():
    """Icônes symboliques propres à Livret, installées à côté du module."""
    for d in (ICI.parent / "icons",                       # paquet installé
              ICI.parent / "data" / "icons" / "actions",   # arborescence des sources
              ICI.parent / "data" / "icons" / "app"):
        if d.is_dir():
            yield str(d)


class Application(Adw.Application):
    def __init__(self):
        # Avant tout widget : le nom de programme sert d'identifiant de fenêtre
        # (WM_CLASS sous X11) pour rattacher la fenêtre à son fichier .desktop.
        GLib.set_prgname(APP_ID)
        GLib.set_application_name("Livret")
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.base = None
        self.fen = None
        for nom, f, touches in (("preferences", self._preferences, ["<Control>comma"]),
                                ("about", self._a_propos, []),
                                ("journal", self._journal, []),
                                ("quit", lambda: self.quit(), ["<Control>q"])):
            a = Gio.SimpleAction.new(nom, None)
            a.connect("activate", lambda _a, _p, f=f: f())
            self.add_action(a)
            if touches:
                self.set_accels_for_action(f"app.{nom}", touches)
        self.set_accels_for_action("window.close", ["<Control>w"])

    def do_startup(self):
        Adw.Application.do_startup(self)
        ecran = Gdk.Display.get_default()
        css = Gtk.CssProvider()
        css.load_from_path(str(ICI / "style.css"))
        Gtk.StyleContext.add_provider_for_display(ecran, css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        theme = Gtk.IconTheme.get_for_display(ecran)
        for d in _chercher_icones():
            theme.add_search_path(d)
        self.base = Base()
        try:
            self.base.sauvegarder("auto")
        except OSError as e:
            print(f"Livret : sauvegarde de démarrage impossible : {e}", file=sys.stderr)

    def do_activate(self):
        if self.fen is None:
            from .fenetre import FenetrePrincipale
            self.fen = FenetrePrincipale(self, self.base)
        self.fen.present()

    def do_shutdown(self):
        if self.fen is not None:
            self.fen.vider_attente()
        if self.base is not None:
            self.base.fermer()
        Adw.Application.do_shutdown(self)

    def _preferences(self):
        if self.fen:
            from .dialogues import Preferences
            Preferences(self.fen).present(self.fen)

    def _journal(self):
        from . import outils
        chemin = journal_erreurs()
        if not chemin.exists():
            if self.fen:
                self.fen.toast("Aucune erreur enregistrée")
            return
        outils.ouvrir_chemin(self.fen, chemin)

    def _a_propos(self):
        d = Adw.AboutDialog(
            application_name="Livret",
            application_icon=APP_ID,
            version=VERSION,
            developer_name="Shogu",
            comments="Appréciations de conseil de classe et suivi des PFMP. "
                     "Toutes les données restent sur cet ordinateur.",
            license_type=Gtk.License.GPL_3_0,
        )
        d.present(self.fen)


def main(argv=None):
    _installer_journal()
    return Application().run(argv if argv is not None else sys.argv)
