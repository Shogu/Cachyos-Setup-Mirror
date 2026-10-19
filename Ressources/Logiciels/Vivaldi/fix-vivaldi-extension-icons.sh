#!/usr/bin/env bash
set -Eeuo pipefail

BASE="$HOME/.config/vivaldi/Default/Extensions"
ADWAITA="/usr/share/icons/Adwaita/symbolic"
CACHE="$HOME/.cache/vivaldi-extension-icons"
RAINDROP_ID="ldgfbffkinooeloadekpmfoklnobpien"
UBLOCK_ID="cjpalhdlnbpafiamejdnhcphjbkeiagm"

RAINDROP_ICON="$ADWAITA/status/weather-overcast-symbolic.svg"
COPY_ICON="$ADWAITA/actions/edit-copy-symbolic.svg"

for cmd in find sed rsvg-convert install; do
    command -v "$cmd" >/dev/null || {
        printf 'Erreur : commande manquante : %s\n' "$cmd" >&2
        exit 1
    }
done
for f in "$RAINDROP_ICON" "$COPY_ICON"; do
    [[ -f "$f" ]] || {
        printf 'Erreur : icône introuvable : %s\n' "$f" >&2
        exit 1
    }
done

[[ -d "$BASE/$RAINDROP_ID" ]] || { echo "Erreur : Raindrop introuvable." >&2; exit 1; }
[[ -d "$BASE/$UBLOCK_ID" ]] || { echo "Erreur : uBlock Origin classique introuvable." >&2; exit 1; }

RAINDROP_FILE="$(find "$BASE/$RAINDROP_ID" -type f -path '*/assets/action_chrome_16.png' -print -quit)"
TABCOPY_FILE="$(find "$BASE" -type f -path '*/img/logo-outline-black-16.png' -print -quit)"
UBLOCK_ICON_FILE="$(find "$BASE/$UBLOCK_ID" -type f -path '*/img/icon_16.png' -print -quit)"

[[ -n "$RAINDROP_FILE" ]] || { echo "Erreur : icônes Raindrop introuvables." >&2; exit 1; }
[[ -n "$TABCOPY_FILE" ]] || { echo "Erreur : icônes Tab Copy introuvables." >&2; exit 1; }
[[ -n "$UBLOCK_ICON_FILE" ]] || { echo "Erreur : icônes uBlock introuvables." >&2; exit 1; }

RAINDROP_DIR="$(dirname "$RAINDROP_FILE")"
TABCOPY_IMG="$(dirname "$TABCOPY_FILE")"
UBLOCK_IMG_DIR="$(dirname "$UBLOCK_ICON_FILE")"
mkdir -p "$CACHE"
TMP="$(mktemp -d "$CACHE/run.XXXXXX")"
trap 'rm -rf -- "$TMP"' EXIT

make_png() {
    local source="$1" color="$2" size="$3" output="$4" svg="$TMP/generated.svg"
    sed -e "s/<svg /<svg style=\"color:$color;fill:$color\" /" \
        -e "s/#2e3436/$color/g" -e "s/#222/$color/g" -e "s/currentColor/$color/g" \
        "$source" > "$svg"
    rsvg-convert -w "$size" -h "$size" "$svg" -o "$output"
    [[ -s "$output" ]] || { printf 'Erreur de génération : %s\n' "$output" >&2; return 1; }
}

# Raindrop : nuage blanc.
for size in 16 24 32; do
    make_png "$RAINDROP_ICON" "#ffffff" "$size" "$TMP/raindrop-$size.png"
done

# Tab Copy : variantes noire et blanche.
for color in black white; do
    if [[ "$color" == "black" ]]; then hex="#202124"; else hex="#ffffff"; fi
    for size in 16 32 48 128; do
        make_png "$COPY_ICON" "$hex" "$size" "$TMP/tabcopy-$color-$size.png"
    done
done

# uBlock : cadre carré arrondi continu = actif ; cadre pointillé et u atténué = inactif.
cat > "$TMP/ublock-active.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
  <!-- Cadre extérieur carré arrondi (identique aux autres icônes) -->
  <rect x="1.5" y="1.5" width="13" height="13" rx="3.5" ry="3.5" fill="none" stroke="currentColor" stroke-width="1.5" />
  <!-- Lettre "u" parfaitement calibrée avec la même épaisseur (1.5px) -->
  <path d="M 6 5.5 L 6 9.5 C 6 11, 10 11, 10 9.5 L 10 5.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
</svg>
SVG

cat > "$TMP/ublock-inactive.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
  <!-- Cadre extérieur en pointillés réguliers -->
  <rect x="1.5" y="1.5" width="13" height="13" rx="3.5" ry="3.5" fill="none" stroke="currentColor" stroke-width="1.3" stroke-dasharray="2,2" />
  <!-- Lettre "u" en semi-transparence pour marquer l'inactivité -->
  <path d="M 6 5.5 L 6 9.5 C 6 11, 10 11, 10 9.5 L 10 5.5" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" opacity="0.4" />
</svg>
SVG

for size in 16 32; do
    make_png "$TMP/ublock-active.svg" "#ffffff" "$size" "$TMP/ublock-active-$size.png"
    make_png "$TMP/ublock-inactive.svg" "#ffffff" "$size" "$TMP/ublock-inactive-$size.png"
done

# Vérifier toutes les destinations avant toute modification.
for size in 16 24 32; do
    [[ -f "$RAINDROP_DIR/action_chrome_$size.png" ]] || { echo "Icône Raindrop manquante : $size" >&2; exit 1; }
done
for color in black white; do
    for size in 16 32 48 128; do
        [[ -f "$TABCOPY_IMG/logo-outline-$color-$size.png" ]] || { echo "Icône Tab Copy manquante : $color $size" >&2; exit 1; }
    done
done
for size in 16 32; do
    [[ -f "$UBLOCK_IMG_DIR/icon_$size.png" ]] || { echo "Icône uBlock manquante : icon_$size.png" >&2; exit 1; }
    [[ -f "$UBLOCK_IMG_DIR/icon_$size-off.png" ]] || { echo "Icône uBlock manquante : icon_$size-off.png" >&2; exit 1; }
done

for size in 16 24 32; do
    install -m 600 "$TMP/raindrop-$size.png" "$RAINDROP_DIR/action_chrome_$size.png"
done
for color in black white; do
    for size in 16 32 48 128; do
        install -m 600 "$TMP/tabcopy-$color-$size.png" "$TABCOPY_IMG/logo-outline-$color-$size.png"
    done
done
for size in 16 32; do
    install -m 600 "$TMP/ublock-active-$size.png" "$UBLOCK_IMG_DIR/icon_$size.png"
    install -m 600 "$TMP/ublock-inactive-$size.png" "$UBLOCK_IMG_DIR/icon_$size-off.png"
done

printf '\nIcônes remplacées avec succès.\n'
printf 'Raindrop : %s\nTab Copy : %s\nuBlock Origin : %s\n' "$RAINDROP_DIR" "$TABCOPY_IMG" "$UBLOCK_IMG_DIR"
printf 'Aucune sauvegarde des originaux créée.\n'
