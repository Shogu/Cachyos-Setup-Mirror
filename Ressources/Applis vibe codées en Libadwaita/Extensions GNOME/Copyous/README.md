# Copyous — fork GNOME 51

Archive fournie : `copyous-gnome51.zip` (à ajouter manuellement à ce dossier).

Le fork apporte un correctif de transition GNOME 51 et un mode **Cumul** du multi-copiage, activable ou désactivable par un toggle dans le menu de l’extension.

La métadonnée `shell-version` de l’archive reçue ne déclare actuellement que GNOME 48, 49 et 50. Avant de présenter l’archive comme compatible GNOME 51, ajouter `"51"` à cette liste, puis vérifier l’extension en session GNOME 51.

Installation :

```fish
sudo pacman -S libgda6
gnome-extensions install --force ./copyous-gnome51.zip
gnome-extensions enable copyous@boerdereinar.dev
```
