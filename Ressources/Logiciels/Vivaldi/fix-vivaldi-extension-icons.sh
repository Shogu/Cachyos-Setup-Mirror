#!/usr/bin/env bash
# Remplace les icônes de Raindrop, Tab Copy et uBlock Origin dans un profil Vivaldi.
#
# Chaque extension est traitée indépendamment : une extension absente, ou dont les
# icônes sont introuvables, est ignorée sans interrompre le traitement des autres.
#
# Chemins et identifiants surchargeables par l'environnement (utile pour tester) :
#   BASE, ADWAITA, CACHE, RAINDROP_ID, TABCOPY_ID, UBLOCK_ID
set -Eeuo pipefail


BASE="\${BASE:-$HOME/.config/vivaldi/Default/Extensions}"
ADWAITA="\${ADWAITA:-/usr/share/icons/Adwaita/symbolic}"
CACHE="\${CACHE:-$HOME/.cache/vivaldi-extension-icons}"

RAINDROP_ID="\${RAINDROP_ID:-ldgfbffkinooeloadekpmfoklnobpien}"
UBLOCK_ID="\${UBLOCK_ID:-cjpalhdlnbpafiamejdnhcphjbkeiagm}"
# L'ID de Tab Copy (visible sur vivaldi://extensions). Vide, Tab Copy est cherchée
# dans tout le profil par le nom de ses fichiers : renseigne-le pour éviter
# qu'une autre extension possédant le même chemin d'image soit modifiée à sa place.
TABCOPY_ID="\${TABCOPY_ID:-}"

RAINDROP_ICON="$ADWAITA/status/weather-overcast-symbolic.svg"
COPY_ICON="$ADWAITA/actions/edit-copy-symbolic.svg"

# Codes de retour des traitements, pour distinguer pourquoi une extension est sautée.
FAIT=0
ABSENTE=1
INUSABLE=2


for cmd in find sed rsvg-convert install; do
    command -v "$cmd" >/dev/null || {
        printf 'Erreur : commande manquante : %s\n' "$cmd" >&2
        exit 1
    }
done

[[ -d "$BASE" ]] || {
    printf 'Erreur : profil Vivaldi introuvable : %s\n' "$BASE" >&2
    exit 1
}


mkdir -p "$CACHE"
TMP="$(mktemp -d "$CACHE/run.XXXXXX")"
trap 'rm -rf -- "$TMP"' EXIT


make_png() {
    local source="$1" color="$2" size="$3" output="$4"
    local svg="$TMP/generated-$(basename -- "$output").svg"
    sed -e "s/<svg /<svg style=\"color:$color;fill:$color\" /" \
        -e "s/#2e3436/$color/g" -e "s/#222/$color/g" -e "s/currentColor/$color/g" \
        "$source" > "$svg"
    rsvg-convert -w "$size" -h "$size" "$svg" -o "$output"
    [[ -s "$output" ]] || {
        printf 'Erreur de génération : %s\n' "$output" >&2
        return 1
    }
}

# Les originaux ne sont jamais sauvegardés : chaque fonction vérifie donc toutes
# ses destinations avant d'écrire quoi que ce soit, pour ne rien laisser à moitié fait.


traiter_raindrop() {
    [[ -d "$BASE/$RAINDROP_ID" ]] || return "$ABSENTE"
    [[ -f "$RAINDROP_ICON" ]] || { printf 'motif absent : %s\n' "$RAINDROP_ICON"; return "$INUSABLE"; }

    local fichier dossier taille
    fichier="$(find "$BASE/$RAINDROP_ID" -type f -path '*/assets/action_chrome_16.png' -print -quit)"
    [[ -n "$fichier" ]] || { printf 'icônes introuvables dans l’extension\n'; return "$INUSABLE"; }
    dossier="$(dirname -- "$fichier")"

    for taille in 16 24 32; do
        [[ -f "$dossier/action_chrome_$taille.png" ]] || { printf 'destination manquante : action_chrome_%s.png\n' "$taille"; return "$INUSABLE"; }
    done
    for taille in 16 24 32; do
        make_png "$RAINDROP_ICON" "#ffffff" "$taille" "$TMP/raindrop-$taille.png" || return "$INUSABLE"
    done
    for taille in 16 24 32; do
        install -m 600 "$TMP/raindrop-$taille.png" "$dossier/action_chrome_$taille.png" || return "$INUSABLE"
    done

    printf '%s\n' "$dossier"
}


