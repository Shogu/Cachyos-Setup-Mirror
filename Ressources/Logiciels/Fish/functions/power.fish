
function power --description "État EPP, TuneD, SCX et batterie"
    set -l cpu0 /sys/devices/system/cpu/cpu0/cpufreq

    set -l epp_raw 'n/a'
    set -l epp_label 'n/a'

    if test -r "$cpu0/energy_performance_preference"
        set epp_raw (cat "$cpu0/energy_performance_preference" 2>/dev/null)
        switch "$epp_raw"
            case balance_power balance_performance
                set epp_label 'balanced'
            case performance
                set epp_label 'performance'
            case power
                set epp_label 'power'
            case '*'
                set epp_label "$epp_raw"
        end
    end

    set -l pprof 'n/a'
    if command -q powerprofilesctl
        set pprof (powerprofilesctl get 2>/dev/null)
        if test -z "$pprof"
            set pprof 'n/a'
        end
    end

    set -l tuned_ppd 'no'
    if command -q systemctl
        if systemctl --user is-active tuned-ppd.service >/dev/null 2>&1
            set tuned_ppd 'yes (user)'
        else if systemctl is-active tuned-ppd.service >/dev/null 2>&1
            set tuned_ppd 'yes (system)'
        end
    end

    set -l scx 'n/a'
    if command -q scxctl
        set scx (scxctl get 2>/dev/null)
        if test -z "$scx"
            set scx 'n/a'
        end
    end

    set -l batdev
    for d in /sys/class/power_supply/*
        if test -r "$d/type"; and test (cat "$d/type" 2>/dev/null) = Battery
            set batdev (basename "$d")
            break
        end
    end

    set -l bat 'none'
    if test -n "$batdev"
        set -l base /sys/class/power_supply/$batdev
        set -l bat_status (cat "$base/status" 2>/dev/null)
        set -l capacity (cat "$base/capacity" 2>/dev/null)
        set -l full (cat "$base/energy_full" 2>/dev/null)
        set -l now (cat "$base/energy_now" 2>/dev/null)
        set -l power_now (cat "$base/power_now" 2>/dev/null)

        set bat "$batdev: $bat_status, $capacity%"

        if string match -rq '^[0-9]+$' -- "$full"; and string match -rq '^[0-9]+$' -- "$now"; and test "$full" -gt 0
            set -l pct (math "round($now * 100 / $full)")
            set bat "$bat, $pct% (energy)"
        end

        if string match -rq '^[0-9]+$' -- "$power_now"; and test "$power_now" -gt 0
            set -l w (math "round($power_now / 1000000 * 100) / 100")
            set bat "$bat, $w W"
        end
    end

    echo "EPP: $epp_label ($epp_raw) | PPD: $pprof | tuned-ppd: $tuned_ppd"
    echo "SCX: $scx"
    echo "BAT: $bat"
end
