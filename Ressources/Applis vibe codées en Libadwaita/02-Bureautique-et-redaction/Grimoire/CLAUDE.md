# Grimoire

Éditeur **Markdown** local pour GNOME : dossier épinglé avec navigation en sous-dossiers, sommaire cliquable, modes Code / Scindé / Rendu, recherche-remplacement, insertion de blocs de code (`fish` par défaut, `python`, `systemd`, Sans langage), zoom 70–200 %.

`readme_grimoire.md` contient l'historique des décisions : le lire avant de modifier. Paquet `grimoire-ogu` (actuel `0.3.0-4`, x86_64 mais Python pur), commande `grimoire`, app id `io.github.shogu.Grimoire`, licence MIT.

## Technique

- **Python / PyGObject**, GTK4, libadwaita ≥ 1.8, GtkSourceView 5, **WebKitGTK 6.0** (rendu), python-markdown, Pygments, Bleach.
- Installé : `usr/share/grimoire/grimoire.py` (UI, ~1900 lignes), `core.py` (documents, I/O, titres, rendu, filtrage HTML), `notes.py` (opérations notes/dossiers partagées avec le widget), `search.py` (fournisseur de recherche GNOME) ; lanceur shell `usr/bin/grimoire`, schéma GSettings `io.github.shogu.Grimoire.gschema.xml`.
- **Sources brutes absentes de ce dépôt** : seul le paquet compilé porte le code. La révision actuelle `grimoire-ogu-0.3.0-4-x86_64.pkg.tar.zst` part du `-3` de `~/Projets` (bouton « Nouvelle note », pastilles de dossiers) auquel ont été ajoutées : le double-clic de renommage d'onglet et la resynchronisation du `# H1` via `retitle()` dans `core.py`. Extraire avec `tar --zstd -xf <paquet> -C <cible>` pour lire ou modifier `usr/share/grimoire/*.py`, puis reconstruire l'archive en préservant `.MTREE`, `.PKGINFO`, `.BUILDINFO`, `usr/` (sans `__pycache__`).

## Décisions à respecter

- **Pas d'autosauvegarde** (retirée explicitement), enregistrement manuel uniquement, dialogue Enregistrer / Ne pas enregistrer / Annuler.
- **Pas d'export HTML/PDF**, pas de fonction Git/GitLab (retirée en 0.1.6).
- Écriture atomique conservant permissions, BOM, CRLF ; pas d'écrasement si le fichier a changé sur disque.
- Rendu : JavaScript désactivé, HTML filtré, images distantes bloquées.
- Au renommage d'une note, le premier `# H1` n'est réécrit que s'il est identique à l'ancien nom (fonction `retitle()` dans `core.py`) : un titre écrit à la main est préservé.