traiter_tabcopie() {
    local racine="$BASE"
    if [[ -n "$TABCOPY_ID" ]]; then
        [[ -d "$BASE/$TABCOPY_ID" ]] || return "$ABSENTE"
        racine="$BASE/$TABCOPY_ID"
    fi
    [[ -f "$COPY_ICON" ]] || { printf 'motif absent : %s\n' "$COPY_ICON"; return "$INUSABLE"; }

    local fichier dossier couleur taille
    fichier="$(find "$racine" -type f -path '*/img/logo-outline-black-16.png' -print -quit)"
    if [[ -z "$fichier" ]]; then
        if [[ -n "$TABCOPY_ID" ]]; then
            printf 'icônes introuvables dans l’extension\n'
            return "$INUSABLE"
        fi
        return "$ABSENTE"
    fi
    dossier="$(dirname -- "$fichier")"

    for couleur in black white; do
        for taille in 16 32 48 128; do
            [[ -f "$dossier/logo-outline-$couleur-$taille.png" ]] || { printf 'destination manquante : logo-outline-%s-%s.png\n' "$couleur" "$taille"; return "$INUSABLE"; }
        done
    done
    for couleur in black white; do
        local hex="#ffffff"
        [[ "$couleur" == "black" ]] && hex="#202124"
        for taille in 16 32 48 128; do
            make_png "$COPY_ICON" "$hex" "$taille" "$TMP/tabcopie-$couleur-$taille.png" || return "$INUSABLE"
        done
    done
    for couleur in black white; do
        for taille in 16 32 48 128; do
            install -m 600 "$TMP/tabcopie-$couleur-$taille.png" "$dossier/logo-outline-$couleur-$taille.png" || return "$INUSABLE"
        done
    done

    printf '%s\n' "$dossier"
}


traiter_ublock() {
    [[ -d "$BASE/$UBLOCK_ID" ]] || return "$ABSENTE"

    local fichier dossier taille
    fichier="$(find "$BASE/$UBLOCK_ID" -type f -path '*/img/icon_16.png' -print -quit)"
    [[ -n "$fichier" ]] || { printf 'icônes introuvables dans l’extension\n'; return "$INUSABLE"; }
    dossier="$(dirname -- "$fichier")"

    for taille in 16 32; do
        [[ -f "$dossier/icon_$taille.png" ]] || { printf 'destination manquante : icon_%s.png\n' "$taille"; return "$INUSABLE"; }
        [[ -f "$dossier/icon_$taille-off.png" ]] || { printf 'destination manquante : icon_%s-off.png\n' "$taille"; return "$INUSABLE"; }
    done

    # Cadre carré arrondi continu = actif ; cadre pointillé et u atténué = inactif.
    cat > "$TMP/ublock-actif.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
  <!-- Cadre extérieur carré arrondi (identique aux autres icônes) -->
  <rect x="1.5" y="1.5" width="13" height="13" rx="3.5" ry="3.5" fill="none" stroke="currentColor" stroke-width="1.5" />
  <!-- Lettre "u" parfaitement calibrée avec la même épaisseur (1.5px) -->
  <path d="M 6 5.5 L 6 9.5 C 6 11, 10 11, 10 9.5 L 10 5.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
</svg>
SVG

    cat > "$TMP/ublock-inactif.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
  <!-- Cadre extérieur en pointillés réguliers -->
  <rect x="1.5" y="1.5" width="13" height="13" rx="3.5" ry="3.5" fill="none" stroke="currentColor" stroke-width="1.3" stroke-dasharray="2,2" />
  <!-- Lettre "u" en semi-transparence pour marquer l'inactivité -->
  <path d="M 6 5.5 L 6 9.5 C 6 11, 10 11, 10 9.5 L 10 5.5" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" opacity="0.4" />
</svg>
SVG

    for taille in 16 32; do
        make_png "$TMP/ublock-actif.svg" "#ffffff" "$taille" "$TMP/ublock-actif-$taille.png" || return "$INUSABLE"
        make_png "$TMP/ublock-inactif.svg" "#ffffff" "$taille" "$TMP/ublock-inactif-$taille.png" || return "$INUSABLE"
    done
    for taille in 16 32; do
        install -m 600 "$TMP/ublock-actif-$taille.png" "$dossier/icon_$taille.png" || return "$INUSABLE"
        install -m 600 "$TMP/ublock-inactif-$taille.png" "$dossier/icon_$taille-off.png" || return "$INUSABLE"
    done

    printf '%s\n' "$dossier"
}


# Chaque traitement tourne dans un contexte conditionnel : avec \`set -e\`, un échec
# n'interrompt donc pas le script, et le code de retour dit quoi afficher.
declare -a faites=() ignorees=() a_verifier=()

traiter() {
    local nom="$1" fonction="$2" sortie code resume
    code=0
    sortie="$("$fonction")" || code=$?
    resume="\${sortie//$'\n'/ }"

    case "$code" in
        0)
            faites+=("$nom")
            printf '%-16s : icônes remplacées\n' "$nom"
            [[ -z "$resume" ]] || printf '                   %s\n' "$resume"
            ;;
        1)
            ignorees+=("$nom")
            printf '%-16s : ignorée — extension absente\n' "$nom"
            ;;
        *)
            a_verifier+=("$nom")
            printf '%-16s : ignorée — %s\n' "$nom" "$resume"
            ;;
    esac
}

traiter "Raindrop" traiter_raindrop
traiter "Tab Copy" traiter_tabcopie
traiter "uBlock Origin" traiter_ublock


printf '\n'
if (("\${#faites[@]}")); then
    printf 'Traitées : %s\n' "\${faites[*]}"
fi
if (("\${#ignorees[@]}")); then
    printf 'Ignorées (absentes) : %s\n' "\${ignorees[*]}"
fi
if (("\${#a_verifier[@]}")); then
    printf 'Ignorées (à vérifier) : %s\n' "\${a_verifier[*]}"
fi

if (("\${#faites[@]} == 0")); then
    printf '\nAucune extension n’a pu être traitée.\n' >&2
    exit 1
fi
printf 'Aucune sauvegarde des originaux créée.\n'
