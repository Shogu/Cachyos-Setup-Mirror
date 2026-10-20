function pacstats --description "Stats des paquets Arch"
    echo "Nombre de paquets installés :"
    pacman -Q | wc -l
    echo "Taille totale des paquets installés :"
    expac -H M '%m' | awk '{sum += $1} END {printf "%.2f GiB\\n", sum/1024}'
end
