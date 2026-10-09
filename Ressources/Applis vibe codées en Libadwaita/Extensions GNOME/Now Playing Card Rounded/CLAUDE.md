# Now Playing Card Rounded

Variante locale de **Now Playing Card** (epogonii, https://github.com/epogonii/nowplaying-card) : indicateur animé + carte média compacte (pochette, barre de progression cliquable, contrôles) pour tout lecteur MPRIS. Variante « rounded », pochette arrondie (`cover20`).

## Technique

- ZIP `nowplaying-card-rounded-cover20.zip`. **UUID upstream conservé** `nowplaying@epogonii.github.io`, version-name 1.0.3, `shell-version` 45 → 51. Schéma `org.gnome.shell.extensions.nowplaying`.
- `extension.js` (~96 Ko), `prefs.js`, `stylesheet.css` + `stylesheet-light.css` / `stylesheet-dark.css` (seuls fichiers modifiés localement, datés du 2 oct.), `icons/qr/` (QR de dons upstream).
- Pas de readme dans ce dossier. Dans le setup, **Musicäa** est l'alternative recommandée (`docs/11` §11.16 « Alternative à Now Playing Card ») ; ne pas activer les deux en même temps.
- Les retouches locales portent sur les CSS : préférer modifier les feuilles de style plutôt que `extension.js`.
