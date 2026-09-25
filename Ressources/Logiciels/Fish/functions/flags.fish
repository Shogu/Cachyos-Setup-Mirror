function flags
    clear
    echo "KERNEL FLAGS (/proc/cmdline)"
    echo "============================="
    echo "Ligne complète :"
    printf "\e[93m%s\e[0m\n\n" (cat /proc/cmdline)
    echo "Flags par ligne (triés, uniques) :"
    set -l sorted_flags (string split ' ' (cat /proc/cmdline) | sort -u)
    set -l i 1
    for flag in $sorted_flags
        printf "\e[92m%2d.\e[0m \e[96m%s\e[0m\n" $i $flag
        set i (math $i + 1)
    end
    echo
end
