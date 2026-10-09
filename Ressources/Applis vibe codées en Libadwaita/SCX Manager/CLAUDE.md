# SCX Manager — Libadwaita

Réécriture GTK4/libadwaita de SCX Manager : lit et pilote **`scx_loader`** (D-Bus système `org.scx.Loader`, objet `/org/scx/Loader`) qui gère les ordonnanceurs **sched-ext**. Choix du scheduler, profil (0 Auto, 1 Gaming, 2 Power Save, 3 Low Latency, 4 Server) ou arguments personnalisés ; Appliquer / Désactiver / Restaurer par défaut / Actualiser.

## Technique

- **C11**, fichier unique `src/main.c` (~37 Ko), build **Meson + Ninja**. Version 0.1.2. App id `org.cachyos.scx-manager-adwaita`.
- Seul projet du dossier livré **en sources** : `scx-manager-adwaita-0.1.2-pacman.zip` contient `meson.build`, `src/main.c`, `data/` (desktop + 2 SVG dont `…-active-symbolic`), `build.sh`, `install.sh`, `uninstall.sh`, `PKGBUILD`, tarball source et README. Aucun `.pkg.tar.zst` précompilé.
- Build : `./build.sh` (→ `build/scx-manager-adwaita`) ou `makepkg -s`. Extraire le ZIP dans le scratchpad pour travailler.
- Méthodes D-Bus : `StartScheduler[WithArgs]`, `SwitchScheduler[WithArgs]`, `StopScheduler`, `RestoreDefault` ; propriétés `CurrentScheduler`, `DefaultScheduler`, `SchedulerMode`, `DefaultMode`, `CurrentSchedulerArgs`, `SupportedSchedulers`. Arguments passés en tableau D-Bus, jamais via un shell.
- Diagnostic : `gdbus call --system --dest org.scx.Loader --object-path /org/scx/Loader --method org.freedesktop.DBus.Properties.GetAll org.scx.Loader`.

## Pièges connus

- API GTK/Adw récentes : `adw_application_window_set_content()` (pas `gtk_window_set_child`), `gtk_css_provider_load_from_string()`, pas de `gtk_editable_set_placeholder_text()`.
- Cas Pandemonium : `CurrentSchedulerArgs == []` → afficher `DefaultMode` comme profil effectif (interprétation d'affichage seulement).
- Hors périmètre : EPP AMD, tuned/tuned-ppd, écoute de `PropertiesChanged`.
