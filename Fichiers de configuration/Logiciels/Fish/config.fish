source /usr/share/cachyos-fish-config/cachyos-config.fish

# Message d'accueil désactivé (voir fonction fish_greeting plus bas)

############################################################################################################################
# === Alias Editeurs ===
alias vim='micro'
alias vi='micro'
alias nano='micro'

alias notepad='gnome-text-editor'
alias gedit='gnome-text-editor'
alias edit='gnome-text-editor'

# === Alias Système ===
alias powertop='sudo powertop'
alias stop='shutdown now'
alias rm='rm -I'
alias stockage='duf'
alias systemd='isd'
alias lastpackages='rip'
alias liminestats='limine-snapper-info'
alias scrub='sudo btrfs scrub start -B /'
alias bios='systemctl reboot --firmware-setup'
alias boot='systemd-analyze'
alias boot!='systemd-analyze blame'
alias watts='echo "scale=2; $(cat /sys/class/power_supply/BAT0/power_now)/1000000" | bc'

# === Alias Shelly ===

# Gestion AUR
alias aur='shelly install aur'
alias aursearch='shelly search aur'
alias aurremove='shelly remove aur --opt-deps'
alias aurlist='shelly list aur'

# Gestion paquets standards
alias add='shelly install standard'
alias remove='shelly remove standard'


# Mises à jour Shelly
alias upgrade='set_color 3584e4; echo "╔══════════════════════╗"; echo "║  MISE À JOUR SHELLY  ║"; echo "╚══════════════════════╝"; set_color normal; echo; shelly upgrade standard; shelly upgrade aur; echo; read -P "Fermer avec ENTREE "'

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

