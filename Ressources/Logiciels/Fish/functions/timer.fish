function timer
    read -P "Fermer Vivaldi puis choisir le nombre de minutes (de 1 à 15) : " -l mins

    # Validation : entier entre 1 et 15
    if not string match -qr '^[0-9]+$' -- $mins
        echo "Erreur : entre un nombre entier." >&2
        return 1
    end
    if test $mins -lt 1 -o $mins -gt 15
        echo "Erreur : le nombre doit être entre 1 et 15." >&2
        return 1
    end

    echo "Arrêt du laptop dans $mins minute(s)..."
    sudo shutdown -h +$mins
end
