# Copyous — fork GNOME 51

**Version du fork : v16.** Cette version corrige une erreur au chargement : le signal `focus-out` était écouté sur `IBusManager`, alors que cet objet ne fournit pas ce signal. Le branchement fautif est corrigé.

Archive attendue pour cette version : copyous-multiclipboard_shogu-v16.zip.

Ce fork apporte un correctif de transition GNOME 51, un mode **Cumul** du multi-copiage et un sélecteur multi-presse-papiers.

## Nouvelles fonctionnalités

- **Multi-Paste Picker natif Adwaita** : sélecteur multi-presse-papiers présenté dans une fenêtre au rendu natif GNOME/Adwaita, ouvrable avec **Super+V** (raccourci configurable).
- **Sélection multiple** : sélectionner plusieurs entrées avec **Ctrl+clic** ou la **barre Espace** ; des cases à cocher indiquent la sélection.
- **Collage séquentiel** : toutes les entrées sélectionnées sont collées successivement, avec un intervalle de **300 ms**.
- **Aperçu des images** : les entrées contenant des images affichent leur aperçu dans la fenêtre.

## Accès et réglages

Le menu contextuel de l’icône Copyous dans la barre supérieure propose désormais **Multi-Paste Picker**, un interrupteur pour activer ou désactiver le sélecteur, au même titre que **Mode accumule** et **Mode incognito**.

Le raccourci **Super+V** est entièrement configurable dans les préférences et peut être désactivé depuis celles-ci ou depuis le menu contextuel. Le dialogue principal historique reste accessible avec **Super+Shift+V**.

## Évolutions v16 — 12–13 novembre 2026

- Supprime la ligne d’aide inférieure du sélecteur et son séparateur.
- N’affiche le pied de fenêtre (compteur, Annuler, Coller) que lorsqu’au moins un élément est sélectionné.

Ces points restent à valider en session GNOME réelle ; voir le [plan de tests](../../../../docs/tests-extensions.md).

## Installation

La dépendance requise est `libgda6`. Depuis la racine du dépôt :

```fish
sudo pacman -S --needed libgda6
gnome-extensions install --force "Ressources/Applis vibe codées en Libadwaita/Extensions GNOME/Copyous/copyous-gnome51.zip"
gnome-extensions enable copyous@boerdereinar.dev
```

La copie préparée pour le dépôt ajoute `"51"` à `shell-version` dans `metadata.json`. Cette correction de métadonnées ne constitue pas un test fonctionnel : le comportement doit être vérifié dans une session GNOME 51.

**Version précédente documentée :** 2.0.1-mc.11 · **Correctif :** v14
