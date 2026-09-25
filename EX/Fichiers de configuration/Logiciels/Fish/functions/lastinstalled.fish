function _lastinstalled_rp
    set -l color 1
    if test (count $argv) -ge 1
        set color $argv[1]
    end

    begin
        awk '
            /\[PACMAN\] Running/ && index($0, sprintf("%c", 39) "pacman") { print; next }
            /\[ALPM\] (installed|removed|upgraded) / && !/\[ALPM-SCRIPTLET\]/ { print }
        ' /var/log/pacman.log |
        sed -E 's/T([0-9]{2}:[0-9]{2}:[0-9]{2})\+[0-9]{4}/ \1/' |
        sed -E \
            -e 's/\[PACMAN\] Running/---/' \
            -e 's/\[ALPM\] upgraded / = /' \
            -e 's/\[ALPM\] installed / + /' \
            -e 's/\[ALPM\] removed / - /'

        awk '
            /Command:/ || /INFO \[STANDARD\]: (Installing|Removing|Upgrading) package:/ { print }
        ' /var/log/shelly.log |
        perl -MTime::Local -pe '
            if (/^\[([0-9]+)\]/) {
                $e = $1;
                ($s,$min,$h,$day,$m,$y) = localtime($e);
                $y += 1900;
                $m++;
                s/^\[[^]]+\]/sprintf("[%04d-%02d-%02d %02d:%02d:%02d]",$y,$m,$day,$h,$min,$s)/e;
            }
            elsif (/^\[([^]]+)Z\]/) {
                ($d,$t)=split("T",$1);
                ($y,$m,$day)=split("-",$d);
                ($h,$min,$s)=split(":",$t);
                $e=timegm($s,$min,$h,$day,$m-1,$y);
                ($s,$min,$h,$day,$m,$y)=localtime($e);
                $y += 1900;
                $m++;
                s/^\[[^]]+\]/sprintf("[%04d-%02d-%02d %02d:%02d:%02d]",$y,$m,$day,$h,$min,$s)/e;
            }
        ' |
        sed -E \
            -e 's/^(.*)INFO \[STANDARD\]: Installing package: (.+)$/\1 + \2/' \
            -e 's/^(.*)INFO \[STANDARD\]: Removing package: (.+)$/\1 - \2/' \
            -e 's/^(.*)INFO \[STANDARD\]: Upgrading package: (.+) -> (.+)$/\1 = \2 -> \3/' \
            -e "s/Command: /--- '/" \
            -e "/--- '/ s/\$/'/" \
            -e 's/^(\[[^]]+\])[[:space:]]+= ([^ ]+) ([^ ]+) -> ([^ ]+)$/\1 = \2 (\3 -> \4)/' \
            -e 's/^(\[[^]]+\])[[:space:]]+(\+|-) (.*) ([^ ]+)$/\1 \2 \3 (\4)/' \
            -e 's/^(\[[^]]+\])[[:space:]]+(\+|-) (.*)-([^ -]+-[^ -]+)$/\1 \2 \3 (\4)/' \
            -e 's/^(.*) = (.*)-([^ -]+-[^ -]+) -> (.*)-([^ -]+-[^ -]+)$/\1 = \2 (\3 -> \5)/'
    end |
    sort -s -k1,2 |
    awk '
        {
            ts=substr($0,1,21)
            rest=substr($0,23)
            if(ts==prev) print rest
            else print $0
            prev=ts
        }
    ' |
    sed -E '/---/! s/^\[[^]]+\] //' |
    awk '
        /--- / {
            if (sep && has) print sep
            sep=$0
            has=0
            next
        }

        {
            if (sep) {
                print sep
                sep=""
            }
            print
            has=1
        }

        END {
            if (sep && has) print sep
        }
    ' |
    begin
        if test "$color" -ne 0
            awk '
                BEGIN {
                    white = sprintf("%c[37m", 27)
                    green = sprintf("%c[32m", 27)
                    yellow = sprintf("%c[33m", 27)
                    red = sprintf("%c[31m", 27)
                    reset = sprintf("%c[0m", 27)
                }

                {
                    line = $0

                    if (line ~ /---/) {
                        sub(/---.*/, white "&" reset, line)
                    }
                    else if (line ~ /^[+] .*/) {
                        sub(/^[+] .*/, green "&" reset, line)
                    }
                    else if (line ~ /^= .*/) {
                        sub(/^= .*/, yellow "&" reset, line)
                    }
                    else if (line ~ /^- .*/) {
                        sub(/^- .*/, red "&" reset, line)
                    }
                    else if (line ~ / [+] .*/) {
                        sub(/ [+] .*/, green "&" reset, line)
                    }
                    else if (line ~ / = .*/) {
                        sub(/ = .*/, yellow "&" reset, line)
                    }
                    else if (line ~ / - .*/) {
                        sub(/ - .*/, red "&" reset, line)
                    }

                    print line
                }
            '
        else
            cat
        end
    end
end

