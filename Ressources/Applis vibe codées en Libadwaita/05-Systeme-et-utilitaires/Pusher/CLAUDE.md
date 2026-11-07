# Pusher

Application GTK4/libadwaita de gestion du dépôt **CACHYOS-Setup** : clone, état local/distant, pull et push GitLab.

## Technique

- **Python / PyGObject**, application GTK4/libadwaita, app id `io.gitlab.shogu.Pusher`.
- Dépôt ciblé : `~/Gitlab/CACHYOS-Setup`.
- Jeton GitLab conservé dans le trousseau GNOME via **libsecret**, transmis à Git par `GIT_ASKPASS`. Ne jamais écrire le jeton en clair.
- Dépendances d’exécution : `python`, `python-gobject`, `gtk4`, `libadwaita`, `libsecret`, `git`, `openssh`.
- Version packagée : **1.8.3-1**. La source de référence est `pusher-1.8.3-pusher.py` et le paquet livré est `pusher-1.8.3-1-any.pkg.tar.zst`.
- Construction reproductible avec `makepkg -f` depuis le dossier : `PKGBUILD`, source Python, `pusher-askpass`, fichier desktop et icône SVG.
- **Garde-fou Git 1.8.3 :** `operation_in_progress()` vérifie `git ls-files -u` ainsi que les marqueurs de rebase/merge/cherry-pick/revert. Un index non fusionné bloque pull et push avant le `reset --soft`, y compris si `MERGE_HEAD` n’existe pas.
- Le dépôt concerné est celui-ci : tester Pusher peut pousser réellement sur `Main`. Tester sur un clone ou une branche jetable.
