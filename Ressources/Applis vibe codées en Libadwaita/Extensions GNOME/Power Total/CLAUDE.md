# Power Total

Fusion d'**Auto Power Profile** (dmy3k) et **Power Switching Manager** (joseruibarros) : profils énergétiques secteur/batterie (défaut : Performance / Équilibré), profils par application, mémorisation des changements manuels, économie à batterie faible, protection chargeur insuffisant (expérimental), luminosité, thème clair/sombre, rétroéclairage clavier. Modules indépendants, tous désactivés sauf le changement de profil.

## Technique

- ZIP `Power-Total.zip`, UUID `power-total@ogu`, version 2 / 0.1.1, session-modes `user` + `unlock-dialog`.
- `extension.js` + `lib/` : `profiles.js`, `powerState.js`, `policy.js`, `performanceAppTracker.js`, `appearance.js`, `dbus.js` (interface **power-profiles-daemon**, servie ici par tuned-ppd). `prefs.js` libadwaita en français, bouton **Importer** des anciens réglages.
- Trois schémas : `power-total` + ceux des deux extensions d'origine (pour l'import). Tests hors Shell : `tests/test.mjs` avec services simulés (`node tests/test.mjs`, `package.json` présent).
- N'installe aucun daemon, ne touche pas à SCX. Voir `docs/05-performance-tuning.md` §5.1 pour la coordination TuneD/SCX.
- **`shell-version` = `["50"]` seulement : ne se charge pas sous GNOME 51** (système actuel). À corriger en priorité à la prochaine version.
- Non testée en session GNOME réelle. La description doit garder le mot « énergie » (catégorie Système et énergie).
