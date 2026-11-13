# Showtime — astuce d’interface

Ce dossier conserve un petit correctif local du lecteur vidéo GNOME Showtime. Ce n’est pas une application vibe coded : il s’agit uniquement d’une personnalisation du comportement de recherche au clavier.

## Comportement

- **← / →** : saut d’environ 1 % de la durée totale de la vidéo.
- **↑ / ↓** : saut d’environ 5 % de la durée totale de la vidéo.

Le pourcentage est calculé par rapport à la durée du média, pour que les déplacements s’adaptent aux vidéos courtes comme aux longues.

## Fichier à déposer

Place le fichier Python corrigé ici, à côté de ce README :

`Ressources/Logiciels/Players/Showtime/window.py`

## Installation

Depuis la racine du dépôt :

```fish
sudo cp "Ressources/Logiciels/Players/Showtime/window.py" (pacman -Ql showtime | string match -r '\\S+/widgets/window\\.py$')
```

Cette commande remplace le fichier `window.py` installé par le paquet Showtime. Une mise à jour du paquet peut écraser le correctif.

## Vérification

```fish
cat /usr/lib/python3.14/site-packages/showtime/widgets/window.py
grep -n -i "sauts" /usr/lib/python3.14/site-packages/showtime/widgets/window.py
```

La recherche doit retrouver le marqueur `sauts` dans le fichier installé. Si le chemin diffère, retrouve le chemin fourni par le paquet :

```fish
pacman -Ql showtime | string match -r '\\S+/widgets/window\\.py$'
```

Le fichier corrigé doit être ajouté manuellement ; le correctif n’est pas inclus dans ce README et doit être testé après installation.
