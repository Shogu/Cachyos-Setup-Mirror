"""Scénario d'interface sous Xvfb, avec captures d'écran.

xvfb-run -s "-screen 0 1280x860x24" python3 tests/scenario.py <dossier d'essai> <dossier des captures>
"""
import os
import subprocess
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, ".."))
os.environ.setdefault("GSETTINGS_SCHEMA_DIR", os.path.join(ICI, "schemas"))
os.environ.setdefault("GSETTINGS_BACKEND", "memory")

import compat  # noqa: E402,F401
from gi.repository import Gio, GLib, Gtk  # noqa: E402

from maquette import application  # noqa: E402

essai, captures = sys.argv[1], sys.argv[2]
os.makedirs(captures, exist_ok=True)
app = application.Application()
etapes = []
journal = []


def capture(nom):
    subprocess.run(["import", "-window", "root", os.path.join(captures, nom + ".png")], check=True)
    journal.append(nom)


def fenetre():
    return app.get_active_window()


def attendre(condition, suite, delai=15000):
    debut = GLib.get_monotonic_time()

    def verifier():
        if condition():
            GLib.timeout_add(400, suite)
            return False
        if (GLib.get_monotonic_time() - debut) / 1000 > delai:
            print("ÉCHEC : délai dépassé", file=sys.stderr)
            app.quit()
            return False
        return True
    GLib.timeout_add(100, verifier)


def etape(f):
    etapes.append(f)
    return f


def suivante():
    if not etapes:
        print("SCÉNARIO TERMINÉ :", ", ".join(journal))
        fenetre()._fermeture_confirmee = True
        app.quit()
        return False
    f = etapes.pop(0)
    print("→", f.__name__)
    f()
    return False


def rendus_finis():
    return all(c.image.get_paintable() is not None for c in fenetre().grille._ordre)


@etape
def e01_vide():
    capture("01-vide")
    f = [Gio.File.new_for_path(os.path.join(essai, n)) for n in ("cours.pdf", "exercices.pdf", "paysage.jpg")]
    fenetre().ajouter_fichiers(f)
    attendre(lambda: len(fenetre().pages) >= 7 and rendus_finis(), suivante)


@etape
def e02_grille():
    w = fenetre()
    assert not w._modifie(), "le chargement initial ne doit pas compter comme une modification"
    capture("02-grille-chargee")
    w.grille.selectionner([w.pages[1].uid, w.pages[2].uid])
    GLib.timeout_add(300, suivante)


@etape
def e03_selection_rotation():
    w = fenetre()
    w.activate_action("win.pivoter-droite", None)
    w._sur_deplacer(None, [w.pages[5].uid], 0)
    w.grille.selectionner([w.pages[3].uid])
    w.activate_action("win.page-blanche", None)
    attendre(rendus_finis, suivante)


@etape
def e04_apres_modifs():
    w = fenetre()
    assert w._modifie()
    capture("03-grille-modifiee")
    w._ouvrir_grand(w.pages[1].uid)
    attendre(lambda: w.page_grand.vue.texture is not None, suivante)


@etape
def e05_outil_recadrer():
    w = fenetre()
    w.activate_action("win.recadrer", None)
    assert w.page_grand.vue.outil == "recadrer"
    vue = w.page_grand.vue
    x, y, l, h = vue._rect_page()
    vue._trace = (x + l * 0.08, y + h * 0.30, x + l * 0.92, y + h * 0.62)
    vue.queue_draw()
    GLib.timeout_add(600, lambda: (capture("04-recadrage-trace"), suivante()) and False)


@etape
def e06_dialogue_recadrage():
    w = fenetre()
    w.page_grand.vue._trace = None
    w.page_grand.vue.emit("zone-tracee", "recadrer", 0.08, 0.30, 0.92, 0.62)
    GLib.timeout_add(700, suivante)


@etape
def e07_choisir_issue():
    capture("05-trois-issues")
    w = fenetre()
    dlg = w.get_visible_dialog()
    assert dlg is not None, "le dialogue des trois issues ne s'est pas ouvert"
    dlg.emit("response", "recadrer")
    dlg.close()
    attendre(lambda: len(w.pages[w._index(w._uid_grand)].ops) == 1, suivante)


@etape
def e08_verifier_issue():
    w = fenetre()
    op = w.pages[w._index(w._uid_grand)].ops[0]
    assert op.genre == "rogner", op.genre
    print("   issue appliquée :", op.genre)
    w.activate_action("win.texte", None)
    assert w.page_grand.vue.outil == "poser-texte"
    w.page_grand.vue.emit("zone-tracee", "poser-texte", 0.1, 0.1, 0.9, 0.3)
    GLib.timeout_add(700, suivante)


@etape
def e09_saisir_texte():
    w = fenetre()
    dlg = w.get_visible_dialog()
    assert dlg is not None, "le dialogue de texte ne s'est pas ouvert"
    vue = dlg.get_extra_child().get_first_child().get_child()
    vue.get_buffer().set_text("NOM : ................  Classe : 2nde\nCorrigé — séance 3 (à é è ç œ)")
    capture("06-saisie-texte")
    dlg.emit("response", "ecrire")
    dlg.close()
    attendre(lambda: len(w.pages[w._index(w._uid_grand)].ops) == 2, suivante)


@etape
def e10_page_avec_texte():
    w = fenetre()
    attendre(lambda: w.page_grand.vue.texture is not None, lambda: (capture("07-page-recadree-et-texte"), suivante()) and False)


