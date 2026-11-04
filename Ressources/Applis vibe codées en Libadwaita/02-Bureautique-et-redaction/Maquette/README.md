# Maquette

**Maquette 1.1.1** est un éditeur et outil de mise en page PDF en Python, GTK4 et libadwaita, conçu en français pour GNOME et CachyOS. Identifiant : `io.gitlab.shogu.Maquette`.

Elle permet de préparer un document final à partir de PDF et d’images, avec aperçu fidèle avant enregistrement.

## Fonctions

- Assembler plusieurs PDF et images, puis réordonner les pages par glisser-déposer.
- Pivoter, supprimer et extraire des pages ; insérer des pages blanches.
- Insérer des images sur des pages, avec marges réglables ou pleine page.
- Recadrer une zone, la vider ou la retirer en réduisant la page.
- Ajouter du texte sur une page.
- Annuler et rétablir les opérations.
- Préparer des brochures A5 sur A4 et des livrets A4 sur A3, avec aperçu du résultat imposé.

Rien n’est écrit sur le disque avant « Enregistrer sous… ».

## Limites

Maquette ne modifie pas le texte déjà présent dans un PDF. Elle n’importe pas directement les fichiers ODT, DOCX ou RTF : exporter ces documents en PDF depuis leur application d’origine.

## Installation

Depuis la racine du dépôt :

```fish
sudo pacman -U "Ressources/Applis vibe codées en Libadwaita/02-Bureautique-et-redaction/Maquette/maquette-1.1.1-1-any.pkg.tar.zst"
```

Le paquet déclare les dépendances nécessaires : Python, PyGObject, Cairo, GTK4, libadwaita, PyMuPDF, Pillow et hicolor-icon-theme.

L’archive `maquette-1.1.1-doc-et-sources.zip` regroupe les sources, tests, fichiers de construction et documentation de développement.

## Licence

AGPL-3.0-or-later.
