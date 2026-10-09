# Fret

Gestionnaire de fichiers GTK4/libadwaita **à deux emplacements** (50/50, non redimensionnables), inspiré de Nautilus, local + GVfs (`ftp://`, `sftp://`, `smb://`). Remplace les anciens noms `periscope` et `torpille` (`replaces`/`conflicts`).

Le `readme_fret.md` est la **spécification de référence** (sections 1 à 13 + historique de 22 demandes). Le lire avant toute modification ; les décisions récentes priment.

## Technique

- **Python / PyGObject**, paquet `any`, actuel `0.2.0-8`. Code : `usr/lib/fret/fret.py` (~3500 lignes, un seul fichier : UI + moteur de transfert), lanceur bash `usr/bin/fret`, `data/home.png`. App id `io.github.fret.Fret`.
- Config : `~/.config/fret/locations.json` (derniers emplacements, favoris, fichiers cachés, réglages Import videos). Jamais de mot de passe d'URI dedans.
- Transferts asynchrones : `os.replace` sur même FS, `copy_file_range` puis fallback GIO, déplacement distant fichier par fichier via `.fret-partial`. Ne jamais supprimer un dossier source non vide.
- Projet source d'origine : `fret.py`, `bin/fret`, `data/`, `install.sh`, `uninstall.sh`, `PKGBUILD`, `build-pkg.sh`, `check.sh` — pas présents ici.

## Choix à ne pas défaire

Double-clic seul pour ouvrir ; pas de libellés gauche/droite ; pas d'onglets ; favoris via bouton étoile visible ; boutons « Copier vers / Couper vers » directs vers le panneau voisin ; pas de notification au démarrage d'un transfert ; mode Œil qui masque l'UI sans suspendre les transferts.

Le readme annonce `0.2.0-1`, le paquet est en `0.2.0-8` : aligner le nom lors de la prochaine mise à jour.
