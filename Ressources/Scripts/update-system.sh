#!/usr/bin/env bash
# update-system.sh – Mise à jour système lancée dans Ptyxis.
#
# Déroulé : vérifie que /boot (ESP) est monté (sinon une MAJ du noyau
# désynchronise l'ESP et ses modules → mode d'urgence), liste les mises à jour
# du dépôt standard (pacman) et de l'AUR (pamac-cli) sans sudo, affiche les
# actualités Arch (avec pause pour les lire), puis lance les mises à jour
# standard (pacman) puis AUR (pamac), seulement si nécessaire.
#
#   • le mot de passe n'est demandé que s'il y a vraiment quelque chose à faire ;
#   • tout échec (listage, montage, upgrade) est signalé et arrête le script :
#     jamais de « système à jour » ou de « ✓ » non vérifiés ;
#   • l'AUR n'est pas lancée si la mise à jour standard a échoué ;
#   • le besoin de redémarrer est détecté de façon fiable (modules du noyau en
#     cours disparus), indépendamment du nom du paquet noyau.
#
# Outils utilisés :
#   – dépôt standard : pacman (autonome, pas besoin du daemon pamac).
#   – AUR            : pamac-cli (nécessite son daemon D-Bus, activé à la
#                      demande — service « static », jamais lancé au boot).
#
# 2026-11-22 : version remplaçant update-shelly.sh (Shelly désinstallé).
#
# Ptyxis est lancé avec --standalone : le processus vit aussi longtemps que sa
# fenêtre, donc ce wrappeur attend vraiment la fin de la mise à jour avant de
# nettoyer témoin et fichier temporaire (sans --standalone, une fenêtre Ptyxis
# déjà ouverte faisait rendre la main tout de suite → script supprimé trop tôt).

set -euo pipefail

flag="${XDG_RUNTIME_DIR:-/tmp}/update-system.running"
self="$(mktemp "${TMPDIR:-/tmp}/update-system.XXXXXX.fish")"

