# Extensions GNOME Shell — consignes communes

Chaque sous-dossier = une extension (ZIP `gnome-extensions install` ou paquet pacman) + readme. Voir aussi le `CLAUDE.md` du dossier parent.

## Cible et technique

- Système : **GNOME Shell 51** (GJS 1.90), cible déclarée 50/51. Extensions **ESM** (`import … from 'gi://St'`, `resource:///org/gnome/shell/…`), classe `export default class extends Extension` avec `enable()`/`disable()` ; préférences `prefs.js` en **libadwaita** (`ExtensionPreferences.fillPreferencesWindow`).
- **`shell-version` dans `metadata.json` doit contenir `"51"`**, sinon GNOME refuse de charger l'extension. Ajouter `"51"` uniquement après relecture des API internes utilisées.
- `disable()` doit tout restaurer : signaux déconnectés, timeouts `GLib.source_remove`, widgets détruits, textes/styles natifs remis.
- Pas de polling si un signal existe. Pas de couleurs codées en dur : classes du thème Shell, variables d'accent.
- Schémas GSettings : `schemas/org.gnome.shell.extensions.<nom>.gschema.xml` + `glib-compile-schemas schemas/` avant de zipper (le `gschemas.compiled` est inclus dans les ZIP).

## Lire / modifier un ZIP

```fish
mkdir -p $scratch/ext; and unzip -o <zip> -d $scratch/ext
node --check $scratch/ext/extension.js   # vérif syntaxe (ESM : renommer en .mjs si besoin)
glib-compile-schemas --strict $scratch/ext/schemas
cd $scratch/ext; and zip -r <Nouveau>.zip .
```

## Tests et installation

- Wayland : après remplacement d'une extension déjà chargée, **déconnexion/reconnexion** obligatoire. Test isolé possible avec `dbus-run-session gnome-shell --devkit --wayland` (GNOME ≥ 49).
- Logs : `journalctl --user -b -o cat /usr/bin/gnome-shell | grep -i <uuid>`.
- Les readmes séparent « syntaxe/schémas vérifiés » et « testé en session réelle » : garder cette distinction.

## Catégories Extension Manager Ogu

Le fork d'Extension Manager classe automatiquement par mots-clés de la `description` : garder les mots-clés voulus (ex. « énergie », « Gestion du bureau et des fenêtres », « productivité ») quand on modifie `metadata.json`.

Documenter toute évolution dans le readme du sous-dossier, `docs/08-gnome-extensions.md` et `docs/11-applications-vibe-coded.md`.
