# 11 — Logiciels

[Accueil](../README.md) · [Précédent](10-installation.md) · [Suivant](12-applications-vibe-coded.md)

> **Dans ce chapitre :** logiciels installés classés par catégorie, et réglages propres à Dropbox, Fragments et aux lecteurs vidéo.

- [11.1 Logiciels à installer](#111--logiciels-à-installer)
- [11.2 Puls et LeLivreScolaire](#112--puls-et-lelivrescolaire)
- [11.3 Dropbox](#113--dropbox)
- [11.4 Téléchargement : Grabber et Fragments](#114--téléchargement--grabber-et-fragments)
- [11.5 Clapper](#115--clapper)
- [11.6 Applications Vibe Coded](#116--applications-vibe-coded)


## 11.1 — Logiciels à installer


### Bureautique

- `onlyoffice` : suite bureautique (traitement de texte, tableur, présentation).
- `papers` : visionneuse de documents (PDF) GNOME.
- `xournal++` : prise de notes et annotation de PDF.
- `gnome-calendar` : agenda GNOME.

### Téléchargement & partage

- `fragments` : client BitTorrent GNOME.
- `nicotine+` : client Soulseek (P2P).

### Audio & vidéo

- `decibels` : lecteur de musique GNOME.
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

Commande complète :

```
sudo pacman -Syu dconf-editor powertop gst-thumbnailers profile-cleaner seahorse extension-manager fragments papers nicotine+ resources onlyoffice xournal++ gnome-calendar duf libgda6 shelly inotify-tools libnotify decibels clapper
```



## 11.2 — Puls et LeLivreScolaire

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

## 11.3 — Dropbox

Installer la bibliothèque d'intégration de l'indicateur :

```fish
sudo pacman -S libappindicator-gtk3
```

Pour retarder le lancement de Dropbox de 10 secondes, conserver son fichier d'autostart dans `~/.config/autostart/` et remplacer sa ligne `Exec` par :

```ini
Exec=/usr/bin/sh -c "sleep 10; exec dropbox"
```

## 11.4 — Téléchargement : Grabber et Fragments

### Grabber

Grabber est documenté avec les autres applications Vibe Coded dans [le chapitre 12](12-applications-vibe-coded.md#122--grabber).



### Fragments

Dans **Général → Ouvrir l'interface Web → Peers**, renseigner l'URL de liste de blocage :

```text
https://raw.githubusercontent.com/Naunter/BT_BlockLists/master/bt_blocklists.gz
```

Aligner le port d'écoute sur les [règles du pare-feu](06-network.md#61--configurer-ufw-pour-fragments-et-nicotine)

### Nicotine

Port 2234, réglage sur wlan0, réglage de l'UI.

## 11.5 — Clapper

Réglage de l'UI uniquement.

## 11.6 — Applications Vibe Coded

Les applications personnelles développées avec l'aide du Vibe Coding sont documentées séparément afin de conserver ici uniquement les logiciels et réglages généraux : [12 — Applications Vibe Coded](12-applications-vibe-coded.md).

---

[Accueil](../README.md) · [Précédent](10-installation.md) · [Suivant](12-applications-vibe-coded.md)
