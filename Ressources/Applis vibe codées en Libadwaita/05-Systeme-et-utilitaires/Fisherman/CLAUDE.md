# Fisherman

Éditeur GTK4/libadwaita des fichiers de configuration du shell **fish** : `config.fish` et les fonctions (`~/.config/fish/functions/*.fish`).

## Technique

- **Python / PyGObject**, GtkSourceView 5. Paquet `any` `fisherman` (actuel : `0.1.8-7`).
- Structure installée : lanceur `usr/bin/fisherman` (ajoute `/usr/share/fisherman` au `sys.path`), package `usr/share/fisherman/fisherman/` avec `main.py` (~700 lignes, tout le code), `.desktop` et metainfo `io.github.fisherman.Fisherman`.
- Utilise encore `Adw.MessageDialog` (déprécié) : migrer vers `Adw.AlertDialog` si on retouche les dialogues.
- Le readme cite `0.1.8-2` alors que le paquet est en `-7` : corriger le nom de fichier lors de la prochaine mise à jour.
- Les révisions récentes ne portaient que sur l'icône (PNG 512×512 transparent dans hicolor).
