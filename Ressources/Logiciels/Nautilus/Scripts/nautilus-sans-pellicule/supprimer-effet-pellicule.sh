#!/usr/bin/env bash
# =============================================================================
#  supprimer-effet-pellicule.sh
#
#  Supprime l'effet "pellicule / trous de film" (filmholes) superposé par
#  Nautilus (Fichiers) sur les vignettes vidéo.
#
#  Méthode : G_RESOURCE_OVERLAYS  (fonctionne sans sudo, sans modifier les
#  fichiers système, et sans rechargement d'icônes tant que le script n'est
#  pas lancé).
#
#  Modes :
#    install (défaut) : sauvegarde l'original, installe un PNG transparent,
#                       configure GLib, vide le cache des vignettes, relance
#                       Nautilus.
#    restore          : annule proprement (retour à l'effet d'origine).
#    status           : affiche l'état de la configuration.
#    help             : aide.
#
#  Par sécurité : le cache n'est jamais vidé ni Nautilus relancé si une
#  étape précédente a échoué.
# =============================================================================
set -euo pipefail

# Dossier d'où le script est lancé (accueille aussi la sauvegarde)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

NAUTILUS_BIN="$(command -v nautilus || true)"
RES_IMAGE_PATH="/org/gnome/nautilus/image/filmholes.png"
RES_ICONS_PATH="/org/gnome/nautilus/icons/filmholes.png"

OVERLAY_DIR="$HOME/.local/share/nautilus/filmholes-overlay"
TRANSPARENT_FILE="$OVERLAY_DIR/pellicule-transparente.png"

# La sauvegarde vit dans le dossier du script (plutôt que dans ~/Sauvegardes)
BACKUP_DIR="$SCRIPT_DIR/sauvegardes"
BACKUP_FILE="$BACKUP_DIR/filmholes.png"

# configuration d'environnement (moderne, lue par systemd user/GNOME Wayland)
ENVD_DIR="$HOME/.config/environment.d"
ENVD_FILE="$ENVD_DIR/60-nautilus-sans-pellicule.conf"
# configuration traditionnelle (login shell)
PROFILE_FILE="$HOME/.profile"
ENV_MARK="G_RESOURCE_OVERLAYS"
ENV_LINE="$ENV_MARK=$RES_IMAGE_PATH=$TRANSPARENT_FILE:$RES_ICONS_PATH=$TRANSPARENT_FILE"

log() { printf '\033[1;32m[+]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*" >&2; }
err()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; }

require_python() {
  command -v python3 >/dev/null 2>&1 || { err "python3 est requis (introuvable)."; return 1; }
}

# ---------------------------------------------------------------------------
# Générer un PNG entièrement transparent (RGBA) de dimensions données
# ---------------------------------------------------------------------------
make_transparent_png() {
  local w="$1" h="$2" out="$3"
  python3 - "$w" "$h" "$out" <<'PY'
import struct, zlib, sys
w, h = int(sys.argv[1]), int(sys.argv[2])
out = sys.argv[3]
def chunk(typ, data):
    c = struct.pack('>I', len(data)) + typ + data
    return c + struct.pack('>I', zlib.crc32(typ + data) & 0xffffffff)
png = b'\x89PNG\r\n\x1a\n'
png += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))  # 8-bit RGBA
raw = b'\x00' * (h * (w * 4 + 1))  # chaque ligne : filtre 0 + pixels RGBA transparents
png += chunk(b'IDAT', zlib.compress(raw))
png += chunk(b'IEND', b'')
open(out, 'wb').write(png)
print(f'{w}x{h} -> {out}')
PY
}

