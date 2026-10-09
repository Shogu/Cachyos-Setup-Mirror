#!/usr/bin/env bash
# upgrade.sh – Lance une mise à jour Shelly dans Ptyxis
# Vérifie d'abord que /boot (ESP) est monté : sans lui, une mise à jour du
# noyau désynchronise le noyau de l'ESP et ses modules (mode d'urgence).

ptyxis --maximize -- fish -c "
set_color 3584e4
echo '╔══════════════════════╗'
echo '║  MISE À JOUR SHELLY  ║'
echo '╚══════════════════════╝'
set_color normal
echo

if not mountpoint -q /boot
    set_color red
    echo '⚠  /boot n est PAS monté : mise à jour du noyau dangereuse.'
    set_color normal
    echo 'Tentative de montage…'
    if not sudo mount /boot
        set_color red
        echo
        echo 'Impossible de monter /boot. Mise à jour ANNULÉE.'
        if not test -d /usr/lib/modules/(uname -r)
            echo 'Les modules du noyau en cours ont disparu (noyau déjà mis à jour) :'
            echo 'redémarre d abord, puis relance la mise à jour.'
        else
            echo 'Vérifie : journalctl -u boot.mount'
        end
        set_color normal
        if command -q notify-send
            notify-send -u critical '/boot non monté' 'Mise à jour annulée.'
        end
        echo
        read -P 'Fermer avec ENTRÉE '
        exit 1
    end
    set_color green
    echo '/boot monté.'
    set_color normal
    echo
end

shelly upgrade standard
shelly upgrade aur
echo
read -P 'Fermer avec ENTRÉE '
"
