# Nautilus Bookmark Icons

Petite extension pour **GNOME Files (Nautilus 48–50)** permettant de changer l’icône des favoris de la barre latérale sans installer l’ensemble de *Nautilus My Computer*.

Le mécanisme d’injection dans la barre latérale et de maintien de l’icône est extrait et adapté du projet **Nautilus My Computer** de Yann Masoch (licence MIT).

## Fonctionnement

1. Ajouter normalement un dossier aux favoris de Nautilus.
2. Faire un **clic droit** sur ce favori dans la barre latérale.
3. Choisir **Changer l’icône**.
4. Rechercher puis sélectionner une icône symbolique du thème GTK courant.
5. Utiliser **Réinitialiser** pour revenir à l’icône native.

Le choix est persistant via GSettings. L’extension réapplique aussi l’icône lorsque Nautilus reconstruit sa barre latérale.

## Installation

Depuis la racine du dépôt :

```fish
sudo pacman -U "Ressources/Applis vibe codées en Libadwaita/Nautilus Bookmark Icons/nautilus-bookmark-icons-0.1.1-1-any.pkg.tar.zst"
nautilus -q
```

Rouvrir ensuite Nautilus.

## Désinstallation

```fish
sudo pacman -Rns nautilus-bookmark-icons
nautilus -q
```

## Dépendances

- Nautilus 48–50
- `python-nautilus`
- GTK 4 / GLib

## Limite technique

Nautilus ne fournit pas d’API officielle pour modifier les lignes de sa barre latérale. Cette extension utilise donc l’arbre de widgets GTK interne de Nautilus. Une future version majeure peut nécessiter une adaptation.

## Licence et attribution

MIT. Le code relatif aux icônes de favoris est dérivé de **Nautilus My Computer**, Copyright © 2026 Yann Masoch, distribué sous licence MIT.
