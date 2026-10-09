# Pusher

App GTK4/libadwaita ultra-basique de gestion du dépôt **CACHYOS-Setup** : le cloner dans `~/Gitlab/CACHYOS-Setup` et pousser les changements sur GitLab. Remplace l'ancien `gitlab-sync`.

## Technique

- **Python / PyGObject**, fichier unique `usr/bin/pusher` (~730 lignes). App id `io.gitlab.shogu.Pusher`, URL https://gitlab.com/Shogu/pusher. Paquet `any`, actuel `1.7.0-2` ; makedepends meson, ninja, glib2-devel, desktop-file-utils, appstream.
- Constantes en tête de fichier : `REPO_URL` (HTTPS) / `REPO_SSH_URL` (`git@gitlab.com:Shogu/CACHYOS-Setup.git`), `REPO_PATH = ~/Gitlab/CACHYOS-Setup`.
- Jeton GitLab stocké dans le trousseau via **libsecret** (`Secret.Schema`), transmis à git par `usr/lib/pusher-askpass` (script sh `GIT_ASKPASS`). Ne jamais écrire le jeton en clair dans un fichier ou un log.
- Dépend de `git` et `openssh`.
- Le dépôt concerné est celui-ci : en tester une modif = risque de pousser réellement sur `Main`. Tester sur un clone ou une branche jetable.
- Le readme cite `1.6.0-1`, `docs/11` cite `1.7.0-1`, le paquet est `1.7.0-2`.
