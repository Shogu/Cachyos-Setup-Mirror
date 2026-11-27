#!/usr/bin/env bash
# update-system.sh – Mise à jour système lancée dans Ptyxis.
#
# Déroulé : vérifie que /boot (ESP) est monté (sinon une MAJ du noyau
# désynchronise l'ESP et ses modules → mode d'urgence), liste les mises à jour
# du dépôt standard (checkupdates) et de l'AUR (pamac-cli) sans sudo, affiche
# les actualités Arch pas encore lues (avec pause pour les lire), puis lance
# les mises à jour standard (pacman) puis AUR (pamac), seulement si nécessaire.
# Actualités déjà vues : ~/.local/state/update-system/arch-news-seen.
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
        # -a fixe le nom d'application affiché (sinon « notify-send ») ;
        # icône : pamac-manager. On passe le CHEMIN ABSOLU du fichier SVG :
        # la résolution par nom ne marchait pas (le démon affichait une icône
        # de repli), alors que le chemin absolu s'affiche correctement.
        notify-send -u critical -a 'Mise à jour CachyOS' \
            -i "$HOME/.local/share/icons/hicolor/scalable/apps/pamac-manager.svg" \
            'Mise à jour CachyOS' "$title"
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

# Taille humaine d'un nombre d'octets (Ko, Mo, Go).
function __hrsize -a bytes
    set -l n (math $bytes 2>/dev/null)
    test -n "$n"; or set n 0
    if test $n -lt 1024
        printf '%do' $n
    else if test $n -lt 1048576
        printf '%s Ko' (math -s1 "$n / 1024")
    else if test $n -lt 1073741824
        printf '%s Mo' (math -s1 "$n / 1048576")
    else
        printf '%s Go' (math -s1 "$n / 1073741824")
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
if not command -q checkupdates
    __fail 'checkupdates est introuvable : impossible de lister les mises à jour.' \
        'Installe-le : sudo pacman -S pacman-contrib'
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
# Dépôt standard : checkupdates (pacman-contrib) synchronise une copie
# temporaire des bases, sans sudo. « pacman -Qu » seul lirait les bases
# locales, pas rafraîchies depuis le dernier -Syu → liste périmée.
# Codes retour : 0 = mises à jour, 2 = aucune, autre = erreur.
set -l cu_err (mktemp)
set -l std_upd (checkupdates 2>$cu_err)
set -l st $status
set -l cu_msg (cat $cu_err)
rm -f -- $cu_err
if test $st -ne 0 -a $st -ne 2
    __fail "Impossible de lister les mises à jour du dépôt (checkupdates, code $st)." \
        $cu_msg
end
set -l repo_names (string replace -r '^([^ ]+).*' '$1' -- $std_upd)
set -l std_count (count $std_upd)

# AUR : pamac checkupdates liste dépôt + AUR ; on retire les noms du dépôt
# déjà comptés pour ne garder que les paquets AUR.
# Codes retour : 0 = rien, 100 = mises à jour disponibles, autre = erreur.
set -l aur_raw (pamac checkupdates --aur --devel -q 2>/dev/null)
set -l st $status
if test $st -ne 0 -a $st -ne 100
    set_color $ORANGE
    echo "⚠  Listage AUR en échec (pamac, code $st) : l’AUR sera ignorée cette fois."
    set_color normal
    set aur_raw
end
set -l aur_mix (__names $aur_raw)
set -l aur_names ()
for n in $aur_mix
    not contains -- $n $repo_names; and set -a aur_names $n
end
set -l aur_count (count $aur_names)

# --- Actualités Arch : seulement celles pas encore lues -------
# Les titres déjà vus sont mémorisés dans un fichier d'état ; seules les
# nouvelles actualités sont affichées. Elles ne sont marquées « lues »
# qu'une fois la suite acceptée (si tu annules, elles reviendront).
set -l state_dir (set -q XDG_STATE_HOME; and echo $XDG_STATE_HOME; or echo $HOME/.local/state)/update-system
set -l seen_file $state_dir/arch-news-seen
set -l seen ()
test -r $seen_file; and set seen (cat $seen_file)

