# 10 — Installation & préparation du setup

[Accueil](../README.md) · [Précédent](09-nautilus-workflow.md) · [Suivant](11-logiciels.md)

> **Dans ce chapitre :** premiers réglages après l'installation (Fish, CachyOS Hello) et configuration du gestionnaire de paquets (Paru/AUR).

- [10.1 Premiers réglages](#101--premiers-réglages)
- [10.2 Installation de paquets](#102--installation-de-paquets)

## 10.1 — Premiers réglages

### Préparer Fish

Installer dès le début le fichier **`config.fish` du dépôt** dans `~/.config/fish/config.fish` afin de disposer des fonctions personnelles, notamment celles utilisées pour l'édition avec `sudoedit`.

```fish
mkdir -p ~/.config/fish
```

Copier le fichier du dépôt à cet emplacement, puis le charger :

```fish
source ~/.config/fish/config.fish
```

Pour les functions : voir [la configuration complète de Fish et des éditeurs](13-shell-terminal.md#132--fish-gnome-text-editor-et-micro).


### Réglages initiaux dans CachyOS Hello

Dans **CachyOS Hello** :

- Désactiver le Bluetooth
- Ne pas activer l'icône de mise à jour CachyOS dans la zone de notification.
- Classer les miroirs.
- Ne pas installer PSD

## 10.2 — Installation de paquets

```fish
paru -Syu libre-menu-editor archclean gapless
```

### Remplacements de paquets

Remplacer `jack` (AUR) par `jack2` des dépôts & installer `geocode-glib`

```fish
sudo pacman -Syu jack2 geocode-glib
```


Remplacement de `sudo` par `sudo-rs` avec le paquet CachyOS et la réutilisation de la configuration existante. 

```fish
sudo pacman -Syu sudo-rs
```


### Mesurer le volume installé


```fish
pacman -Q | wc -l
expac -H M '%m' | awk '{sum += $1} END {printf "%.2f GiB\n", sum/1024}'
```
---
Ou function Fish `pacstats`

[Accueil](../README.md) · [Précédent](09-nautilus-workflow.md) · [Suivant](11-logiciels.md)
