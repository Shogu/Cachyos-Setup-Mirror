function fwupdate --description "Mettre à jour firmware (fwupdmgr full)"
    echo
    set_color yellow
    echo "📦 fwupdmgr : mise à jour firmware complète"
    set_color normal

    echo
    set_color green
    echo "1. Unmask du service fwupd…"
    set_color normal
    sudo systemctl unmask fwupd.service

    echo
    set_color green
    echo "2. Démarrage du service fwupd…"
    set_color normal
    sudo systemctl start fwupd.service

    echo
    set_color green
    echo "3. Rafraîchissement metadata (fwupdmgr refresh)…"
    set_color normal
    sudo fwupdmgr refresh --force

    echo
    set_color green
    echo "4. Vérifier les mises à jour disponibles (fwupdmgr get-updates)…"
    set_color normal
    sudo fwupdmgr get-updates

    echo
    set_color green
    echo "5. Installer les mises à jour (fwupdmgr update)…"
    set_color normal
    sudo fwupdmgr update

    echo
    set_color green
    echo "6. Arrêter le service fwupd…"
    set_color normal
    sudo systemctl stop fwupd.service

    echo
    set_color green
    echo "7. Masquer le service fwupd…"
    set_color normal
    sudo systemctl mask fwupd.service

    echo
    set_color cyan
    echo "📦 Mise à jour firmware terminée."
    set_color normal
end
