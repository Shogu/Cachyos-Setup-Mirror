# Radar

Recherche de fichiers avec **aperçu** (texte coloré, images, audio/vidéo, première page PDF), GTK4/libadwaita.

## Technique

- **Python / PyGObject**, fichier unique `usr/bin/radar` (~780 lignes). Paquet `any`, actuel `1.4.0-3`. APP_ID `local.Radar`, desktop `radar.desktop` (pas d'ID reverse-DNS, pas de metainfo).
- libadwaita ≥ 1.5 (`Adw.NavigationPage`, `Adw.ToolbarView`). Optionnels : gtksourceview5 (coloration), gst-plugins-gtk4 (audio/vidéo), poppler (`pdftoppm` pour l'aperçu PDF).
- Le readme et `docs/11` disent « construit autour de `fzf` », mais le code actuel **n'appelle pas fzf** et ne le déclare pas en dépendance : corriger la doc plutôt que réintroduire fzf, sauf demande.
- `url` du PKGBUILD = `https://example.invalid/radar` (placeholder).
- Le readme cite `1.4.0-2`, le paquet est en `-3`.
