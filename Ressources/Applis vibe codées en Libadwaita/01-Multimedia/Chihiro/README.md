# Chihito

**Chihito** est une application d’ambiance de travail dans l’esprit de **Lofi Girl**, pensée pour accompagner les sessions de concentration.

Le paquet intègre également une extension GNOME Shell qui ajoute une bascule de lancement dans les réglages rapides. Son UUID est `chihiro-quicksettings-launch-toggle@ogu`.

## Installation

Le paquet Arch `chihiro-0.7.0-2-any.pkg.tar.zst` est fourni dans ce dossier ; l’installer depuis celui-ci :

```fish
sudo pacman -U ./chihiro-0.7.0-2-any.pkg.tar.zst
```

## Activer l’extension GNOME

Après l’installation :

1. **Déconnecte-toi de GNOME puis reconnecte-toi.** Sous Wayland, GNOME Shell ne découvre les nouvelles extensions qu’à l’ouverture de session.
2. Active la bascule intégrée dans les réglages rapides :

```fish
gnome-extensions enable chihiro-quicksettings-launch-toggle@ogu
```

L’extension est fournie avec le paquet Chihito ; il n’est pas nécessaire de l’installer séparément.

## Ressources

Le dossier contient le paquet `chihiro-0.7.0-2-any.pkg.tar.zst`, ses sources `chihiro-0.7.0.tar.gz`, le `PKGBUILD-chihiro` et `chihiro.install` (resynchronisés avec le paquet 0.7.0-2 le 14/11/2026 : licence GPL-3.0-or-later, sans gst-plugins-bad).
