# 10 — Logiciels

[Accueil](../README.md) · [Précédent](01-installation.md) · [Suivant](11-applications-vibe-coded.md)

> **Dans ce chapitre :** logiciels installés classés par catégorie, builds GTK4 spécifiques au setup, Dropbox sans interface, Claude Code, et réglages propres à Fragments et aux lecteurs vidéo.

- [10.1 Logiciels à installer](#101--logiciels-à-installer)
  - [10.1.1 dconf-editor GTK4](#1011--dconf-editor-gtk4)
  - [10.1.2 Snapper GTK4](#1012--snapper-gtk4)
  - [10.1.3 Extension Manager](#1013--extension-manager)
  - [10.1.4 Messagerie : Mail](#1014--messagerie--mail)
- [10.2 Puls et LeLivreScolaire](#102--puls-et-lelivrescolaire)
- [10.3 Dropbox](#103--dropbox)
- [10.4 Téléchargement : Grabber et Fragments](#104--téléchargement--grabber-et-fragments)
- [10.5 Showtime](#105--showtime)
- [10.6 Applications Vibe Coded](#106--applications-vibe-coded)
- [10.7 Claude Code](#107--claude-code)


## 10.1 — Logiciels à installer


### Bureautique

- **Samizdat** : installer [le traitement de texte léger GTK4/libadwaita](11-applications-vibe-coded.md#1125--samizdat), pour les documents courants DOCX, ODT et Markdown, avec export PDF.

- **Grille** : [visionneuse simple de fichiers tableurs, codée avec Claude](11-applications-vibe-coded.md#1124--grille).

- `papers` : visionneuse de documents (PDF) GNOME.
- `xournal++` : prise de notes et annotation de PDF.
- `gnome-calendar` : agenda GNOME.
- **[Mail (`mail-postcard`)](#1014--messagerie--mail)** : client compilé avec Claude depuis Postcard, avec recherche, aperçu des pièces jointes à droite, vue à trois volets, sélection multiple, clic droit, purge des copies locales à la fermeture, contraste entre panneaux et francisation complète.
- **Grimoire** : installer [l’éditeur Markdown maison](11-applications-vibe-coded.md#113--grimoire).

### Téléchargement & partage

- `fragments` : client BitTorrent GNOME.
- `nicotine+` : client Soulseek (P2P).
- **Grabber** : installer [l’interface maison de JDownloader](11-applications-vibe-coded.md#112--grabber) (AppImage).
- **Fret** : installer [le gestionnaire de fichiers maison à deux panneaux](11-applications-vibe-coded.md#114--fret).

### Audio & vidéo

- **Amplifaya** : installer [le moteur headless et sa télécommande GTK4/libadwaita](11-applications-vibe-coded.md#1123--amplifaya--moteur-headless-et-interface), fork allégé de JamesDSP.

- **Decibel** : installer [le fork maison du lecteur audio GNOME](11-applications-vibe-coded.md#117--decibel), fourni dans le dépôt.
- [**Showtime**](https://apps.gnome.org/Showtime/) (`showtime`) : lecteur vidéo GNOME GTK4/libadwaita.
- `gst-thumbnailers` : génération des vignettes audio/vidéo dans Nautilus.

### Système & outils

- **dconf-editor GTK4** : build du [portage GTK4 officiel en cours](11-applications-vibe-coded.md#1115--dconf-editor-gtk4), compilé depuis les sources upstream ; il remplace le `dconf-editor` GTK3 des dépôts.
- `powertop` : diagnostic de consommation énergétique.
- `profile-cleaner` : nettoyage des profils navigateurs.
- `seahorse` : gestion du trousseau de mots de passe.
- [**Extension Manager**](#1013--extension-manager) : version personnalisée avec classement des extensions GNOME par catégorie et icône Ogu ; paquet local `extension-manager-ogu`.
- `resources` : moniteur système GNOME (CPU, RAM, disque, réseau).
- `duf` : visualisation de l'espace disque en ligne de commande.
- `trash-cli` : corbeille en ligne de commande, utilisée via l’abréviation Fish `delete`.
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
- **Sismographe** : installer [l’outil maison d’analyse du démarrage et des journaux](11-applications-vibe-coded.md#1113--sismographe).
- **Snapper GTK4** : installer [l’interface GTK4/libadwaita pour Snapper et Limine](11-applications-vibe-coded.md#1114--snapper-gtk4).

Commande des paquets des dépôts (les applications maison se trouvent ci-dessous) :

```
sudo pacman -Syu powertop gst-thumbnailers profile-cleaner seahorse fragments papers nicotine+ resources xournal++ gnome-calendar duf trash-cli libgda6 shelly inotify-tools libnotify showtime
```

### 10.1.1 — dconf-editor GTK4

Le setup n’utilise plus le paquet `dconf-editor` GTK3 des dépôts. Il utilise le **portage GTK4 officiel en cours**, compilé directement depuis les sources upstream. Ce build n’est **pas** une application vibe codée et ne doit pas être confondu avec un fork maison.

Avant d’installer le build GTK4, désinstaller la version GTK3 :

```fish
sudo pacman -Rns dconf-editor
```

Compiler ensuite dconf-editor depuis les sources officielles du portage GTK4 utilisées par le setup. Les détails sont rappelés dans [11.15 — dconf-editor GTK4](11-applications-vibe-coded.md#1115--dconf-editor-gtk4).

### 10.1.2 — Snapper GTK4

**Snapper GTK4** est l’interface GTK4/libadwaita utilisée pour gérer les snapshots Snapper/Limine. Le paquet natif courant du setup est `snapper-gtk4-1.4.0-5-any.pkg.tar.zst`.

Installation du paquet local :

```fish
sudo pacman -U ./snapper-gtk4-1.4.0-5-any.pkg.tar.zst
```

L’application est détaillée dans [11.14 — Snapper GTK4](11-applications-vibe-coded.md#1114--snapper-gtk4).


Depuis la racine du dépôt, installer les paquets maison fournis ci-dessus :

```fish
sudo pacman -U \
  "Ressources/Applis vibe codées en Libadwaita/Grimoire/grimoire-ogu-0.2.0-10-x86_64.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/Fret/fret-0.2.0-1-any.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/Decibel/decibel-49.6.1-1-any.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/systemd-gui/systemd-gui-0.4.0-5-any.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/Fisherman/fisherman-0.1.8-1-any.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/Pacto/pacto-1.0.0-1-any.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/Radar/radar-1.4.0-2-any.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/Pusher/pusher-1.7.0-1-any.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/Nautilus Bookmark Icons/nautilus-bookmark-icons-0.1.1-1-any.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/Sismographe/sismographe-1.0.0-1-any.pkg.tar.zst"
```

Pour **Grabber** (AppImage) et **SCX Manager** (sources), suivre leurs [instructions d’installation](11-applications-vibe-coded.md). La commande Pacman ci-dessus suppose que chaque paquet a été vérifié pour cette machine.

### 10.1.3 — Extension Manager

Le setup utilise le paquet local **extension-manager-ogu 0.6.5.ogu2-1** pour disposer du classement par catégories et de l’icône personnalisée. Il remplace le paquet `extension-manager` des dépôts.

Depuis la racine du dépôt :

```fish
sudo pacman -U "Ressources/Applis vibe codées en Libadwaita/Extension Manager/extension-manager-ogu-0.6.5.ogu2-1-x86_64.pkg.tar.zst"
```

Si la version des dépôts `extension-manager` est installée, accepter son remplacement proposé par pacman. Le paquet local s’appelle `extension-manager-ogu`, fournit `extension-manager` et entre en conflit avec la version des dépôts.

Fermer complètement l’ancienne instance, puis lancer l’application :

```fish
extension-manager
```

Voir [11.22 — Extension Manager](11-applications-vibe-coded.md#1122--extension-manager) pour les fonctions et [8.11 — Classer les extensions avec Extension Manager](08-gnome-extensions.md#811--classer-les-extensions-avec-extension-manager) pour l’utilisation.

### 10.1.4 — Messagerie : Mail

**Mail (`mail-postcard`)** est le client de messagerie retenu pour ce setup, compilé avec **Claude** depuis les sources de [Postcard](https://github.com/gxanshu/postcard). Il ne s’agit pas d’une application créée de zéro par vibe coding : la base upstream est conservée, avec quelques ajouts : 

- **Recherche et affichage des pièces jointes**.
- **Aperçu des pièces jointes à droite** : PDF, images, texte et documents Word/LibreOffice.
- **Vue à trois volets**, avec sélection multiple et menu au clic droit.
- **Purge des copies locales à la fermeture**.
- **Contraste entre les panneaux** et **francisation complète**.

Ces ajouts ont été réalisés avec **Claude**.

**Dépendance pour la visualisation des pièces jointes PDF : `poppler-glib`.** L’installer avant d’utiliser leur aperçu :

```fish
sudo pacman -Syu --needed poppler-glib
```

Le paquet Arch compilé avec Claude est à ajouter manuellement dans [le dossier Mail](../Ressources/Logiciels/Mail/). Sa version exacte n’est pas précisée ici.

Depuis le dossier contenant le paquet, installer le fichier correspondant puis lancer Mail :

```fish
set paquets_mail (find . -maxdepth 1 -type f -name 'mail-postcard*.pkg.tar.zst')
if test (count $paquets_mail) -eq 1
    sudo pacman -U "$paquets_mail[1]"
else
    printf '%s\n' 'Conserver un seul paquet Mail dans ce dossier avant installation.'
end
```

Après une installation réussie :

```fish
mail-postcard
```

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

Utiliser le démon officiel en arrière-plan, sans icône, avec un service systemd utilisateur. Les commandes ci-dessous s’exécutent dans **Fish**.

### Configuration graphique initiale

Installer temporairement l’intégration Nautilus avec **Shelly**, puis ouvrir Dropbox :

```fish
shelly aur install nautilus-dropbox dropbox-cli
dropbox-cli start -i
```

L’extension GNOME **AppIndicator** permet d’afficher l’icône pour lier le compte, choisir le dossier `~/Dropbox`, régler la synchronisation sélective, la bande passante, la synchronisation LAN et les notifications. Les réglages sont conservés dans `~/.dropbox`. Quitter ensuite Dropbox depuis son icône.

### Conserver le démon et retirer l’intégration Nautilus

Marquer `dropbox` comme installé explicitement avant de retirer son intégration, pour conserver cette dépendance :

```fish
sudo pacman -D --asexplicit dropbox
sudo pacman -Rns nautilus-dropbox
shelly aur install dropbox dropbox-cli
rm -f "$HOME/.config/autostart/dropbox.desktop"
```

Retirer aussi un éventuel ancien fichier d’autostart personnalisé avec délai : le service ci-dessous remplace ce lancement.

### Service systemd utilisateur

Créer le fichier depuis Fish :

```fish
mkdir -p "$HOME/.config/systemd/user"
printf '%s\n' \
    '[Unit]' \
    'Description=Dropbox (démon headless)' \
    '' \
    '[Service]' \
    'ExecStart=/usr/bin/dropbox' \
    'UnsetEnvironment=DISPLAY WAYLAND_DISPLAY' \
    'Restart=on-failure' \
    'RestartSec=10' \
    '' \
    '[Install]' \
    'WantedBy=default.target' \
    > "$HOME/.config/systemd/user/dropbox.service"

systemctl --user daemon-reload
systemctl --user enable --now dropbox.service
```

Le démon démarre à l’ouverture de session. `UnsetEnvironment` retire l’accès aux affichages X11 et Wayland pour le lancement sans interface. Aucun `network-online.target` utilisateur n’est ajouté : il ne garantit pas la disponibilité du réseau système ; Dropbox se reconnecte lorsque le réseau devient disponible.

Si le compte n’est pas encore lié, consulter le journal pour obtenir le lien d’autorisation :

```fish
journalctl --user -u dropbox.service -f
```

### Vérification

```fish
systemctl --user status dropbox.service
dropbox-cli status
dropbox-cli filestatus "$HOME/Dropbox"
```

Le service doit être actif et le client indiquer l’état de synchronisation. Pour tester sans écraser un fichier existant :

```fish
set test_sync (mktemp "$HOME/Dropbox/test-sync-XXXXXX.txt")
printf '%s\n' 'Test de synchronisation Dropbox' > "$test_sync"
dropbox-cli filestatus "$test_sync"
```

Attendre la synchronisation et vérifier le fichier sur le compte Dropbox, puis supprimer uniquement ce fichier de test :

```fish
rm -- "$test_sync"
set -e test_sync
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

## 10.5 — Showtime

[**Showtime**](https://apps.gnome.org/Showtime/) est le lecteur vidéo GNOME retenu dans ce setup.

Installation et lancement :

```fish
sudo pacman -Syu --needed showtime
showtime
```

Réglage de l’interface selon les préférences.

## 10.6 — Applications Vibe Coded

Les applications personnelles développées avec l'aide du Vibe Coding sont documentées séparément afin de conserver ici uniquement les logiciels et réglages généraux : [11 — Applications Vibe Coded](11-applications-vibe-coded.md).

## 10.7 — Claude Code

[**Claude Code**](https://code.claude.com/docs/en/quickstart) est l’assistant de programmation Anthropic en terminal. Utiliser l’installateur natif officiel pour Linux : il ne nécessite pas Node.js et gère ses mises à jour automatiquement. Cette installation est indépendante de Shelly et des paquets AUR.

Depuis Fish, installer sans `sudo`, ajouter le répertoire au PATH et contrôler la version :

```fish
sudo pacman -Syu --needed curl bash git
curl -fsSL https://claude.ai/install.sh | bash
fish_add_path "$HOME/.local/bin"
claude --version
```

Ouvrir ensuite le terminal dans le projet et lancer l’assistant :

```fish
cd "$HOME/Gitlab/CACHYOS-Setup"
claude
```

Au premier lancement, suivre la connexion dans le navigateur avec un abonnement Claude compatible (Pro, Max, Team ou Enterprise), ou un compte Claude Console disposant de crédits API. Dans Claude Code, `/help` affiche l’aide et `/login` permet de changer de compte.


---

[Accueil](../README.md) · [Précédent](01-installation.md) · [Suivant](11-applications-vibe-coded.md)
