#!/usr/bin/env bash
# icones — range tes icônes maison dans le thème, sous les noms qu'attend GNOME,
# avec leurs symboliques, et fait pointer les lanceurs dessus.
#
#   icones inventaire           repère les lanceurs dont Icon= est un chemin de fichier,
#                               et prépare ~/icones-inventaire.tar.gz à m'envoyer
#   icones appliquer DOSSIER    installe le dossier que je te renvoie
#                               (NOM-symbolic.svg, et NOM.svg si fourni ; sinon l'icône
#                               couleur actuelle du lanceur est reprise) et corrige les lanceurs
#   icones etat                 montre où en est chaque lanceur
#   icones sauvegarder          crée ~/icones-maison-DATE.zip : ce script, toutes tes icônes
#                               et tes lanceurs faits main
#   icones restaurer DOSSIER    après réinstallation : remet tout depuis une sauvegarde
set -euo pipefail

DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
THEME="$DATA/icons/hicolor"
USER_APPS="$DATA/applications"
APP_DIRS=("$USER_APPS"
          "$DATA/flatpak/exports/share/applications"
          /var/lib/flatpak/exports/share/applications
          /usr/local/share/applications
          /usr/share/applications)

die() { printf 'icones : %s\n' "$*" >&2; exit 1; }

# Tous les lanceurs visibles, un par identifiant ; la copie perso masque la copie système.
lanceurs() {
    local seen=" " d f b
    for d in "${APP_DIRS[@]}"; do
        for f in "$d"/*.desktop; do
            [[ -f "$f" ]] || continue
            b="$(basename "$f" .desktop)"
            [[ "$seen" == *" $b "* ]] && continue
            seen+="$b "
            printf '%s\t%s\n' "$b" "$f"
        done
    done
}

champ() {   # champ $1 de la section [Desktop Entry] du fichier $2
    awk -v k="$1" '/^\[/{m=($0=="[Desktop Entry]")} m && index($0, k"=")==1 {print substr($0, length(k)+2); exit}' "$2"
}

inventaire() {
    local out="$HOME/icones-inventaire" id f icon name ext n=0
    rm -rf "$out"; mkdir -p "$out"
    printf 'nom_icone\tnom_affiche\tlanceur\tfichier_actuel\n' > "$out/inventaire.tsv"
    while IFS=$'\t' read -r id f; do
        icon="$(champ Icon "$f")"
        [[ "$icon" == /* && -f "$icon" ]] || continue
        [[ "$icon" == *.png && -f "${icon%.png}.svg" ]] && icon="${icon%.png}.svg"
        name="$(champ Name "$f")"
        ext="${icon##*.}"
        cp "$icon" "$out/$id.$ext"            # renommé d'office avec le bon nom
        printf '%s\t%s\t%s\t%s\n' "$id" "$name" "$f" "$icon" >> "$out/inventaire.tsv"
        n=$((n+1))
    done < <(lanceurs)
    tar -czf "$out.tar.gz" -C "$HOME" icones-inventaire
    echo "$n icône(s) trouvée(s), déjà renommée(s) avec le nom qu'attend GNOME :"
    awk -F'\t' 'NR>1{printf "  %-40s %s\n", $1, $2}' "$out/inventaire.tsv"
    echo
    echo "→ envoie-moi : $out.tar.gz"
}

# Rendu d'une image à une taille donnée : $1 source, $2 côté en px, $3 destination
rendre() {
    mkdir -p "$(dirname "$3")"
    if [[ "$1" == *.svg ]] && command -v rsvg-convert >/dev/null; then
        rsvg-convert -w "$2" -h "$2" "$1" -o "$3"
    elif command -v magick >/dev/null; then
        magick -background none -density 384 "$1" -resize "$2x$2" "$3"
    elif command -v convert >/dev/null; then
        convert -background none -density 384 "$1" -resize "$2x$2" "$3"
    else
        return 1
    fi
}

# Une appli qui livre aussi des PNG en tailles fixes (Nicotine+…) : GNOME préfère ces
# PNG à une icône « scalable », même placée dans ton dossier. On pose donc, dans ton
# thème, un PNG de ton icône pour chacune de ces tailles : il passe devant celui du paquet.
masquer_png_systeme() {   # $1 = icône couleur installée, $2 = nom
    local src="$1" nom="$2" base png sub px n=0
    for base in /usr/share/icons/hicolor /usr/local/share/icons/hicolor \
                /var/lib/flatpak/exports/share/icons/hicolor "$DATA/flatpak/exports/share/icons/hicolor"; do
        for png in "$base"/*/apps/"$nom".png; do
            [[ -f "$png" ]] || continue
            sub="$(basename "$(dirname "$(dirname "$png")")")"      # ex. 128x128@2
            [[ "$sub" =~ ^([0-9]+)x[0-9]+(@([0-9]+))?$ ]] || continue
            px=$(( BASH_REMATCH[1] * ${BASH_REMATCH[3]:-1} ))
            if rendre "$src" "$px" "$THEME/$sub/apps/$nom.png"; then n=$((n+1))
            else printf '  %-40s ⚠ installe librsvg (rsvg-convert) : l’icône du paquet reste prioritaire\n' "$nom"; return; fi
        done
    done
    (( n )) && printf '  %-40s %d PNG posé(s) devant ceux du paquet\n' "$nom" "$n"
    return 0
}

