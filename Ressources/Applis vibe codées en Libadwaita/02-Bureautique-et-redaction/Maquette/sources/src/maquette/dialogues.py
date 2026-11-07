"""Petits dialogues : mot de passe, mise en page des images, confirmations."""

import os

from gi.repository import Adw, Gdk, GObject, Gtk

from .modele import ISSUES_RECADRAGE


def demander_mot_de_passe(parent, chemin, incorrect, reponse):
    """reponse(mot_de_passe ou None)."""
    entree = Adw.PasswordEntryRow(title="Mot de passe", activates_default=True)
    liste = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
    liste.add_css_class("boxed-list")
    liste.append(entree)
    corps = f"« {os.path.basename(chemin)} » est protégé par un mot de passe."
    if incorrect:
        corps = "Mot de passe incorrect. " + corps
    dialogue = Adw.AlertDialog(heading="Document protégé", body=corps, extra_child=liste)
    dialogue.add_response("annuler", "Ignorer ce fichier")
    dialogue.add_response("ouvrir", "Ouvrir")
    dialogue.set_response_appearance("ouvrir", Adw.ResponseAppearance.SUGGESTED)
    dialogue.set_default_response("ouvrir")
    dialogue.set_close_response("annuler")
    dialogue.connect("response", lambda _d, r: reponse(entree.get_text() if r == "ouvrir" else None))
    dialogue.present(parent)
    entree.grab_focus()


def demander_mise_en_page_images(parent, reglages, nombre, reponse):
    """reponse(dict de réglages d'image, ou None si annulé)."""
    marges = Adw.SpinRow.new_with_range(0, 50, 1)
    marges.set_title("Marges")
    marges.set_subtitle("En millimètres")
    marges.set_value(reglages.get_double("images-marges"))
    mode = Adw.ComboRow(title="Mise en page", model=Gtk.StringList.new(["Ajustée dans les marges", "Pleine page"]))
    mode.set_selected(1 if reglages.get_string("images-mode") == "pleine" else 0)
    mode.bind_property("selected", marges, "sensitive", GObject.BindingFlags.SYNC_CREATE, lambda _b, v: v == 0)
    orientation = Adw.SwitchRow(title="Orientation automatique", subtitle="Paysage pour les images plus larges que hautes",
                                active=reglages.get_boolean("images-orientation-auto"))
    groupe = Adw.PreferencesGroup()
    for rangee in (mode, marges, orientation):
        groupe.add(rangee)

    titre = "Insérer une image" if nombre == 1 else f"Insérer {nombre} images"
    dialogue = Adw.AlertDialog(heading=titre, body="Une image par page A4.", extra_child=groupe)
    dialogue.add_response("annuler", "Annuler")
    dialogue.add_response("inserer", "Insérer")
    dialogue.set_response_appearance("inserer", Adw.ResponseAppearance.SUGGESTED)
    dialogue.set_default_response("inserer")
    dialogue.set_close_response("annuler")

    def repondre(_d, r):
        if r != "inserer":
            reponse(None)
            return
        reponse({"images_marges": marges.get_value(),
                 "images_mode": "pleine" if mode.get_selected() == 1 else "ajustee",
                 "images_orientation_auto": orientation.get_active()})
    dialogue.connect("response", repondre)
    dialogue.present(parent)


def confirmer(parent, titre, corps, libelle, reponse, destructif=True):
    """reponse() n'est appelée que si l'utilisateur confirme."""
    dialogue = Adw.AlertDialog(heading=titre, body=corps)
    dialogue.add_response("annuler", "Annuler")
    dialogue.add_response("ok", libelle)
    dialogue.set_response_appearance(
        "ok", Adw.ResponseAppearance.DESTRUCTIVE if destructif else Adw.ResponseAppearance.SUGGESTED)
    dialogue.set_default_response("annuler")
    dialogue.set_close_response("annuler")
    dialogue.connect("response", lambda _d, r: r == "ok" and reponse())
    dialogue.present(parent)


