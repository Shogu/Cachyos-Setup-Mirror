# Showtime — correctif des sauts vidéo

Ce dossier conserve le correctif local de `showtime/widgets/window.py` pour adapter les sauts de recherche à la durée totale de la vidéo.

## Comportement visé

- **← / →** : environ 1 % de la durée totale.
- **↑ / ↓** : environ 5 % de la durée totale.

Le fichier corrigé `window.py` est à déposer manuellement dans ce dossier. Il n'est pas inclus dans le dépôt tant qu'il n'a pas été ajouté.

## Installation

Depuis la racine du dépôt, après avoir ajouté `window.py` dans ce dossier :

```fish
sudo cp "Ressources/Applis vibe codées en Libadwaita/01-Multimedia/Showtime/window.py" (pacman -Ql showtime | string match -r '\S+/widgets/window\.py$')
```

La copie remplace le fichier Python fourni par le paquet. Une mise à jour de Showtime peut écraser ce correctif ; réappliquer la commande après vérification du nouveau chemin installé.

## Vérification

```fish
cat /usr/lib/python3.14/site-packages/showtime/widgets/window.py
grep -n -i "sauts" /usr/lib/python3.14/site-packages/showtime/widgets/window.py
```

La recherche doit retrouver le marqueur `sauts` dans le fichier installé. Si la version de Python change, déterminer le chemin réel avec :

```fish
pacman -Ql showtime | string match -r '\S+/widgets/window\.py$'
```

Le correctif doit encore être ajouté et testé sur la machine cible.