# ---------------------------------------------------------------------------
# Sauvegarder l'image filmholes d'origine.
# Priorité : 1) gresource (méthode classique)  2) extraction du PNG embarqué
#            dans le binaire Nautilus (méthode de secours pour les builds où
#            la ressource est compilée dans l'ELF et outil gresource absent).
# Ne sauvegarde QUE SI l'original existe (l'original système n'est jamais
# modifié de toute façon). Si on n'y arrive pas, on continue en avertissant.
# ---------------------------------------------------------------------------
backup_original() {
  mkdir -p "$BACKUP_DIR"
  [ -s "$BACKUP_FILE" ] && { log "Sauvegarde déjà présente : $BACKUP_FILE"; return 0; }

  local got=""

  # Méthode A : gresource (outil glib2)
  if command -v gresource >/dev/null 2>&1; then
    for p in "$RES_IMAGE_PATH" "$RES_ICONS_PATH"; do
      if gresource list "$NAUTILUS_BIN" 2>/dev/null | grep -qx "$p"; then
        gresource extract "$NAUTILUS_BIN" "$p" > "$BACKUP_FILE" 2>/dev/null \
          && [ -s "$BACKUP_FILE" ] && { got="gresource"; break; }
      fi
    done
  fi

  # Méthode B : PNG embarqué dans le binaire (binaire nautilus)
  if [ -z "$got" ]; then
    if python3 - "$NAUTILUS_BIN" "$BACKUP_FILE" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
data = open(src, 'rb').read()
sig = b'\x89PNG\r\n\x1a\n'
emb = []
i = 0
while True:
    i = data.find(sig, i)
    if i < 0: break
    end = data.find(b'IEND', i)
    if end < 0: break
    raw = data[i:end + 8]
    # dimensions depuis IHDR (bytes 16..23)
    w = int.from_bytes(data[i+16:i+20], 'big')
    h = int.from_bytes(data[i+20:i+24], 'big')
    emb.append((w, h, raw))
    i += 1
# Le filmholes est une bande/frise étroite (petite largeur). On retient donc le
# PNG embarqué de plus petite largeur, hors icônes/pictogrammes carrés.
cands = [e for e in emb if e[0] <= 24 and e[1] > e[0]]
if not cands:
    cands = emb
if cands:
    cands.sort(key=lambda e: e[0])          # plus petite largeur d'abord
    w, h, raw = cands[0]
    open(dst, 'wb').write(raw)
    print(f'{w}x{h}')
    sys.exit(0)
open(dst, 'wb').close()
sys.exit(1)
PY
      then
        [ -s "$BACKUP_FILE" ] && got="embedded"
      fi
    fi

  if [ -n "$got" ]; then
    log "Original sauvegardé ($got) : $BACKUP_FILE"
  else
    warn "Impossible d'extraire l'image d'origine (outil gresource absent)."
    warn "L'original système n'est PAS modifié ; restore remettra l'effet par"
    warn "simple suppression de la configuration. Sauvegarde : $BACKUP_FILE (vide)."
  fi
}

# ---------------------------------------------------------------------------
# Écrire / mettre à jour la variable d'environnement (de façon idempotente)
# ---------------------------------------------------------------------------
write_env_config() {
  # 1) environment.d (sessions modernes systemd / Wayland) : on réécrit le fichier
  mkdir -p "$ENVD_DIR"
  printf '# Suppression de l\x27effet pellicule (filmholes) de Nautilus.\n' > "$ENVD_FILE"
  printf '%s\n' "G_RESOURCE_OVERLAYS=$RES_IMAGE_PATH=$TRANSPARENT_FILE:$RES_ICONS_PATH=$TRANSPARENT_FILE" >> "$ENVD_FILE"
  log "Config systemd user écrite : $ENVD_FILE"

  # 2) ~/.profile (login shell) : on retire nos anciennes lignes puis on ajoute
  local tmp
  tmp="$(mktemp)"
  if [ -f "$PROFILE_FILE" ]; then
    awk '
      /filmholes/ { next }
      { print }
    ' "$PROFILE_FILE" >> "$tmp"
  fi
  printf '# Suppression de l\x27effet pellicule (filmholes) de Nautilus (géré par script).\n' >> "$tmp"
  printf 'export %s\n' "$ENV_LINE" >> "$tmp"
  mv "$tmp" "$PROFILE_FILE"
  log "Config ~/.profile mise à jour."
}

remove_env_config() {
  # environment.d
  rm -f "$ENVD_FILE"
  # ~/.profile : retirer nos lignes (commentaire + export)
  if [ -f "$PROFILE_FILE" ]; then
    local tmp
    tmp="$(mktemp)"
    awk '
      /filmholes/ { next }
      { print }
    ' "$PROFILE_FILE" > "$tmp" || true
    mv "$tmp" "$PROFILE_FILE"
  fi
  log "Configuration d'environnement supprimée."
}

