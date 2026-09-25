function journal
    journalctl -p err -n 20 --no-pager | bat -l log
end
