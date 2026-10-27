function fwupdclean --description "Nettoyer fwupd après une mise à jour firmware (cas 'n' au reboot)"
    echo
    set_color yellow
    echo "🧹 Nettoyage de fwupd…"
    set_color normal

    if not pacman -Qq fwupd &>/dev/null
        set_color blue
        echo "ℹ️  fwupd n'est pas installé — rien à faire."
        set_color normal
        return 0
    end

    sudo systemctl disable --now fwupd.service 2>/dev/null
    sudo systemctl mask fwupd.service
    sudo pacman -Rns --noconfirm fwupd
    or begin
        set_color red
        echo "⚠️  Échec de la désinstallation de fwupd."
        set_color normal
        return 1
    end

    set_color cyan
    echo "✅ fwupd supprimé et service masqué."
    set_color normal
end