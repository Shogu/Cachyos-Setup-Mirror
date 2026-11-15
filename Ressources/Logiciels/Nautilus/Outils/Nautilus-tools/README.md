# Nautilus-tools-ogu — intégration Ptyxis à Nautilus

Ce dossier accueille le paquet Arch compilé **nautilus-tools-ogu**. Déposer ici manuellement le fichier `.pkg.tar.zst`.

L'intégration ajoute cinq actions à Nautilus :

- **Ouvrir dans un terminal** : lance Ptyxis dans le dossier affiché ou sélectionné.
- **Ouvrir en root** : ouvre le dossier avec les droits administrateur.
- **Terminal intégré** : affiche un terminal dans le panneau inférieur de Nautilus, avec bascule par **F4** ou le bouton dédié.
- **Installer le paquet** : clic droit sur un fichier `.pkg.tar.zst` ; un nouvel onglet Ptyxis lance `sudo pacman -U` sur ce paquet.
- **Copier le chemin** : clic droit sur un ou plusieurs éléments copie leur chemin complet dans le presse-papiers ; avec plusieurs éléments, un chemin est copié par ligne.

## Installation

Depuis la racine du dépôt, après avoir déposé le paquet dans ce dossier :

```fish
sudo pacman -U "Ressources/Logiciels/Nautilus/Outils/Nautilus-tools/"*.pkg.tar.zst
nautilus -q
```

Rouvrir Nautilus après l'installation. La documentation générale se trouve dans [12.1 — Intégrer Ptyxis à Nautilus](../../../../../docs/12-shell-terminal.md#121--intégrer-ptyxis-à-nautilus-et-aux-outils-cachyos).
