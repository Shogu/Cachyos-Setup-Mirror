function pacremove --description "Supprime un paquet avec vérification des dépendances"
    command sudo pacman -Rns $argv
end
