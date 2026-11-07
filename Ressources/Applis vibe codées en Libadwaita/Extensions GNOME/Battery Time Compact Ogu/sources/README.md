# Battery Time Compact — Ogu v55

Fork local de **Battery Time (Percentage) Compact**, ciblé sur GNOME Shell **50 et 51**.

## Affichage

- **Top bar** : `9:27 - 56%`
  - pourcentage toujours visible ;
  - aucune parenthèse.
- **Quick Settings** : `9:27 - 4.2 W`
  - aucun pourcentage redondant ;
  - puissance instantanée issue de `UPower.Device.EnergyRate`.

Quand UPower ne fournit pas encore d’estimation de temps, `…` est affiché. Batterie pleine : `∞`.

La v55 surcharge `PowerToggle._sync`, appelée par GNOME à chaque changement d’UPower (pourcentage, durée) : le texte personnalisé est donc réappliqué juste après la mise à jour native, sans timer. La puissance instantanée (`EnergyRate`) n’est pas exposée par le proxy UPower de GNOME : un proxy D-Bus dédié la lit et relance la mise à jour à chaque changement.

## Réglages

`gnome-extensions prefs batterytimepercentagecompact@sagrland.de`

- **Barre du haut** : temps - pourcentage (défaut), pourcentage - temps, temps seul (sans pourcentage) ou pourcentage seul.
- **Quick Settings** : afficher ou masquer la puissance instantanée (W) dans le bouton batterie. À la désactivation, les textes natifs reviennent immédiatement. Compatible GNOME 50 et 51.

## Installation

```fish
gnome-extensions install --force ./Battery-Time-Compact-Ogu-v55.zip
gnome-extensions enable batterytimepercentagecompact@sagrland.de
```

Le UUID d’origine est conservé pour remplacer directement l’extension upstream.

## Retour à la version d’origine

Réinstaller simplement le ZIP officiel avec `gnome-extensions install --force`.