# === RECHERCHE  D'ORPHELINS + DÉPENDANCES INUTILES ===
alias orphans='pacman -Qdtq'

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

    set -l output (scxctl get 2>/dev/null)

    if test -z "$output"
        set_color red
        echo "KO  scxctl ne retourne rien."
        set_color normal
        return 1
    end

    echo "$output"
    echo

    set -l sched_name (string match -rg 'running\s+([[:alnum:]_-]+)' -- $output)

    if test -z "$sched_name"
        set_color red
        echo "KO  Aucun scheduler sched-ext actif."
        set_color normal
        return 1
    end

    set -l sched_name (string lower -- $sched_name)
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

    return 0
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

    sudo pacman -Scc
    profile-cleaner v
    shelly purify standard
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
# === Fuzzy search ===
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
        "Éditer /boot/limine.conf" \
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
                        sudo micro /boot/limine.conf
                    case 2
                        sudo micro /etc/default/limine
                    case 3
                        sudo limine-install
                    case 4
                        sudo limine-update
                    case 5
                        sudo limine-mkinitcpio
                    case 6
                        limine-scan
                    case 7
                        limine-list
                    case 8
                        sudo limine-snapper-sync
                    case 9
                        limine-snapper-list
                    case 10
                        limine-snapper-info
                    case 11
                        sudo limine-snapper-restore
                    case 12
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
# === MEMO UNIFIÉ (Alias + Fonctions) ===
function memo --description "Liste interactive des alias et fonctions disponibles, organisés par catégories"
    echo
    set_color brcyan
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║              📝 MEMO - Alias et Fonctions Disponibles       ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    set_color normal
    echo

    echo "Sélectionnez une catégorie :"
    echo
    set_color brblue
    echo "  [1] 📑  ALIAS"
    echo "  [2] ⚙️  FONCTIONS"
    set_color normal
    echo
    set_color yellow
    read -P "Choix (1-2) ou 'q' pour quitter : " main_choice
    set_color normal

    if test "$main_choice" = "q"
        echo "Abandon."
        return 0
    end

    if not string match -rq '^[0-9]+$' -- "$main_choice"
        set_color red
        echo "Entrée invalide. Veuillez entrer un numéro valide."
        set_color normal
        return 1
    end

    if test "$main_choice" -lt 1 -o "$main_choice" -gt 2
        set_color red
        echo "Numéro hors plage. Veuillez choisir entre 1 et 2."
        set_color normal
        return 1
    end

    if test "$main_choice" = "1"
        # Affichage des alias
        set_color brcyan
        echo "╔═══════════════════════════════════════════════════════════╗"
        echo "║                     📑  ALIAS                             ║"
        echo "╚═══════════════════════════════════════════════════════════╝"
        set_color normal
        echo
        set_color brmagenta
        echo "✏️  ÉDITEURS"
        set_color normal
        set_color brblue; echo -n "  1) vim"; set_color normal; echo " → Micro"
        set_color brblue; echo -n "  2) vi"; set_color normal; echo " → Micro"
        set_color brblue; echo -n "  3) nano"; set_color normal; echo " → Micro"
        set_color brblue; echo -n "  4) notepad"; set_color normal; echo " → Éditeur GNOME"
        set_color brblue; echo -n "  5) gedit"; set_color normal; echo " → Éditeur GNOME"
        set_color brblue; echo -n "  6) edit"; set_color normal; echo " → Éditeur GNOME"
        echo

        set_color brmagenta
        echo "⚙️  SYSTÈME"
        set_color normal
        set_color brblue; echo -n "  7) powertop"; set_color normal; echo " → Powertop (sudo)"
        set_color brblue; echo -n "  8) stop"; set_color normal; echo " → Arrêt système"
        set_color brblue; echo -n "  9) rm"; set_color normal; echo " → Suppression sécurisée"
        set_color brblue; echo -n " 10) stockage"; set_color normal; echo " → Usage disque (duf)"
        set_color brblue; echo -n " 11) systemd"; set_color normal; echo " → Outil systemd"
        set_color brblue; echo -n " 12) lastpackages"; set_color normal; echo " → Derniers paquets"
        set_color brblue; echo -n " 13) liminestats"; set_color normal; echo " → Snapshots Limine"
        set_color brblue; echo -n " 14) scrub"; set_color normal; echo " → Scrub Btrfs sur /"
        set_color brblue; echo -n " 15) bios"; set_color normal; echo " → Redémarrage BIOS/UEFI"
        set_color brblue; echo -n " 16) boot"; set_color normal; echo " → Infos boot"
        set_color brblue; echo -n " 17) boot!"; set_color normal; echo " → Lenteurs boot"
        set_color brblue; echo -n " 18) watts"; set_color normal; echo " → Consommation énergétique"
        echo

        set_color brmagenta
        echo "📦  SHELLY (AUR & Paquets)"
        set_color normal
        set_color brblue; echo -n " 19) aur"; set_color normal; echo " → Installe paquet AUR"
        set_color brblue; echo -n " 20) aursearch"; set_color normal; echo " → Recherche AUR"
        set_color brblue; echo -n " 21) aurremove"; set_color normal; echo " → Supprime paquet AUR"
        set_color brblue; echo -n " 22) aurlist"; set_color normal; echo " → Liste paquets AUR"
        set_color brblue; echo -n " 23) add"; set_color normal; echo " → Installe paquet standard"
        set_color brblue; echo -n " 24) remove"; set_color normal; echo " → Supprime paquet standard"
        set_color brblue; echo -n " 25) upgrade"; set_color normal; echo " → Met à jour Shelly"
        echo

        set_color brmagenta
        echo "🐟  FISH"
        set_color normal
        set_color brblue; echo -n " 26) sourcefish"; set_color normal; echo " → Recharge config Fish"
        set_color brblue; echo -n " 27) fishedit"; set_color normal; echo " → Édite config Fish"
        set_color brblue; echo -n " 28) !!"; set_color normal; echo " → Dernière commande"
        echo

        set_color brmagenta
        echo "👾  PACMAN"
        set_color normal
        set_color brblue; echo -n " 29) pacsearch"; set_color normal; echo " → Recherche paquet"
        set_color brblue; echo -n " 30) pacsearch_installed"; set_color normal; echo " → Recherche paquet installé"
        set_color brblue; echo -n " 31) pacdep"; set_color normal; echo " → Dépendances inverses"
        set_color brblue; echo -n " 32) pacfiles"; set_color normal; echo " → Fichiers paquet"
        set_color brblue; echo -n " 33) orphans"; set_color normal; echo " → Supprime paquets orphelins"
        set_color brblue; echo -n " 34) pacinstall"; set_color normal; echo " → Installe paquet"
        set_color brblue; echo -n " 35) pacremove"; set_color normal; echo " → Supprime paquet"
        set_color brblue; echo -n " 36) pacinfo"; set_color normal; echo " → Infos paquet"
        set_color brblue; echo -n " 37) pacpick"; set_color normal; echo " → Paquet propriétaire fichier"
        set_color brblue; echo -n " 38) orphans+"; set_color normal; echo " → Dépendances inutiles"
        echo

        set_color yellow
        read -P "Choisissez un numéro entre 1 et 38, 'r' pour revenir au menu principal, ou 'q' pour quitter : " choice
        set_color normal

        if test "$choice" = "q"
            echo "Abandon."
            return 0
        else if test "$choice" = "r"
            fish -c "memo"
            return 0
        end

        if not string match -rq '^[0-9]+$' -- "$choice"
            set_color red
            echo "Entrée invalide. Veuillez entrer un numéro valide."
            set_color normal
            return 1
        end

        if test "$choice" -lt 1 -o "$choice" -gt 38
            set_color red
            echo "Numéro hors plage. Veuillez choisir entre 1 et 38."
            set_color normal
            return 1
        end

        # Exécution de la commande
        switch "$choice"
            case 1; set -l cmd "vim"
            case 2; set -l cmd "vi"
            case 3; set -l cmd "nano"
            case 4; set -l cmd "notepad"
            case 5; set -l cmd "gedit"
            case 6; set -l cmd "edit"
            case 7; set -l cmd "powertop"
            case 8; set -l cmd "stop"
            case 9; set -l cmd "rm"
            case 10; set -l cmd "stockage"
            case 11; set -l cmd "systemd"
            case 12; set -l cmd "lastpackages"
            case 13; set -l cmd "liminestats"
            case 14; set -l cmd "scrub"
            case 15; set -l cmd "bios"
            case 16; set -l cmd "boot"
            case 17; set -l cmd "boot!"
            case 18; set -l cmd "watts"
            case 19; set -l cmd "aur"
            case 20; set -l cmd "aursearch"
            case 21; set -l cmd "aurremove"
            case 22; set -l cmd "aurlist"
            case 23; set -l cmd "add"
            case 24; set -l cmd "remove"
            case 25; set -l cmd "upgrade"
            case 26; set -l cmd "sourcefish"
            case 27; set -l cmd "fishedit"
            case 28; set -l cmd "!!"
            case 29; set -l cmd "pacsearch"
            case 30; set -l cmd "pacsearch_installed"
            case 31; set -l cmd "pacdep"
            case 32; set -l cmd "pacfiles"
            case 33; set -l cmd "orphans"
            case 34; set -l cmd "pacinstall"
            case 35; set -l cmd "pacremove"
            case 36; set -l cmd "pacinfo"
            case 37; set -l cmd "pacpick"
            case 38; set -l cmd "orphans+"
        end

        echo
        set_color green
        echo "→ Exécution : $cmd"
        set_color normal
        echo
        fish -c "$cmd"
        echo

    else if test "$main_choice" = "2"
        # Affichage des fonctions
        set_color brcyan
        echo "╔═══════════════════════════════════════════════════════════╗"
        echo "║                   ⚙️  FONCTIONS                        ║"
        echo "╚═══════════════════════════════════════════════════════════╝"
        set_color normal
        echo
        set_color brmagenta
        echo "📈  SURVEILLANCE"
        set_color normal
        set_color brblue; echo -n "  1) scx"; set_color normal; echo " → Scheduler SCX"
        set_color brblue; echo -n "  2) journal"; set_color normal; echo " → Erreurs journalctl"
        set_color brblue; echo -n "  3) flags"; set_color normal; echo " → Flags kernel"
        set_color brblue; echo -n "  4) power"; set_color normal; echo " → EPP et batterie"
        echo

        set_color brmagenta
        echo "🚀  BOOT"
        set_color normal
        set_color brblue; echo -n "  5) fstab"; set_color normal; echo " → /etc/fstab"
        set_color brblue; echo -n "  6) mkinitcpio"; set_color normal; echo " → /etc/mkinitcpio.conf"
        set_color brblue; echo -n "  7) fwupdate"; set_color normal; echo " → Mise à jour firmware"
        echo

        set_color brmagenta
        echo "🧹  MAINTENANCE"
        set_color normal
        set_color brblue; echo -n "  8) clean"; set_color normal; echo " → Nettoyage système"
        set_color brblue; echo -n "  9) pacstats"; set_color normal; echo " → Statistiques paquets"
        set_color brblue; echo -n " 10) search"; set_color normal; echo " → Recherche fichiers"
        echo

        set_color brmagenta
        echo "🔍  LIMINE"
        set_color normal
        set_color brblue; echo -n " 11) liminevault"; set_color normal; echo " → Commandes Limine"
        echo

        set_color yellow
        read -P "Choisissez un numéro entre 1 et 11, 'r' pour revenir au menu principal, ou 'q' pour quitter : " choice
        set_color normal

        if test "$choice" = "q"
            echo "Abandon."
            return 0
        else if test "$choice" = "r"
            fish -c "memo"
            return 0
        end

        if not string match -rq '^[0-9]+$' -- "$choice"
            set_color red
            echo "Entrée invalide. Veuillez entrer un numéro valide."
            set_color normal
            return 1
        end

        if test "$choice" -lt 1 -o "$choice" -gt 11
            set_color red
            echo "Numéro hors plage. Veuillez choisir entre 1 et 11."
            set_color normal
            return 1
        end

        # Exécution de la commande
        switch "$choice"
            case 1; set -l cmd "scx"
            case 2; set -l cmd "journal"
            case 3; set -l cmd "flags"
            case 4; set -l cmd "power"
            case 5; set -l cmd "fstab"
            case 6; set -l cmd "mkinitcpio"
            case 7; set -l cmd "fwupdate"
            case 8; set -l cmd "clean"
            case 9; set -l cmd "pacstats"
            case 10; set -l cmd "search"
            case 11; set -l cmd "liminevault"
        end

        echo
        set_color green
        echo "→ Exécution : $cmd"
        set_color normal
        echo
        fish -c "$cmd"
        echo
    end
end
