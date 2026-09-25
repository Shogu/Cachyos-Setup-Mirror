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
                            command pacman -Ss "$pkg"
                        end
                    case 2
                        read -P "Nom du paquet: " pkg
                        if test -n "$pkg"
                            command pacman -Qs "$pkg"
                        end
                    case 3
                        read -P "Nom du paquet: " pkg
                        if test -n "$pkg"
                            pacinfo "$pkg"
                        end
                    case 4
                        read -P "Terme de recherche: " term
                        if test -n "$term"
                            command pacman -Ql "$term"
                        end
                    case 5
                        read -P "Terme de recherche: " term
                        if test -n "$term"
                            command pactree -r "$term"
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
