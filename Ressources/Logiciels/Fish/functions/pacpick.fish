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
