# Battery Time Compact — Ogu v53

Fork local de **Battery Time (Percentage) Compact**, ciblé sur GNOME Shell **50 et 51**.

## Affichage

- **Top bar** : `9:27 - 56%`
  - pourcentage toujours visible ;
  - aucune parenthèse.
- **Quick Settings** : `9:27 - 4.2 W`
  - aucun pourcentage redondant ;
  - puissance instantanée issue de `UPower.Device.EnergyRate`.

Quand UPower ne fournit pas encore d’estimation de temps, `…` est affiché. Batterie pleine : `∞`.

La v53 renforce la synchronisation : GNOME effectue d’abord sa mise à jour native, puis l’extension réapplique le texte personnalisé. Une écoute explicite de `EnergyRate` actualise également les watts lorsque la puissance varie sans autre changement d’état de la batterie.

## Installation

```fish
gnome-extensions install --force ./Battery-Time-Compact-Ogu-v53.zip
gnome-extensions enable batterytimepercentagecompact@sagrland.de
```

Le UUID d’origine est conservé pour remplacer directement l’extension upstream.

## Retour à la version d’origine

Réinstaller simplement le ZIP officiel avec `gnome-extensions install --force`.