# ---------------------------------------------------------------------------
# Relancer Nautilus (image en transparence avant re-lancement : l'effet
# disparaît immédiatement dans les fenêtres ouvertes ensuite)
# ---------------------------------------------------------------------------
restart_nautilus() {
  export "$ENV_LINE"
  # rend la variable active dans la session systemd user courante (sans attendre
  # une reconnexion), pour les apps lancées ensuite dans cette session.
  systemctl --user import-environment "$ENV_MARK" 2>/dev/null || true
  pkill -x nautilus 2>/dev/null || true
  sleep 1
  nohup "$NAUTILUS_BIN" >/dev/null 2>&1 &
  log "Nautilus relancé avec l'effet 'pellicule' supprimé."
}

clear_thumbnail_cache() {
  rm -rf "$HOME/.cache/thumbnails"
  log "Cache de vignettes vidé : ~/.cache/thumbnails"
}

# ===========================================================================
cmd_install() {
  [ -n "$NAUTILUS_BIN" ] || { err "Nautilus introuvable."; exit 1; }
  require_python || exit 1
  log "Binaire Nautilus : $NAUTILUS_BIN"

  # 1) sauvegarder l'original d'abord (best-effort), pour en déduire les dimensions
  backup_original

  # dimensions : celles du réel filmholes sauvegardé (sinon défaut 9x35)
  local w=9 h=35
  if [ -s "$BACKUP_FILE" ]; then
    local dh
    dh="$(python3 -c "import struct;d=open('$BACKUP_FILE','rb').read();print(struct.unpack('>II',d[16:24])[0],struct.unpack('>II',d[16:24])[1])" 2>/dev/null || true)"
    if [ -n "$dh" ]; then set -- $dh; w=$1; h=$2; fi
  fi

  # 2) générer le PNG transparent aux dimensions de l'original
  mkdir -p "$OVERLAY_DIR"
  make_transparent_png "$w" "$h" "$TRANSPARENT_FILE"
  [ -s "$TRANSPARENT_FILE" ] || { err "Échec de création du PNG transparent."; exit 1; }
  log "PNG transparent créé ($w x $h) : $TRANSPARENT_FILE"

  # 3) configurer GLib / l'environnement (idempotent)
  write_env_config

  # 4) VÉRIFICATION avant toute action destructive
  [ -s "$TRANSPARENT_FILE" ] || { err "Vérification : PNG transparent absent."; exit 1; }
  [ -f "$ENVD_FILE" ] || { err "Vérification : config environment.d absente."; exit 1; }
  log "Vérifications OK — on peut maintenant vider le cache et relancer."

  # 5) étapes destructives, seulement après succès
  clear_thumbnail_cache
  restart_nautilus

  log "Terminé. L'effet pellicule est supprimé. Déconnexion/reconnexion pour"
  log "le rendre permanent si besoin (la config systemd user s'applique en général déjà)."
}

cmd_restore() {
  remove_env_config
  rm -rf "$OVERLAY_DIR"
  [ -n "$NAUTILUS_BIN" ] && clear_thumbnail_cache && restart_nautilus
  log "Restauré : l'effet pellicule d'origine est de retour."
}

cmd_status() {
  echo "--- PNV transparent ---"
  [ -s "$TRANSPARENT_FILE" ] && echo "  présent : $TRANSPARENT_FILE" || echo "  ABSENT"
  echo "--- environment.d ---"
  [ -f "$ENVD_FILE" ] && { echo "  présent : $ENVD_FILE"; cat "$ENVD_FILE" | sed 's/^/    /'; } || echo "  ABSENT"
  echo "--- ~/.profile ---"
  grep -n "filmholes" "$PROFILE_FILE" 2>/dev/null | sed 's/^/    /' || echo "  aucune ligne"
  echo "--- Sauvegarde ---"
  [ -s "$BACKUP_FILE" ] && echo "  présent : $BACKUP_FILE" || echo "  ABSENT (ou vide)"
}

cmd_help() {
  sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
}

ACTION="${1:-install}"
case "$ACTION" in
  install) cmd_install ;;
  restore) cmd_restore ;;
  status)  cmd_status ;;
  help|-h|--help) cmd_help ;;
  *) err "Mode inconnu : $ACTION (install | restore | status | help)"; exit 1 ;;
esac
