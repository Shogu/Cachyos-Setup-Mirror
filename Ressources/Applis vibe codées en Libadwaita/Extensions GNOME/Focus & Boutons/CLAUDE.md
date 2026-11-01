# Focus & Boutons

Extension maison Quick Settings / panneau Calendrier : fermeture auto au départ du pointeur (délai réglable, 350 ms), bouton Réglages scindé (Paramètres + menu Ajustements / Éditeur dconf / Extension Manager), bouton Power scindé (Éteindre + Suspendre / Redémarrer / Reconnexion / Verrouiller), masquage optionnel du bouton Capture, du sélecteur de sortie audio, de la colonne « Aucune notification », renommage du profil en « Énergie », carte rendez-vous en couleur d'accent. Boutons scindés bleus seulement tant que leur menu est ouvert.

## Technique

- UUID `focus-et-boutons@ogu`, schéma `org.gnome.shell.extensions.focus-et-boutons`, `shell-version` 50, 51.
- Fichiers : `extension.js` (~25 Ko, l'essentiel), `prefs.js` (libadwaita), `stylesheet.css`, `schemas/` (+ `gschemas.compiled`). Toutes les options s'appliquent à chaud.
- Hors périmètre : volume, micro, sortie audio par défaut (Amplifaya/JamesDSP).

## État des versions — attention

- Le dépôt ne contient que **`Focus-et-Boutons-v12.zip`** (metadata `version: 12`).
- Le readme décrit la **v14**, et le `README.md` racine annonce une **v16** (« Redémarrer la session » → « Reconnexion »). Ces ZIP ne sont pas dans le dépôt.
- Ne jamais renommer le ZIP v12 en v14/v16. Si on reconstruit, partir de la dernière source fournie par Ogu et aligner readme, `docs/` et nom du ZIP.
