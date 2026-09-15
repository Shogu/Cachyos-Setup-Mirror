function memo --description "Liste interactive des alias et fonctions disponibles, organisés par catégories"
    echo
    set_color brcyan
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║              📝 MEMO - Alias et Fonctions Disponibles       ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    set_color normal
    echo

    echo "Sélectionnez une catégorie :"
    echo
    set_color brblue
    echo "  [1] 📑  ALIAS"
    echo "  [2] ⚙️  FONCTIONS"
    set_color normal
    echo
    set_color yellow
    read -P "Choix (1-2) ou 'q' pour quitter : " main_choice
    set_color normal

    if test "$main_choice" = "q"
        echo "Abandon."
        return 0
    end

    if not string match -rq '^[0-9]+$' -- "$main_choice"
        set_color red
        echo "Entrée invalide. Veuillez entrer un numéro valide."
        set_color normal
        return 1
    end

    if test "$main_choice" -lt 1 -o "$main_choice" -gt 2
        set_color red
        echo "Numéro hors plage. Veuillez choisir entre 1 et 2."
        set_color normal
        return 1
    end

    if test "$main_choice" = "1"
        # Affichage des alias
        set_color brcyan
        echo "╔═══════════════════════════════════════════════════════════╗"
        echo "║                     📑  ALIAS                             ║"
        echo "╚═══════════════════════════════════════════════════════════╝"
        set_color normal
        echo
        set_color brmagenta
        echo "✏️  ÉDITEURS"
        set_color normal
        set_color brblue; echo -n "  1) vim"; set_color normal; echo " → Micro"
        set_color brblue; echo -n "  2) vi"; set_color normal; echo " → Micro"
        set_color brblue; echo -n "  3) nano"; set_color normal; echo " → Micro"
        set_color brblue; echo -n "  4) notepad"; set_color normal; echo " → Éditeur GNOME"
        set_color brblue; echo -n "  5) gedit"; set_color normal; echo " → Éditeur GNOME"
        set_color brblue; echo -n "  6) edit"; set_color normal; echo " → Éditeur GNOME"
        echo

        set_color brmagenta
        echo "⚙️  SYSTÈME"
        set_color normal
        set_color brblue; echo -n "  7) powertop"; set_color normal; echo " → Powertop (sudo)"
        set_color brblue; echo -n "  8) stop"; set_color normal; echo " → Arrêt système"
        set_color brblue; echo -n "  9) rm"; set_color normal; echo " → Suppression sécurisée"
        set_color brblue; echo -n " 10) stockage"; set_color normal; echo " → Usage disque (duf)"
        set_color brblue; echo -n " 11) lastpackages"; set_color normal; echo " → Derniers paquets"
        set_color brblue; echo -n " 12) liminestats"; set_color normal; echo " → Snapshots Limine"
        set_color brblue; echo -n " 13) scrub"; set_color normal; echo " → Scrub Btrfs sur /"
        set_color brblue; echo -n " 14) bios"; set_color normal; echo " → Redémarrage BIOS/UEFI"
        set_color brblue; echo -n " 15) boot"; set_color normal; echo " → Infos boot"
        set_color brblue; echo -n " 16) boot!"; set_color normal; echo " → Lenteurs boot"
        set_color brblue; echo -n " 17) watts"; set_color normal; echo " → Consommation énergétique"
        echo

        set_color brmagenta
        echo "📦  SHELLY (AUR & Paquets)"
        set_color normal
        set_color brblue; echo -n " 18) aur"; set_color normal; echo " → Installe paquet AUR"
        set_color brblue; echo -n " 19) aursearch"; set_color normal; echo " → Recherche AUR"
        set_color brblue; echo -n " 20) aurremove"; set_color normal; echo " → Supprime paquet AUR"
        set_color brblue; echo -n " 21) aurlist"; set_color normal; echo " → Liste paquets AUR"
        set_color brblue; echo -n " 22) add"; set_color normal; echo " → Installe paquet standard"
        set_color brblue; echo -n " 23) remove"; set_color normal; echo " → Supprime paquet standard"
        set_color brblue; echo -n " 24) upgrade"; set_color normal; echo " → Met à jour Shelly"
        echo

        set_color brmagenta
        echo "🐟  FISH"
        set_color normal
        set_color brblue; echo -n " 25) sourcefish"; set_color normal; echo " → Recharge config Fish"
        set_color brblue; echo -n " 26) fishedit"; set_color normal; echo " → Édite config Fish"
        set_color brblue; echo -n " 27) !!"; set_color normal; echo " → Dernière commande"
        echo

        set_color brmagenta
        echo "👾  PACMAN"
        set_color normal
        set_color brblue; echo -n " 28) pacsearch"; set_color normal; echo " → Recherche paquet"
        set_color brblue; echo -n " 29) pacsearch_installed"; set_color normal; echo " → Recherche paquet installé"
        set_color brblue; echo -n " 30) pacdep"; set_color normal; echo " → Dépendances inverses"
        set_color brblue; echo -n " 31) pacfiles"; set_color normal; echo " → Fichiers paquet"
        set_color brblue; echo -n " 32) orphans"; set_color normal; echo " → Supprime paquets orphelins"
        set_color brblue; echo -n " 33) pacinstall"; set_color normal; echo " → Installe paquet"
        set_color brblue; echo -n " 34) pacremove"; set_color normal; echo " → Supprime paquet"
        set_color brblue; echo -n " 35) pacinfo"; set_color normal; echo " → Infos paquet"
        set_color brblue; echo -n " 36) pacpick"; set_color normal; echo " → Paquet propriétaire fichier"
        set_color brblue; echo -n " 37) orphans+"; set_color normal; echo " → Dépendances inutiles"
        echo

        set_color yellow
        read -P "Choisissez un numéro entre 1 et 37, 'r' pour revenir au menu principal, ou 'q' pour quitter : " choice
        set_color normal

        if test "$choice" = "q"
            echo "Abandon."
            return 0
        else if test "$choice" = "r"
            # Revenir au menu dans le même shell : un fish -c séparé ne
            # partage pas l'état des alias et des fonctions déjà chargés.
            memo
            return 0
        end

        if not string match -rq '^[0-9]+$' -- "$choice"
            set_color red
            echo "Entrée invalide. Veuillez entrer un numéro valide."
            set_color normal
            return 1
        end

        if test "$choice" -lt 1 -o "$choice" -gt 37
            set_color red
            echo "Numéro hors plage. Veuillez choisir entre 1 et 37."
            set_color normal
            return 1
        end

        # Déclarer cmd avant le switch : une variable locale créée dans un
        # case peut disparaître à la sortie de ce bloc avec Fish.
        set -l cmd ""
        switch "$choice"
            case 1; set cmd "vim"
            case 2; set cmd "vi"
            case 3; set cmd "nano"
            case 4; set cmd "notepad"
            case 5; set cmd "gedit"
            case 6; set cmd "edit"
            case 7; set cmd "powertop"
            case 8; set cmd "stop"
            case 9; set cmd "rm"
            case 10; set cmd "stockage"
            case 11; set cmd "lastpackages"
            case 12; set cmd "liminestats"
            case 13; set cmd "scrub"
            case 14; set cmd "bios"
            case 15; set cmd "boot"
            case 16; set cmd "boot!"
            case 17; set cmd "watts"
            case 18; set cmd "aur"
            case 19; set cmd "aursearch"
            case 20; set cmd "aurremove"
            case 21; set cmd "aurlist"
            case 22; set cmd "add"
            case 23; set cmd "remove"
            case 24; set cmd "upgrade"
            case 25; set cmd "sourcefish"
            case 26; set cmd "fishedit"
            case 27; set cmd "!!"
            case 28; set cmd "pacsearch"
            case 29; set cmd "pacsearch_installed"
            case 30; set cmd "pacdep"
            case 31; set cmd "pacfiles"
            case 32; set cmd "orphans"
            case 33; set cmd "pacinstall"
            case 34; set cmd "pacremove"
            case 35; set cmd "pacinfo"
            case 36; set cmd "pacpick"
            case 37; set cmd "orphans+"
        end

        echo
        set_color green
        echo "→ Exécution : $cmd"
        set_color normal
        echo
        # Exécuter la commande dans ce shell permet à Fish de résoudre les
        # alias et les fonctions autoloadées dans fish_function_path.
        $cmd
        echo

    else if test "$main_choice" = "2"
        # Affichage des fonctions
        set_color brcyan
        echo "╔═══════════════════════════════════════════════════════════╗"
        echo "║                   ⚙️  FONCTIONS                        ║"
        echo "╚═══════════════════════════════════════════════════════════╝"
        set_color normal
        echo
        set_color brmagenta
        echo "📈  SURVEILLANCE"
        set_color normal
        set_color brblue; echo -n "  1) scx"; set_color normal; echo " → Scheduler SCX"
        set_color brblue; echo -n "  2) journal"; set_color normal; echo " → Erreurs journalctl"
        set_color brblue; echo -n "  3) flags"; set_color normal; echo " → Flags kernel"
        set_color brblue; echo -n "  4) power"; set_color normal; echo " → EPP et batterie"
        echo

        set_color brmagenta
        echo "🚀  BOOT"
        set_color normal
        set_color brblue; echo -n "  5) fstab"; set_color normal; echo " → /etc/fstab"
        set_color brblue; echo -n "  6) mkinitcpio"; set_color normal; echo " → /etc/mkinitcpio.conf"
        set_color brblue; echo -n "  7) fwupdate"; set_color normal; echo " → Mise à jour firmware"
        echo

        set_color brmagenta
        echo "🧹  MAINTENANCE"
        set_color normal
        set_color brblue; echo -n "  8) clean"; set_color normal; echo " → Nettoyage système"
        set_color brblue; echo -n "  9) pacstats"; set_color normal; echo " → Statistiques paquets"
        set_color brblue; echo -n " 10) search"; set_color normal; echo " → Recherche fichiers"
        echo

        set_color brmagenta
        echo "🔍  LIMINE"
        set_color normal
        set_color brblue; echo -n " 11) liminevault"; set_color normal; echo " → Commandes Limine"
        echo

        set_color yellow
        read -P "Choisissez un numéro entre 1 et 11, 'r' pour revenir au menu principal, ou 'q' pour quitter : " choice
        set_color normal

        if test "$choice" = "q"
            echo "Abandon."
            return 0
        else if test "$choice" = "r"
            memo
            return 0
        end

        if not string match -rq '^[0-9]+$' -- "$choice"
            set_color red
            echo "Entrée invalide. Veuillez entrer un numéro valide."
            set_color normal
            return 1
        end

        if test "$choice" -lt 1 -o "$choice" -gt 11
            set_color red
            echo "Numéro hors plage. Veuillez choisir entre 1 et 11."
            set_color normal
            return 1
        end

        # Exécution de la commande
        set -l cmd ""
        switch "$choice"
            case 1; set cmd "scx"
            case 2; set cmd "journal"
            case 3; set cmd "flags"
            case 4; set cmd "power"
            case 5; set cmd "fstab"
            case 6; set cmd "mkinitcpio"
            case 7; set cmd "fwupdate"
            case 8; set cmd "clean"
            case 9; set cmd "pacstats"
            case 10; set cmd "search"
            case 11; set cmd "liminevault"
        end

        echo
        set_color green
        echo "→ Exécution : $cmd"
        set_color normal
        echo
        $cmd
        echo
    end
end