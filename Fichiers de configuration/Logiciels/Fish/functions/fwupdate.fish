function fwupdate --description "Installer, exécuter puis désinstaller fwupd (mise à jour firmware complète)"
    echo
    set_color yellow
    echo "📦 fwupdmgr : mise à jour firmware complète (install → run → cleanup)"
    set_color normal

    # Vérifier si fwupd est déjà installé
    set -l fwupd_was_installed 0
    if pacman -Qq fwupd &>/dev/null
        set fwupd_was_installed 1
        set_color blue
        echo "ℹ️  fwupd est déjà installé — il sera conservé après l'opération."
        set_color normal
    else
        echo
        set_color green
        echo "0. Installation de fwupd via pacman…"
        set_color normal
        sudo pacman -S --needed --noconfirm fwupd
        or begin
            set_color red
            echo "❌ Échec de l'installation de fwupd."
            set_color normal
            return 1
        end
    end

    echo
    set_color green
    echo "1. Unmask du service fwupd…"
    set_color normal
    sudo systemctl unmask fwupd.service

    echo
    set_color green
    echo "2. Activation et démarrage du service fwupd…"
    set_color normal
    sudo systemctl enable --now fwupd.service

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

    # Vérifier si un redémarrage est nécessaire
    echo
    set_color green
    echo "6. Vérification de la nécessité d'un redémarrage…"
    set_color normal

    if sudo fwupdmgr check-reboot-needed &>/dev/null
        # --- Cas : reboot requis ---
        set_color yellow
        echo "⚠️  Un redémarrage est nécessaire pour finaliser la mise à jour du firmware."
        echo "   fwupd n'a PAS été désinstallé (nécessaire jusqu'au reboot)."
        set_color normal

        # Notification GNOME
        notify-send \
            --urgency=critical \
            --icon=system-reboot \
            --app-name="fwupd" \
            --expire-time=0 \
            "⚠️ Redémarrage requis" \
            "Mise à jour firmware terminée. Redémarre la machine pour l'appliquer."

        # Boucle de confirmation : attend un Y (ou y)
        set_color cyan
        echo
        echo "👉 Redémarrer maintenant ? [Y/n]"
        set_color normal

        while true
            read -l -P "➜ Réponse : " reponse

            switch (string lower -- $reponse)
                case y yes oui
                    set_color cyan
                    echo "🔄 Redémarrage en cours…"
                    set_color normal
                    sudo systemctl reboot
                    return 0
                case n no non ''
                    set_color yellow
                    echo "⏸️  Redémarrage annulé. Pense à redémarrer manuellement plus tard."
                    echo "   Après reboot, tu pourras nettoyer avec :"
                    echo "     sudo systemctl disable --now fwupd.service"
                    echo "     sudo systemctl mask fwupd.service"
                    echo "     sudo pacman -Rns fwupd   (uniquement s'il n'était pas installé avant)"
                    set_color normal
                    return 0
                case '*'
                    set_color red
                    echo "❓ Réponse invalide. Tape 'Y' pour redémarrer ou 'n' pour annuler."
                    set_color normal
            end
        end
    else
        # --- Cas : pas de reboot requis, on peut nettoyer ---
        set_color green
        echo "✅ Aucun redémarrage nécessaire."
        set_color normal

        echo
        set_color green
        echo "7. Arrêt et désactivation du service fwupd…"
        set_color normal
        sudo systemctl disable --now fwupd.service

        echo
        set_color green
        echo "8. Masquer le service fwupd…"
        set_color normal
        sudo systemctl mask fwupd.service

        # Désinstaller fwupd seulement s'il n'était pas installé au départ
        if test $fwupd_was_installed -eq 0
            echo
            set_color green
            echo "9. Désinstallation de fwupd et de ses dépendances orphelines…"
            set_color normal
            sudo pacman -Rns --noconfirm fwupd
            or begin
                set_color red
                echo "⚠️  Échec de la désinstallation de fwupd."
                set_color normal
            end
        else
            echo
            set_color blue
            echo "ℹ️  fwupd était déjà installé — pas de désinstallation."
            set_color normal
        end
    end

    echo
    set_color cyan
    echo "📦 Mise à jour firmware terminée."
    set_color normal
end