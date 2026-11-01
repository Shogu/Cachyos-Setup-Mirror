# Battery Time Compact — Ogu

Fork de Battery Time (Percentage) Compact (SaGrLand). Topbar : `9:27 - 56%` ; Quick Settings : `9:27 - 4.2 W` (puissance `UPower.Device.EnergyRate`). Temps inconnu `…`, batterie pleine `∞`.

## Technique

- ZIP `Battery-Time-Compact-Ogu-v54.zip` : `extension.js` (~3,5 Ko), `metadata.json`, LICENSE, README. Pas de préférences ni de schéma.
- **Même UUID que l'upstream** `batterytimepercentagecompact@sagrland.de` (remplacement direct) ; version 54 ; `shell-version` 50, 51.
- Les textes sont réappliqués sur les signaux de mise à jour natifs (pas de timer) et restaurés dans `disable()`. Conserver ce principe.
- Incrémenter `version` et le nom du ZIP (`-v55`…) à chaque livraison.
