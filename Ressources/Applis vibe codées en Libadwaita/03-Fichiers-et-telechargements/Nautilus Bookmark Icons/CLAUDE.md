# Nautilus Bookmark Icons

Extension **nautilus-python** : clic droit sur un favori de la barre latérale de Nautilus → « Changer l'icône » (choix parmi les icônes symboliques du thème) / « Réinitialiser ». Choix persistant via GSettings, réappliqué quand Nautilus reconstruit la barre.

## Technique

- **Python** (`from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk, Nautilus`), fichier unique `usr/share/nautilus-python/extensions/nautilus-bookmark-icons.py`, schéma `io.github.ogu.nautilus-bookmark-icons.gschema.xml`. Paquet `any` 0.1.1-1, MIT.
- Dérivé de **Nautilus My Computer** (Yann Masoch, MIT) : conserver l'attribution.
- Pas d'API officielle : l'extension parcourt l'**arbre de widgets GTK interne** de Nautilus. Fragile à chaque version majeure.
- Dépend de `nautilus>=50`. Le système est en **Nautilus 51** : en cas de bug, vérifier d'abord que la structure interne de la barre latérale n'a pas changé (inspecter avec `GTK_DEBUG=interactive nautilus`).
- Recharger après modification : `nautilus -q` puis relancer Nautilus. Le readme indique « Nautilus 48–50 » : mettre à jour après validation sur 51.
