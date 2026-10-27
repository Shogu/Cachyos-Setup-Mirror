# Pacto

Gestion des fichiers pacman **`.pacnew` / `.pacsave`** : collecte, tri, comparaison avec le fichier en service (diff), édition, remplacement, suppression.

## Technique

- **Python / PyGObject**, GTK4/libadwaita, polkit pour les écritures dans `/etc`. Build **Meson + Ninja** (makedepends). Paquet `any`, actuel `1.0.0-4`. App id `io.github.ugotrevisiol.Pacto`, URL https://github.com/ugotrevisiol/pacto.
- Package installé `usr/share/pacto/pacto/` : `application.py`, `window.py`, `scanner.py` (recherche des fichiers), `files.py` (opérations fichiers), `diff.py` (calcul), `diffview.py` (affichage), `style.css`, `__main__.py`.
- Le readme cite `1.0.0-1` alors que le paquet est en `-4`.
- Opérations destructrices (remplacement, suppression d'un fichier de config système) : toujours confirmer via `Adw.AlertDialog` et passer par polkit, jamais par un lancement en root.
