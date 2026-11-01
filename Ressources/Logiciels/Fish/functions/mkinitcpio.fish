function mkinitcpio --description "Affiche le fichier MKINITCPIO"
    clear
    echo "/etc/mkinitcpio.conf"
    echo
    sudo bat --language=ini --paging=never --style=plain /etc/mkinitcpio.conf
    echo
end
