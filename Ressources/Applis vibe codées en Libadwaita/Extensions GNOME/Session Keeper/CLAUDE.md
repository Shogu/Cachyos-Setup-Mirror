# Session Keeper

Adaptation de Session Keeper 1.0.6 (ALT Linux) : sauvegarde continue (événementielle, sans polling) et restauration rapide des applications, fenêtres, géométries, espaces de travail, écrans et états de fenêtres. Restauration dès `startup-complete`, lancement légèrement échelonné.

## Technique

- ZIP `Session-Keeper.zip`, **UUID upstream conservé** `session-keeper@altlinux.org`, version 131, gettext `session-keeper`, schéma `org.gnome.shell.extensions.session-keeper`.
- `extension.js` + `services/sessionManager.js` (~45 Ko, cœur), `services/notificationService.js`, `utils/` (sessionStore — écriture atomique, permissions privées ; bootTracker ; loginSessionTracker ; log), `models/sessionModes.js`, `ui/sessionOnClose.js`, `ui/prefs/generalPage.js` + `debugPage.js`.
- API natives uniquement : GNOME Shell, GJS, Mutter, Gio, GLib. Flush synchrone à la fermeture propre de session.
- **`shell-version` = `["50"]` seulement : ne se charge pas sous GNOME 51** (système actuel).
- Limite : le contenu interne des apps (onglets, documents) n'est restauré que si l'app le gère elle-même.
- Catégorie Extension Manager : Productivité (mot « productivity » dans la description).
