# Always on top, always on top

Une icône dans la zone d'état de la topbar : clic = `make_above()` / `unmake_above()` sur la fenêtre active (la fonction native « Toujours au premier plan » de Mutter). Inactif : icône `radio-symbolic` ; actif : icône symbolique de l'app épinglée (mapping prioritaire Ptyxis, Text Editor, Nautilus, Showtime, Grimoire, sinon `<icon>-symbolic`, sinon `application-x-executable-symbolic`). Suit la fenêtre épinglée, pas le focus.

## Technique

- ZIP `always-on-top-always-on-top-v18-radio-checked.shell-extension.zip`. UUID `always-on-top-always-on-top@localhost`, version 18, gettext (`po/fr.po`, `locale/`).
- Un seul `extension.js` (~8,6 Ko) + `stylesheet.css` (classe `aot-indicator`, largeur réglée via `-natural-hpadding` / `-minimum-hpadding`, pas `padding`).
- Zéro préférence, zéro menu, zéro icône embarquée (`Gio.ThemedIcon`).
- **`shell-version` = 45 → 50 : ne se charge pas sous GNOME 51** (système actuel). Prochaine version : ajouter `"51"` après vérification, et remplacer l'URL placeholder `CHANGE-ME` du metadata.
- Le readme dit `UUID@localhost.shell-extension.zip` mais le fichier réel s'appelle `…-v18-radio-checked…zip`.
