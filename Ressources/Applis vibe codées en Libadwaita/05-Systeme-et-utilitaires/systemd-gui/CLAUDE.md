# systemd-gui

Frontend GTK4/libadwaita pour les **services systemd** (système et `--user`). Nom affiché dans GNOME : « systemd » ; commande `systemd-gui`. Ancien nom : Factotum.

`readme_systemd-gui.md` est la spécification détaillée (fonctions, historique, check-list de publication). La suivre.

## Technique

- **Python / PyGObject**. Paquet `any`, actuel `0.4.0-9`. App id installé `io.github.systemd_gui.SystemdGui` (le readme parle encore de `org.gnome.Systemd` : noms de fichiers de l'ancien projet source).
- Installé : `usr/lib/systemd-gui/systemd.py` (app), `usr/lib/systemd-gui/systemd-file-helper` (helper de suppression via polkit), lanceur sh `usr/bin/systemd-gui`.
- `systemctl` / `journalctl` restent la source de vérité, appelés via `subprocess.run([...])` sans shell, noms d'unités validés. Journal : `--lines=20`, repli `pkexec journalctl` si illisible.
- Le helper ne touche jamais `/usr/lib/systemd/system`, `/lib/systemd/system`, `/run/systemd/system`, les fichiers de paquets ni les journaux. Côté utilisateur : uniquement `~/.config/systemd/user` et `~/.local/share/systemd/user`.

## Invariants (check-list du readme)

- Exactement 4 onglets : `overview`, `status`, `unit`, `journal` (l'onglet Propriétés a été retiré, ne pas le recréer).
- Actions confirmées pour arrêt / masquage / désactivation / suppression ; suppression complète = saisie exacte du nom.
- Erreurs affichées dans l'UI, jamais avalées.
- Vérifs : `python3 -B -m py_compile systemd.py systemd-file-helper.py`, `bash -n PKGBUILD`, `sh -n install.sh uninstall.sh run.sh bin/systemd-gui`.
- Nouvelle version : `APP_VERSION` dans `systemd.py`, `pkgver` du PKGBUILD, entrée dans l'appdata, historique du readme.
- Le readme cite `0.4.0-5`, le paquet est en `-9`.
