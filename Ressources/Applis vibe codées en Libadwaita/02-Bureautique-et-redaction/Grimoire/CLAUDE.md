# Grimoire

Éditeur **Markdown** local pour GNOME : dossier épinglé avec navigation en sous-dossiers, sommaire cliquable, modes Code / Scindé / Rendu, recherche-remplacement, insertion de blocs de code (`fish` par défaut, `python`, `systemd`, Sans langage), zoom 70–200 %.

`readme_grimoire.md` contient l'historique des décisions : le lire avant de modifier. Paquet `grimoire-ogu` (actuel `0.2.0-15`, x86_64 mais Python pur), commande `grimoire`, app id `io.github.shogu.Grimoire`, licence MIT.

## Technique

- **Python / PyGObject**, GTK4, libadwaita ≥ 1.8, GtkSourceView 5, **WebKitGTK 6.0** (rendu), python-markdown, Pygments, Bleach.
- Installé : `usr/share/grimoire/grimoire.py` (UI, ~1400 lignes) et `core.py` (documents, I/O, titres, rendu, filtrage HTML), lanceur shell `usr/bin/grimoire`, schéma GSettings `io.github.shogu.Grimoire.gschema.xml`.
- Projet source d'origine : `src/`, `tests/test_core.py`, `tests/test_manual_save.py`, `data/`, `build.py` (assembleur du paquet + `.PKGINFO`/`.MTREE`), `PKGBUILD`. Tests : `python -m unittest discover -s tests -v`.

## Décisions à respecter

- **Pas d'autosauvegarde** (retirée explicitement), enregistrement manuel uniquement, dialogue Enregistrer / Ne pas enregistrer / Annuler.
- **Pas d'export HTML/PDF**, pas de fonction Git/GitLab (retirée en 0.1.6).
- Écriture atomique conservant permissions, BOM, CRLF ; pas d'écrasement si le fichier a changé sur disque.
- Rendu : JavaScript désactivé, HTML filtré, images distantes bloquées.
- Garder cohérentes les versions de l'app, de `build.py`, du `PKGBUILD` et du readme (le readme mentionne encore `-10`).
