function rosetta --description 'Aide-mémoire Shelly CLI (dépôts + AUR), d’après la Rosetta Pacman ↔ Shelly'
    argparse h/help p/pacman -- $argv
    or return 1

    if set -q _flag_help
        echo "Usage : rosetta [-p|--pacman]"
        echo "  -p, --pacman   ajoute une colonne avec l’équivalent pacman"
        return 0
    end

    # ── Données (une ligne = même indice dans chaque liste) ───────────────
    set -l fonc \
        Rechercher \
        'Installer (dépôt)' \
        'Installer (AUR)' \
        'Installer (archive locale)' \
        'Construire + installer' \
        Désinstaller \
        'Lister les installés' \
        'Lister les mises à jour' \
        'Mettre à jour' \
        'Nettoyer le cache' \
        Configurer

    set -l synt \
        'shelly search <standard|aur> <terme>' \
        'shelly install standard <paquet>' \
        'shelly install aur <paquet>' \
        'shelly install standard ./<archive.pkg.tar.zst>' \
        'shelly build --sync-deps --install [PKGBUILD]' \
        'shelly remove <standard|aur> <paquet>' \
        'shelly list <standard|aur>' \
        'shelly list-updates <standard|aur|all>' \
        'shelly upgrade <standard|aur|all>' \
        'shelly purify standard --cache <n>' \
        'shelly config set <clé> <valeur>'

    set -l pac \
        'pacman -Ss' \
        'pacman -S' \
        '—' \
        'pacman -U' \
        'makepkg -si' \
        'pacman -Rns' \
        'pacman -Q' \
        'pacman -Qu' \
        'pacman -Syu' \
        'paccache -rk3' \
        '—'

    set -l titres Fonction Syntaxe
    set -l ncol 2
    if set -q _flag_pacman
        set -a titres Pacman
        set ncol 3
    end

    # ── Largeur de chaque colonne ─────────────────────────────────────────
    set -l w
    for c in (seq $ncol)
        switch $c
            case 1
                set -f vals $fonc
            case 2
                set -f vals $synt
            case 3
                set -f vals $pac
        end
        set -a w (math max (string length -- $titres[$c] $vals | string join ,))
    end

    # ── Helpers de dessin ─────────────────────────────────────────────────
    set -l bord (set_color brblack)
    set -l rst (set_color normal)

    function __rosetta_ligne --no-scope-shadowing --argument-names g m d
        set -l segs
        for c in (seq $ncol)
            set -a segs (string repeat -n (math $w[$c] + 2) '─')
        end
        echo $bord$g(string join $m $segs)$d$rst
    end

    function __rosetta_cell --no-scope-shadowing --argument-names txt larg couleur
        printf '%s %s%s%s %s│%s' $bord $couleur (string pad -r -w $larg -- $txt) $rst $bord $rst
    end

    set -l couleurs (set_color --bold) (set_color cyan) (set_color yellow)

    # ── Rendu ─────────────────────────────────────────────────────────────
    echo
    echo (set_color --bold)'  Shelly CLI — Rosetta (dépôts + AUR)'$rst
    __rosetta_ligne '┌' '┬' '┐'
    printf '%s│%s' $bord $rst
    for c in (seq $ncol)
        __rosetta_cell $titres[$c] $w[$c] (set_color --bold --underline)
    end
    echo
    __rosetta_ligne '├' '┼' '┤'
    for i in (seq (count $fonc))
        printf '%s│%s' $bord $rst
        set -l ligne $fonc[$i] $synt[$i] $pac[$i]
        for c in (seq $ncol)
            __rosetta_cell $ligne[$c] $w[$c] $couleurs[$c]
        end
        echo
    end
    __rosetta_ligne '└' '┴' '┘'
    echo (set_color brblack)'  Archive locale : préfixer par ./ (ou chemin complet) ; .pkg.tar.zst, pas de .xz. Raccourcis : shelly -Ss, -Is, -Ia, -Rs, -Ux…'$rst
    echo

    functions -e __rosetta_ligne __rosetta_cell
end