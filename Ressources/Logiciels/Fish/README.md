# Configuration Fish

Ce dossier contient les fichiers personnels Fish utilisés par le setup CachyOS.

## Fichiers

- **`config.fish`** — configuration principale, abréviations, alias (dont `upgrade` → mise à jour Pacman + Pamac-AUR) et environnement.
- **`functions/*.fish`** — fonctions personnelles chargées automatiquement par Fish.

> La complétion `conf.d/shelly-local.fish` (pour l'ancien `shelly install standard ./`) a été retirée : Shelly est remplacé par Pamac. Pour installer une archive locale, on passe directement par `pacman -U ./<archive.pkg.tar.zst>`.

## Installation

Depuis la racine du dépôt, copier les fichiers dans la configuration de l’utilisateur :

```fish
mkdir -p ~/.config/fish/{conf.d,functions}
cp "Ressources/Logiciels/Fish/config.fish" ~/.config/fish/config.fish
cp Ressources/Logiciels/Fish/functions/*.fish ~/.config/fish/functions/
source ~/.config/fish/config.fish
```

## Usage

- **`rosetta`** (ou `rosetta -p`) — aide-mémoire de la ligne de commande Pacman ↔ Pamac (dépôts + AUR).
- **`memo`** — liste interactive des abréviations et fonctions, dont les commandes AUR (via Pamac) : `aur` / `aursearch` / `aurremove` / `aurlist` / `add` / `remove`.
- **`upgrade`** — met à jour le système : dépôts officiels via `pacman -Syu`, puis AUR via `pamac upgrade --aur`.
- **`lastinstalled`** — derniers paquets installés/supprimés, depuis `/var/log/pacman.log`.
