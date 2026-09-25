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