installer_fichier() {   # $1 = fichier, $2 = nom (avec -symbolic éventuel)
    local f="$1" nom="$2" ext="${1##*.}" taille
    if [[ "$nom" == *-symbolic ]]; then
        install -Dm644 "$f" "$THEME/symbolic/apps/$nom.svg"
    elif [[ "$ext" == svg ]]; then
        install -Dm644 "$f" "$THEME/scalable/apps/$nom.svg"
        masquer_png_systeme "$f" "$nom"
    else    # PNG : rangé dans le dossier de sa taille réelle
        taille="$(file -b "$f" | grep -o '[0-9]* x [0-9]*' | head -1 | tr -d ' ')"
        [[ -n "$taille" ]] || die "taille illisible : $f"
        # GNOME ne connaît que les tailles standard : on range dans la plus proche au-dessus
        local w="${taille%%x*}" s
        for s in 16 24 32 48 64 128 256 512; do (( w <= s )) && break; done
        install -Dm644 "$f" "$THEME/${s}x${s}/apps/$nom.png"
        masquer_png_systeme "$f" "$nom"
    fi
}

appliquer() {
    local dir="${1:-}" f base nom id desk dst icon fixed=0 installed=0
    [[ -d "$dir" ]] || die "usage : icones appliquer DOSSIER"
    for f in "$dir"/*.svg "$dir"/*.png; do
        [[ -f "$f" ]] || continue
        base="$(basename "$f")"; nom="${base%.*}"
        installer_fichier "$f" "$nom"; installed=$((installed+1))
    done
    # chaque lanceur dont l'icône couleur vient d'être installée passe en Icon=NOM
    while IFS=$'\t' read -r id desk; do
        compgen -G "$dir/$id.*" >/dev/null || [[ -e "$dir/$id-symbolic.svg" ]] || continue
        icon="$(champ Icon "$desk")"
        # dossier sans icône couleur : on reprend celle que vise déjà le lanceur
        if [[ ! -e "$dir/$id.svg" && ! -e "$dir/$id.png" ]]; then
            if [[ "$icon" == /* && -f "$icon" ]]; then
                # un SVG du même nom à côté du PNG ? on le préfère
                [[ "$icon" == *.png && -f "${icon%.png}.svg" ]] && icon="${icon%.png}.svg"
                installer_fichier "$icon" "$id"; installed=$((installed+1))
            elif [[ "$icon" != "$id" ]]; then
                printf '  %-40s ignoré : pas d’icône couleur (Icon=%s)\n' "$id" "$icon"; continue
            fi
        fi
        [[ "$icon" == "$id" ]] && continue
        dst="$USER_APPS/$id.desktop"
        [[ "$desk" == "$dst" ]] || install -Dm644 "$desk" "$dst"   # le fichier système reste intact
        awk -v n="$id" '/^\[/{m=($0=="[Desktop Entry]")} m&&/^Icon=/{print "Icon=" n; next} {print}' \
            "$dst" > "$dst.tmp" && mv "$dst.tmp" "$dst"
        printf '  %-40s Icon=%s\n' "$id" "$id"; fixed=$((fixed+1))
    done < <(lanceurs)
    gtk-update-icon-cache -q -f -t "$THEME" 2>/dev/null || true
    command -v update-desktop-database >/dev/null && update-desktop-database -q "$USER_APPS" || true
    echo "$installed fichier(s) installé(s), $fixed lanceur(s) corrigé(s)."
    echo "Si une ancienne icône persiste : déconnexion / reconnexion."
}

etat() {
    local id f icon kind sym
    printf '%-40s %-7s %-10s %s\n' LANCEUR ICON= SYMBOLIQUE VALEUR
    while IFS=$'\t' read -r id f; do
        icon="$(champ Icon "$f")"; [[ -n "$icon" ]] || continue
        if [[ "$icon" == /* ]]; then kind=chemin; sym="impossible"
        else
            kind=nom; sym=non
            for d in "$THEME" "$DATA/flatpak/exports/share/icons/hicolor" /var/lib/flatpak/exports/share/icons/hicolor \
                     /usr/local/share/icons/hicolor /usr/share/icons/hicolor /usr/share/icons/Adwaita; do
                compgen -G "$d/*/apps/$icon-symbolic.*" >/dev/null && { sym=oui; break; }
            done
        fi
        printf '%-40s %-7s %-10s %s\n' "$id" "$kind" "$sym" "$icon"
    done < <(lanceurs)
}

