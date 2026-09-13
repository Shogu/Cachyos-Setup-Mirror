# I — Réglages logiciels

[Accueil](README.md) · [Précédent](B-logiciels-a-supprimer-installer.md) · [Suivant](C-boot.md)

- [Dropbox : client retenu et démarrage différé](#i1--dropbox--client-retenu-et-démarrage-différé)
- [Intégrer Ptyxis à Nautilus et aux outils CachyOS](#i2--intégrer-ptyxis-à-nautilus-et-aux-outils-cachyos)
- [Configurer Fish, GNOME Text Editor et Micro](#i3--configurer-fish-gnome-text-editor-et-micro)
- [Configurer Ciné ou Celluloid](#i4--configurer-ciné-ou-celluloid)
- [Installer JDownloader et Fragments](#i5--configurer-jdownloader-et-fragments)
- [Installer le script de transfert de vidéos](#i6--installer-le-script-de-transfert-de-vidéos)

## I1 — Dropbox


Installer la bibliothèque d’intégration de l’indicateur :

```fish
sudo pacman -S libappindicator-gtk3
```

Pour retarder le lancement de Dropbox de 10 secondes, conserver son fichier d’autostart dans `~/.config/autostart/` et remplacer sa ligne `Exec` par :

```ini
Exec=/usr/bin/sh -c "sleep 10; exec dropbox"
```


## I2 — Intégrer Ptyxis à Nautilus et aux outils CachyOS

Installer l’intégration du terminal dans Nautilus :

```fish
paru -S nautilus-open-any-terminal
gsettings set com.github.stunkymonkey.nautilus-open-any-terminal terminal ptyxis
gsettings set com.github.stunkymonkey.nautilus-open-any-terminal new-tab true
```

L’option `new-tab` ouvre un onglet dans la session existante. En cas d’erreur avec GNOME 49, consulter [le ticket du projet](https://github.com/Stunkymonkey/nautilus-open-any-terminal/issues/242).

Pour ajouter Ptyxis aux terminaux proposés par les outils CachyOS, le mémo conserve [ce guide communautaire](https://www.reddit.com/r/cachyos/comments/1rry7qh/guide_add_your_terminal_to_cachyos_tools_like/).

## I3 — Configurer Fish, GNOME Text Editor et Micro

Configurer Ptyxis et **GNOME Text Editor**, puis installer le fichier **`config.fish` du dépôt** dans `~/.config/fish/config.fish`. Il contient les alias, la désactivation du message d’accueil et les fonctions personnelles `scx`, `journal`, `flags`, `sudoedit`, `vault`, etc.

**Conserver un fichier Fish unique**, conformément au choix retenu. Recharger sa configuration :

```fish
source ~/.config/fish/config.fish
```

Dans GNOME Text Editor, ajuster les préférences internes et désactiver la correction orthographique ; le mémo l’utilise pour éviter les avertissements observés lors d’un lancement en ligne de commande.

Pour Micro, créer le dossier puis éditer le fichier :

```fish
mkdir -p ~/.config/micro
gnome-text-editor ~/.config/micro/settings.json
```

Insérer ces valeurs dans l’objet JSON existant, ou utiliser ce contenu si le fichier est neuf :

```json
{
  "keymenu": true,
  "mkparents": true
}
```

## I4 — Configurer Ciné ou Celluloid

Le mémo préfère **Ciné** à Celluloid. Pour Ciné, créer puis éditer :

```fish
mkdir -p ~/.config/cine
gnome-text-editor ~/.config/cine/input.conf
```

```text
# Flèches horizontales : 60 secondes ; verticales : 5 minutes.
RIGHT seek 60
LEFT seek -60
UP seek 300
DOWN seek -300
```

Pour les options du moteur vidéo, le mémo indique `vo=gpu-next` et `gpu-api=vulkan` dans **Paramètres → Divers → Options supplémentaires**. Adapter leur syntaxe au champ proposé par l’application : options de configuration MPV et arguments de ligne de commande ne se saisissent pas nécessairement de la même manière.

Activer les options **focus** et **toujours afficher les boutons de titre**. Installer les scripts Lua **Visualizer** et **Delete File** pour l’usage musical ; leurs URL ne sont pas précisées dans le README source.

## I5 — Configurer JDownloader et Fragments

### JDownloader

Installer l'AppImage libadwaita créée par ChatGPT et créer son lanceur depuis /local/bin.


```ini
StartupWMClass=org-jdownloader-update-launcher-JDLauncher
```


### Fragments

Dans **Général → Ouvrir l’interface Web → Peers**, renseigner l’URL de liste de blocage :

```text
https://raw.githubusercontent.com/Naunter/BT_BlockLists/master/bt_blocklists.gz
```

Aligner le port d’écoute sur les [règles du pare-feu](F-reseau.md#f1--configurer-ufw-pour-fragments-et-nicotine).

## I6 — Installer le script de transfert de vidéos

Télécharger le script **`transfert_videos`** depuis le dossier **SCRIPTS** du dépôt. Il déplace automatiquement les vidéos vers le dossier Vidéos et supprime leur sous-dossier d’origine.

Créer le dossier de destination du script :

```fish
mkdir -p /home/ogu/.local/bin
```

Placer le script sous `/home/ogu/.local/bin/transfert_videos.sh`, puis créer un lanceur avec l’éditeur de menus.

Commande du lanceur :

```text
/usr/bin/fish /home/ogu/.local/bin/transfert_videos.sh
```

Icône :

```text
/usr/share/icons/Adwaita/scalable/devices/drive-multidisk.svg
```

[Accueil](README.md) · [Précédent](B-logiciels-a-supprimer-installer.md) · [Suivant](C-boot.md)
