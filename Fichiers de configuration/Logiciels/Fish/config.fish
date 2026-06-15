source /usr/share/cachyos-fish-config/cachyos-config.fish

# Message d'accueil désactivé (voir fonction fish_greeting plus bas)

############################################################################################################################
# === Alias Editeurs ===
alias vim='micro'
alias vi='micro'
alias gedit='gnome-text-editor'
alias nano='micro'
alias notepad='gnome-text-editor'

# === Alias Système ===
alias rm='rm -I'
alias stockage='duf'
alias systemd='isd'
alias lastpackages='rip'
alias liminestats='limine-snapper-info'
alias scrub='sudo btrfs scrub start -B /'
alias bios='systemctl reboot --firmware-setup'
alias boot='systemd-analyze'
alias boot!='systemd-analyze blame'

# === Alias Shelly pour AUR ===
alias aur='shelly aur install'
alias aursearch='shelly aur search'

# === Alias Fish ===
alias sourcefish='source ~/.config/fish/config.fish'
alias fishedit='xdg-open ~/.config/fish/config.fish'

# === Alias Pacman ===

# === RECHERCHE DE PAQUETS ===
alias pacsearch='pacman -Ss'
alias pacsearch_installed='pacman -Qs'

# === DÉPENDANCES ===
alias pacdep='pactree -r'

# === RECHERCHE DE FICHIERS DANS UN PAQUET ===
alias pacfiles='pacman -Ql'

# === RECHERCHE ET SUPPRESSION D'ORPHELINS + DÉPENDANCES INUTILES ===
alias orphans='pacman -Qdtq | xargs -r sudo pacman -Rns'

# === INFORMATIONS SUR LES PAQUETS ===
#pacinfo (function)


############################################################################################################################
# ===  Editeurs ===
set -gx SUDO_EDITOR gnome-text-editor
set -gx EDITOR gnome-text-editor
set -gx VISUAL gnome-text-editor

############################################################################################################################
# === Message d'accueil Fish ===
function fish_greeting
end

############################################################################################################################
# === SUDO!! ===
function last_history_item
    history --max=1 --show-time=''
end

abbr -a !! --position anywhere --function last_history_item


############################################################################################################################
# === Surveilance du système ===

# === SCX ===
function scx --description 'scxctl get + check scheduler + monitor sans WARN'
    if not set -q USE_SCX
    return 0
end
    
    
    set -l output (scxctl get 2>/dev/null)

    if test -z "$output"
        set_color red
        echo "KO  scxctl ne retourne rien."
        set_color normal
        return 1
    end

    echo $output
    echo

    set -l sched_name (string match -rg 'running\\s+([[:alnum:]_-]+)' -- $output)

    if test -z "$sched_name"
        set_color red
        echo "KO  Aucun scheduler sched-ext actif."
        set_color normal
        return 1
    end

    set sched_name (string lower -- $sched_name)
    set -l bin "scx_$sched_name"

    set -l disk nvme0n1
    if test -r /sys/block/$disk/queue/scheduler
        set -l current_io (awk -F'[][]' '{print $2}' /sys/block/$disk/queue/scheduler)

        set_color cyan
        echo "Disk       : $disk"
        set_color normal
        echo "Scheduler  : $current_io"
    else
        set_color yellow
        echo "WARN Impossible de lire /sys/block/$disk/queue/scheduler"
        set_color normal
    end

    echo
    set_color brmagenta
    echo "Monitor : sudo $bin --monitor 3"
    set_color normal

    command sudo $bin --monitor 3 2>/dev/null
end

# === Journalctl ===
function journal
    journalctl -p err -n 20 --no-pager | bat -l log
end

# === Flags Kernel ===
function flags
    clear
    echo "KERNEL FLAGS (/proc/cmdline)"
    echo "============================="
    echo "Ligne complète :"
    printf "\e[93m%s\e[0m\n\n" (cat /proc/cmdline)
    echo "Flags par ligne (triés, uniques) :"
    set -l sorted_flags (string split ' ' (cat /proc/cmdline) | sort -u)
    set -l i 1
    for flag in $sorted_flags
        printf "\e[92m%2d.\e[0m \e[96m%s\e[0m\n" $i $flag
        set i (math $i + 1)
    end
    echo
end

