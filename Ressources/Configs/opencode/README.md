# Config OpenCode (Albert API)

Sauvegarde de la configuration OpenCode pour survivre à une réinstallation.

## Contenu
- `opencode.json` — provider **Albert**, modèles, réglage **effort DeepSeek** (`low`/`medium`/`high`), agents et plugin.
- `plugins/albert-fallback/` — plugin de repli.
- `restore.sh` — restaure le tout dans `~/.config/opencode`.

## Clé API (secret, NON versionnée)
La clé n'est pas dans ce dépôt (voir `.gitignore`). Conserve-la dans un
gestionnaire de mots de passe (KeePassXC, Bitwarden, `pass`…) ou un support chiffré.

## Restauration après une fresh install
1. Installer OpenCode, puis **le lancer une première fois** (crée `~/.config/opencode`).
2. Depuis ce dossier :
   ```fish
   ./restore.sh
   ```
   Le script copie la config et les plugins, puis demande la clé API
   (ou dépose-la dans `~/.config/opencode/secrets/albert.key`, `chmod 600`).
3. Relancer OpenCode. Les variantes d'effort apparaissent via `/models`
   (ex. `albert/deepseek-v4-flash-0731#high`).

## Mise à jour de la sauvegarde
Après toute modification de `~/.config/opencode/opencode.json`, recopier le fichier ici :
```fish
cp ~/.config/opencode/opencode.json ~/Gitlab/CACHYOS-Setup/Ressources/Configs/opencode/
```
