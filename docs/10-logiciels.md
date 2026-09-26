# 10 — Logiciels

[Accueil](../README.md) · [Précédent](01-installation.md) · [Suivant](11-applications-vibe-coded.md)

> **Dans ce chapitre :** logiciels installés classés par catégorie, et réglages propres à Dropbox, Fragments et aux lecteurs vidéo.

- [10.1 Logiciels à installer](#101--logiciels-à-installer)
- [10.2 Puls et LeLivreScolaire](#102--puls-et-lelivrescolaire)
- [10.3 Dropbox](#103--dropbox)
- [10.4 Téléchargement : Grabber et Fragments](#104--téléchargement--grabber-et-fragments)
- [10.5 Clapper](#105--clapper)
- [10.6 Applications Vibe Coded](#106--applications-vibe-coded)


## 10.1 — Logiciels à installer


### Bureautique

- `onlyoffice` : suite bureautique (traitement de texte, tableur, présentation).
- `papers` : visionneuse de documents (PDF) GNOME.
- `xournal++` : prise de notes et annotation de PDF.
- `gnome-calendar` : agenda GNOME.
- **Grimoire** : installer [l’éditeur Markdown maison](11-applications-vibe-coded.md#113--grimoire).

### Téléchargement & partage

- `fragments` : client BitTorrent GNOME.
- `nicotine+` : client Soulseek (P2P).
- **Grabber** : installer [l’interface maison de JDownloader](11-applications-vibe-coded.md#112--grabber) (AppImage).
- **Periscope** : installer [le gestionnaire de fichiers maison à deux panneaux](11-applications-vibe-coded.md#114--periscope).

### Audio & vidéo

- **Decibel** : installer [le fork maison du lecteur audio GNOME](11-applications-vibe-coded.md#117--decibel), fourni dans le dépôt.
- `clapper` : lecteur vidéo GNOME.
- `gst-thumbnailers` : génération des vignettes audio/vidéo dans Nautilus.

### Système & outils

- `dconf-editor` : éditeur de la base de registres GNOME (dconf).
- `powertop` : diagnostic de consommation énergétique.
- `profile-cleaner` : nettoyage des profils navigateurs.
- `seahorse` : gestion du trousseau de mots de passe.
- `extension-manager` : gestion des extensions GNOME Shell.
- `resources` : moniteur système GNOME (CPU, RAM, disque, réseau).
- `duf` : visualisation de l'espace disque en ligne de commande.
- `libgda6` : bibliothèque d'accès aux données, requise par certaines extensions GNOME.
- `inotify-tools` : surveillance des évènements du système de fichiers.
- `libnotify` : notifications système.
- **SCX Manager** : installer [l’interface maison pour sched-ext](11-applications-vibe-coded.md#115--scx-manager) depuis son archive source.
- **systemd-gui** : installer [l’interface maison de gestion des services](11-applications-vibe-coded.md#116--systemd).
- **Fisherman** : installer [le gestionnaire maison de configuration Fish](11-applications-vibe-coded.md#118--fisherman).
- **Pacto** : installer [le gestionnaire maison des fichiers `.pacnew` et `.pacsave`](11-applications-vibe-coded.md#119--pacto).
- **Radar** : installer [l’outil maison de recherche de fichiers](11-applications-vibe-coded.md#1110--radar).
- **Pusher** : installer [l’interface maison du dépôt GitLab](11-applications-vibe-coded.md#1111--pusher).
- **Nautilus Bookmark Icons** : installer [l’extension maison de personnalisation des icônes de favoris Nautilus](11-applications-vibe-coded.md#1112--nautilus-bookmark-icons).
- **Stethoscope** : installer [l’outil maison d’analyse du démarrage et des journaux](11-applications-vibe-coded.md#1113--stethoscope).

Commande des paquets des dépôts (les applications maison se trouvent ci-dessous) :

```
sudo pacman -Syu dconf-editor powertop gst-thumbnailers profile-cleaner seahorse extension-manager fragments papers nicotine+ resources onlyoffice xournal++ gnome-calendar duf libgda6 shelly inotify-tools libnotify clapper
```


Depuis la racine du dépôt, installer les paquets maison fournis ci-dessus :

```bash
sudo pacman -U \
  "Ressources/Applis vibe codées en Libadwaita/Grimoire/grimoire-ogu-0.2.0-9-x86_64.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/Periscope/periscope-0.2.0-4-final-any.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/Decibel/decibel-49.6.1-1-any.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/systemd-gui/systemd-gui-0.4.0-4-any.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/Fisherman/fisherman-0.1.7-2-any.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/Pacto/pacto-1.0.0-1-any.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/Radar/radar-1.4.0-1-any.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/Pusher/pusher-1.7.0-1-any.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/Nautilus Bookmark Icons/nautilus-bookmark-icons-0.1.1-1-any.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/Stethoscope/stethoscope-0.6.4-1-any.pkg.tar.zst"
```

Pour **Grabber** (AppImage) et **SCX Manager** (sources), suivre leurs [instructions d’installation](11-applications-vibe-coded.md). La commande Pacman ci-dessus suppose que chaque paquet a été vérifié pour cette machine.

## 10.2 — Puls et LeLivreScolaire

[Puls](https://github.com/word-sys/puls/releases/tag/v0.9.3) : à installer dans `/home/ogu/.local/bin/`

Installer l'AppImage `LeLivreScolaire` :

1. Déplacer l'AppImage de Téléchargements à `/home/USERNAME/.local/Lelivrescolaire.fr.AppImage` :

```fish
mv "$HOME/Téléchargements/Lelivrescolaire.fr.AppImage" "$HOME/.local/"
```

2. Rendre l'AppImage exécutable :

```fish
chmod +x "$HOME/.local/Lelivrescolaire.fr.AppImage"
```

3. Créer le fichier `.desktop` :

```fish
mkdir -p "$HOME/.local/share/applications" && xdg-open "$HOME/.local/share/applications/lelivrescolaire.fr.desktop"
```

Y copier ce contenu :

```ini
[Desktop Entry]
Version=1.0
Type=Application
Name=Lelivrescolaire.fr
Comment=Consulter les manuels scolaires Lelivrescolaire.fr
Exec=/home/%u/.local/Lelivrescolaire.fr.AppImage %U
Icon=application-x-executable
Terminal=false
StartupNotify=true
StartupWMClass=Lelivrescolaire.fr
MimeType=x-scheme-handler/lls;
Categories=Education;
```

4. Valider et enregistrer le protocole `lls://` :

```fish
desktop-file-validate "$HOME/.local/share/applications/lelivrescolaire.fr.desktop" && update-desktop-database "$HOME/.local/share/applications" && xdg-mime default lelivrescolaire.fr.desktop x-scheme-handler/lls
```

5. Tester :

```fish
"$HOME/.local/Lelivrescolaire.fr.AppImage"
```

## 10.3 — Dropbox

Installer la bibliothèque d'intégration de l'indicateur :

```fish
sudo pacman -S libappindicator-gtk3
```

Pour retarder le lancement de Dropbox de 10 secondes, conserver son fichier d'autostart dans `~/.config/autostart/` et remplacer sa ligne `Exec` par :

```ini
Exec=/usr/bin/sh -c "sleep 10; exec dropbox"
```

## 10.4 — Téléchargement : Grabber et Fragments

### Grabber

Grabber est documenté avec les autres applications Vibe Coded dans [le chapitre 11](11-applications-vibe-coded.md#112--grabber).



### Fragments

Dans **Général → Ouvrir l'interface Web → Peers**, renseigner l'URL de liste de blocage :

```text
https://raw.githubusercontent.com/Naunter/BT_BlockLists/master/bt_blocklists.gz
```

Aligner le port d'écoute sur les [règles du pare-feu](06-network.md#61--configurer-ufw-pour-fragments-et-nicotine)

### Nicotine

Port 2234, réglage sur wlan0, réglage de l'UI.

## 10.5 — Clapper

Réglage de l'UI uniquement.

## 10.6 — Applications Vibe Coded

Les applications personnelles développées avec l'aide du Vibe Coding sont documentées séparément afin de conserver ici uniquement les logiciels et réglages généraux : [11 — Applications Vibe Coded](11-applications-vibe-coded.md).

---

[Accueil](../README.md) · [Précédent](01-installation.md) · [Suivant](11-applications-vibe-coded.md)
