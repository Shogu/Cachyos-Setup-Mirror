# Extension Nautilus — « Ouvrir dans Opencode »

Ajoute une entrée **« Ouvrir dans Opencode »** au menu contextuel de Nautilus :
- clic droit sur un **dossier** → ouvre une session `opencode` dessus
- clic droit en **zone vide** d'un dossier → idem pour le dossier courant

Au clic : ouvre `ptyxis -d <dossier> -x opencode`.

## Installation

1. Copier `opencode_open.py` dans :
   ```
   ~/.local/share/nautilus-python/extensions/
   ```
2. Installer la dépendance (une seule fois) :
   ```
   sudo pacman -S nautilus-python
   ```
3. Recharger Nautilus : `nautilus -q`

## Remarques

- API ciblée : Nautilus 51 / nautilus-python 4.x (`get_file_items(files)`, `get_background_items(current_folder)` — plus d'argument `window`).
- L'entrée n'apparaît que si **un seul dossier** est sélectionné.
- Désinstallation : retirer le fichier puis `nautilus -q`.
