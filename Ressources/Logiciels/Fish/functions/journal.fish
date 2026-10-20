function journal --description "Journald"
    journalctl -p err -n 20 --no-pager | bat -l log
end
