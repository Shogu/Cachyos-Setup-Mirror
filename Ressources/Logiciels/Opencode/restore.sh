#!/usr/bin/env bash
# Restaure la configuration OpenCode (provider Albert, effort DeepSeek, plugin)
# depuis ce dossier vers ~/.config/opencode.
# La clé API n'est PAS stockée dans le dépôt : elle est demandée ou doit être
# déposée manuellement dans ~/.config/opencode/secrets/albert.key.
set -euo pipefail

src="$(cd "$(dirname "$0")" && pwd)"
dest="${XDG_CONFIG_HOME:-$HOME/.config}/opencode"

mkdir -p "$dest/secrets" "$dest/plugins"

cp "$src/opencode.json" "$dest/opencode.json"
cp -a "$src/plugins/." "$dest/plugins/"

keyfile="$dest/secrets/albert.key"
if [ ! -s "$keyfile" ]; then
  if [ -t 0 ]; then
    printf "Clé API Albert (laisser vide pour ignorer) : "
    read -rs key
    echo
    if [ -n "${key:-}" ]; then
      printf '%s\n' "$key" > "$keyfile"
    fi
  fi
fi

if [ -s "$keyfile" ]; then
  chmod 600 "$keyfile"
  echo "✓ Config OpenCode restaurée dans $dest (clé API en place)"
else
  echo "✓ Config OpenCode restaurée dans $dest"
  echo "⚠️  Clé API manquante : place-la dans $keyfile (chmod 600)"
  echo "    ou relance ce script dans un terminal pour la saisir."
fi
