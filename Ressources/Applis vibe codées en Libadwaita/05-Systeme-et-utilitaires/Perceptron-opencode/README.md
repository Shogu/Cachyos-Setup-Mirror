# Perceptron

Interface GNOME native pour [OpenCode](https://opencode.ai), réalisée en GTK4/libadwaita et WebKitGTK 6.0.

Perceptron est un wrapper : il démarre `opencode serve`, réalise l’appairage avec `opencode pair` et affiche l’interface web d’OpenCode dans une fenêtre Adwaita. OpenCode doit être installé séparément et accessible dans le `PATH`.

## Installation

Le paquet Arch/CachyOS est fourni dans ce dossier :

```fish
sudo pacman -U ./opencode-perceptron-0.1.0-1-any.pkg.tar.zst
```

Puis lancer l’application depuis le menu GNOME ou avec :

```fish
opencode-perceptron
```

## Dépendances

`python`, `python-gobject`, `gtk4`, `libadwaita`, `webkitgtk-6.0` et **OpenCode** (à installer séparément).

## Reconstruction

Depuis le dossier des sources : `makepkg -si` ou `./build.sh` (voir la documentation du projet).

## Désinstallation

```fish
sudo pacman -Rns opencode-perceptron
```

Licence : MIT.