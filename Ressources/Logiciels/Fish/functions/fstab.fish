function fstab --description "Affiche les entrées FSTAB"
    clear
    echo "/etc/fstab"
    echo
    sudo bat --language=fstab --paging=never --style=plain /etc/fstab
    echo
end
