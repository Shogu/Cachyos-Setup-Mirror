function memo --description "Liste interactive des abbr et fonctions disponibles, organisés par catégories"
    echo
    set_color brcyan
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║          MEMO  -  Abbr et Fonctions Disponibles           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    set_color normal
    echo

    echo "Sélectionnez une catégorie :"
    echo
    set_color brblue
    echo "  [1]  ABBRÉVIATIONS"
    echo "  [2]  FONCTIONS"
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
        # Affichage des abbr
        set_color brcyan
        echo "╔═══════════════════════════════════════════════════════════╗"
        echo "║                    ABRÉVIATIONS                           ║"
        echo "╚═══════════════════════════════════════════════════════════╝"
        set_color normal
        echo
        set_color brmagenta
        echo "  ÉDITEURS"
        set_color normal
        set_color brblue; echo -n "  1) vim"; set_color normal; echo " → Micro"
        set_color brblue; echo -n "  2) vi"; set_color normal; echo " → Micro"
        set_color brblue; echo -n "  3) nano"; set_color normal; echo " → Micro"
        set_color brblue; echo -n "  4) notepad"; set_color normal; echo " → Éditeur GNOME"
        set_color brblue; echo -n "  5) gedit"; set_color normal; echo " → Éditeur GNOME"
        set_color brblue; echo -n "  6) edit"; set_color normal; echo " → Éditeur GNOME"
        echo

        set_color brmagenta
        echo "  SYSTÈME"
        set_color normal
        set_color brblue; echo -n "  7) to"; set_color normal; echo " → z (zoxide)"
        set_color brblue; echo -n "  8) powertop"; set_color normal; echo " → Powertop (sudo)"
        set_color brblue; echo -n "  9) stop"; set_color normal; echo " → Arrêt système"
        set_color brblue; echo -n " 10) rm"; set_color normal; echo " → Suppression sécurisée"
        set_color brblue; echo -n " 11) stockage"; set_color normal; echo " → Usage disque (duf)"
        set_color brblue; echo -n " 12) lastpackages"; set_color normal; echo " → Derniers paquets"
        set_color brblue; echo -n " 13) liminestats"; set_color normal; echo " → Snapshots Limine"
        set_color brblue; echo -n " 14) scrub"; set_color normal; echo " → Scrub Btrfs sur /"
        set_color brblue; echo -n " 15) bios"; set_color normal; echo " → Redémarrage BIOS/UEFI"
        set_color brblue; echo -n " 16) boot"; set_color normal; echo " → Infos boot"
        set_color brblue; echo -n " 17) boot+"; set_color normal; echo " → Lenteurs boot"
        set_color brblue; echo -n " 18) watts"; set_color normal; echo " → Consommation énergétique"
        echo

        set_color brmagenta
        echo "  SHELLY (AUR & Paquets)"
        set_color normal
        set_color brblue; echo -n " 19) aur"; set_color normal; echo " → Installe paquet AUR"
        set_color brblue; echo -n " 20) aursearch"; set_color normal; echo " → Recherche AUR"
        set_color brblue; echo -n " 21) aurremove"; set_color normal; echo " → Supprime paquet AUR"
        set_color brblue; echo -n " 22) aurlist"; set_color normal; echo " → Liste paquets AUR"
        set_color brblue; echo -n " 23) add"; set_color normal; echo " → Installe paquet standard"
        set_color brblue; echo -n " 24) remove"; set_color normal; echo " → Supprime paquet standard"
        echo

        set_color brmagenta
        echo "  FISH"
        set_color normal
        set_color brblue; echo -n " 25) sourcefish"; set_color normal; echo " → Recharge config Fish"
        set_color brblue; echo -n " 26) fishedit"; set_color normal; echo " → Édite config Fish"
        echo

        set_color brmagenta
        echo "  PACMAN"
        set_color normal
        set_color brblue; echo -n " 27) pacsearch"; set_color normal; echo " → Recherche paquet"
        set_color brblue; echo -n " 28) pacsearch_installed"; set_color normal; echo " → Recherche paquet installé"
        set_color brblue; echo -n " 29) pacdep"; set_color normal; echo " → Dépendances inverses"
        set_color brblue; echo -n " 30) pacfiles"; set_color normal; echo " → Fichiers paquet"
        set_color brblue; echo -n " 31) orphans"; set_color normal; echo " → Paquets orphelins"
        echo

        set_color brmagenta
        echo "  PRESSE-PAPIERS (Wayland)"
        set_color normal
        set_color brblue; echo -n " 32) clip"; set_color normal; echo " → En fin de ligne : | wl-copy"
        echo

        set_color yellow
        read -P "Choisissez un numéro entre 1 et 32, 'r' pour revenir au menu principal, ou 'q' pour quitter : " choice
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

        if test "$choice" -lt 1 -o "$choice" -gt 32
            set_color red
            echo "Numéro hors plage. Veuillez choisir entre 1 et 32."
            set_color normal
            return 1
        end

        set -l cmd ""
        switch "$choice"
            case 1; set cmd "vim"
            case 2; set cmd "vi"
            case 3; set cmd "nano"
            case 4; set cmd "notepad"
            case 5; set cmd "gedit"
            case 6; set cmd "edit"
            case 7; set cmd "to"
            case 8; set cmd "powertop"
            case 9; set cmd "stop"
            case 10; set cmd "rm"
            case 11; set cmd "stockage"
            case 12; set cmd "lastpackages"
            case 13; set cmd "liminestats"
            case 14; set cmd "scrub"
            case 15; set cmd "bios"
            case 16; set cmd "boot"
            case 17; set cmd "boot+"
            case 18; set cmd "watts"
            case 19; set cmd "aur"
            case 20; set cmd "aursearch"
            case 21; set cmd "aurremove"
            case 22; set cmd "aurlist"
            case 23; set cmd "add"
            case 24; set cmd "remove"
            case 25; set cmd "sourcefish"
            case 26; set cmd "fishedit"
            case 27; set cmd "pacsearch"
            case 28; set cmd "pacsearch_installed"
            case 29; set cmd "pacdep"
            case 30; set cmd "pacfiles"
            case 31; set cmd "orphans"
            case 32; set cmd "clip"
        end

        echo
        set_color green
        echo "→ Exécution : $cmd"
        set_color normal
        echo

        # Cas spécial : clip n'est pas une vraie commande, juste un pipe
        # en fin de ligne. Impossible de l'exécuter comme ça.
        if test "$cmd" = "clip"
            set_color yellow
            echo "⚠️  'clip' est une abbr de fin de ligne : tape 'commande clip' au lieu de l'exécuter ici."
            set_color normal
            return 1
        end

        # Pour les abbr : on récupère l'expansion via `abbr --query`
        # Pour les fonctions : on appelle directement
        set -l expanded (abbr --query "$cmd" 2>/dev/null)
        if test -n "$expanded"
            echo "(abbr → $expanded)"
            eval $expanded
        else if functions -q "$cmd"
            $cmd
        else
            set_color yellow
            echo "⚠️  '$cmd' n'est ni une abbr ni une fonction connue."
            set_color normal
        end
        echo

    else if test "$main_choice" = "2"
        # Affichage des fonctions
        set_color brcyan
        echo "╔═══════════════════════════════════════════════════════════╗"
        echo "║                       FONCTIONS                           ║"
        echo "╚═══════════════════════════════════════════════════════════╝"
        set_color normal
        echo
        set_color brmagenta
        echo "  SURVEILLANCE"
        set_color normal
        set_color brblue; echo -n "  1) scx"; set_color normal; echo " → Scheduler SCX"
        set_color brblue; echo -n "  2) journal"; set_color normal; echo " → Erreurs journalctl"
        set_color brblue; echo -n "  3) flags"; set_color normal; echo " → Flags kernel"
        set_color brblue; echo -n "  4) power"; set_color normal; echo " → EPP et batterie"
        echo

        set_color brmagenta
        echo "  BOOT"
        set_color normal
        set_color brblue; echo -n "  5) fstab"; set_color normal; echo " → /etc/fstab"
        set_color brblue; echo -n "  6) mkinitcpio"; set_color normal; echo " → /etc/mkinitcpio.conf"
        set_color brblue; echo -n "  7) fwupdate"; set_color normal; echo " → Mise à jour firmware"
        echo

        set_color brmagenta
        echo "  MAINTENANCE"
        set_color normal
        set_color brblue; echo -n "  8) clean"; set_color normal; echo " → Nettoyage système"
        set_color brblue; echo -n "  9) pacstats"; set_color normal; echo " → Statistiques paquets"
        set_color brblue; echo -n " 10) search"; set_color normal; echo " → Recherche fichiers"
        set_color brblue; echo -n " 11) upgrade"; set_color normal; echo " → Mise à jour Shelly"
        echo

        set_color brmagenta
        echo "  LIMINE"
        set_color normal
        set_color brblue; echo -n " 12) liminevault"; set_color normal; echo " → Commandes Limine"
        echo

        set_color yellow
        read -P "Choisissez un numéro entre 1 et 12, 'r' pour revenir au menu principal, ou 'q' pour quitter : " choice
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

        if test "$choice" -lt 1 -o "$choice" -gt 12
            set_color red
            echo "Numéro hors plage. Veuillez choisir entre 1 et 12."
            set_color normal
            return 1
        end

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
            case 11; set cmd "upgrade"
            case 12; set cmd "liminevault"
        end

        echo
        set_color green
        echo "→ Exécution : $cmd"
        set_color normal
        echo

        if functions -q "$cmd"
            $cmd
        else
            set_color yellow
            echo "⚠️  '$cmd' n'est pas une fonction connue."
            set_color normal
        end
        echo
    end
end