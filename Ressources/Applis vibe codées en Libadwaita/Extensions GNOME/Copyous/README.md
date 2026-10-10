# Copyous — fork GNOME 51

Archive fournie : `copyous-gnome51.zip` (à ajouter manuellement à ce dossier).

Le fork apporte un correctif de transition GNOME 51 et un mode **Cumul** du multi-copiage, activable ou désactivable par un toggle dans le menu de l’extension.

La copie préparée pour le dépôt ajoute `"51"` à `shell-version` dans `metadata.json`. Cette correction de métadonnées ne constitue pas un test fonctionnel : le comportement doit encore être vérifié en session GNOME 51.

Installation :

```fish
sudo pacman -S libgda6
gnome-extensions install --force ./copyous-gnome51.zip
gnome-extensions enable copyous@boerdereinar.dev
```
