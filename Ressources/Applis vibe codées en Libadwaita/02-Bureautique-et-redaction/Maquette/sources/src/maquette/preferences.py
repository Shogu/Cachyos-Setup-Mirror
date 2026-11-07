"""Préférences de Maquette, liées directement à GSettings."""

import os

from gi.repository import Adw, Gio, GLib, GObject, Gtk


def _interrupteur(reglages, cle, titre, sous_titre=None):
    rangee = Adw.SwitchRow(title=titre, subtitle=sous_titre or "")
    reglages.bind(cle, rangee, "active", Gio.SettingsBindFlags.DEFAULT)
    return rangee


def _nombre(reglages, cle, titre, mini, maxi, pas, sous_titre=None, chiffres=0):
    rangee = Adw.SpinRow.new_with_range(mini, maxi, pas)
    rangee.set_title(titre)
    rangee.set_digits(chiffres)
    if sous_titre:
        rangee.set_subtitle(sous_titre)
    reglages.bind(cle, rangee, "value", Gio.SettingsBindFlags.DEFAULT)
    return rangee


def _choix(reglages, cle, titre, options, sous_titre=None):
    """options : [(pseudo de l'énumération, libellé)]."""
    pseudos = [p for p, _l in options]
    rangee = Adw.ComboRow(title=titre, subtitle=sous_titre or "",
                          model=Gtk.StringList.new([l for _p, l in options]))
    rangee.set_selected(pseudos.index(reglages.get_string(cle)))
    rangee.connect("notify::selected", lambda r, _p: reglages.set_string(cle, pseudos[r.get_selected()]))
    return rangee


def _dossier(reglages, cle, titre, choix):
    """Rangée de choix d'un dossier, active seulement si « Toujours le même »."""
    rangee = Adw.ActionRow(title=titre)
    bouton = Gtk.Button(valign=Gtk.Align.CENTER, tooltip_text="Choisir un dossier")
    contenu = Adw.ButtonContent(icon_name="folder-symbolic")
    bouton.set_child(contenu)

    def montrer(chemin):
        contenu.set_label(os.path.basename(chemin.rstrip("/")) or chemin if chemin else "Choisir…")
        rangee.set_subtitle(chemin or "Aucun dossier choisi")
    montrer(reglages.get_string(cle))

    def choisir(_b):
        dialogue = Gtk.FileDialog(title="Dossier d'enregistrement", modal=True)
        depart = reglages.get_string(cle)
        if depart and os.path.isdir(depart):
            dialogue.set_initial_folder(Gio.File.new_for_path(depart))

        def choisi(d, resultat):
            try:
                fichier = d.select_folder_finish(resultat)
            except GLib.Error:
                return
            reglages.set_string(cle, fichier.get_path())
            montrer(fichier.get_path())
        dialogue.select_folder(rangee.get_root(), None, choisi)
    bouton.connect("clicked", choisir)
    rangee.add_suffix(bouton)
    rangee.set_activatable_widget(bouton)
    choix.bind_property("selected", rangee, "sensitive", GObject.BindingFlags.SYNC_CREATE,
                        lambda _b, v: v == 2)
    return rangee


def _groupe(page, titre, rangees, description=None):
    groupe = Adw.PreferencesGroup(title=titre, description=description or "")
    for rangee in rangees:
        groupe.add(rangee)
    page.add(groupe)
    return groupe