sauvegarder() {
    local stamp tmp dir f nom best sz bsz n=0
    stamp="$(date +%Y-%m-%d)"
    tmp="$(mktemp -d)"; dir="$tmp/icones-maison"
    mkdir -p "$dir/icones"
    cp "$(readlink -f "$0")" "$dir/icones.sh"; chmod +x "$dir/icones.sh"
    # icônes couleur (SVG) et symboliques
    for f in "$THEME"/scalable/apps/*.svg "$THEME"/symbolic/apps/*-symbolic.svg; do
        [[ -f "$f" ]] && { cp "$f" "$dir/icones/"; n=$((n+1)); }
    done
    # icônes couleur seulement en PNG : on garde la plus grande
    for f in "$THEME"/*x*/apps/*.png; do
        [[ -f "$f" ]] || continue
        nom="$(basename "$f" .png)"
        [[ -e "$dir/icones/$nom.svg" ]] && continue
        sz="$(basename "$(dirname "$(dirname "$f")")")"; sz="${sz%%x*}"
        best="$dir/icones/$nom.png"
        if [[ -e "$best" ]]; then
            bsz="$(file -b "$best" | grep -o '^[^,]*, [0-9]*' | grep -o '[0-9]*$')"
            (( sz > bsz )) || continue
        else n=$((n+1)); fi
        cp "$f" "$best"
    done
    # lanceurs faits main (Upgrade…) : aucun paquet ne les recréera, on les garde
    local f2 b2 d2 sys nl=0
    mkdir -p "$dir/lanceurs"
    for f2 in "$USER_APPS"/*.desktop; do
        [[ -f "$f2" ]] || continue
        b2="$(basename "$f2")"; sys=0
        for d2 in "${APP_DIRS[@]:1}"; do [[ -f "$d2/$b2" ]] && { sys=1; break; }; done
        (( sys )) || { cp "$f2" "$dir/lanceurs/"; nl=$((nl+1)); }
    done
    cat > "$dir/LISEZMOI.txt" <<TXT
Icônes maison — sauvegarde du $stamp ($n icônes)

Après une réinstallation :
  1. installe tes applis comme d'habitude ;
  2. dans ce dossier :  ./icones.sh restaurer .
     (remet les lanceurs faits main, range les icônes et corrige les lanceurs ;
      sans danger, relançable à volonté : refais-le après avoir installé d'autres applis)
  3. déconnexion / reconnexion.

Chaque fichier de « icones » porte le nom de l'appli qu'il habille :
  NOM.svg            icône couleur      → ~/.local/share/icons/hicolor/scalable/apps/
  NOM-symbolic.svg   icône symbolique   → ~/.local/share/icons/hicolor/symbolic/apps/
  NOM = nom du lanceur sans .desktop (ex. org.gnome.Nautilus)
TXT
    local out="$HOME/icones-maison-$stamp"
    if command -v zip >/dev/null; then
        (cd "$tmp" && zip -qr "$out.zip" icones-maison); out="$out.zip"
    else
        tar -czf "$out.tar.gz" -C "$tmp" icones-maison; out="$out.tar.gz"
    fi
    rm -rf "$tmp"
    echo "$n icône(s) et $nl lanceur(s) fait(s) main sauvegardé(s) avec le script → $out"
}

restaurer() {   # $1 = dossier de sauvegarde décompressé (contient icones/ et lanceurs/)
    local dir="${1:-.}" f n=0
    [[ -d "$dir/icones" ]] || die "usage : icones restaurer DOSSIER_DE_SAUVEGARDE"
    for f in "$dir"/lanceurs/*.desktop; do
        [[ -f "$f" ]] || continue
        install -Dm644 "$f" "$USER_APPS/$(basename "$f")"; n=$((n+1))
    done
    echo "$n lanceur(s) fait(s) main remis en place."
    appliquer "$dir/icones"
}

case "${1:-}" in
    restaurer)   shift; restaurer "$@" ;;
    sauvegarder) sauvegarder ;;
    inventaire) inventaire ;;
    appliquer)  shift; appliquer "$@" ;;
    etat)       etat ;;
    *) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 1 ;;
esac
