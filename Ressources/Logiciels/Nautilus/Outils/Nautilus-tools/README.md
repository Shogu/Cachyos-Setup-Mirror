# Nautilus-tools-ogu — intégration Ptyxis à Nautilus

Ce dossier accueille le paquet Arch compilé **nautilus-tools-ogu**. Déposer ici manuellement le fichier `.pkg.tar.zst`.

L'extension, native (une bibliothèque `libnautilus-tools-ogu.so`), ajoute les actions suivantes à Nautilus.

### Actions de terminal et de fichiers

- **Ouvrir dans un terminal** : lance Ptyxis dans le dossier affiché ou sélectionné.
- **Ouvrir en root** : ouvre le dossier avec les droits administrateur.
- **Terminal intégré** : affiche un terminal dans le panneau inférieur de Nautilus, avec bascule par **F4** ou le bouton dédié.
- **Copier le chemin** : clic droit sur un ou plusieurs éléments copie leur chemin complet dans le presse-papiers ; avec plusieurs éléments, un chemin est copié par ligne.
- **Ouvrir dans OpenCode** : clic droit sur un **dossier** (ou dans une **zone vide**) → ouvre une session `opencode` dans ce dossier via Ptyxis (`ptyxis -d <dossier> -x opencode`). L'entrée n'apparaît que lorsqu'un seul dossier est sélectionné.

### Icônes des favoris

- **Changer l'icône des favoris** : clic droit sur un favori de la barre latérale → **Changer l'icône** pour sélectionner une icône symbolique du thème courant ; **Réinitialiser** restaure l'icône native.

### Dossiers récents et fréquents (0.8)

À l'ouverture de la recherche (loupe, `Ctrl+F` ou frappe directe dans un dossier), une liste centrée sous la loupe propose :

- **Récents** : les 5 derniers dossiers ouverts dans Nautilus ;
- **Fréquents** : les 5 dossiers les plus visités selon zoxide, sans doublon avec les récents.

La liste suit le texte tapé (mots n'importe où dans le chemin, dans l'ordre : `cours tm` → `TMCV2`) et disparaît quand aucun dossier ne correspond. Elle ne prend jamais le clavier : la recherche classique marche comme avant.

- Clic : ouvre le dossier dans l'onglet courant. Clic du milieu : dans un nouvel onglet.
- Chaque dossier ouvert dans Nautilus est ajouté à zoxide (`zoxide add`) : `z` dans le terminal le connaît aussi.
- Exclus : `/tmp`, `/var/tmp`, `~/.cache`, `/run/media`, `/media`, `/mnt`, montages GVfs. Changer d'onglet ne compte pas comme une visite.
- Historique des récents : `~/.local/state/nautilus-tools-ogu/recent-folders` (50 dossiers au plus).
- Sans zoxide : seulement les récents. Si une mise à jour de Nautilus fait disparaître le champ de recherche interne, un bouton dans la barre d'en-tête prend le relais.

Nécessite Nautilus 47 ou plus récent (action `slot.open-location`).

Nautilus n'expose pas d'API officielle pour modifier les lignes de sa sidebar : cette fonction parcourt donc l'arbre de widgets GTK interne. Une future version majeure peut nécessiter une adaptation.

Depuis la version 0.4.0, l'extension retouche aussi le menu du clic droit de Nautilus :

- **Courriel…** est retiré.
- **Extraire ici** (ajouté par File Roller) est retiré : il fait doublon avec **Extraire** de Nautilus.
- **Copier vers…** et **Déplacer vers…** ouvrent le sélecteur de dossier moderne de Nautilus (portail GNOME) au lieu de l'ancien sélecteur GTK. La copie ou le déplacement reste fait par Nautilus : barre de progression, gestion des conflits et annulation par **Ctrl+Z** inchangées.

**Extraire vers…** garde l'ancien sélecteur : Nautilus n'expose aucune interface pour lancer une extraction depuis l'extension.

## Pourquoi « Copier vers… » utilisait l'ancien sélecteur

Depuis GNOME 47, le sélecteur de fichiers moderne est fourni par Nautilus lui-même, via le portail `xdg-desktop-portal-gnome`. Les autres applications (Éditeur de texte, etc.) l'obtiennent en passant par ce portail. Nautilus, lui, désactive le portail de sélection de fichiers pour son propre processus (`gtk_disable_portal_interfaces`), afin de ne pas s'appeler lui-même. Ses propres boîtes de dialogue retombent donc sur l'ancien `GtkFileChooser`. L'extension contourne ce blocage en appelant le portail directement par D-Bus.

## Installation

Depuis la racine du dépôt, après avoir déposé le paquet dans ce dossier :

```fish
sudo pacman -U "Ressources/Logiciels/Nautilus/Outils/Nautilus-tools/"*.pkg.tar.zst
nautilus -q
```

Rouvrir Nautilus après l'installation. La documentation générale se trouve dans [12.1 — Intégrer Ptyxis à Nautilus](../../../../../docs/12-shell-terminal.md#121--intégrer-ptyxis-à-nautilus-et-aux-outils-cachyos).

## Dépannage

Les messages de l'extension s'affichent quand Nautilus est lancé depuis un terminal :

```fish
nautilus -q; nautilus 2>&1 | grep nautilus-tools-ogu
```
