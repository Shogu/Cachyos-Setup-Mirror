# Pusher

Application GTK4/libadwaita de gestion du dépôt **CACHYOS-Setup** : clone, vérification de l’état local/distant, pull et push GitLab.

## Technique

- **Python / PyGObject**, application GTK4/libadwaita, app id `io.gitlab.shogu.Pusher`.
- Dépôt ciblé : `~/Gitlab/CACHYOS-Setup`.
- Jeton GitLab stocké dans le trousseau via **libsecret**, transmis à git par `GIT_ASKPASS`. Ne jamais écrire le jeton en clair dans un fichier ou un log.
- Dépend de `git` et `openssh`.
- Le code source de référence est `pusher-1.8.3-pusher.py`. Le paquet binaire encore présent dans le dépôt est `pusher-1.8.2-1-any.pkg.tar.zst` ; reconstruire 1.8.3 pour intégrer le correctif de conflit d’index.
- **Garde-fou Git 1.8.3 :** `operation_in_progress()` contrôle `git ls-files -u` en plus des marqueurs de rebase/merge/cherry-pick/revert. Un index non fusionné bloque pull et push avant le `reset --soft`.
- Le dépôt concerné est celui-ci : tester une modification de Pusher peut pousser réellement sur `Main`. Tester sur un clone ou une branche jetable.