@etape
def e11_retour_grille():
    w = fenetre()
    w.navigation.pop()
    attendre(rendus_finis, lambda: (capture("08-grille-finale"), suivante()) and False)


@etape
def e11b_apercu():
    w = fenetre()
    w.activate_action("win.apercu", None)
    attendre(lambda: w.page_apercu.vue.texture is not None, suivante)


@etape
def e11c_apercu_fidele():
    w = fenetre()
    capture("12-apercu-fidele")
    assert w.navigation.get_visible_page() is w.page_apercu
    assert w.page_apercu.titre.get_title().startswith("Page 1 sur"), w.page_apercu.titre.get_title()
    w.page_apercu.emit("naviguer", 1)
    attendre(lambda: w.page_apercu.index == 1 and w.page_apercu.vue.texture is not None, suivante)


@etape
def e11d_apercu_livret():
    w = fenetre()
    w.navigation.pop()
    w.reglages.set_string("imposition", "brochure-a5")
    w.activate_action("win.apercu", None)
    attendre(lambda: w.page_apercu.vue.texture is not None, suivante)


@etape
def e11e_verifier_apercu_livret():
    w = fenetre()
    capture("13-apercu-brochure")
    assert w.page_apercu.titre.get_title().startswith("Feuille 1 sur 4"), w.page_apercu.titre.get_title()
    assert "Brochure A5" in w.page_apercu.titre.get_subtitle()
    print("   aperçu brochure :", w.page_apercu.titre.get_title())
    w.navigation.pop()
    w.reglages.set_string("imposition", "fidele")
    attendre(rendus_finis, suivante)


@etape
def e12_enregistrer():
    w = fenetre()
    sortie = os.path.join(captures, "resultat.pdf")
    w._ecrire(w.pages, sortie, extraction=False)
    attendre(lambda: os.path.exists(sortie) and not w._modifie(), suivante)


@etape
def e13_enregistrer_livret():
    import pymupdf
    w = fenetre()
    d = pymupdf.open(os.path.join(captures, "resultat.pdf"))
    assert d.page_count == len(w.pages), (d.page_count, len(w.pages))
    assert "NOM :" in d[1].get_text(), d[1].get_text()[:80]
    print("   PDF :", d.page_count, "pages ;", os.path.getsize(os.path.join(captures, "resultat.pdf")), "octets")
    # l'action passe par un sélecteur de fichier : on vérifie seulement son câblage
    action = w.lookup_action("enregistrer-ainsi")
    assert action is not None and action.get_enabled()
    assert action.get_parameter_type().dup_string() == "s"
    GLib.timeout_add(200, suivante)
    attendre(lambda: os.path.exists(os.path.join(captures, "livret.pdf")), suivante)


@etape
def e14_verifier_livret():
    w = fenetre()
    # le bouton scindé passe par le sélecteur de fichier : on écrit directement
    w._ecrire(w.pages, os.path.join(captures, "livret.pdf"), extraction=False, imposition="brochure-a5")
    attendre(lambda: os.path.exists(os.path.join(captures, "livret.pdf")), suivante)


@etape
def e14b_livret_ecrit():
    import pymupdf
    d = pymupdf.open(os.path.join(captures, "livret.pdf"))
    print("   livret :", d.page_count, "feuilles", [round(v) for v in (d[0].rect.width, d[0].rect.height)])
    assert d[0].rect.width > d[0].rect.height
    app.activate_action("preferences", None)
    GLib.timeout_add(900, suivante)


@etape
def e15_preferences():
    capture("09-preferences")
    w = fenetre()
    w.reglages.set_string("dossier-propose", "fixe")
    w.reglages.set_string("dossier-fixe", "/tmp")
    assert w._dossier_propose() == "/tmp", w._dossier_propose()
    print("   dossier fixe pris en compte")
    w.get_visible_dialog().force_close()
    w.activate_action("win.annuler", None)
    attendre(lambda: w.get_visible_dialog() is None, suivante)


@etape
def e16_fermeture():
    w = fenetre()
    assert w._modifie(), "le document devrait être modifié avant la fermeture"
    # close() ne déclenche pas close-request sans gestionnaire de fenêtres :
    # on émet le signal, ce que fait un vrai clic sur la croix.
    # Le seul point critique ici : la fermeture doit être RETENUE, sinon le
    # travail non enregistré serait perdu. L'affichage de la confirmation
    # dépend du gestionnaire de fenêtres, absent de ce conteneur.
    assert w.emit("close-request"), "la fermeture doit être retenue tant qu'on n'a pas confirmé"
    print("   fermeture retenue, document non perdu")
    GLib.timeout_add(600, suivante)


@etape
def e16b_dialogue_fermeture():
    w = fenetre()
    visible = w.get_visible_dialog()
    if visible is not None:
        capture("10-fermeture")
    w._confirmation = None
    GLib.timeout_add(300, suivante)


@etape
def e17_fin():
    w = fenetre()
    dlg = w.get_visible_dialog()
    if dlg is not None:
        dlg.force_close()
    w.reglages.set_int("taille-miniatures", 110)
    attendre(rendus_finis, lambda: (capture("11-petites-miniatures"), suivante()) and False)


def demarrer(_app):
    fenetre().set_default_size(1200, 820)
    GLib.timeout_add(1200, suivante)


app.connect_after("activate", demarrer)
Gtk.Settings.get_default()
sys.exit(app.run([sys.argv[0]]))
