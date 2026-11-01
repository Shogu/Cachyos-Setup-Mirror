# Polaroid

**Polaroid** est une visionneuse d’images pour GNOME, basée sur un fork de [Loupe](https://gitlab.gnome.org/GNOME/loupe). Elle est écrite en Rust avec GTK4 et libadwaita et remplace le paquet `loupe` dans ce setup.

## Fonctions

- Visionneuse : zoom, navigation entre les images d’un dossier, propriétés et impression.
- Annotations : flèches, cercles, rectangles, traits, dessin libre et étiquettes de texte en six couleurs.
- Les étiquettes se déplacent à la souris et se modifient par double-clic.
- Recadrage, rotation et retournement.
- Annuler / rétablir : `Ctrl+Z` et `Ctrl+Maj+Z`.

## Captures d’écran

1. Faire une capture d’écran avec GNOME.
2. Cliquer sur sa notification pour l’ouvrir dans Polaroid.
3. Cliquer sur le bouton de recadrage pour ouvrir l’éditeur, puis annoter.
4. Cliquer sur **Remplacer** :
   - le fichier est remplacé par la version annotée ;
   - l’image annotée est copiée dans le presse-papiers ;
   - l’original est conservé sept jours dans `~/.cache/polaroid/originals/`.

## Installation

Ajouter manuellement le paquet compilé `polaroid-51.1.0-1-x86_64.pkg.tar.zst` dans ce dossier. Depuis la racine du dépôt, désinstaller Loupe puis installer Polaroid :

```fish
sudo pacman -Rns loupe
sudo pacman -U "Ressources/Applis vibe codées en Libadwaita/01-Multimedia/Polaroid/polaroid-51.1.0-1-x86_64.pkg.tar.zst"
```

Lancer l’application avec `polaroid`, ou depuis la grille d’applications GNOME.

## Licence

GPL-3.0-or-later, comme Loupe.