cleanup() {
    rm -f -- "$flag" "$self" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP

cat > "$self" <<'FISH'
# ---------------------------------------------------------------
#  Corps du script fish (exécuté dans Ptyxis)
#  Argument : $argv[1] = témoin « en cours »
# ---------------------------------------------------------------
set -g self (status filename)
set -g flag $argv[1]

function __u_cleanup --on-event fish_exit
    rm -f -- $flag $self 2>/dev/null
end

set -g BLUE 3584e4
set -g GREEN 2ec27e
set -g ORANGE ff7800
set -g RED e01b24
set -g CYAN 62a0ea
set -g DIM 77767b

function __rule -a color
    set -l w $COLUMNS
    test -n "$w"; or set w 80
    set_color $color
    string repeat -n $w '━'
    set_color normal
end

function __header -a title color
    echo
    __rule $color
    set_color --bold $color
    printf '  %s\n' $title
    set_color normal
    echo
end

# Affiche un message d'erreur (1er argument = titre, suivants = détails),
# notifie, attend ENTRÉE puis quitte.
function __fail
    set -l title $argv[1]
    set -e argv[1]
    echo
    set_color --bold $RED
    echo "✗  $title"
    set_color normal
    for l in $argv
        echo "   $l"
    end
    if command -q notify-send
        notify-send -u critical 'Mise à jour système' "$title"
    end
    echo
    read -P 'Fermer avec ENTRÉE '
    exit 1
end

# Extrait les noms des lignes « nom version -> nouvelle_version ».
# Filtre aussi les lignes de progression des outils (synchronisation de bases…).
function __names
    for l in $argv
        string match -q -r '.+ -> .+' -- $l
        and string replace -r '^([^ ]+).*' '$1' -- $l
    end
end

# --- Vérif des outils utilisés ---------------------------------
if not command -q pacman
    __fail 'pacman est introuvable : impossible de mettre à jour le système.'
end
if not command -q pamac
    __fail 'pamac est introuvable : impossible de gérer l’AUR.' \
        'Installe-le : sudo pacman -S pamac-aur'
end
if not command -q curl
    echo '⚠  curl absent : les actualités Arch ne seront pas affichées.' >&2
end

# --- Bannière -------------------------------------------------
set_color --bold $BLUE
printf '\n  ◆  MISE À JOUR SYSTÈME  \n'
set_color $DIM
printf '     %s\n' (date +'%a %d %b %Y — %H:%M')
set_color normal
__rule $BLUE

# --- /boot : vérification + montage si besoin -----------------
if not mountpoint -q /boot
    set_color $ORANGE
    echo
    echo '⚠  /boot n’est PAS monté : mise à jour du noyau dangereuse.'
    set_color normal
    echo 'Tentative de montage…'
    if not sudo mount /boot
        if not test -d /usr/lib/modules/(uname -r)
            __fail 'Impossible de monter /boot. Mise à jour ANNULÉE.' \
                'Les modules du noyau en cours ont disparu (noyau déjà mis à jour) :' \
                'redémarre d’abord, puis relance la mise à jour.'
        else
            __fail 'Impossible de monter /boot. Mise à jour ANNULÉE.' \
                'Vérifie : journalctl -u boot.mount'
        end
    end
    set_color $GREEN
    echo '✓  /boot monté.'
    set_color normal
end

# --- Listage des mises à jour (sans mot de passe) -------------
# Dépôt standard : pacman -Qu (propre, une ligne par mise à jour).
set -l std_upd (pacman -Qu 2>/dev/null)
set -l repo_names (string replace -r '^([^ ]+).*' '$1' -- $std_upd)
set -l std_count (count $std_upd)

# AUR : pamac checkupdates liste dépôt + AUR ; on retire les noms du dépôt
# déjà comptés par pacman pour ne garder que les paquets AUR.
set -l aur_raw (pamac checkupdates --aur --devel -q 2>/dev/null)
set -l aur_mix (__names $aur_raw)
set -l aur_names ()
for n in $aur_mix
    not contains -- $n $repo_names; and set -a aur_names $n
end
set -l aur_count (count $aur_names)

# --- Actualités Arch (lecture seule) --------------------------
set -l news ()
if command -q curl
    set -l feed (curl -s --max-time 10 https://archlinux.org/feeds/news/)
    set -l titles (string match -r '<title>[^<]+</title>' -- $feed \
        | string replace -r '.*<title>(.*)</title>' '$1' 2>/dev/null)
    # La 1ère entrée est le titre du flux ; on la retire.
    test (count $titles) -gt 1; and set -e titles[1]
    if test (count $titles) -gt 0
        set news $titles
    end
end

if test (count $news) -gt 0
    __header 'ACTUALITÉS ARCH' $CYAN
    for t in $news
        echo "  ▸ $t"
    end
    if test $std_count -gt 0 -o $aur_count -gt 0
        echo
        set_color --bold $ORANGE
        echo '  Lis ces actualités : certaines demandent une intervention manuelle.'
        set_color normal
        read -l -P '  Continuer la mise à jour ? [o/N] ' rep
        if not string match -qir '^(o|oui|y|yes)$' -- $rep
            __header 'ANNULÉ' $ORANGE
            echo '  Mise à jour non lancée.'
            echo
            read -P 'Fermer avec ENTRÉE '
            exit 0
        end
    end
end

# --- Mise à jour effective ------------------------------------
set -l running_kernel (uname -r)
set -l did_std 0
set -l did_aur 0

if test $std_count -gt 0
    __header "MISE À JOUR SYSTÈME (dépôt) — $std_count paquet(s)" $BLUE
    sudo pacman -Syu
    or __fail 'La mise à jour système a échoué ou a été interrompue.' \
        'La mise à jour AUR n’a pas été lancée.'
    set did_std 1
end

if test $aur_count -gt 0
    __header "MISE À JOUR AUR — $aur_count paquet(s)" $ORANGE
    pamac upgrade --aur --devel
    or __fail 'La mise à jour AUR a échoué ou a été interrompue.' \
        (test $did_std -eq 1; and echo 'La mise à jour du dépôt, elle, a bien été faite.')
    set did_aur 1
end

# --- Verdict final --------------------------------------------
__header 'TERMINÉ' $GREEN
if test $did_std -eq 1 -o $did_aur -eq 1
    set_color $GREEN
    printf '  ✓  Mise à jour effectuée'
    set_color normal
    test $did_std -eq 0; and printf ' (dépôt inchangé)'
    test $did_aur -eq 0; and printf ' (AUR inchangée)'
    echo
    echo
    # Fiable quel que soit le nom du paquet noyau (linux, linux-cachyos…) :
    # si les modules du noyau en cours ont disparu, il a été remplacé.
    if not test -d /usr/lib/modules/$running_kernel
        set_color --bold $ORANGE
        echo '  ⚠  Le noyau a été mis à jour : redémarre pour utiliser le nouveau noyau.'
        set_color normal
        echo
    end
else
    set_color $GREEN
    echo '  Rien à faire — système à jour.'
    set_color normal
    echo
end

read -P 'Fermer avec ENTRÉE '
FISH

touch -- "$flag"

# Fenêtre Ptyxis maximisée, instance autonome : la commande ne rend la main
# qu'à la fermeture de la fenêtre.
ptyxis --standalone --maximize -- fish "$self" "$flag"
