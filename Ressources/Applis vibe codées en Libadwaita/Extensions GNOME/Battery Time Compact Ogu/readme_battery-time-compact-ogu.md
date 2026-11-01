# Battery Time Compact — Ogu v54

Fork de [Battery Time (Percentage) Compact](https://github.com/SaGrLand/gnome-shell-battery-time-percentage-compact) pour GNOME Shell 50 et 51, remplaçant directement la version habituelle avec le même UUID.

- Barre supérieure : `9:27 - 56%`.
- Quick Settings : `9:27 - 4.2 W`, puissance fournie par `UPower.Device.EnergyRate`.
- Temps indisponible : `…` ; batterie pleine : `∞`. Si la puissance est nulle ou indisponible, seuls les temps sont affichés dans Quick Settings.
- Textes réappliqués après les mises à jour natives, sans timer supplémentaire ; restauration à la désactivation.

Depuis la racine du dépôt :

```fish
gnome-extensions install --force "Ressources/Applis vibe codées en Libadwaita/Extensions GNOME/Battery Time Compact Ogu/Battery-Time-Compact-Ogu-v54.zip"
gnome-extensions enable batterytimepercentagecompact@sagrland.de
```

Fermer puis rouvrir la session GNOME sous Wayland après remplacement d’une version déjà chargée. UUID : `batterytimepercentagecompact@sagrland.de`. Réinstaller le ZIP upstream pour revenir à l’original.

Archive et code inspectés ; fonctionnement à confirmer dans la session GNOME cible.
