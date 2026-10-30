# Perceptron — interface GNOME pour OpenCode

**Perceptron** (`opencode-perceptron`) est une interface GTK4/libadwaita pour [OpenCode](https://opencode.ai), intégrée dans une vue WebKitGTK 6.0. Elle fournit une fenêtre GNOME avec barre d’en-tête, menus, raccourcis, thème clair/sombre synchronisé avec le système et restauration de la taille de fenêtre.

Perceptron est un **wrapper natif** : toute la logique reste côté OpenCode. L’application démarre le serveur local avec `opencode serve`, effectue l’appairage avec `opencode pair`, puis affiche l’interface web d’OpenCode.

## Fonctionnement et caractéristiques

- `Adw.ApplicationWindow`, `Adw.HeaderBar` et `Adw.ToolbarView`.
- Indicateur de chargement natif et page d’erreur `Adw.StatusPage` avec bouton Réessayer.
- Cookies persistants pendant 30 jours dans `~/.local/share/opencode-perceptron`.
- Thème clair/sombre transmis à WebKit depuis le système.
- Taille de fenêtre restaurée au lancement.
- Icônes couleur et symbolique : `org.gnome.Perceptron` et `org.gnome.Perceptron-symbolic`.

## Dépendances

- `python`
- `python-gobject`
- `gtk4`
- `libadwaita`
- `webkitgtk-6.0`
- **OpenCode** : le binaire `opencode` doit être installé séparément et disponible dans le `PATH`. Il est indispensable au fonctionnement, mais n’est pas embarqué dans le paquet Perceptron.

## Installation

Depuis ce dossier, installer le paquet fourni :

```fish
sudo pacman -U ./opencode-perceptron-0.1.0-1-any.pkg.tar.zst
```

Vérifier la présence d’OpenCode puis lancer l’application :

```fish
opencode --version
opencode-perceptron
```

Perceptron est également disponible dans le menu des applications GNOME.

## Raccourcis

| Raccourci | Action |
|---|---|
| `Ctrl+R` | Recharger |
| `Ctrl++` / `Ctrl+-` / `Ctrl+0` | Zoom avant / arrière / 100 % |
| `F11` | Plein écran |
| `Ctrl+?` | Afficher les raccourcis |
| `Ctrl+Q` | Quitter |

## Reconstruction

Depuis le dossier des sources :

```bash
makepkg -si
```

Cette méthode nécessite notamment `fakeroot`. Variante fournie par le projet, sans fakeroot :

```bash
./build.sh
```

## Fichiers installés

- `/usr/bin/opencode-perceptron`
- `/usr/share/applications/org.gnome.Perceptron.desktop`
- `/usr/share/icons/hicolor/scalable/apps/org.gnome.Perceptron.svg`
- `/usr/share/icons/hicolor/scalable/apps/org.gnome.Perceptron-symbolic.svg`
- `/usr/share/licenses/opencode-perceptron/LICENSE`

## Désinstallation

```fish
sudo pacman -Rns opencode-perceptron
```

Les données de session et cookies sont conservés dans `~/.local/share/opencode-perceptron` sauf suppression manuelle.

## Licence

MIT.