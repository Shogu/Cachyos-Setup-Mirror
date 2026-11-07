"""Petits utilitaires d'interface partagés."""

from __future__ import annotations

import urllib.parse

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

ID_CARTES = "org.gnome.Maps.desktop"


# ------------------------------------------------------------------ textes

def copier(widget: Gtk.Widget, texte: str) -> bool:
    if not texte:
        return False
    widget.get_clipboard().set_content(Gdk.ContentProvider.new_for_value(texte))
    return True


def retarder(attente_ms: int):
    """Appelle une fonction après un délai ; un nouvel appel annule le précédent."""
    class _Retard:
        def __init__(self):
            self.source = 0
            self.fonction = None

        def planifier(self, fonction):
            self.annuler()
            self.fonction = fonction
            self.source = GLib.timeout_add(attente_ms, self._tick)

        def _tick(self):
            self.source = 0
            f, self.fonction = self.fonction, None
            if f:
                f()
            return GLib.SOURCE_REMOVE

        def annuler(self):
            if self.source:
                GLib.source_remove(self.source)
                self.source = 0
            self.fonction = None

        def vider(self):
            """Exécute tout de suite l'appel en attente."""
            if self.source:
                GLib.source_remove(self.source)
                self.source = 0
                f, self.fonction = self.fonction, None
                if f:
                    f()

    return _Retard()


# --------------------------------------------------------------- widgets

def focus_differe(widget: Gtk.Widget):
    """Donne le focus au widget une seule fois, dès que la boucle GTK est libre.

    Piège : GLib.idle_add(widget.grab_focus) rappelle grab_focus() tant qu'il
    renvoie True, c'est-à-dire en boucle. Un champ texte qui reprend le focus
    resélectionne tout son contenu : chaque frappe remplace la précédente et
    on ne peut saisir qu'un seul caractère."""
    def une_fois():
        widget.grab_focus()
        return GLib.SOURCE_REMOVE
    GLib.idle_add(une_fois)


def bouton(icone: str | None = None, libelle: str | None = None, infobulle: str | None = None,
           classes=(), clic=None) -> Gtk.Button:
    b = Gtk.Button(valign=Gtk.Align.CENTER)
    if icone and libelle:
        b.set_child(Adw.ButtonContent(icon_name=icone, label=libelle, use_underline=True))
    elif icone:
        b.set_icon_name(icone)
    else:
        b.set_label(libelle or "")
    if infobulle:
        b.set_tooltip_text(infobulle)
    for c in classes:
        b.add_css_class(c)
    if clic:
        b.connect("clicked", lambda *_: clic())
    return b


def pastille(etat: str = "vide") -> Gtk.Widget:
    p = Gtk.Box(valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER)
    p.add_css_class("pastille")
    definir_pastille(p, etat)
    return p


LIBELLES_ETAT = {"vide": "Vide", "brouillon": "Brouillon", "termine": "Terminé"}


def definir_pastille(p: Gtk.Widget, etat: str):
    for e in LIBELLES_ETAT:
        p.remove_css_class(e)
    p.add_css_class(etat)
    p.set_tooltip_text(LIBELLES_ETAT.get(etat, etat))
    p.update_property([Gtk.AccessibleProperty.LABEL], [LIBELLES_ETAT.get(etat, etat)])


def vider(conteneur):
    """Retire tous les enfants d'une Gtk.Box / Gtk.ListBox / Gtk.FlowBox."""
    if isinstance(conteneur, (Gtk.ListBox, Gtk.FlowBox)):
        conteneur.remove_all()
        return
    enfant = conteneur.get_first_child()
    while enfant:
        suivant = enfant.get_next_sibling()
        conteneur.remove(enfant)
        enfant = suivant


def liste_chaines(chaines) -> Gtk.StringList:
    return Gtk.StringList.new(list(chaines))


def titre_section(texte: str) -> Gtk.Label:
    l = Gtk.Label(label=texte, xalign=0)
    l.add_css_class("heading")
    return l


# ----------------------------------------------------------- dialogues

def alerte(parent, titre, corps="", ok="Fermer"):
    d = Adw.AlertDialog(heading=titre, body=corps)
    d.add_response("ok", ok)
    d.present(fenetre_parent(parent))
    return d


def confirmer(parent, titre, corps, libelle, action, destructif=True, extra=None):
    d = Adw.AlertDialog(heading=titre, body=corps)
    d.add_response("annuler", "_Annuler")
    d.add_response("ok", libelle)
    d.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE if destructif
                              else Adw.ResponseAppearance.SUGGESTED)
    d.set_default_response("annuler" if destructif else "ok")
    d.set_close_response("annuler")
    if extra:
        d.set_extra_child(extra)

    def reponse(_d, r):
        if r == "ok":
            action()
    d.connect("response", reponse)
    d.present(fenetre_parent(parent))
    return d