def signaler_erreur(parent, titre, corps):
    dialogue = Adw.AlertDialog(heading=titre, body=corps)
    dialogue.add_response("ok", "Fermer")
    dialogue.present(parent)


def choisir_issue_recadrage(parent, reponse):
    """Demande ce que devient la zone tracée. reponse(genre) si on recadre."""
    groupe = Adw.PreferencesGroup()
    boutons = {}
    premier = None
    for cle, libelle, aide in ISSUES_RECADRAGE:
        bouton = Gtk.CheckButton(valign=Gtk.Align.CENTER)
        if premier is None:
            premier = bouton
            bouton.set_active(True)
        else:
            bouton.set_group(premier)
        rangee = Adw.ActionRow(title=libelle, subtitle=aide, activatable_widget=bouton)
        rangee.add_prefix(bouton)
        groupe.add(rangee)
        boutons[cle] = bouton

    dialogue = Adw.AlertDialog(heading="Recadrer la page",
                               body="Que faire de la zone que tu viens de tracer ?",
                               extra_child=groupe)
    dialogue.add_response("annuler", "Annuler")
    dialogue.add_response("recadrer", "Recadrer")
    dialogue.set_response_appearance("recadrer", Adw.ResponseAppearance.SUGGESTED)
    dialogue.set_default_response("recadrer")
    dialogue.set_close_response("annuler")

    def repondu(_d, r):
        if r == "recadrer":
            reponse(next(c for c, b in boutons.items() if b.get_active()))
    dialogue.connect("response", repondu)
    dialogue.present(parent)


def saisir_texte(parent, reglages, reponse):
    """Demande le texte à poser. reponse(texte, taille, couleur hexadécimale)."""
    vue = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR, top_margin=6, bottom_margin=6,
                       left_margin=6, right_margin=6)
    vue.set_size_request(-1, 110)
    cadre = Gtk.Frame(child=vue)

    taille = Adw.SpinRow.new_with_range(6, 48, 1)
    taille.set_title("Corps")
    taille.set_subtitle("En points ; réduit si le texte déborde du cadre")
    taille.set_value(reglages.get_double("texte-taille"))

    couleur = Gtk.ColorDialogButton(dialog=Gtk.ColorDialog(with_alpha=False),
                                    valign=Gtk.Align.CENTER)
    rgba = Gdk.RGBA()
    rgba.parse(reglages.get_string("texte-couleur"))
    couleur.set_rgba(rgba)
    rangee_couleur = Adw.ActionRow(title="Couleur")
    rangee_couleur.add_suffix(couleur)

    groupe = Adw.PreferencesGroup()
    groupe.add(taille)
    groupe.add(rangee_couleur)
    boite = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    boite.append(cadre)
    boite.append(groupe)

    dialogue = Adw.AlertDialog(heading="Écrire sur la page", extra_child=boite)
    dialogue.add_response("annuler", "Annuler")
    dialogue.add_response("ecrire", "Écrire")
    dialogue.set_response_appearance("ecrire", Adw.ResponseAppearance.SUGGESTED)
    dialogue.set_default_response("ecrire")
    dialogue.set_close_response("annuler")

    def repondu(_d, r):
        if r != "ecrire":
            return
        tampon = vue.get_buffer()
        texte = tampon.get_text(tampon.get_start_iter(), tampon.get_end_iter(), False)
        if not texte.strip():
            return
        rgba = couleur.get_rgba()
        hexa = "#%02x%02x%02x" % tuple(round(c * 255) for c in (rgba.red, rgba.green, rgba.blue))
        reglages.set_double("texte-taille", taille.get_value())
        reglages.set_string("texte-couleur", hexa)
        reponse(texte, taille.get_value(), hexa)
    dialogue.connect("response", repondu)
    dialogue.present(parent)
    vue.grab_focus()
