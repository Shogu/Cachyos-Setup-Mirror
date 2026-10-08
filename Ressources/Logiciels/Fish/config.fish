source /usr/share/cachyos-fish-config/cachyos-config.fish

# Message d'accueil désactivé.
# CachyOS peut déjà définir fish_greeting dans sa configuration vendor ; cette
# redéfinition doit donc rester dans config.fish plutôt que dans un fichier
# autoloadé, qui serait alors ignoré.
function fish_greeting
end

############################################################################################################################

# Mises à jour Shelly
alias upgrade='set_color 3584e4; echo "╔══════════════════════╗"; echo "║  MISE À JOUR SHELLY  ║"; echo "╚══════════════════════╝"; set_color normal; echo; shelly upgrade standard; shelly upgrade aur; echo; read -P "Fermer avec ENTREE "'


# === Abbréviations ===

# === Éditeurs ===
abbr --add vim micro
abbr --add vi micro
abbr --add nano micro

abbr --add notepad gnome-text-editor
abbr --add gedit gnome-text-editor
abbr --add edit gnome-text-editor

# === Système ===
abbr --add to z
abbr --add powertop 'sudo powertop'
abbr --add stop 'shutdown now'
abbr --add rm 'rm -I'
abbr --add stockage duf
abbr --add lastpackages rip
abbr --add liminestats limine-snapper-info
abbr --add scrub 'sudo btrfs scrub start -B /'
abbr --add bios 'systemctl reboot --firmware-setup'
abbr --add boot 'systemd-analyze'
abbr --add boot+ 'systemd-analyze blame'
abbr --add watts 'echo "scale=2; $(cat /sys/class/power_supply/BAT0/power_now)/1000000" | bc'

# === Shelly ===
abbr --add aur 'shelly install aur'
abbr --add aursearch 'shelly search aur'
abbr --add aurremove 'shelly remove aur --opt-deps'
abbr --add aurlist 'shelly list aur'

abbr --add add 'shelly install standard'
abbr --add remove 'shelly remove standard'

# === Fish ===
abbr --add sourcefish 'source ~/.config/fish/config.fish'
abbr --add fishedit 'xdg-open ~/.config/fish/config.fish'

# === Pacman ===
abbr --add pacsearch 'pacman -Ss'
abbr --add pacsearch_installed 'pacman -Qs'
abbr --add pacdep 'pactree -r'
abbr --add pacfiles 'pacman -Ql'
abbr --add orphans 'pacman -Qdtq'

# === Presse-papiers Wayland ===
abbr --add clip --position anywhere '2>&1 | wl-copy'

# === Corbeille ===
abbr --add -- delete 'trash-put'
abbr --add -- rm 'rm -I'

# === Dropbox-cli ===
abbr --add dropbox-sync dropbox-cli status
abbr --add dropbox-share dropbox-cli sharelink
abbr --add dropbox-file dropbox-cli filestatus


# === Relancer extensions GNOME après freeze du shell ===
abbr --add extensions-fix 'gsettings set org.gnome.shell disable-user-extensions false'

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

#zoxide - fzf cd
zoxide init fish | source

############################################################################################################################
