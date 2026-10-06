# Musicäa

Extension GNOME Shell dédiée à **Gapless (G4Music)**.

Version fournie : **0.5.0**, reconstruite à partir de la base **0.2.0** sans reprendre les essais ultérieurs sur le radius ou la géométrie du lecteur.

## Modifications conservées par rapport à la 0.2.0

- indicateur à trois barres dans Quick Settings, animé en lecture et figé en pause ;
- indicateur visible tant que Gapless est présent ;
- suppression des notifications de changement de piste ;
- suppression du bouton dédié « Ouvrir Gapless » ;
- clic natif sur la carte GNOME conservé pour ouvrir Gapless ; les boutons du lecteur gardent leurs actions propres.

Aucun autre changement de taille, de layout ou de rendu de la pochette n’est ajouté.

## Installation

```fish
sudo pacman -U ./Musicäa-0.5.0-1-any.pkg.tar.zst
gnome-extensions enable musicaa@ogu.local
```

Sous Wayland, si nécessaire, se déconnecter puis se reconnecter.