set -l news ()
set -l all_titles ()
if command -q curl
    set -l feed (curl -s --max-time 10 https://archlinux.org/feeds/news/)
    set all_titles (string match -r '<title>[^<]+</title>' -- $feed \
        | string replace -r '.*<title>(.*)</title>' '$1' \
        | string replace -a '&amp;' '&' | string replace -a '&#39;' "'" \
        | string replace -a '&quot;' '"' | string replace -a '&lt;' '<' \
        | string replace -a '&gt;' '>')
    # La 1ère entrée est le titre du flux ; on la retire.
    test (count $all_titles) -gt 1; and set -e all_titles[1]
    for t in $all_titles
        contains -- $t $seen; or set -a news $t
    end
end

function __mark_news_read -V state_dir -V seen_file -V all_titles
    test (count $all_titles) -gt 0; or return
    mkdir -p $state_dir
    # Le flux ne garde que les ~10 dernières : on enregistre la liste
    # actuelle, le fichier ne grossit donc jamais.
    printf '%s\n' $all_titles > $seen_file
end

if test (count $news) -gt 0
    __header "ACTUALITÉS ARCH — "(count $news)" nouvelle(s)" $CYAN
    for t in $news
        echo "  ▸ $t"
    end
    echo
    set_color $DIM
    echo '  https://archlinux.org/news/'
    set_color normal
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
__mark_news_read

# --- Mise à jour effective ------------------------------------
set -l running_kernel (uname -r)
set -l did_std 0
set -l did_aur 0

if test $std_count -gt 0
    __header "MISE À JOUR SYSTÈME (dépôt) — $std_count paquet(s)" $BLUE
    # Tableau : noms, versions, taille et dépôt d'origine en bout de ligne.
    # Détails lus dans la copie de bases fraîche synchronisée par checkupdates
    # (sans root) via --print-format.
    set -l cu_db (set -q TMPDIR; and string length -q -- "$TMPDIR"; and echo "$TMPDIR"; or echo /tmp)"/checkup-db-"(id -u)
    set -l info_lines ()
    if test -d "$cu_db"
        set info_lines (pacman --dbpath "$cu_db" -S -u -p --print-format '%n|%v|%s|%r' 2>/dev/null)
    end
    # Rassemble les lignes puis calcule la largeur de chaque colonne.
    set -l rows ()
    for l in $std_upd
        set -l f (string split ' ' -- $l)             # repo/name old -> new
        set -l name (string replace -r '^[^/]+/' '' -- $f[1])
        set -l ver "$f[2] -> $f[4]"
        set -l sz ''
        set -l repo ''
        # Recherche de la ligne info (nom | nouvelle version | taille | dépôt)
        # par comparaison du 1er champ : `string match -r` ne renverrait ici que
        # le groupe capturé, pas toute la ligne.
        set -l hit ''
        for i in $info_lines
            set -l fld (string split '|' -- $i)
            if test "$fld[1]" = "$name"
                set hit $i
                break
            end
        end
        if test -n "$hit"
            set -l p (string split '|' -- $hit)       # name | new | bytes | repo
            set sz (__hrsize $p[3])
            set repo $p[4]
        end
        set -a rows "$name|$ver|$sz|$repo"
    end
    set -l w1 6    # Paquet
    set -l w2 19   # Ancienne -> Nouvelle
    set -l w3 6    # Taille
    set -l w4 5    # Dépôt
    for r in $rows
        set -l c (string split '|' -- $r)
        test (string length -- $c[1]) -gt $w1; and set w1 (string length -- $c[1])
        test (string length -- $c[2]) -gt $w2; and set w2 (string length -- $c[2])
        test (string length -- $c[3]) -gt $w3; and set w3 (string length -- $c[3])
        test (string length -- $c[4]) -gt $w4; and set w4 (string length -- $c[4])
    end
    set_color $BLUE
    printf '┌─%s─┬─%s─┬─%s─┬─%s─┐\n' (string repeat -n $w1 '─') (string repeat -n $w2 '─') (string repeat -n $w3 '─') (string repeat -n $w4 '─')
    set_color --bold $BLUE
    printf '│ %s │ %s │ %s │ %s │\n' \
        (string pad -w $w1 -- 'Paquet') \
        (string pad -w $w2 -- 'Ancienne -> Nouvelle') \
        (string pad -w $w3 -- 'Taille') \
        (string pad -w $w4 -- 'Dépôt')
    set_color $BLUE
    printf '├─%s─┼─%s─┼─%s─┼─%s─┤\n' (string repeat -n $w1 '─') (string repeat -n $w2 '─') (string repeat -n $w3 '─') (string repeat -n $w4 '─')
    for r in $rows
        set -l c (string split '|' -- $r)
        set_color $BLUE
        printf '│ '
        set_color --bold $BLUE
        printf '%s' (string pad -w $w1 -- $c[1])
        set_color $BLUE
        printf ' │ '
        set_color $DIM
        printf '%s' (string pad -w $w2 -- $c[2])
        set_color $BLUE
        printf ' │ '
        set_color $CYAN
        printf '%s' (string pad -w $w3 -- $c[3])
        set_color $BLUE
        printf ' │ '
        set_color $DIM
        printf '%s' (string pad -w $w4 -- $c[4])
        set_color $BLUE
        echo ' │'
    end
    printf '└─%s─┴─%s─┴─%s─┴─%s─┘\n' (string repeat -n $w1 '─') (string repeat -n $w2 '─') (string repeat -n $w3 '─') (string repeat -n $w4 '─')
    set_color normal
    echo
    # et on filtre aussi la ligne « Packages (N) » qu'affiche pacman lui-même.
    # --color=always conserve les couleurs syntaxiques de pacman malgré le
    # filtre en pipe ; stderr (progression, erreurs) n'est pas pipé.
    sudo pacman -Syu --color=always | perl -pe '
        s/\e\[[0-9;]*m//g;
        if (/^Packages\s*\((\d+)\)/) {
            my $n = $1;
            my @pkgs = grep { length } split /\s+/, (split /\)/, $_, 2)[1];
            my @names = map {
                my $x = $_;
                $x =~ s{^[^/]+/}{};   # retire « dépôt/ »
                $x =~ s{-[^-]+$}{};   # retire l’éventuel -pkgrel (peut être « -1.1 »)
                $x =~ s{-[^-]+$}{};   # retire la version
                $x
            } @pkgs;
            $_ = "\e[1;38;2;53;132;228mPackages ($n)\e[0m " . join(" ", @names) . "\n";
        }
    '
    set -l ps $pipestatus
    if test $ps[1] -ne 0
        __fail 'La mise à jour système a échoué ou a été interrompue.' \
            'La mise à jour AUR n’a pas été lancée.'
    end
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
