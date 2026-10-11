# Decibel

Fork de **Decibels** (lecteur audio GNOME, https://apps.gnome.org/Decibels/) renommé `decibel` / `org.gnome.Decibel`.

Modifications maison :
- `Suppr` supprime le titre courant ;
- ouvrir un nouveau fichier audio remplace le morceau dans la fenêtre existante (pas de seconde fenêtre).

## Technique

- **GJS** (upstream en TypeScript compilé en JS), GStreamer, GTK4/libadwaita. Paquet `any` ; le code est empaqueté dans `usr/share/org.gnome.Decibel/org.gnome.Decibel.src.gresource` (extraire avec `gresource list|extract`).
- Paquet `decibel-49.6.1-1` : base upstream 49.x, `conflicts`/`replaces` = `decibels`.
- Build upstream : Meson + Ninja (+ TypeScript via npm). Les sources du fork ne sont pas ici.
- Pour une mise à jour vers GNOME 50/51 : repartir de la version upstream correspondante et ré-appliquer les deux patchs ci-dessus, sans autres changements.
