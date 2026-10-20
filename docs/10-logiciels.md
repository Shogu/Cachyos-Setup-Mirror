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

- **Semitone** : lecteur musical GTK4/libadwaita, fork de Gapless, compilé avec Claude. Il remplace `gapless` ; le paquet Arch sera ajouté manuellement dans [son dossier](../Ressources/Applis%20vibe%20codées%20en%20Libadwaita/01-Multimedia/Semitone/). Voir [11.29 — Semitone](11-applications-vibe-coded.md#1129--semitone).
- **Decibel** : installer [le fork maison du lecteur audio GNOME](11-applications-vibe-coded.md#117--decibel), fourni dans le dépôt.
- **Disquaire** : installer [l’éditeur de tags MP3/FLAC](11-applications-vibe-coded.md#1128--disquaire), qui ne conserve que les sept champs retenus.
- [**Showtime**](https://apps.gnome.org/Showtime/) (`showtime`) : lecteur vidéo GNOME GTK4/libadwaita.
- `gst-thumbnailers` : génération des vignettes audio/vidéo dans Nautilus.

### Système & outils

- `sushi` : prévisualisation rapide des fichiers dans Nautilus avec la barre d’espace.
- **thumbnailer-docx-nautilus-sushi** : paquet local qui ajoute à Sushi des aperçus de documents, présentations, tableurs et archives, ainsi que des miniatures Nautilus pour documents, présentations, tableurs, texte brut et code. Le paquet compilé est à déposer manuellement dans [son dossier](../Ressources/Logiciels/thumbnailer-docx-nautilus-sushi/). Voir [9.7 — Aperçu et miniatures avec Sushi](09-nautilus-workflow.md#97--aperçu-et-miniatures-avec-sushi) et le [README du paquet](../Ressources/Logiciels/thumbnailer-docx-nautilus-sushi/README.md).

  Après installation ou mise à jour du paquet, relancer les deux applications et vider le cache des miniatures :

  ```fish
  pkill -f NautilusPreviewer
  nautilus -q
  rm -rf ~/.cache/thumbnails/*
  ```


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
- **systemd-gui** : installer [l’interface maison de gestion des services](11-applications-vibe-coded.md#116--systemd).
- **Fisherman** : installer [le gestionnaire maison de configuration Fish](11-applications-vibe-coded.md#118--fisherman).
- **Pacto** : installer [le gestionnaire maison des fichiers `.pacnew` et `.pacsave`](11-applications-vibe-coded.md#119--pacto).
- **Radar** : installer [l’outil maison de recherche de fichiers](11-applications-vibe-coded.md#1110--radar).
- **Pusher** : installer [l’interface maison du dépôt GitLab](11-applications-vibe-coded.md#1111--pusher).
- **Nautilus Bookmark Icons** : installer [l’extension maison de personnalisation des icônes de favoris Nautilus](11-applications-vibe-coded.md#1112--nautilus-bookmark-icons).
- **Icônes UI** : outil Python pour importer, appliquer, restaurer et exporter les icônes couleur et symboliques des applications installées ([instructions et lancement](11-applications-vibe-coded.md#1126--icônes-ui)).
- **Sismographe** : installer [l’outil maison d’analyse du démarrage et des journaux](11-applications-vibe-coded.md#1113--sismographe).
- **Snapper GTK4** : installer [l’interface GTK4/libadwaita pour Snapper et Limine](11-applications-vibe-coded.md#1114--snapper-gtk4).

Commande des paquets des dépôts (les applications maison se trouvent ci-dessous) :

```
sudo pacman -Syu powertop gst-thumbnailers profile-cleaner seahorse fragments papers nicotine+ resources xournal++ gnome-calendar duf trash-cli libgda6 shelly inotify-tools libnotify showtime sushi
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
  "Ressources/Applis vibe codées en Libadwaita/02-Bureautique-et-redaction/Grimoire/grimoire-ogu-0.2.0-10-x86_64.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/03-Fichiers-et-telechargements/Fret/fret-0.2.0-1-any.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/01-Multimedia/Decibel/decibel-49.6.1-1-any.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/05-Systeme-et-utilitaires/systemd-gui/systemd-gui-0.4.0-5-any.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/05-Systeme-et-utilitaires/Fisherman/fisherman-0.1.8-1-any.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/05-Systeme-et-utilitaires/Pacto/pacto-1.0.0-1-any.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/05-Systeme-et-utilitaires/Radar/radar-1.4.0-2-any.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/05-Systeme-et-utilitaires/Pusher/pusher-1.7.0-1-any.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/03-Fichiers-et-telechargements/Nautilus Bookmark Icons/nautilus-bookmark-icons-0.1.1-1-any.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/05-Systeme-et-utilitaires/Sismographe/sismographe-1.0.0-1-any.pkg.tar.zst" \
  "Ressources/Applis vibe codées en Libadwaita/01-Multimedia/Disquaire/disquaire-1.0.0-1-any.pkg.tar.zst"
```

Pour **Semitone**, installer séparément le paquet Arch compilé avec Claude, après l’avoir ajouté manuellement dans son dossier de ressources ; voir [les instructions d’installation](11-applications-vibe-coded.md#1129--semitone). Pour **Grabber** (AppImage), suivre ses [instructions d’installation](11-applications-vibe-coded.md). La commande Pacman ci-dessus suppose que chaque paquet a été vérifié pour cette machine.

### 10.1.3 — Extension Manager

Le setup utilise le paquet local **extension-manager-ogu 0.6.5.ogu2-1** pour disposer du classement par catégories et de l’icône personnalisée. Il remplace le paquet `extension-manager` des dépôts.

Depuis la racine du dépôt :

```fish
sudo pacman -U "Ressources/Applis vibe codées en Libadwaita/04-Bureau-et-personnalisation/Extension Manager/extension-manager-ogu-0.6.5.ogu2-1-x86_64.pkg.tar.zst"
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

Utiliser le client officiel Dropbox en arrière-plan, avec un démarrage automatique par **XDG Autostart**. Cette méthode fonctionne dans la session GNOME : Dropbox démarre à l’ouverture de session et `dropbox-cli status` permet de vérifier la synchronisation. Les commandes ci-dessous s’exécutent dans **Fish**.

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
```

### Démarrage automatique par XDG

Dropbox crée sa propre entrée. Autrement, créer le fichier `~/.config/autostart/dropbox.desktop` :

```fish
mkdir -p "$HOME/.config/autostart"

cat > "$HOME/.config/autostart/dropbox.desktop" <<'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=Dropbox
Comment=Synchronisation Dropbox
Exec=/usr/bin/dropbox
Icon=dropbox
Terminal=false
StartupNotify=false
X-GNOME-Autostart-enabled=true
Categories=Network;
EOF

desktop-file-validate "$HOME/.config/autostart/dropbox.desktop"
```


Se déconnecter puis se reconnecter à GNOME pour vérifier le démarrage automatique. Pour tester immédiatement le lanceur :

```fish
/usr/bin/dropbox
```

### Vérification

```fish
dropbox-cli status
pgrep -a -f '[d]ropbox'
```

Le client doit indiquer l’état de synchronisation, idéalement **« À jour »**.

Pour tester sans écraser un fichier existant :

```fish
set test_sync (mktemp "$HOME/Dropbox/test-sync-XXXXXX.txt")
printf '%s\\n' 'Test de synchronisation Dropbox' > "$test_sync"
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

### Astuce d’interface — sauts proportionnels dans la vidéo

Un petit correctif local de `window.py` modifie la recherche au clavier : les flèches **gauche/droite** déplacent la lecture d’environ **1 %** de la durée totale, et les flèches **haut/bas** d’environ **5 %**. Les sauts s’adaptent ainsi à la longueur de la vidéo. Il s’agit d’une astuce de personnalisation de Showtime, pas d’une application vibe coded.

Le fichier corrigé à conserver dans le dépôt est :
`Ressources/Logiciels/Players/Showtime/window.py`.

Depuis la racine du dépôt, après avoir placé ce fichier :

```fish
sudo cp "Ressources/Logiciels/Players/Showtime/window.py" (pacman -Ql showtime | string match -r '\\S+/widgets/window\\.py
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
)
```

Vérifier le fichier installé et rechercher le marqueur `sauts` :

```fish
cat /usr/lib/python3.14/site-packages/showtime/widgets/window.py
grep -n -i "sauts" /usr/lib/python3.14/site-packages/showtime/widgets/window.py
```

Si le chemin change avec la version de Python ou du paquet, retrouver le chemin installé avec :

```fish
pacman -Ql showtime | string match -r '\\S+/widgets/window\\.py
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

```

Voir le [README du correctif Showtime](../Ressources/Logiciels/Players/Showtime/README.md). Une mise à jour de Showtime peut écraser le fichier modifié ; il faudra alors réappliquer le correctif.

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
