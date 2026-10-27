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
