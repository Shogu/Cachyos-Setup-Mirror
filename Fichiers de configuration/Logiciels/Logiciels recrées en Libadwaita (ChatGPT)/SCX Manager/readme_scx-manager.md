Réécriture vibe codée de sched-ext (CachyOS) en libadwaita.

Installation à partir du zip:

```fish
cd ~/Téléchargements
unzip scx-manager-adwaita-0.1.1-pacman.zip
cd scx-manager-adwaita
sudo pacman -S --needed base-devel meson ninja pkgconf gtk4 libadwaita scx-tools scx-scheds
makepkg
sudo pacman -U ./scx-manager-adwaita-0.1.1-1-x86_64.pkg.tar.zst
```

Supprimer les paquets de build :
```fish
sudo pacman -Rns meson ninja
```

Désinstallation :
```fish
sudo pacman -Rns scx-manager-adwaita
```