# Showtime — astuce d’interface

Ce dossier conserve un petit correctif local du lecteur vidéo GNOME Showtime. Ce n’est pas une application vibe coded : il s’agit uniquement d’une personnalisation du comportement de recherche au clavier.

## Comportement

- **← / →** : saut d’environ **1 %** de la durée totale de la vidéo (minimum 5 s).
- **↑ / ↓** : saut d’environ **5 %** de la durée totale de la vidéo (minimum 30 s).
- **Maj + ← / →** : saut fixe de **10 s** pour l’ajustement fin.
- **Volume** : déplacé sur `Ctrl + ↑ / ↓` (les flèches ↑/↓ sont réutilisées pour les sauts de 5 %).

Les pourcentages sont calculés par rapport à la durée du média, pour que les déplacements s’adaptent aux vidéos courtes comme aux longues (avec un saut minimal en secondes).

## Fichier à déposer

Place le fichier Python corrigé ici, à côté de ce README :

`Ressources/Logiciels/Players/Showtime/window.py`

## Installation

Depuis la racine du dépôt :

```fish
sudo cp "Ressources/Logiciels/Players/Showtime/window.py" (pacman -Ql showtime | string match -r '\S+/widgets/window\.py$')
```

Cette commande remplace le fichier `window.py` installé par le paquet Showtime.

## Vérification

```fish
cat /usr/lib/python3.14/site-packages/showtime/widgets/window.py
grep -n -i "sauts" /usr/lib/python3.14/site-packages/showtime/widgets/window.py
```

La recherche doit retrouver le marqueur `sauts` dans le fichier installé. Si le chemin diffère, retrouve le chemin fourni par le paquet :

```fish
pacman -Ql showtime | string match -r '\S+/widgets/window\.py$'
```

## ⚠️ Après une mise à jour de Showtime — ré-appliquer, ne pas réécrire l’ancien fichier

Une mise à jour du paquet remplace `window.py` et **efface le correctif**. Pour le ré-appliquer :

1. **Ne jamais poser l’ancien `window.py` entier en lieu et place du nouveau.** Le fichier de ce dossier reflète la version actuellement installée : une mise à jour de Showtime fait évoluer `window.py` (API, connecteurs, gestion des plugins…). Régresser tout le fichier à une version antérieure casse le lancement de Showtime.
2. **Ré-injecter uniquement les blocs du correctif** sur le `window.py` **neuf** du paquet. Le cœ ur du correctif tient en deux parties :

   - les deux méthodes `_seek_by()` et `_seek_by_percent()` (sauts par % de durée et saut minimal en secondes) à insérer dans la classe `Window`, juste avant `_create_actions()` ;
   - dans `_create_actions()`, remplacer les actions `backwards` / `forwards` et les raccourcis volume par les raccourcis proportionnels (voir le comportement ci-dessus).

3. Tester avec `showtime` puis, le cas échéant, mettre à jour ce dossier avec le nouveau `window.py` corrigé pour qu’il reste aligné sur la version installée.

Le marqueur `sauts` sert justement à vérifier que le correctif est bien présent après installation.