def module_exports(parent):
    """Importe le module d'export en montrant l'erreur si une dépendance manque.

    L'import se fait ici, et non au début du gestionnaire de clic : si
    python-cairo ou PangoCairo manque, l'échec se produisait dans le
    gestionnaire, où GTK l'avale — le bouton semblait alors ne rien faire."""
    try:
        from . import exports
        return exports
    except Exception as e:  # noqa: BLE001 — dépendance absente ou cassée
        alerte(parent, "Export impossible",
               f"Le module d'export n'a pas pu être chargé :\n{e}")
        return None


def fenetre_parent(parent):
    """Gtk.FileDialog veut une Gtk.Window comme parent. Un Adw.Dialog ou une
    Adw.PreferencesDialog n'en est pas une : on remonte à la fenêtre racine,
    sinon None (le sélecteur s'ouvre sans parent). Sans cela, le sélecteur ne
    s'ouvrait pas du tout depuis ces dialogues."""
    if isinstance(parent, Gtk.Window):
        return parent
    racine = parent.get_root() if isinstance(parent, Gtk.Widget) else None
    return racine if isinstance(racine, Gtk.Window) else None


def _filtre(nom, motifs=(), types=()):
    f = Gtk.FileFilter(name=nom)
    for m in motifs:
        f.add_suffix(m)
    for t in types:
        f.add_mime_type(t)
    return f


def filtres(*specs):
    store = Gio.ListStore.new(Gtk.FileFilter)
    for s in specs:
        store.append(_filtre(*s))
    return store


def choisir_fichier(parent, titre, specs, rappel):
    d = Gtk.FileDialog(title=titre, modal=True)
    if specs:
        d.set_filters(filtres(*specs))

    def fini(dlg, res):
        try:
            f = dlg.open_finish(res)
        except GLib.Error:
            return
        if f and f.get_path():
            rappel(f.get_path())
    d.open(fenetre_parent(parent), None, fini)


def enregistrer_fichier(parent, titre, nom_initial, specs, rappel):
    d = Gtk.FileDialog(title=titre, modal=True, initial_name=nom_initial)
    if specs:
        d.set_filters(filtres(*specs))

    def fini(dlg, res):
        try:
            f = dlg.save_finish(res)
        except GLib.Error:
            return
        if f and f.get_path():
            rappel(f.get_path())
    d.save(fenetre_parent(parent), None, fini)


def choisir_dossier(parent, titre, rappel):
    d = Gtk.FileDialog(title=titre, modal=True)

    def fini(dlg, res):
        try:
            f = dlg.select_folder_finish(res)
        except GLib.Error:
            return
        if f and f.get_path():
            rappel(f.get_path())
    d.select_folder(fenetre_parent(parent), None, fini)


def ouvrir_chemin(parent, chemin):
    """Ouvre un fichier ou un dossier avec l'application par défaut."""
    lanceur = Gtk.FileLauncher.new(Gio.File.new_for_path(str(chemin)))

    def fini(l, res):
        try:
            l.launch_finish(res)
        except GLib.Error:
            pass
    lanceur.launch(fenetre_parent(parent), None, fini)


def montrer_dans_dossier(parent, chemin):
    lanceur = Gtk.FileLauncher.new(Gio.File.new_for_path(str(chemin)))

    def fini(l, res):
        try:
            l.open_containing_folder_finish(res)
        except GLib.Error:
            pass
    lanceur.open_containing_folder(fenetre_parent(parent), None, fini)


# ------------------------------------------------------------- itinéraire

def cartes_installe() -> bool:
    try:
        return Gio.DesktopAppInfo.new(ID_CARTES) is not None
    except TypeError:
        return False


def ouvrir_itineraire(parent: Gtk.Widget, adresse: str):
    """GNOME Cartes s'il est installé (dépendance optionnelle gnome-maps),
    sinon OpenStreetMap dans le navigateur par défaut."""
    adresse = " ".join((adresse or "").split())
    if not adresse:
        return
    requete = urllib.parse.quote(adresse, safe="")
    try:
        info = Gio.DesktopAppInfo.new(ID_CARTES)
    except TypeError:
        info = None
    if info is not None:
        contexte = parent.get_display().get_app_launch_context()
        try:
            if info.launch_uris([f"maps:q={requete}"], contexte):
                return
        except GLib.Error:
            pass
    lanceur = Gtk.UriLauncher.new(f"https://www.openstreetmap.org/search?query={requete}")

    def fini(l, res):
        try:
            l.launch_finish(res)
        except GLib.Error:
            pass
    racine = parent.get_root() if isinstance(parent, Gtk.Widget) else parent
    lanceur.launch(racine if isinstance(racine, Gtk.Window) else None, None, fini)
