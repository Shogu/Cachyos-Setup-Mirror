source /usr/share/cachyos-fish-config/cachyos-config.fish

# overwrite greeting
# potentially disabling fastfetch
#function fish_greeting
#    # smth smth
#end

############################################################################################################################
# Alias Editeurs
alias vim='micro'
alias vi='micro'
alias gedit='gnome-text-editor'
alias nano='micro'
alias notepad='gnome-text-editor'

# Alias système
alias rm='rm -I'
alias stockage='duf'
alias systemd='isd'
alias lastpackages='rip'
alias liminestats='limine-snapper-info'
alias scrub='sudo btrfs scrub start -B /'
alias bios='systemctl reboot --firmware-setup'
alias boot='systemd-analyze'
alias boot!='systemd-analyze blame'

# Alias Fish
alias sourcefish='source ~/.config/fish/config.fish'
alias fishedit='xdg-open ~/.config/fish/config.fish'


############################################################################################################################
# Éditeur par défaut
set -gx SUDO_EDITOR gnome-text-editor
set -gx EDITOR gnome-text-editor
set -gx VISUAL gnome-text-editor

############################################################################################################################
# Message d'accueil Fish
function fish_greeting
end

############################################################################################################################
# Surveillance
function scx --description 'scxctl get + check scheduler + monitor sans WARN'
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

function journal
    journalctl -p err -n 20 --no-pager | bat -l log
end

function flags
    clear
    echo "KERNEL FLAGS (/proc/cmdline)"
    echo "============================="
    echo "Ligne complète :"
    printf "\\e[93m%s\\e[0m\\n\\n" (cat /proc/cmdline)
    echo "Flags par ligne (triés, uniques) :"
    set -l all_flags (string split ' ' (cat /proc/cmdline))
    set -l flags
    for flag in $all_flags
        if not contains -- $flag $flags
            set flags $flags $flag
        end
    end
    set -l sorted_flags (printf "%s\\n" $flags | sort)
    set -l i 1
    for flag in $sorted_flags
        printf "\\e[92m%2d.\\e[0m \\e[96m%s\\e[0m\\n" $i $flag
        set i (math $i + 1)
    end
    echo
end

############################################################################################################################
# Boot
function fstab
    clear
    echo "/etc/fstab"
    echo
    sudo bat --language=fstab --paging=never --style=plain /etc/fstab
    echo
end

function mkinitcpio
    clear
    echo "/etc/mkinitcpio.conf"
    echo
    sudo bat --language=ini --paging=never --style=plain /etc/mkinitcpio.conf
    echo
end

############################################################################################################################
# Maintenance
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

function pacstats
    echo "Nombre de paquets installés :"
    pacman -Q | wc -l
    echo "Taille totale des paquets installés :"
    expac -H M '%m' | awk '{sum += $1} END {printf "%.2f GiB\\n", sum/1024}'
end

############################################################################################################################
# Système
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
    echo "7. Masker le service fwupd…"
    set_color normal
    sudo systemctl mask fwupd.service

    echo
    set_color cyan
    echo "📦 Mise à jour firmware terminée."
    set_color normal
end

function control
    command control
end

############################################################################################################################
# Menu
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
                eval $cmd
                set_color normal
                return $status
            end
        end

        set_color red
        echo "Entrée invalide. Numéro entre 1 et $count, ou q pour quitter."
        set_color normal
    end
end

############################################################################################################################
# Recherche fuzzy de fichiers sur toutes les partitions montées
#utilise find + fzf avec prévisualisation
function search --description "Recherche fuzzy de fichiers (toutes partitions)"
    set -l pattern $argv
    if test -z "$pattern"
        echo "Usage: search <motif>"
        return 1
    end

    find / -xdev -type f -name "*$pattern*" 2>/dev/null | \
        fzf --preview "bat --color=always {} 2>/dev/null || cat {} 2>/dev/null | head -n 100" \
            --preview-window "right:60%" \
            --height 80% \
            --bind "ctrl-a:select-all" \
            --multi | \
        while read -l file
            test -n "$file" && echo "$file"
        end
end

############################################################################################################################
# Pacman

# === RECHERCHE DE PAQUETS ===
alias pacsearch='pacman -Ss'
alias pacsearch_installed='pacman -Qs'

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

# === DÉPENDANCES ===
alias pacdep='pactree -r'

