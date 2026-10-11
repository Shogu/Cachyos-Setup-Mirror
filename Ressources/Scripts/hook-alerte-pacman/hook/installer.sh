#!/bin/sh
# Installe le hook pacman d'alerte (tuned, noyaux CachyOS / LTS).
set -e
cd "$(dirname "$0")"
sudo install -Dm755 alerte-paquets-sensibles /usr/local/bin/alerte-paquets-sensibles
sudo install -Dm644 90-alerte-paquets-sensibles.hook /etc/pacman.d/hooks/90-alerte-paquets-sensibles.hook
echo "Installé. Test à blanc :"
printf 'tuned\nlinux-cachyos\n' | /usr/local/bin/alerte-paquets-sensibles