# === EPP ===
function power
    set -l cpu0 /sys/devices/system/cpu/cpu0/cpufreq

    set -l epp_raw 'n/a'
    set -l epp_label 'n/a'
    if test -r $cpu0/energy_performance_preference
        set epp_raw (cat $cpu0/energy_performance_preference 2>/dev/null)
        switch $epp_raw
            case balance_power balance_performance
                set epp_label 'balanced'
            case performance
                set epp_label 'performance'
            case power
                set epp_label 'power'
            case default
                set epp_label $epp_raw
        end
    end

    set -l pprof 'n/a'
    if command -q powerprofilesctl
        set pprof (powerprofilesctl get 2>/dev/null)
        if test -z "$pprof"
            set pprof 'n/a'
        end
    end

    set -l tuned_ppd 'no'
    if command -q systemctl
        if systemctl --user is-active tuned-ppd.service >/dev/null 2>&1; or systemctl is-active tuned-ppd.service >/dev/null 2>&1
            set tuned_ppd 'yes'
        end
    end

    set -l scx 'n/a'
    if command -q scxctl
        set scx (scxctl get 2>/dev/null)
        if test -z "$scx"
            set scx 'n/a'
        end
    end

    set -l batdev (for d in /sys/class/power_supply/*; test -e "$d/type"; and string match -qr '^Battery$' (cat $d/type 2>/dev/null); and basename $d; end | head -n 1)
    set -l bat 'none'
    if test -n "$batdev"
        set -l base /sys/class/power_supply/$batdev
        set -l bat_status (cat $base/status 2>/dev/null)
        set -l capacity (cat $base/capacity 2>/dev/null)
        set -l full (cat $base/energy_full 2>/dev/null)
        set -l now (cat $base/energy_now 2>/dev/null)
        set -l power_now (cat $base/power_now 2>/dev/null)

        set bat "$batdev: $bat_status, $capacity%"
        if test -n "$full" -a -n "$now" -a "$full" -gt 0
            set -l pct (math "round($now * 100 / $full)")
            set bat "$bat, $pct% (energy)"
        end
        if test -n "$power_now" -a "$power_now" -gt 0
            set -l w (math "round($power_now / 1000000 * 100) / 100")
            set bat "$bat, $w W"
        end
    end

    echo "EPP: $epp_label ($epp_raw) | PPD: $pprof | tuned-ppd: $tuned_ppd"
    echo "SCX: $scx"
    echo "BAT: $bat"
end

############################################################################################################################
# === Surveillance Boot ===

# === FSTAB ===
function fstab
    clear
    echo "/etc/fstab"
    echo
    sudo bat --language=fstab --paging=never --style=plain /etc/fstab
    echo
end

# === MKINITCPIO ===
function mkinitcpio
    clear
    echo "/etc/mkinitcpio.conf"
    echo
    sudo bat --language=ini --paging=never --style=plain /etc/mkinitcpio.conf
    echo
end


############################################################################################################################
# === Maintenance ===

# === Clean ===
function clean
    set -l orphans (pacman -Qtdq 2>/dev/null)

    if test (count $orphans) -gt 0
        echo "Suppression des paquets orphelins : $orphans"
        sudo pacman -Rns $orphans
    else
        echo "Aucun paquet orphelin."
    end

    paru -Scc
    profile-cleaner v
    archclean full
end

# === Statistiques Pacman ===
function pacstats
    echo "Nombre de paquets installés :"
    pacman -Q | wc -l
    echo "Taille totale des paquets installés :"
    expac -H M '%m' | awk '{sum += $1} END {printf "%.2f GiB\\n", sum/1024}'
end


# === FWUPDATE ===
function fwupdate --description "Mettre à jour firmware (fwupdmgr full)"
    echo
    set_color yellow
    echo "📦 fwupdmgr : mise à jour firmware complète"
    set_color normal

    echo
    set_color green
    echo "1. Unmask du service fwupd…"
    set_color normal
    sudo systemctl unmask fwupd.service

    echo
    set_color green
    echo "2. Démarrage du service fwupd…"
    set_color normal
    sudo systemctl start fwupd.service

    echo
    set_color green
    echo "3. Rafraîchissement metadata (fwupdmgr refresh)…"
    set_color normal
    sudo fwupdmgr refresh --force

    echo
    set_color green
    echo "4. Vérifier les mises à jour disponibles (fwupdmgr get-updates)…"
    set_color normal
    sudo fwupdmgr get-updates

    echo
    set_color green
    echo "5. Installer les mises à jour (fwupdmgr update)…"
    set_color normal
    sudo fwupdmgr update

    echo
    set_color green
    echo "6. Arrêter le service fwupd…"
    set_color normal
    sudo systemctl stop fwupd.service

    echo
    set_color green
    echo "7. Masquer le service fwupd…"
    set_color normal
    sudo systemctl mask fwupd.service

    echo
    set_color cyan
    echo "📦 Mise à jour firmware terminée."
    set_color normal
end

############################################################################################################################
# === VAULT de commandes ===
function vault --description "Vault de commandes utiles"
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                  📦 VAULT - Mémo alias et functions                 ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""

    set -l vault_labels \
        "=== BOOT ===" \
        "MAJ initramfs (limine-mkinitcpio)" \
        "Boot time (systemd-analyze)" \
        "Boot analyze (systemd-analyze blame)" \
        "=== SURVEILLANCE ===" \
        "Scheduler scx (scx)" \
        "Erreurs journalctl" \
        "Flags kernel" \
        "Afficher EPP / power" \
        "=== MAINTENANCE ===" \
        "Nettoyage système (clean)" \
        "pacstats" \
        "=== SYSTÈME ===" \
        "fstab" \
        "mkinitcpio.conf" \
        "stockage (duf)" \
        "fwupd" \
        "control"

    set -l vault_cmds \
        "" \
        "sudo limine-mkinitcpio" \
        "systemd-analyze" \
        "systemd-analyze blame" \
        "" \
        "scx" \
        "journal" \
        "flags" \
        "power" \
        "" \
        "clean" \
        "pacstats" \
        "" \
        "fstab" \
        "mkinitcpio" \
        "stockage" \
        "fwupdate" \
        "control"

    set -l count (count $vault_labels)

    for i in (seq $count)
        if string match -qr '^===.*===$' -- $vault_labels[$i]
            set_color brblue
            echo $vault_labels[$i]
            set_color normal
        else
            printf "%2d) %s\n" $i $vault_labels[$i]
        end
    end

    echo
    set_color yellow
    echo "Choisis un numéro entre 1 et $count (q pour quitter)"
    set_color normal

    while true
        read -P "> " choice

        if test -z "$choice"
            continue
        end

        if test "$choice" = "q"
            echo "Abandon."
            set_color normal
            return 0
        end

        if string match -rq '^[0-9]+$' -- $choice
            if test $choice -ge 1 -a $choice -le $count
                set -l cmd $vault_cmds[$choice]
                if test -z "$cmd"
                    continue
                end
                echo
                set_color green
                echo "→ Exécution : $cmd"
                set_color normal
                echo
                fish -c $cmd
                set_color normal
                echo
                continue
            end
        end

        set_color red
        echo "Entrée invalide. Numéro entre 1 et $count, ou q pour quitter."
        set_color normal
    end
end

############################################################################################################################
# === Fussy search ===
function search --description "Recherche fuzzy de fichiers (sans les caches) avec aperçu et lancement du fichier (ENTREE)"

    set -l pattern $argv
    if test (count $pattern) -eq 0
        echo "Usage: search <motif>"
        return 1
    end

    set -l file (
        find / \
            \( -path /proc -o -path /sys -o -path /dev -o -path /run -o -path /tmp -o -path /var/tmp -o -path /var/cache -o -path '*/.cache' -o -path '*/.cache/*' -o -path '*/.local/share/Trash' -o -path '*/.local/share/Trash/*' -o -path '*/node_modules' -o -path '*/node_modules/*' -o -path '*/.git' -o -path '*/.git/*' -o -path '*/.venv' -o -path '*/.venv/*' -o -path '*/venv' -o -path '*/venv/*' -o -path '*/build' -o -path '*/build/*' -o -path '*/dist' -o -path '*/dist/*' -o -path '*/target' -o -path '*/target/*' \) -prune -o \
            -type f -iname "*$pattern*" -print 2>/dev/null | \
        awk '
            function basename(path,    n,a) {
                n = split(path, a, "/")
                return a[n]
            }
            {
                n++
                b = basename($0)
                sub("/" b "$", "", $0)
                if ($0 == "") $0 = "/"
                printf "\033[38;5;245m%3d\033[0m  \033[38;5;111m%s\033[0m/\033[38;5;81m%s\033[0m\n", n, $0, b
            }
        ' | \
        fzf --ansi \
            --prompt='🔎 search > ' \
            --pointer='▶' \
            --marker='✓' \
            --layout=reverse \
            --border=rounded \
            --height=80% \
            --preview "bat --color=always --style=plain --line-range=:200 {2..} 2>/dev/null || head -n 200 {2..} 2>/dev/null" \
            --preview-window='right:60%:wrap'
    )

    if test -n "$file"
        set -l path (string replace -r '^\s*[0-9]+\s+' '' -- "$file")
        xdg-open "$path" >/dev/null 2>&1 &
    end
end


############################################################################################################################
# === PACMAN ===

# === INSTALLATION/DESINSTALLATION DE PAQUETS ===
# === sudo pacman -S ===
function pacinstall --description "Installe un paquet avec pacman"
    command sudo pacman -S $argv
end

# === sudo pacman -Rns ===
function pacremove --description "Supprime un paquet avec vérification des dépendances"
    command sudo pacman -Rns $argv
end

# === INFORMATIONS SUR LES PAQUETS ===
function pacinfo --description "Infos paquet (installé ou dépôt)"
    set -l pkg $argv
    if test -z "$pkg"
        echo "Usage: pacinfo <nom_paquet>"
        return 1
    end

    if pacman -Q --quiet "$pkg" > /dev/null 2>&1
        echo "=== Paquet installé ==="
        pacman -Qi "$pkg"
    else
        echo "=== Paquet dans les dépôts ==="
        pacman -Si "$pkg"
    end
end

# === RECHERCHE DE CHEMIN D'UN PAQUET PUIS DE QUEL PAQUET IL DEPEND ===
function pacpick --description "Trouver un fichier par nom puis lancer pacman -Qo sur le chemin choisi"
    read -P "Nom du fichier ou fragment: " term
    if test -z "$term"
        echo "Aucune saisie."
        return 1
    end

    set -l matches (pacman -Ql | grep -F "$term")
    if test (count $matches) -eq 0
        echo "Aucun fichier trouvé."
        return 1
    end

    set -l paths
    echo

    for i in (seq (count $matches))
        set -l path (string replace -r '^[^ ]+\s+' '' -- $matches[$i])
        set paths $paths "$path"
        printf "%3d) %s\n" $i "$path"
    end

    echo
    read -P "Numéro du fichier (q pour quitter): " choice

    if test "$choice" = "q"
        echo "Abandon."
        return 0
    end

    if not string match -rq '^[0-9]+$' -- "$choice"
        echo "Entrée invalide."
        return 1
    end

    if test "$choice" -lt 1 -o "$choice" -gt (count $paths)
        echo "Numéro hors plage."
        return 1
    end

    echo
    pacman -Qo "$paths[$choice]"
end
# === RECHERCHE DE DÉPENDANCES INUTILES !! VERIFIER CHAQUE PAQUET AVEC PACMAN -Qi ===
function orphans+ --description "Affiche les dépendances inutiles, avec avertissement"
    echo
    set_color yellow
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║      ⚠️  DÉPENDANCES INUTILES — VÉRIFIER AVEC Qi         ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo
    echo "Aperçu uniquement : aucune suppression."
    echo "Commande de contrôle : pacman -Qi <paquet>"
    echo
    set_color normal

    pacman -Qdq | xargs -r sudo pacman -Rsu --print
end

############################################################################################################################
# === VAULT Pacman ===
function pacvault --description "Affiche la liste des alias pacman et leurs fonctions"
    echo
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                  📦 PACVAULT - Mémo Pacman               ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo

    set -l vault_labels \
        "Recherche dans les dépôts" \
        "Recherche dans les paquets installés" \
        "Infos paquet" \
        "Fichiers d'un paquet" \
        "Dépendances d'un paquet" \
        "Fichier → paquet propriétaire"

    set -l count (count $vault_labels)

    for i in (seq $count)
        printf "%2d) %s\n" $i $vault_labels[$i]
    end

    echo
    set_color yellow
    echo "Choisis un numéro entre 1 et $count (q pour quitter)"
    set_color normal

    while true
        read -P "> " choice

        if test -z "$choice"
            continue
        end

        if test "$choice" = "q"
            echo "Abandon."
            set_color normal
            return 0
        end

        if string match -rq '^[0-9]+$' -- $choice
            if test $choice -ge 1 -a $choice -le $count
                switch $choice
                    case 1
                        read -P "Nom du paquet: " pkg
                        if test -n "$pkg"
                            pacsearch "$pkg"
                        end
                    case 2
                        read -P "Nom du paquet: " pkg
                        if test -n "$pkg"
                            pacsearch_installed "$pkg"
                        end
                    case 3
                        read -P "Nom du paquet: " pkg
                        if test -n "$pkg"
                            pacinfo "$pkg"
                        end
                    case 4
                        read -P "Terme de recherche: " term
                        if test -n "$term"
                            pacfiles "$term"
                        end
                    case 5
                        read -P "Terme de recherche: " term
                        if test -n "$term"
                            pacdep "$term"
                        end
                    case 6
                        pacpick
                end
                echo
                continue
            end
        end

        set_color red
        echo "Entrée invalide. Numéro entre 1 et $count, ou q pour quitter."
        set_color normal
    end
end

############################################################################################################################
# === VAULT LIMINE ===
function liminevault --description "Affiche la liste des commandes Limine/Snapper"
    echo
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                 🧭 LIMINEVAULT - Mémo Limine                   ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo

    echo "Boot / installation"
    echo

    set -l boot_labels \
        "Éditer /etc/default/limine" \
        "Installer Limine sur l'ESP (limine-install)" \
        "Mettre à jour Limine (limine-update)" \
        "Mettre à jour avec mkinitcpio (limine-mkinitcpio)" \
        "Scanner les entrées EFI actives (limine-scan)" \
        "Lister l'arborescence des entrées (limine-list)"

    set -l boot_count (count $boot_labels)

    for i in (seq $boot_count)
        printf "%2d) %s\n" $i $boot_labels[$i]
    end

    echo
    echo "Snapper / snapshots"
    echo

    set -l snap_labels \
        "Synchroniser les snapshots Snapper (limine-snapper-sync)" \
        "Lister les snapshots gérés par Limine (limine-snapper-list)" \
        "Détails sur les snapshots bootables (limine-snapper-info)" \
        "Restaurer depuis un snapshot (limine-snapper-restore)" \
        "Afficher /etc/mkinitcpio.conf (mkinitcpio)"

    set -l snap_count (count $snap_labels)

    for i in (seq $snap_count)
        printf "%2d) %s\n" (math $boot_count + $i) $snap_labels[$i]
    end

    set -l count (math $boot_count + $snap_count)

    echo
    set_color yellow
    echo "Choisis un numéro entre 1 et $count (q pour quitter)"
    set_color normal

    while true
        read -P "> " choice

        if test -z "$choice"
            continue
        end

        if test "$choice" = "q"
            echo "Abandon."
            set_color normal
            return 0
        end

        if string match -rq '^[0-9]+$' -- $choice
            if test $choice -ge 1 -a $choice -le $count
                switch $choice
                    case 1
                        sudo micro /etc/default/limine
                    case 2
                        sudo limine-install
                    case 3
                        sudo limine-update
                    case 4
                        sudo limine-mkinitcpio
                    case 5
                        limine-scan
                    case 6
                        limine-list
                    case 7
                        sudo limine-snapper-sync
                    case 8
                        limine-snapper-list
                    case 9
                        limine-snapper-info
                    case 10
                        sudo limine-snapper-restore
                    case 11
                        mkinitcpio
                end
                echo
                continue
            end
        end

        set_color red
        echo "Entrée invalide. Numéro entre 1 et $count, ou q pour quitter."
        set_color normal
    end
end


############################################################################################################################
# === MEMO GENERAL ===
function memo --description "Liste les commandes utiles du config.fish par catégories"
    echo
    set_color brcyan
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║              📝 MEMO - Commandes du config.fish          ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    set_color normal
    echo

    set -l n 1

    function __memo_print_section --argument title icon color
        echo
        set_color $color
        echo "$icon $title"
        set_color normal
    end

    function __memo_print_item --argument idx cmd desc
        set_color brblack
        printf "%2d) " $idx
        set_color brgreen
        printf "%s" $cmd
        set_color normal
        printf " — %s\n" $desc
    end

    __memo_print_section "Éditeurs" "✏️" brmagenta
    __memo_print_item $n "vim" "Ouvre Micro à la place de Vim."; set n (math $n + 1)
    __memo_print_item $n "vi" "Ouvre Micro à la place de Vi."; set n (math $n + 1)
    __memo_print_item $n "gedit" "Ouvre l'éditeur GNOME."; set n (math $n + 1)
    __memo_print_item $n "nano" "Ouvre Micro à la place de Nano."; set n (math $n + 1)
    __memo_print_item $n "notepad" "Ouvre l'éditeur GNOME."; set n (math $n + 1)

    __memo_print_section "Système" "⚙️" brcyan
    __memo_print_item $n "rm" "Demande confirmation avant suppression."; set n (math $n + 1)
    __memo_print_item $n "stockage" "Affiche l'usage disque."; set n (math $n + 1)
    __memo_print_item $n "systemd" "Lance l'outil systemd simplifié."; set n (math $n + 1)
    __memo_print_item $n "lastpackages" "Recherche les derniers paquets."; set n (math $n + 1)
    __memo_print_item $n "liminestats" "Affiche les infos snapshot Limine."; set n (math $n + 1)
    __memo_print_item $n "scrub" "Lance un scrub Btrfs sur /."; set n (math $n + 1)
    __memo_print_item $n "bios" "Redémarre dans le BIOS/UEFI."; set n (math $n + 1)
    __memo_print_item $n "boot" "Affiche les infos de boot."; set n (math $n + 1)
    __memo_print_item $n "boot!" "Affiche le détail des lenteurs de boot."; set n (math $n + 1)

    __memo_print_section "AUR" "📦" bryellow
    __memo_print_item $n "aur" "Installe un paquet AUR via Shelly."; set n (math $n + 1)
    __memo_print_item $n "aursearch" "Recherche dans l'AUR via Shelly."; set n (math $n + 1)

    __memo_print_section "Fish" "🐟" brblue
    __memo_print_item $n "sourcefish" "Recharge la config Fish."; set n (math $n + 1)
    __memo_print_item $n "fishedit" "Ouvre la config Fish dans l'éditeur."; set n (math $n + 1)
    __memo_print_item $n "!!" "Remplace par la dernière commande."; set n (math $n + 1)

    __memo_print_section "Pacman" "👾" brgreen
    __memo_print_item $n "pacsearch" "Recherche un paquet dans les dépôts."; set n (math $n + 1)
    __memo_print_item $n "pacsearch_installed" "Recherche un paquet installé."; set n (math $n + 1)
    __memo_print_item $n "pacdep" "Affiche les dépendances inverses."; set n (math $n + 1)
    __memo_print_item $n "pacfiles" "Liste les fichiers d'un paquet."; set n (math $n + 1)
    __memo_print_item $n "orphans" "Supprime les orphelins."; set n (math $n + 1)
    __memo_print_item $n "pacinstall" "Installe un paquet avec pacman."; set n (math $n + 1)
    __memo_print_item $n "pacremove" "Supprime un paquet avec pacman et vérifie les dépendances."; set n (math $n + 1)
    __memo_print_item $n "pacinfo" "Affiche les infos d'un paquet installé ou dépôt."; set n (math $n + 1)
    __memo_print_item $n "pacpick" "Affiche le chemin d'un pbinaire puis à quel paquet il appartient."; set n (math $n + 1)
    __memo_print_item $n "orphans+" "Liste les dépendances inutiles sans supprimer."; set n (math $n + 1)

    __memo_print_section "Surveillance" "📈" bryellow
    __memo_print_item $n "scx" "Affiche le scheduler SCX et son monitoring."; set n (math $n + 1)
    __memo_print_item $n "journal" "Affiche les 20 dernières erreurs du journal systemd."; set n (math $n + 1)
    __memo_print_item $n "flags" "Montre les flags kernel de /proc/cmdline."; set n (math $n + 1)
    __memo_print_item $n "power" "Montre EPP, power profile, SCX et batterie."; set n (math $n + 1)

    __memo_print_section "Boot" "🚀" brred
    __memo_print_item $n "fstab" "Affiche /etc/fstab en lecture seule."; set n (math $n + 1)
    __memo_print_item $n "mkinitcpio" "Affiche /etc/mkinitcpio.conf en lecture seule."; set n (math $n + 1)
    __memo_print_item $n "fwupdate" "Lance une mise à jour firmware complète."; set n (math $n + 1)
    __memo_print_item $n "vault" "Menu des commandes utiles globales."; set n (math $n + 1)
    __memo_print_item $n "liminevault" "Menu des commandes Limine/Snapper."; set n (math $n + 1)
    __memo_print_item $n "pacvault" "Menu des commandes Pacman."; set n (math $n + 1)

    __memo_print_section "Utilitaires" "🔎" brwhite
    __memo_print_item $n "clean" "Nettoie les paquets orphelins et le cache."; set n (math $n + 1)
    __memo_print_item $n "pacstats" "Affiche le nombre et la taille des paquets."; set n (math $n + 1)
    __memo_print_item $n "search" "Recherche fuzzy de fichiers sur le système."; set n (math $n + 1)

    functions -e __memo_print_section
    functions -e __memo_print_item
end