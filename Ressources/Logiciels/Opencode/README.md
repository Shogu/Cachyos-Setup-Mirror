# Config OpenCode — sauvegarde

Sauvegarde de la configuration OpenCode pour survivre à une réinstallation.
Aucune clé API ici (voir `.gitignore`).

## Contenu
- `opencode-backup-20261115.zip` : `opencode.json`, `cli.json`, `AGENTS.md`, `command/`, `plugins/albert-fallback/`.
- `.gitignore` : exclut les clés (`albert.key`, `secrets/`).

## Clés API (secrets, NON versionnées)
Les clés sont dans l'archive chiffrée stockée sur Dropbox : `DOMESTIQUE/INFORMATIQUE/opencode-secrets-20261115.7z`.
Voir `README-opencode-secrets.md` dans le même dossier.

## Restauration après une fresh install
1. Installer OpenCode, puis le lancer une fois (crée `~/.config/opencode`).
2. Décompresser le zip dans `~/.config/opencode/` :
   ```fish
   python3 -m zipfile -e ~/Gitlab/CACHYOS-Setup/Ressources/Logiciels/Opencode/opencode-backup-20261115.zip /tmp/opencode-restore
   cp -r /tmp/opencode-restore/opencode/* ~/.config/opencode/
   ```
3. Extraire les clés depuis l'archive chiffrée Dropbox (voir son README).
4. Dans OpenCode : `/connect` pour GitHub Copilot (OAuth), puis `/models`.

## Mise à jour de la sauvegarde
Après un changement de configuration, recréer le zip avec les fichiers de `~/.config/opencode/` (`opencode.json`, `cli.json`, `AGENTS.md`, `command/`, `plugins/`) et remplacer l'ancien zip.
