# Musicäa

Extension GNOME Shell dédiée au lecteur **Gapless (G4Music)** : indicateur à trois barres dans Quick Settings (animé en lecture, figé en pause), visible tant que Gapless tourne ; suppression des notifications de changement de piste et du bouton « Ouvrir Gapless » ; le clic natif sur la carte média ouvre Gapless.

## Technique

- Livrée en **paquet pacman** (pas en ZIP) : `Musicäa-0.5.0-1-any.pkg.tar.zst`, pkgname `gnome-shell-extension-musicaa`, GPL-2.0-or-later. Installée dans `/usr/share/gnome-shell/extensions/musicaa@ogu.local/` (`extension.js`, `stylesheet.css`, `metadata.json`).
- UUID `musicaa@ogu.local`, version 7 / 0.5.0, `shell-version` 50, 51. Elle enrichit aussi le lecteur média natif du panneau Calendrier/Notifications.
- La 0.5.0 est reconstruite depuis la base **0.2.0** sans les essais de radius/géométrie : **ne pas toucher à la taille, au layout ni à la pochette** de la carte média sans demande explicite.
