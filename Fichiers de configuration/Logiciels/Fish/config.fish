source /usr/share/cachyos-fish-config/cachyos-config.fish

# Message d'accueil désactivé.
# CachyOS peut déjà définir fish_greeting dans sa configuration vendor ; cette
# redéfinition doit donc rester dans config.fish plutôt que dans un fichier
# autoloadé, qui serait alors ignoré.
function fish_greeting
end

############################################################################################################################
# === Alias Editeurs ===
alias vim='micro'
alias vi='micro'
alias nano='micro'

alias notepad='gnome-text-editor'
alias gedit='gnome-text-editor'
alias edit='gnome-text-editor'

# === Alias Système ===
alias powertop='sudo powertop'
alias stop='shutdown now'
alias rm='rm -I'
alias stockage='duf'
alias systemd='isd'
alias lastpackages='rip'
alias liminestats='limine-snapper-info'
alias scrub='sudo btrfs scrub start -B /'
alias bios='systemctl reboot --firmware-setup'
alias boot='systemd-analyze'
alias boot!='systemd-analyze blame'
alias watts='echo "scale=2; $(cat /sys/class/power_supply/BAT0/power_now)/1000000" | bc'

# === Alias Shelly ===

# Gestion AUR
alias aur='shelly install aur'
alias aursearch='shelly search aur'
alias aurremove='shelly remove aur --opt-deps'
alias aurlist='shelly list aur'

# Gestion paquets standards
alias add='shelly install standard'
alias remove='shelly remove standard'


# Mises à jour Shelly
alias upgrade='set_color 3584e4; echo "╔══════════════════════╗"; echo "║  MISE À JOUR SHELLY  ║"; echo "╚══════════════════════╝"; set_color normal; echo; shelly upgrade standard; shelly upgrade aur; echo; read -P "Fermer avec ENTREE "'

# === Alias Fish ===
alias sourcefish='source ~/.config/fish/config.fish'
alias fishedit='xdg-open ~/.config/fish/config.fish'

# === Alias Pacman ===

# === RECHERCHE DE PAQUETS ===
alias pacsearch='pacman -Ss'
alias pacsearch_installed='pacman -Qs'

# === DÉPENDANCES ===
alias pacdep='pactree -r'

# === RECHERCHE DE FICHIERS DANS UN PAQUET ===
alias pacfiles='pacman -Ql'

# === RECHERCHE  D'ORPHELINS + DÉPENDANCES INUTILES ===
alias orphans='pacman -Qdtq'

# === INFORMATIONS SUR LES PAQUETS ===
#pacinfo (function)

############################################################################################################################
# ===  Editeurs ===
set -gx SUDO_EDITOR gnome-text-editor
set -gx EDITOR gnome-text-editor
set -gx VISUAL gnome-text-editor

############################################################################################################################
# === Fonctions autoloadées ===
# Les fonctions personnelles se trouvent dans ~/.config/fish/functions/.


############################################################################################################################
# === SUDO!! ===

abbr -a !! --position anywhere --function last_history_item


############################################################################################################################