class Preferences(Adw.PreferencesDialog):
    __gtype_name__ = "MaquettePreferences"

    def __init__(self, reglages: Gio.Settings):
        super().__init__(search_enabled=False)
        r = reglages

        general = Adw.PreferencesPage(title="Général", icon_name="preferences-system-symbolic")
        suffixe = Adw.EntryRow(title="Suffixe du nom proposé")
        r.bind("suffixe-nom", suffixe, "text", Gio.SettingsBindFlags.DEFAULT)
        choix_dossier = _choix(r, "dossier-propose", "Dossier proposé",
                               [("source", "Dossier du premier fichier"),
                                ("dernier", "Dernier dossier utilisé"),
                                ("fixe", "Toujours le même dossier")])
        _groupe(general, "Fichier proposé à l'enregistrement", [
            choix_dossier,
            _dossier(r, "dossier-fixe", "Mon dossier", choix_dossier),
            suffixe,
            _interrupteur(r, "ouvrir-apres", "Ouvrir le fichier après l'enregistrement"),
        ], "Le nom proposé est celui du premier fichier suivi du suffixe, par exemple « cours-maquette.pdf ».")
        _groupe(general, "Grille des pages", [
            _nombre(r, "taille-miniatures", "Taille des miniatures", 96, 400, 8, "En pixels ; aussi Ctrl + molette"),
            _interrupteur(r, "numeros", "Numéros de page"),
            _interrupteur(r, "couleur-source", "Couleur du fichier d'origine",
                          "Fine bande colorée sous chaque page, utile après une fusion"),
        ])
        _groupe(general, "Fermeture", [
            _interrupteur(r, "confirmer-fermeture", "Demander avant de fermer un document modifié"),
        ])
        self.add(general)

        insertion = Adw.PreferencesPage(title="Insertion", icon_name="list-add-symbolic")
        _groupe(insertion, "Pages blanches", [
            _choix(r, "format-page-blanche", "Format",
                   [("voisine", "Comme la page voisine"), ("a4-portrait", "A4 portrait"), ("a4-paysage", "A4 paysage"),
                    ("a3-portrait", "A3 portrait"), ("a3-paysage", "A3 paysage")]),
        ])
        mode = _choix(r, "images-mode", "Mise en page",
                      [("ajustee", "Ajustée dans les marges"), ("pleine", "Pleine page")])
        marges_images = _nombre(r, "images-marges", "Marges", 0, 50, 1, "En millimètres")
        mode.bind_property("selected", marges_images, "sensitive", GObject.BindingFlags.SYNC_CREATE,
                           lambda _b, choix: choix == 0)
        _groupe(insertion, "Images", [
            mode, marges_images,
            _interrupteur(r, "images-orientation-auto", "Orientation automatique",
                          "Paysage pour les images plus larges que hautes"),
            _interrupteur(r, "images-demander", "Demander à chaque insertion"),
        ], "Une image par page A4 (PNG, JPG, WebP, GIF, TIFF, AVIF, HEIC…).")
        _groupe(insertion, "Texte posé sur une page", [
            _nombre(r, "texte-taille", "Corps du texte", 6, 48, 1, "En points", chiffres=0),
        ], "Le corps est réduit automatiquement si le texte déborde de son cadre.")
        self.add(insertion)

        enregistrement = Adw.PreferencesPage(title="Enregistrement", icon_name="document-save-symbolic")
        dpi = _nombre(r, "dpi-images", "Résolution maximale", 72, 300, 10, "En points par pouce (ppp)")
        r.bind("reduire-images", dpi, "sensitive", Gio.SettingsBindFlags.GET)
        reduire = _interrupteur(r, "reduire-images", "Réduire la résolution des images",
                                "Fichier bien plus léger, au prix d'une perte de qualité")
        r.bind("compresser", reduire, "sensitive", Gio.SettingsBindFlags.GET)
        _groupe(enregistrement, "Optimisation", [
            _interrupteur(r, "compresser", "Compresser et alléger",
                          "Retire les objets inutiles et compresse, sans perte de qualité"),
            reduire, dpi,
        ])
        _groupe(enregistrement, "Mise en page", [
            _choix(r, "imposition", "Disposition des pages",
                   [("fidele", "Assemblage fidèle"), ("brochure-a5", "Brochure A5 sur A4"),
                    ("livret-a4", "Livret A4 sur A3")]),
        ], "La brochure et le livret placent deux pages par face, dans l'ordre d'impression "
           "recto verso, pour plier et agrafer au centre.")
        _groupe(enregistrement, "Confidentialité", [
            _interrupteur(r, "effacer-metadonnees", "Effacer les métadonnées",
                          "Titre, auteur, sujet et mots-clés du document d'origine"),
        ])
        self.add(enregistrement)
