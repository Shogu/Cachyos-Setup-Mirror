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
