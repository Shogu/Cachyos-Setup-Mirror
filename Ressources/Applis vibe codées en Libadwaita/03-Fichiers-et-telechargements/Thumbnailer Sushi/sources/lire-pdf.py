#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Lecture d'un PDF pour l'aperçu Sushi.

    lire-pdf.py infos CHEMIN
        → JSON : nombre de pages et dimensions de la première page (points).

    lire-pdf.py page CHEMIN NUMERO LARGEUR
        → PNG de cette page sur la sortie standard, LARGEUR pixels de large.

Le rendu est fait par poppler (pdftocairo) : c'est le moteur de Papers et
d'Evince, donc le rendu réel du document — polices, images, marges, tout
vient du fichier — et non une reconstitution.
"""

import json
import os
import re
import shutil
import subprocess
import sys

E_LECTURE = 2
E_PARAMETRES = 64

TAILLE_MAX = 400 * 1024 * 1024      # au-delà, le rendu serait trop long
LARGEUR_DEFAUT = 1600
LARGEUR_MAX = 4000
DELAI = 60                          # secondes, par appel à poppler

# Format A4, si pdfinfo ne donne pas de dimensions exploitables.
LARGEUR_DEFAUT_PT = 595.276
HAUTEUR_DEFAUT_PT = 841.89

MSG_MOT_DE_PASSE = ("Ce PDF est protégé par un mot de passe : aucune page ne "
                    "peut être affichée.")


class Erreur(Exception):
    """Message affiché tel quel dans l'aperçu."""


def outil(nom):
    """Chemin d'un outil poppler (pdftocairo, pdfinfo…), cherché dans le PATH."""
    chemin = shutil.which(nom)
    if chemin is not None:
        return chemin
    for dossier in ('/usr/bin', '/usr/local/bin'):
        candidat = os.path.join(dossier, nom)
        if os.access(candidat, os.X_OK):
            return candidat
    raise Erreur(f"« {nom} » est introuvable : l'aperçu des PDF a besoin de "
                 "poppler (paquet « poppler »).")


def verifier(chemin):
    if not os.path.isfile(chemin):
        raise Erreur("Fichier introuvable.")
    taille = os.path.getsize(chemin)
    if taille == 0:
        raise Erreur("Ce fichier est vide.")
    if taille > TAILLE_MAX:
        raise Erreur("Fichier trop volumineux pour l'aperçu "
                     f"({taille / 1024 ** 2:.0f} Mo).")


def executer(argv):
    try:
        return subprocess.run(argv, capture_output=True, timeout=DELAI)
    except subprocess.TimeoutExpired:
        raise Erreur("Lecture du PDF trop longue : aperçu abandonné.")
    except OSError as e:
        raise Erreur(f"Lancement de « {os.path.basename(argv[0])} » impossible "
                     f"({e.strerror}).")


def derniere_ligne(octets):
    lignes = octets.decode('utf-8', 'replace').strip().splitlines()
    return lignes[-1].strip() if lignes else ''


def message_poppler(octets):
    """Dernière ligne d'erreur de poppler ; None si le PDF est protégé."""
    texte = derniere_ligne(octets)
    if 'password' in texte.lower() or 'encrypt' in texte.lower():
        return None
    return texte


def infos(chemin):
    verifier(chemin)
    res = executer([outil('pdfinfo'), '-f', '1', '-l', '1', '-enc', 'UTF-8', chemin])
    if res.returncode != 0:
        message = message_poppler(res.stderr)
        if message is None:
            raise Erreur(MSG_MOT_DE_PASSE)
        raise Erreur("PDF illisible"
                     + (f" ({message})." if message else "."))

    valeurs = {}
    tailles = {}
    for ligne in res.stdout.decode('utf-8', 'replace').splitlines():
        cle, _, valeur = ligne.partition(':')
        cles = cle.strip().lower()
        valeurs[cles] = valeur.strip()
        if re.fullmatch(r'page\s+\d+\s+size', cles):
            tailles[cles] = valeur.strip()

    try:
        pages = int(valeurs.get('pages', '0'))
    except ValueError:
        pages = 0
    if pages < 1:
        raise Erreur("Ce PDF ne contient aucune page.")

    largeur, hauteur = LARGEUR_DEFAUT_PT, HAUTEUR_DEFAUT_PT
    brut = next(iter(tailles.values()), valeurs.get('page size', ''))
    m = re.search(r'([\d.]+)\s+x\s+([\d.]+)\s+pts', brut)
    if m:
        largeur, hauteur = float(m.group(1)), float(m.group(2))
        if not (1 < largeur < 100000 and 1 < hauteur < 100000):
            largeur, hauteur = LARGEUR_DEFAUT_PT, HAUTEUR_DEFAUT_PT

    return {'pages': pages, 'largeur': round(largeur, 2), 'hauteur': round(hauteur, 2)}


def page(chemin, numero, largeur):
    verifier(chemin)
    if numero < 1:
        raise Erreur("Numéro de page invalide.")
    if not 100 <= largeur <= LARGEUR_MAX:
        raise Erreur("Largeur de rendu invalide.")

    # pdftocairo écrit sur stdout quand la sortie demandée est « - ».
    # (pdftoppm, lui, créerait un fichier nommé « -.png ».)
    res = executer([
        outil('pdftocairo'), '-png',
        '-f', str(numero), '-l', str(numero), '-singlefile',
        '-scale-to-x', str(largeur), '-scale-to-y', '-1',
        chemin, '-',
    ])
    if res.returncode != 0 or not res.stdout:
        message = message_poppler(res.stderr)
        if message is None:
            raise Erreur(MSG_MOT_DE_PASSE)
        texte = (message or '').lower()
        if 'wrong page' in texte or 'invalid page' in texte:
            raise Erreur(f"La page {numero} n'existe pas dans ce PDF.")
        raise Erreur("Rendu de la page impossible"
                     + (f" ({message})." if message else "."))
    sys.stdout.buffer.write(res.stdout)


def main(argv):
    if len(argv) < 3:
        raise Erreur("Utilisation : lire-pdf.py infos|page CHEMIN …")
    commande, chemin = argv[1], argv[2]
    if commande == 'infos':
        print(json.dumps(infos(chemin)))
    elif commande == 'page':
        if len(argv) < 4:
            raise Erreur("Numéro de page manquant.")
        largeur = int(argv[4]) if len(argv) > 4 else LARGEUR_DEFAUT
        page(chemin, int(argv[3]), largeur)
    else:
        raise Erreur(f"Commande inconnue : « {commande} ».")


if __name__ == '__main__':
    try:
        main(sys.argv)
    except Erreur as e:
        print(str(e), file=sys.stderr)
        sys.exit(E_LECTURE)
    except (ValueError, IndexError):
        print("Paramètres invalides.", file=sys.stderr)
        sys.exit(E_PARAMETRES)
