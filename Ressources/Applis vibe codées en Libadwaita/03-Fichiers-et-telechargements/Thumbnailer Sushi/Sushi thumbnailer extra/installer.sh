#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
#
# installer.sh — installe sushi-thumbnailer-docs-extra et, s'il est là,
# nautilus-vignettes-arrondies-sushi, depuis le dossier de ce script.
#
# Usage : sh installer.sh [-s] [-y] [-n]
#   -s  simulation : affiche ce qui serait fait, sans rien modifier
#   -y  ne pas demander confirmation à pacman
#   -n  ne pas relancer Nautilus à la fin
#
# Étapes :
#   1. trouver le paquet le plus récent de chaque nom et vérifier l'archive ;
#   2. arrêter Nautilus et l'aperçu (Sushi) ;
#   3. installer avec un seul « sudo pacman -U » ;
#   4. purger les miniatures (toutes les tailles, échecs compris) ;
#   5. relancer Nautilus s'il tournait, afficher les versions installées.
#
# À lancer sans sudo : le mot de passe est demandé pour pacman seulement.

set -eu

PRINCIPAL=sushi-thumbnailer-docs-extra
ARRONDIES=nautilus-vignettes-arrondies-sushi
ANCIENS="thumbnailer-docx-nautilus-sushi thumbnailer-docx-nautilus-sushi-arrondi thumbnailer-docx-nautilus-sushi-arrondi-rabat sushi-apercu-bureau"

DOSSIER=$(cd "$(dirname "$0")" && pwd)
SIMULATION=0
CONFIRMER=1
RELANCER=1
nautilus_actif=0

while getopts syn option; do
    case $option in
        s) SIMULATION=1 ;;
        y) CONFIRMER=0 ;;
        n) RELANCER=0 ;;
        *) echo "Usage : sh installer.sh [-s] [-y] [-n]" >&2; exit 2 ;;
    esac
done

erreur() { printf 'erreur : %s\n' "$*" >&2; exit 1; }
info() { printf '  %s\n' "$*"; }
etape() { printf '\n==> %s\n' "$*"; }
lancer() {
    if [ "$SIMULATION" = 1 ]; then
        printf '  [simulation] %s\n' "$*"
    else
        "$@"
    fi
}

[ "$(id -u)" != 0 ] || erreur "à lancer sans sudo (le mot de passe est demandé pour pacman)."
command -v pacman >/dev/null 2>&1 || erreur "pacman introuvable."

# Paquet le plus récent d'un nom donné ; le chiffre après le nom écarte les
# noms plus longs qui commenceraient pareil.
plus_recent() {
    ls "$DOSSIER/$1"-[0-9]*.pkg.tar.zst 2>/dev/null | sort -V | tail -n 1
}

# Nom lu dans .PKGINFO (archive vérifiée au passage)
nom_du_paquet() {
    if command -v bsdtar >/dev/null 2>&1; then
        bsdtar -xOf "$1" .PKGINFO 2>/dev/null
    else
        tar --zstd -xOf "$1" .PKGINFO 2>/dev/null
    fi | awk -F' = ' '$1 == "pkgname" {print $2; exit}'
}

# --- 1. Paquets ----------------------------------------------------------------

etape "Paquets trouvés dans $DOSSIER"

anciens=""
for ancien in $ANCIENS; do
    if pacman -Q "$ancien" >/dev/null 2>&1; then
        anciens="$anciens $ancien"
    fi
done
if [ -n "$anciens" ]; then
    erreur "anciens paquets encore installés :$anciens
       Retire-les d'abord :  sudo pacman -R$anciens"
fi

principal=$(plus_recent "$PRINCIPAL")
[ -n "$principal" ] || erreur "aucun $PRINCIPAL-*.pkg.tar.zst dans ce dossier."
[ "$(nom_du_paquet "$principal")" = "$PRINCIPAL" ] \
    || erreur "archive illisible ou invalide : $(basename "$principal")"
info "$(basename "$principal")"

arrondies=$(plus_recent "$ARRONDIES")
if [ -n "$arrondies" ]; then
    [ "$(nom_du_paquet "$arrondies")" = "$ARRONDIES" ] \
        || erreur "archive illisible ou invalide : $(basename "$arrondies")"
    info "$(basename "$arrondies")"
else
    info "($ARRONDIES absent : miniatures sans coins arrondis)"
fi

# --- 2. Nautilus et l'aperçu ------------------------------------------------------

etape "Arrêt de Nautilus et de l'aperçu"

if pgrep -x nautilus >/dev/null 2>&1; then
    nautilus_actif=1
    lancer nautilus -q || true
    if [ "$SIMULATION" = 0 ]; then
        i=0
        while pgrep -x nautilus >/dev/null 2>&1 && [ $i -lt 20 ]; do
            sleep 0.15; i=$((i + 1))
        done
        pgrep -x nautilus >/dev/null 2>&1 && pkill -x nautilus || true
    fi
    info "Nautilus arrêté"
else
    info "Nautilus ne tournait pas"
fi

# L'aperçu est un script gjs : on le repère par sa ligne de commande exacte,
# jamais par un motif qui viserait aussi le terminal qui lance ce script.
for pid in $(pgrep -f 'org\.gnome\.NautilusPreviewer$' 2>/dev/null || true); do
    [ "$pid" != "$$" ] || continue
    lancer kill "$pid" 2>/dev/null || true
    info "aperçu arrêté"
done

# --- 3. Installation ----------------------------------------------------------------

etape "Installation"

set -- -U
[ "$CONFIRMER" = 1 ] || set -- "$@" --noconfirm
set -- "$@" "$principal"
[ -z "$arrondies" ] || set -- "$@" "$arrondies"
lancer sudo pacman "$@"

# --- 4. Miniatures -----------------------------------------------------------------

etape "Purge des miniatures"

cache=${XDG_CACHE_HOME:-$HOME/.cache}/thumbnails
for taille in fail normal large x-large xx-large; do
    lancer rm -rf "$cache/$taille"
done
info "$cache vidé (toutes les tailles)"

# --- 5. Fin --------------------------------------------------------------------------

etape "Vérification"

if [ "$SIMULATION" = 1 ]; then
    printf '\nSimulation terminée : rien n'"'"'a été modifié.\n'
    exit 0
fi

pacman -Q "$PRINCIPAL" | sed 's/^/  /'
[ -z "$arrondies" ] || pacman -Q "$ARRONDIES" | sed 's/^/  /'

if [ "$RELANCER" = 1 ] && [ "$nautilus_actif" = 1 ]; then
    if command -v setsid >/dev/null 2>&1; then
        setsid -f nautilus >/dev/null 2>&1 || true
    else
        nohup nautilus >/dev/null 2>&1 &
    fi
    info "Nautilus relancé"
fi

printf '\nTerminé. Les miniatures se redessinent au fil de la navigation.\n'
