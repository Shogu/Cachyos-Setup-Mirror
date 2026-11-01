function search --description "Recherche fuzzy de fichiers (sans les caches) avec aperçu et lancement du fichier (ENTREE)"

    set -l pattern $argv
    if test (count $pattern) -eq 0
        echo "Usage: search <motif>"
        return 1
    end

    set -l file (
        find / \
            \( -path /proc -o -path /sys -o -path /dev -o -path /run -o -path /tmp -o -path /var/tmp -o -path /var/cache -o -path '*/.cache' -o -path '*/.cache/*' -o -path '*/.local/share/Trash' -o -path '*/.local/share/Trash/*' -o -path '*/node_modules' -o -path '*/node_modules/*' -o -path '*/.git' -o -path '*/.git/*' -o -path '*/.venv' -o -path '*/.venv/*' -o -path '*/venv' -o -path '*/venv/*' -o -path '*/build' -o -path '*/build/*' -o -path '*/dist' -o -path '*/dist/*' -o -path '*/target' -o -path '*/target/*' \) -prune -o \
            -type f -iname "*$pattern*" -print 2>/dev/null | \
        awk '
            function basename(path,    n,a) {
                n = split(path, a, "/")
                return a[n]
            }
            {
                n++
                b = basename($0)
                sub("/" b "$", "", $0)
                if ($0 == "") $0 = "/"
                printf "\033[38;5;245m%3d\033[0m  \033[38;5;111m%s\033[0m/\033[38;5;81m%s\033[0m\n", n, $0, b
            }
        ' | \
        fzf --ansi \
            --prompt='🔎 search > ' \
            --pointer='▶' \
            --marker='✓' \
            --layout=reverse \
            --border=rounded \
            --height=80% \
            --preview "bat --color=always --style=plain --line-range=:200 {2..} 2>/dev/null || head -n 200 {2..} 2>/dev/null" \
            --preview-window='right:60%:wrap'
    )

    if test -n "$file"
        set -l path (string replace -r '^\s*[0-9]+\s+' '' -- "$file")
        xdg-open "$path" >/dev/null 2>&1 &
    end
end
