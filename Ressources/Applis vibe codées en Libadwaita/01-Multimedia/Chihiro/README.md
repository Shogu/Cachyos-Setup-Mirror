# Chihito

**Chihito** est une application d’ambiance de travail dans l’esprit de **Lofi Girl**, pensée pour accompagner les sessions de concentration.

Le paquet intègre également une extension GNOME Shell qui ajoute une bascule de lancement dans les réglages rapides. Son UUID est `chihiro-quicksettings-launch-toggle@ogu`.

## Installation

Déposer le paquet Arch `chihiro-0.6.1-1-any.pkg.tar.zst` dans ce dossier, puis l’installer depuis celui-ci :

```fish
sudo pacman -U ./chihiro-0.6.1-1-any.pkg.tar.zst
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

Le paquet `chihiro-0.6.1-1-any.pkg.tar.zst` est à déposer manuellement dans ce dossier.