function _lastinstalled_blocks
    set -l mode $argv[1]
    set -l color 1

    if test (count $argv) -ge 2
        set color $argv[2]
    end

    begin
        switch $mode
            case c
                _lastinstalled_rp "$color" | sed '/= /d'
            case u
                _lastinstalled_rp "$color" | sed -E '/ \+ /d; / - /d'
            case a
                _lastinstalled_rp "$color"
            case '*'
                return 1
        end
    end |
    awk '
        /--- / {
            if (block != "" && has)
                blocks[++n]=block

            block=$0 ORS
            has=0
            next
        }

        {
            block=block $0 ORS

            if ($0 ~ /\+ / || $0 ~ /= / || $0 ~ /- /)
                has=1
        }

        END {
            if (block != "" && has)
                blocks[++n]=block

            for (i=n; i>=1; i--)
                printf "%s", blocks[i]
        }
    ' |
    sed 's/--- //'
end

function _lastinstalled_fzf
    set -l mode $argv[1]
    set -l number $argv[2]
    set -l color 1

    if test (count $argv) -ge 3
        set color $argv[3]
    end

    if not command -q fzf
        printf '%s\n' 'lastinstalled: fzf est requis pour le mode interactif.' >&2
        return 127
    end

    set -l output (_lastinstalled_blocks "$mode" "$color")

    if test "$number" -eq 1
        set output (printf '%s\n' $output | awk '{print NR " " $0}')
    end

    set -l preview 'cmd=$(printf "%s\n" {} | sed -E "s/\x1B\[[0-9;]*m//g;s/^[[:space:]]*[0-9]*[[:space:]]*//;s/^\[[^]]*\][[:space:]]*//"); set -- $cmd; p=""; case "$1" in +|=|-) p="$2";; esac; if [[ -n "$p" ]]; then out=$(pacman -Sii "$p" 2>/dev/null) && printf "%s\n" "$out" || printf "%s\n" "$cmd"; else printf "%s\n" "$cmd"; fi'

    set -l selected (printf '%s\n' $output |
        env SHELL=/bin/bash fzf --exact --ansi -e --no-sort --height=100% \
            --preview "$preview" \
            --preview-window=right:65%)

    if test (count $selected) -eq 0
        return 0
    end

    set -l clean (printf '%s\n' "$selected" |
        sed -E 's/\x1b\[[0-9;]*m//g; s/^[[:space:]]*[0-9]+[[:space:]]+//; s/^\[[^]]+\][[:space:]]*//; s/^[[:space:]]+//')

    set -l clipboard_text

    if string match --quiet --regex '^[+=-][[:space:]]+' -- "$clean"
        set clipboard_text (printf '%s\n' "$clean" | awk '{print $2}')
    else
        set clipboard_text (string trim --chars "'" -- "$clean")
    end

    if command -q wl-copy
        printf '%s\n' "$clipboard_text" | wl-copy
    else if command -q xsel
        printf '%s\n' "$clipboard_text" | xsel --clipboard --input
    end
end

function lastinstalled
    set -l mode a
    set -l dump 0
    set -l number 0
    set -l color 1

    for arg in $argv
        switch $arg
            case c change
                set mode c
            case u update
                set mode u
            case d dump
                set dump 1
            case n number
                set number 1
            case m monochrome
                set color 0

            case '-h' '--help'
                printf '%s\n' \
                    'Usage:' \
                    '' \
                    '  lastinstalled [MODE] [MODIFIERS]' \
                    '' \
                    'Modes:' \
                    '  c | change          changes (+ / -)' \
                    '  u | update          updates (=)' \
                    '  d | dump            dump (raw output)' \
                    '  <empty>             all (interactive)' \
                    '' \
                    'Modifiers:' \
                    '  n | number          add line numbers' \
                    '  m | monochrome      monochrome output' \
                    '' \
                    'Examples:' \
                    '  lastinstalled' \
                    '  lastinstalled c' \
                    '  lastinstalled u' \
                    '  lastinstalled d' \
                    '  lastinstalled n' \
                    '  lastinstalled cn' \
                    '  lastinstalled un' \
                    '  lastinstalled du' \
                    '  lastinstalled dn' \
                    '  lastinstalled unm' \
                    '' \
                    'Options:' \
                    '  -h, --help          show this help' \
                    '  -v, --version       show version'
                return 0

            case '--version' '-v'
                printf '%s\n' 'lastinstalled 1.0'
                return 0

            case '*'
                if string match --quiet --regex '^[cudnm]+$' -- "$arg"
                    for char in (string split '' -- "$arg")
                        switch $char
                            case c
                                set mode c
                            case u
                                set mode u
                            case d
                                set dump 1
                            case n
                                set number 1
                            case m
                                set color 0
                        end
                    end
                else
                    printf 'lastinstalled: unknown argument: %s\n' "$arg" >&2
                    lastinstalled --help
                    return 2
                end
        end
    end

    if test "$dump" -eq 1
        set -l output

        switch $mode
            case c
                set output (_lastinstalled_rp "$color" | sed '/= /d')
            case u
                set output (_lastinstalled_rp "$color" | sed -E '/ \+ /d; / - /d')
            case a
                set output (_lastinstalled_rp "$color")
        end

        if test "$number" -eq 1
            printf '%s\n' $output | awk '{print NR " " $0}' | sed 's/--- //'
        else
            printf '%s\n' $output | sed 's/--- //'
        end

        return 0
    end

    _lastinstalled_fzf "$mode" "$number" "$color"
end
