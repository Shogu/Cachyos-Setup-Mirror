# Applis sans sources récupérables

Généré le 07/11/2026.

Ces applis livrent un **binaire compilé** (ou un code GJS/autre embarqué dans un bundle
non extractible simplement) et **aucun arbre de sources n'est inclus** dans l'archive.
Les sources ne sont donc pas récupérables depuis le paquet/zip.

| Appli | Raison |
|---|---|
| **Amplifaya** | paquet LADSPA en C (`amplifaya.so` compilé) — pas de source dans le paquet |
| **Dactylo** | binaire ELF compilé (C/GTK4) — pas de source dans le paquet |
| **dconf-editor GTK4** | binaire C — projet upstream GNOME |
| **Decibel** | GJS compilé dans un bundle **GVariant/gresource** (`org.gnome.Decibel.src.gresource`) non extractible simplement — projet upstream GNOME (source dispo sur gitlab.gnome.org) |
| **Extension Manager** | binaire ELF compilé — fork upstream (mattjakeman) |
| **Grille** | binaire ELF compilé — pas de source dans le paquet |
| **Polaroid** | binaire ELF compilé — pas de source dans le paquet |
| **Semitone** | binaire ELF compilé — pas de source dans le paquet |
| **nautilus-vignettes-arrondies-sushi** (sous Thumbnailer Sushi) | `.so` compilé — pas de source dans le paquet |

## Notes

- **Icônes UI** et **PLACES** : livrés en `.pyz` (zipapp python) — le code Python est
  **embarqué** dans le `.pyz` (le zipapp EST la source) ; il a été extrait dans `sources/`
  pour un versionnage plus lisible, mais ce n'est pas un « vrai » arbre de sources séparé.
- Pour les applis upstream (Decibel, dconf-editor, Extension Manager), les sources
  officielles existent en amont si tu veux les référencer plus tard.
- Si tu retrouves les arbres de sources d'origine des applis compilées (Dactylo, Grille,
  Semitone, Polaroid, Amplifaya), dépose-les dans `sources/` et je les intégrerai.
