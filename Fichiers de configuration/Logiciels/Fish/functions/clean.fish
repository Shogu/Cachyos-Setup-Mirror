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
