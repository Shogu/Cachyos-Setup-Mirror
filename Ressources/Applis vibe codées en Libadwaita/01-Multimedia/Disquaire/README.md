# Disquaire

Éditeur de tags MP3 et FLAC pour GNOME, qui ne garde que l'essentiel.

Disquaire conserve sept éléments : **artiste, titre, album, date, genre,
pochette et paroles**. Tout le reste est supprimé à l'enregistrement.

## Fonctions

- Arbre des dossiers à gauche, recherche dans la liste
- Modification de plusieurs morceaux à la fois (ronds de sélection)
- Aperçu et changement de la pochette, par bouton ou glisser-déposer
- Lecture intégrée, ou ouverture dans le lecteur de son choix
- Renommer, déplacer, mettre à la corbeille
- Conversion FLAC → MP3 320 kb/s, 44,1 kHz (le FLAC part à la corbeille)

## Installation

Paquet prêt :

```sh
sudo pacman -U disquaire-1.0.0-1-any.pkg.tar.zst
```

Ou depuis les sources :

```sh
cd disquaire-1.0.0
makepkg -si
```

## Utilisation

Les fichiers qui ont des tags en trop sont marqués d'un point bleu. Rien n'est
modifié sur le disque tant que vous n'enregistrez pas.

En modification groupée, un champ « Valeurs différentes » n'est changé que si
vous écrivez dedans. Plusieurs artistes ou genres se séparent par « ; ».

| Raccourci | Action |
|---|---|
| Ctrl+S | Enregistrer la sélection |
| Ctrl+Maj+S | Tout enregistrer |
| F2 | Renommer le fichier |
| F5 | Rafraîchir la liste |
| Ctrl+F | Rechercher |
| Ctrl+P | Lire / pause |
| Ctrl+A / Échap | Tout cocher / tout décocher |

## Dépendances

python, python-gobject, python-mutagen, gtk4, libadwaita, gstreamer,
gst-plugins-base, gst-plugins-good, ffmpeg.

## Licence

GPL-3.0-or-later
