# Snapper-GTK4

Frontend GTK4/libadwaita pour **Snapper + Limine** (`limine-snapper-sync`) : liste et filtre des snapshots (Tous / Avant / Après), création, suppression, restauration, réglages de nettoyage `number` / `timeline` / paires vides, activation des timers systemd Snapper, nettoyage manuel.

## Technique

- **Python / PyGObject**, fichier unique `usr/bin/snapper-gtk4` (~1760 lignes). APP_ID `io.github.Shogu.SnapperGtk4`. Paquet `any`, actuel `1.4.0-5`.
- Toutes les actions privilégiées passent par `usr/lib/snapper-gtk4/snapper-gtk4-helper` (Python, root) via `pkexec`, action polkit `io.github.Shogu.SnapperGtk4.policy`.
- La restauration n'est pas réimplémentée : elle s'appuie sur les outils Snapper/Limine.
- Dépendances : snapper, limine-snapper-sync, polkit, util-linux.
- Pas de readme dans ce dossier ; la doc est `docs/11-applications-vibe-coded.md` §11.14 (créer un `readme_snapper-gtk4.md` si on documente une évolution).
- Données sensibles (restauration du système) : toute action destructive doit garder une confirmation `Adw.AlertDialog` en `DESTRUCTIVE`.
