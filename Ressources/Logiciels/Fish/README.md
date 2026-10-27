# Configuration Fish

Ce dossier contient les fichiers personnels Fish utilisés par le setup CachyOS.

## Fichiers

- **`config.fish`** — configuration principale, abréviations, alias et environnement.
- **`conf.d/shelly-local.fish`** — active la complétion des chemins de fichiers locaux pour `shelly install standard`. Après `./` ou `../`, la touche **Tab** propose les fichiers correspondants, ce qui facilite la sélection d’un paquet local dans le flux d’installation Shelly.
- **`functions/*.fish`** — fonctions personnelles chargées automatiquement par Fish.

## Installation

Depuis la racine du dépôt, copier les fichiers dans la configuration de l’utilisateur :

```fish
mkdir -p ~/.config/fish/{conf.d,functions}
cp "Ressources/Logiciels/Fish/config.fish" ~/.config/fish/config.fish
cp "Ressources/Logiciels/Fish/conf.d/shelly-local.fish" ~/.config/fish/conf.d/shelly-local.fish
cp Ressources/Logiciels/Fish/functions/*.fish ~/.config/fish/functions/
source ~/.config/fish/config.fish
```

Tester la complétion dans une nouvelle commande :

```fish
shelly install standard ./
``

Appuyer sur **Tab** après `./` pour afficher les chemins locaux disponibles. Cette complétion aide à sélectionner un paquet local ; elle ne remplace pas la commande `pacman -U`.
