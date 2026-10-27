function pacvault --description "Affiche la liste des abbr et fonctions pacman disponibles"
    echo
    set_color brcyan
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                  📦 PACVAULT - Mémo Pacman                ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    set_color normal
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

        if not string match -rq '^[0-9]+$' -- $choice
            set_color red
            echo "Entrée invalide. Numéro entre 1 et $count, ou q pour quitter."
            set_color normal
            continue
        end

        if test $choice -lt 1 -o $choice -gt $count
            set_color red
            echo "Entrée invalide. Numéro entre 1 et $count, ou q pour quitter."
            set_color normal
            continue
        end

        switch $choice
            case 1
                read -P "Nom du paquet: " pkg
                if test -n "$pkg"
                    # pacsearch = abbr → pacman -Ss
                    set -l exp (abbr --query pacsearch 2>/dev/null)
                    if test -n "$exp"
                        eval $exp "$pkg"
                    else
                        command pacman -Ss "$pkg"
                    end
                end
            case 2
                read -P "Nom du paquet: " pkg
                if test -n "$pkg"
                    # pacsearch_installed = abbr → pacman -Qs
                    set -l exp (abbr --query pacsearch_installed 2>/dev/null)
                    if test -n "$exp"
                        eval $exp "$pkg"
                    else
                        command pacman -Qs "$pkg"
                    end
                end
            case 3
                read -P "Nom du paquet: " pkg
                if test -n "$pkg"
                    # pacinfo = fonction (autoload)
                    if functions -q pacinfo
                        pacinfo "$pkg"
                    else
                        command pacman -Qi "$pkg"
                    end
                end
            case 4
                read -P "Terme de recherche: " term
                if test -n "$term"
                    # pacfiles = abbr → pacman -Ql
                    set -l exp (abbr --query pacfiles 2>/dev/null)
                    if test -n "$exp"
                        eval $exp "$term"
                    else
                        command pacman -Ql "$term"
                    end
                end
            case 5
                read -P "Terme de recherche: " term
                if test -n "$term"
                    # pacdep = abbr → pactree -r
                    set -l exp (abbr --query pacdep 2>/dev/null)
                    if test -n "$exp"
                        eval $exp "$term"
                    else
                        command pactree -r "$term"
                    end
                end
            case 6
                # pacpick = fonction (autoload)
                if functions -q pacpick
                    pacpick
                else
                    read -P "Fichier: " file
                    if test -n "$file"
                        command pacman -Qo "$file"
                    end
                end
        end
        echo
        continue
    end
end