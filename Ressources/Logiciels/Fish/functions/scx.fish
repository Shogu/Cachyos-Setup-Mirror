function scx --description 'scxctl get + check scheduler + monitor sans WARN'

    set -l output (scxctl get 2>/dev/null)

    if test -z "$output"
        set_color red
        echo "KO  scxctl ne retourne rien."
        set_color normal
        return 1
    end

    echo "$output"
    echo

    set -l sched_name (string match -rg 'running\s+([[:alnum:]_-]+)' -- $output)

    if test -z "$sched_name"
        set_color red
        echo "KO  Aucun scheduler sched-ext actif."
        set_color normal
        return 1
    end

    # sched_name existe déjà dans la portée de la fonction : le réassigner
    # sans -l évite de créer une variable locale dans un bloc différent.
    set sched_name (string lower -- $sched_name)
    set -l bin "scx_$sched_name"

    set -l disk nvme0n1
    if test -r /sys/block/$disk/queue/scheduler
        set -l current_io (awk -F'[][]' '{print $2}' /sys/block/$disk/queue/scheduler)

        set_color cyan
        echo "Disk       : $disk"
        set_color normal
        echo "Scheduler  : $current_io"
    else
        set_color yellow
        echo "WARN Impossible de lire /sys/block/$disk/queue/scheduler"
        set_color normal
    end

    return 0
end
