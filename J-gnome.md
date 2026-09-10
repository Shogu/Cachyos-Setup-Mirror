# J — GNOME

[Accueil](README.md) · [Précédent](H-powersave.md) · [Suivant](K-vivaldi.md)

- [Ajuster le rendu des polices](#j1--ajuster-le-rendu-des-polices)
- [Régler les actions de session et les rappels](#j2--régler-les-actions-de-session-et-les-rappels)
- [Organiser Nautilus et les marque-pages](#j3--organiser-nautilus-et-les-marque-pages)
- [Modifier le mot de passe du trousseau](#j4--modifier-le-mot-de-passe-du-trousseau)
- [Installer le fond d’écran et le thème de curseurs](#j5--installer-le-fond-décran-et-le-thème-de-curseurs)
- [Régler l’échelle et masquer les dossiers](#j6--régler-léchelle-et-masquer-les-dossiers)
- [Régler Xwayland et les fonctions expérimentales de Mutter](#j7--régler-xwayland-et-les-fonctions-expérimentales-de-mutter)
- [Importer et activer le profil couleur de l’écran](#j8--importer-et-activer-le-profil-couleur-de-lécran)
- [Renommer et organiser les lanceurs](#j9--renommer-et-organiser-les-lanceurs)
- [Installer et régler les extensions GNOME](#j10--installer-et-régler-les-extensions-gnome)
- [Régler temporairement les permissions avec malcontent](#j11--régler-temporairement-les-permissions-avec-malcontent)
- [Installer les scripts et extensions Nautilus](#j12--installer-les-scripts-et-extensions-nautilus)
- [Raccourcir le libellé du profil énergétique](#j13--raccourcir-le-libellé-du-profil-énergétique)
- [Créer les raccourcis BIOS, Ptyxis et Ressources](#j14--créer-les-raccourcis-bios-ptyxis-et-ressources)
- [Créer des modèles de documents dans Nautilus](#j15--créer-des-modèles-de-documents-dans-nautilus)

## J1 — Ajuster le rendu des polices

Éditer le fichier d’environnement :

```fish
sudoedit /etc/environment
```

Ajouter :

```ini
FREETYPE_PROPERTIES="cff:no-stem-darkening=0 autofitter:no-stem-darkening=0"
```

Se déconnecter puis se reconnecter pour appliquer le réglage aux nouvelles applications.

Le README proposait aussi une variante « moins grasse », mais reproduisait exactement la même valeur. Il n’y a donc qu’un réglage distinct à reprendre ici ; aucune seconde valeur n’a été inventée.

## J2 — Régler les actions de session et les rappels

Afficher l’action de fermeture de session dans GNOME 50 :

```fish
gsettings set org.gnome.shell always-show-log-out true
```

Le mémo propose également cette clé pour les boutons de redémarrage et d’arrêt à l’écran de connexion :

```fish
gsettings set org.gnome.login-screen disable-restart-buttons false
```

Une écriture depuis la session utilisateur ne garantit pas à elle seule l’application à la session GDM ; vérifier le résultat sur l’écran de connexion.

Désactiver le rappel de don GNOME si la clé existe dans la version installée :

```fish
gsettings set org.gnome.settings-daemon.plugins.housekeeping donation-reminder-enabled false
```

## J3 — Organiser Nautilus et les marque-pages

Dans Nautilus, créer les marque-pages utiles :

- Le dossier `Dropbox`.
- Le serveur FTP donnant accès au SSD de la télévision Android : `ftp://192.168.31.68:2121`.
- L’accès administrateur au système de fichiers via `admin:///` : saisir cette adresse, ouvrir le système de fichiers puis ajouter un marque-page avec **Ctrl+D**.

Personnaliser les icônes des dossiers Dropbox, MP3, Root, Domestique et Lycée dans Dropbox, ainsi que des extensions GNOME, à partir des icônes **Places** du dossier **Icons & background** du dépôt.

## J4 — Modifier le mot de passe du trousseau

Dans **Seahorse**, modifier le mot de passe du trousseau concerné et laisser les champs du nouveau mot de passe vides si c’est le comportement souhaité. Reconnecter ensuite le compte Google dans GNOME si nécessaire.

Cette opération concerne le **trousseau de mots de passe**, pas le mot de passe du compte Linux ni l’activation d’une connexion automatique. Un trousseau sans mot de passe n’a plus cette protection de ses secrets sur disque.

## J5 — Installer le fond d’écran et le thème de curseurs

Installer le [fond d’écran Fedora 34 nocturne](https://fedoraproject.org/w/uploads/d/de/F34_default_wallpaper_night.jpg), ou le fond **cosmos_dark_blue** du dépôt.

Pour le curseur, utiliser la variante **Phinger NO LEFT Light** du [projet Phinger Cursors](https://github.com/phisch/phinger-cursors/releases). Placer le dossier du thème dans `/usr/share/icons/` ; vérifier son nom réel, attendu ici comme `phinger-cursors-light`.

Dans dconf-editor, régler la taille sur **32** :

```text
org/gnome/desktop/interface/cursor-size
```

Appliquer le thème au compte GDM :

```fish
sudo -u gdm dbus-launch gsettings set org.gnome.desktop.interface cursor-theme phinger-cursors-light
```

Utiliser ensuite **GDM Settings**, notamment pour le fond d’écran de connexion, et importer le fichier **`gdm-settings.ini`** du dépôt. Une fois les réglages effectués, le mémo prévoit de supprimer le paquet de cet outil.

## J6 — Régler l’échelle et masquer les dossiers

Dans les paramètres d’affichage, choisir une mise à l’échelle **125 %**. Dans Nautilus :

- Masquer les dossiers Modèles et Bureau si souhaité.
- Masquer les fichiers du fond d’écran et de l’image utilisateur sans les déplacer hors des chemins configurés.
- Augmenter la taille des icônes de dossiers.
- Attribuer une icône personnalisée au dossier Dropbox.

La création du dossier caché de modèles est détaillée dans [Modèles Nautilus](#j15--créer-des-modèles-de-documents-dans-nautilus).

## J7 — Régler Xwayland et les fonctions expérimentales de Mutter

Dans **dconf-editor**, ouvrir :

```text
org.gnome.mutter experimental-features
```

Conserver les valeurs utiles déjà présentes et activer, si elles existent dans la version installée :

- `autoclose-xwayland` pour la fermeture de Xwayland lorsqu’il n’est plus utilisé ;
- `scale-monitor-framebuffer` pour la mise à l’échelle fractionnaire ;
- `xwayland-native-scaling` pour la mise à l’échelle native des applications Xwayland.

Les options expérimentales peuvent varier selon la version de Mutter.

## J8 — Importer et activer le profil couleur de l’écran

Rappel ajouté conformément au choix exprimé pour ce setup : importer le profil **ICM/ICC de l’écran** dans **Paramètres GNOME → Couleur**, l’associer à l’écran intégré puis l’activer comme profil utilisé. Importer le fichier seul ne garantit pas sa sélection pour l’écran.

Le profil lui-même doit être récupéré parmi les fichiers de configuration ou la sauvegarde personnelle ; aucun profil de calibration n’est inventé ni joint à cette documentation.

## J9 — Renommer et organiser les lanceurs

Avec **Menu Principal / l’éditeur de menus**, renommer les applications dans la vue d’ensemble et masquer les lanceurs inutiles pour viser une seule page d’applications.

Remplacer également l’icône de Ptyxis par celle de [GNOME Terminal](https://upload.wikimedia.org/wikipedia/commons/d/da/GNOME_Terminal_icon_2019.svg).

## J10 — Installer et régler les extensions GNOME

En cas de mise à jour de GNOME Shell, le mémo propose de désactiver temporairement la validation des versions plutôt que de modifier chaque `metadata.json` :

```fish
gsettings set org.gnome.shell disable-extension-version-validation true
```

Cela ne rend pas une extension incompatible fonctionnelle ; réactiver la validation une fois les extensions adaptées :

```fish
gsettings set org.gnome.shell disable-extension-version-validation false
```

**Extensions esthétiques :**

- [Panel Corners](https://extensions.gnome.org/extension/4805/panel-corners/)

- [Just Perfection](https://extensions.gnome.org/extension/3843/just-perfection/) qui permet de réunir en une extension Grand Theft Focus, Hide Worldclocks, Hide Activities Button, Hide Screenshot, Impatience etc...

- [Lilypad Topbar Organizer](https://extensions.gnome.org/extension/7266/lilypad/)

**Extensions apportant des fonctions de productivité :**

- [Appindicator](https://extensions.gnome.org/extension/615/appindicator-support/)

- [Caffeine](https://extensions.gnome.org/extension/517/caffeine/) à activer seulement après résolution du problème de veille

- [Clipboard History](https://extensions.gnome.org/extension/4839/clipboard-history/) ou plus graphique avec [Copyous](https://extensions.gnome.org/extension/8834/copyous/) : penser à installer la dépendance libgda6 `sudo pacman -S libgda6`

- [Slider percentages](https://extensions.gnome.org/extension/10125/slider-percentages/)

**Extensions apportant des fonctions UI :**

- [Battery Time Percentage Compact](https://extensions.gnome.org/extension/2929/battery-time-percentage-compact/) ou [Battery Time](https://extensions.gnome.org/extension/5425/battery-time/)

- [AutoActivities](https://extensions.gnome.org/extension/5500/auto-activities/)

- [Power Switching Manager](https://extensions.gnome.org/extension/9178/power-switching-manager/) & supprimer la luminosité automatique dans Settings de GNOME !!

- [Hot Edge](https://extensions.gnome.org/extension/4222/hot-edge/)

- [Custom Command Toggle](https://extensions.gnome.org/extension/7012/custom-command-toggle/)

- [Drag'n'Tile](https://extensions.gnome.org/extension/7863/dragntile/)

- [Quick Close Overview](https://extensions.gnome.org/extension/352/middle-click-to-close-in-overview/)

- [Auto Power Profile](https://extensions.gnome.org/extension/6583/auto-power-profile/)

- [Battery Monitor](https://extensions.gnome.org/extension/8348/battery-monitor/)

- [Privacy Settings](https://extensions.gnome.org/extension/4491/privacy-settings-menu/) puis la supprimer une fois les réglages faits.

- [Media Controls](https://extensions.gnome.org/extension/4470/media-controls/)

- [Windows Rounded Corners](https://extensions.gnome.org/extension/7048/rounded-window-corners-reborn/)

- [Quick Settings Audio Device](https://extensions.gnome.org/extension/5964/quick-settings-audio-devices-hider/) pour masquer les périphériques audio inutiles. L’exemple JamesDSP du mémo est sans objet depuis sa désinstallation.

- [Night Light Slider](https://extensions.gnome.org/extension/6781/night-light-slider-updated/)

- [AppIndicator Quick Setting](https://github.com/VaZark/appindicator-quicksetting) : indicateurs d’applications dans les réglages rapides.

Pour les extensions qui changent les profils d’alimentation, choisir une configuration cohérente : éviter que deux extensions imposent simultanément des profils opposés. Le passage automatique secteur/batterie conserve un rôle distinct de l’application des réglages par TuneD.

## J11 — Régler temporairement les permissions avec malcontent

Installer temporairement `malcontent` pour accéder aux réglages d’applications correspondants dans GNOME Control Center :

```fish
sudo pacman -S malcontent
```

Effectuer les réglages voulus, puis retirer le paquet si cette interface n’est plus nécessaire :

```fish
sudo pacman -Rns malcontent
```

## J12 — Installer les scripts et extensions Nautilus

Télécharger depuis **SCRIPTS** les scripts **`Hide.py`**, **`Unhide.py`** et **`Dropbox`** :

- Hide/Unhide masquent ou rendent visibles les fichiers à la demande.
- Dropbox ouvre le fichier dans l’interface Web du service afin de récupérer son URL de partage, pour reproduire cet usage de l’intégration Nautilus.

Créer le dossier, y placer les scripts puis les rendre exécutables :

```fish
mkdir -p /home/ogu/.local/share/nautilus/scripts
chmod +x /home/ogu/.local/share/nautilus/scripts/Hide.py
chmod +x /home/ogu/.local/share/nautilus/scripts/Unhide.py
chmod +x /home/ogu/.local/share/nautilus/scripts/Dropbox
```

Adapter les noms aux fichiers réellement téléchargés.

Ajouter les extensions de copie du chemin et d’accès administrateur :

```fish
paru -S nautilus-copy-path nautilus-admin
sudo pacman -Syu nautilus-python
```

Éditer les fichiers de configuration et d’extension :

```fish
sudoedit /usr/share/nautilus-python/extensions/nautilus-copy-path/nautilus_copy_path.py
sudoedit /usr/share/nautilus-python/extensions/nautilus-copy-path/config.json
sudoedit /usr/share/nautilus-python/extensions/nautilus-admin.py
```

Dans la configuration de copie de chemin, passer **URI** et **Content** à `false`. Dans l’extension administrateur, traduire **Open as admin**, en reprenant la traduction du dépôt.

Ces modifications touchent des fichiers de paquets et peuvent être remplacées lors d’une mise à jour. Fermer puis rouvrir Nautilus après l’édition :

```fish
nautilus -q
nautilus
```

## J13 — Raccourcir le libellé du profil énergétique

Raccourcir le libellé du bouton de profil énergétique, trop long dans les réglages rapides GNOME.

Installer l’outil de traduction et récupérer le fichier français :

```fish
sudo pacman -S gettext
wget https://gitlab.gnome.org/GNOME/gnome-shell/-/raw/main/po/fr.po -O fr.po
gnome-text-editor fr.po
```

Modifier la traduction **Mode puissance** en **Énergie** ou **Profil**, puis compiler :

```fish
msgfmt fr.po -o gnome-shell.mo
```

Le lien du mémo vise la branche `main` : pour éviter de remplacer les traductions installées par celles d’une autre version, privilégier le fichier `fr.po` correspondant à la version de GNOME Shell utilisée.

Sauvegarder l’original puis installer le fichier compilé :

```fish
sudo cp -a /usr/share/locale/fr/LC_MESSAGES/gnome-shell.mo /usr/share/locale/fr/LC_MESSAGES/gnome-shell.mo.bak
sudo cp gnome-shell.mo /usr/share/locale/fr/LC_MESSAGES/gnome-shell.mo
```

Après vérification, supprimer les deux fichiers de travail créés dans le dossier courant :

```fish
rm -i fr.po gnome-shell.mo
```

Cette personnalisation peut être remplacée par une mise à jour de GNOME Shell.

## J14 — Créer les raccourcis BIOS, Ptyxis et Ressources

Télécharger le script **`reboot_bios.sh`** du dépôt, le placer dans `/home/ogu/.local/bin/` puis le rendre exécutable :

```fish
chmod +x /home/ogu/.local/bin/reboot_bios.sh
```

Créer un lanceur **Boot to BIOS**, avec confirmation assurée par le script, l’icône **jockey** et cette commande :

```text
ptyxis -- /home/ogu/.local/bin/reboot_bios.sh
```

Dans les paramètres GNOME, affecter :

- La touche **Copilot** à Ptyxis.
- **Ctrl+Alt+Suppr** à Ressources.

Personnaliser les icônes Places des dossiers Dropbox, Nicotine, Téléchargements, `usr`, `root`, Extensions, Icons et des autres dossiers souhaités.

## J15 — Créer des modèles de documents dans Nautilus

Utiliser un dossier caché **`.Modèles`** pour le menu de création de fichiers de Nautilus.

Renommer l’ancien dossier s’il existe et si la destination n’existe pas encore, puis créer le dossier caché :

```fish
if test -d "$HOME/Modèles"; and not test -e "$HOME/.Modèles"
    mv -- "$HOME/Modèles" "$HOME/.Modèles"
end
mkdir -p "$HOME/.Modèles"
```

Si les deux dossiers existaient déjà, déplacer manuellement les modèles à conserver dans `.Modèles`.

Créer le modèle texte :

```fish
touch "$HOME/.Modèles/notepad.txt"
```

Pour **`word.docx`**, ouvrir OnlyOffice, créer un document vierge et l’enregistrer comme `/home/ogu/.Modèles/word.docx`. Un simple `touch word.docx`, proposé dans le mémo, créerait un fichier vide et non un document Word valide.

Faire pointer XDG vers ce dossier :

```fish
mkdir -p "$HOME/.config"
touch "$HOME/.config/user-dirs.dirs"
sed -i '/^XDG_TEMPLATES_DIR=/d' "$HOME/.config/user-dirs.dirs"
printf '%s\n' 'XDG_TEMPLATES_DIR="$HOME/.Modèles"' >> "$HOME/.config/user-dirs.dirs"
xdg-user-dirs-update
nautilus -q
```

Rouvrir Nautilus et vérifier la présence des deux modèles dans le menu de création de documents.

[Accueil](README.md) · [Précédent](H-powersave.md) · [Suivant](K-vivaldi.md)