# === RECHERCHE DE FICHIERS DANS UN PAQUET ===
alias pacfiles='pacman -Ql'


############################################################################################################################
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
        "Dépendances d'un paquet"

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
                end
                return $status
            end
        end




############################################################################################################################
function fetch --description "System info type fastfetch"
    set -l os (grep '^PRETTY_NAME=' /etc/os-release | cut -d= -f2- | tr -d '"')
    set -l kernel (uname -r)
    set -l shell (basename $SHELL)

    set -l pkgs "N/A"
    if type -q pacman
        set pkgs (pacman -Qq 2>/dev/null | count)
    end

    set -l cpu "N/A"
    set -l cpu_raw ""
    if test -r /proc/cpuinfo
        set cpu_raw (awk -F': *' '/model name/ {print $2; exit}' /proc/cpuinfo)
    end
    if test -z "$cpu_raw" -a (type -q lscpu; echo $status) -eq 0
        set cpu_raw (lscpu 2>/dev/null | awk -F': *' '/Model name:/ {print $2; exit}')
    end
    if test -n "$cpu_raw"
        set cpu (string replace -r '\s+w/ Radeon.*$' '' -- $cpu_raw)
        set cpu (string replace -r '\s+with Radeon.*$' '' -- $cpu)
        set cpu (string trim -- $cpu)
    end
    test -z "$cpu"; and set cpu "N/A"

    set -l gpu "N/A"
    if type -q lspci
        set -l gpu_raw (lspci -nn 2>/dev/null | awk '/VGA compatible controller|3D controller|Display controller/ {print; exit}')
        if test -n "$gpu_raw"
            set gpu (echo $gpu_raw | sed -E 's/^.*: //; s/ \[[0-9a-fA-F]{4}:[0-9a-fA-F]{4}\]$//; s/ \(rev [^)]+\)$//')
            set gpu (string replace -r '^Advanced Micro Devices, Inc\. \[AMD/ATI\] ' 'AMD ' -- $gpu)
            set gpu (string replace -r ' \[Radeon ([^]]+) Graphics\]' ' Radeon \1' -- $gpu)
            set gpu (string replace -r '^AMD ([Kk]rackan).*' 'AMD Radeon $1' -- $gpu)
            set gpu (string replace -r '\s+/\s+' '/' -- $gpu)
            set gpu (string trim -- $gpu)
        end
    end
    test -z "$gpu"; and set gpu "N/A"

    set -l ramline "N/A"
    if type -q free
        set -l mem_total (free -h | awk '/^Mem:/ {print $2}')
        set -l mem_used (free -h | awk '/^Mem:/ {print $3}')
        set -l mem_pct (free | awk '/^Mem:/ {if ($2>0) printf "%.0f", $3/$2*100}')
        if test -n "$mem_total" -a -n "$mem_used" -a -n "$mem_pct"
            set ramline "$mem_used / $mem_total ($mem_pct%)"
        end
    end

    set -l de "N/A"
    set -q XDG_CURRENT_DESKTOP; and set de $XDG_CURRENT_DESKTOP

    set -l session "Wayland"
    set -q XDG_SESSION_TYPE; and set session $XDG_SESSION_TYPE
    set -l wm "Mutter"

    set -l uptime (uptime -p | sed 's/^up //')
    test -z "$uptime"; and set uptime "N/A"

    set -l bootline "N/A"
    if type -q systemd-analyze
        set bootline (systemd-analyze time 2>/dev/null | sed -n 's/.*= \([0-9.]*s\).*/\1/p' | head -n1)
        test -z "$bootline"; and set bootline "N/A"
    end

    set -l scxline "N/A"
    if type -q scxctl
        set scxline (scxctl get 2>/dev/null | string trim)
        test -z "$scxline"; and set scxline "N/A"
    end

    set -l iosched "N/A"
    for dev in nvme0n1 nvme1n1 nvme2n1 sda sdb vda vdb
        set -l schedfile /sys/block/$dev/queue/scheduler
        if test -r $schedfile
            set -l raw (cat $schedfile 2>/dev/null | string trim)
            set -l picked (string replace -r '.*\[([^]]+)\].*' '$1' -- $raw)
            if test -n "$picked"
                set iosched "$dev: $picked"
                break
            else if test -n "$raw"
                set iosched "$dev: $raw"
                break
            end
        end
    end

    set -l root_line "N/A"
    set -l root_src (findmnt -n -o SOURCE / 2>/dev/null)
    set -l root_fstype (findmnt -n -o FSTYPE / 2>/dev/null)
    set -l root_used (df -h / | awk 'NR==2 {print $3}')
    set -l root_size (df -h / | awk 'NR==2 {print $2}')
    set -l root_pct (df -h / | awk 'NR==2 {print $5}')
    if test -n "$root_size" -a -n "$root_used"
        set root_line "$root_size $root_used /"
        if test -n "$root_fstype"
            set root_line "$root_line $root_fstype"
        end
        if test -n "$root_pct"
            set root_line "$root_line ($root_pct)"
        end
        if test -n "$root_src"
            set root_line "$root_line - $root_src"
        end
    end

    set -l boot_fs_line "N/A"
    if test -d /boot
        set -l boot_src (findmnt -n -o SOURCE /boot 2>/dev/null)
        set -l boot_fstype (findmnt -n -o FSTYPE /boot 2>/dev/null)
        set -l boot_used (df -h /boot | awk 'NR==2 {print $3}')
        set -l boot_size (df -h /boot | awk 'NR==2 {print $2}')
        set -l boot_pct (df -h /boot | awk 'NR==2 {print $5}')
        if test -n "$boot_size" -a -n "$boot_used"
            set boot_fs_line "$boot_size $boot_used /"
            if test -n "$boot_fstype"
                set boot_fs_line "$boot_fs_line $boot_fstype"
            end
            if test -n "$boot_pct"
                set boot_fs_line "$boot_fs_line ($boot_pct)"
            end
            if test -n "$boot_src"
                set boot_fs_line "$boot_fs_line - $boot_src"
            end
        end
    end

    set -l battery_line "N/A"
    if type -q upower
        set -l batdev (upower -e 2>/dev/null | awk '/battery/ {print; exit}')
        if test -n "$batdev"
            set -l batt_pct (upower -i $batdev 2>/dev/null | awk -F': *' '/percentage/ {print $2; exit}')
            set -l batt_state (upower -i $batdev 2>/dev/null | awk -F': *' '/state/ {print $2; exit}')
            set -l batt_time (upower -i $batdev 2>/dev/null | awk -F': *' '/time to (empty|full)/ {print $2; exit}')
            set -l batt_watts (upower -i $batdev 2>/dev/null | awk -F': *' '/energy-rate/ {print $2; exit}')
            if test -n "$batt_pct"
                set battery_line $batt_pct
                if test -n "$batt_state"
                    set battery_line "$battery_line, $batt_state"
                end
                if test -n "$batt_time"
                    set battery_line "$battery_line, $batt_time"
                end
                if test -n "$batt_watts"
                    set battery_line "$battery_line, $batt_watts"
                end
            end
        end
    end

    set_color cyan
    echo "╭──  Software ────────────────────────────"
    set_color normal
    echo "  OS: $os"
    echo "  Kernel: Linux $kernel"
    echo "󰏖  Packages: $pkgs (pacman)"
    echo "  Shell: $shell"

    set_color cyan
    echo "╭──  Hardware ───────────────────────────"
    set_color normal
    echo "  CPU: $cpu"
    echo "󰢮  GPU: $gpu"
    echo "  RAM: $ramline"
    echo "  Disk /: $root_line"
    echo "󰜋  Disk /boot: $boot_fs_line"

    set_color cyan
    echo "╭── 󰍹 Desktop ────────────────────────────"
    set_color normal
    echo "󰍹  Session: $session"
    echo "󰌽  WM: $wm"
    echo "  DE: $de"

    set_color cyan
    echo "╭──  Kernel extras ──────────────────────"
    set_color normal
    echo "  SCX: $scxline"
    echo "󰕍  I/O scheduler: $iosched"
    echo "󰔟  Boot: $bootline"

    set_color cyan
    echo "╭── 󰂄 Power ──────────────────────────────"
    set_color normal
    echo "󰂄  Battery: $battery_line"

    set_color cyan
    echo "╭── 󰥔 Uptime ─────────────────────────────"
    set_color normal
    echo "󰥔  Uptime: $uptime"
end
        echo "Entrée invalide. Numéro entre 1 et $count, ou q pour quitter."
        set_color normal
    end
end