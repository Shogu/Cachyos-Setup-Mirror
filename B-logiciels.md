# B — Suppression et installation de logiciels

[Accueil](README.md) · [Précédent](A-installation-preparation.md) · [Suivant](C-boot-systemd.md)

- [Alléger les logiciels installés](#suppression-paquets)
- [Conserver les firmwares nécessaires](#firmwares)
- [Installer les logiciels et configurer les outils de paquets](#installation-paquets)

<a id="suppression-paquets"></a>

## B1 — Alléger les logiciels installés

Ces listes correspondent aux choix de cette machine. Vérifier les paquets présents et les dépendances annoncées par pacman ; retirer de la commande les noms absents ou les logiciels à conserver. Les commandes `-Rdd` du mémo sont conservées comme opérations forcées : elles ignorent les dépendances et peuvent casser un logiciel, notamment Papers avec `djvulibre`.

Les outils de compilation sont à conserver ou à réinstaller si des paquets AUR doivent être construits. Les composants réseau, scanners et bibliothèques 32 bits sont à garder lorsqu’un périphérique ou une application les utilise.

### Accessibilité et aide

- `speech-dispatcher` : synthèse vocale.
- `brltty` : support des afficheurs braille.
- `orca` : lecteur d’écran GNOME.
- `yelp` : visionneuse d’aide GNOME.
- `gnome-user-docs` : documentation utilisateur GNOME.

```
sudo pacman -Rns speech-dispatcher brltty orca yelp gnome-user-docs
```

### Composants GNOME optionnels

- `gnome-remote-desktop` : partage et contrôle du bureau à distance.
- `gnome-backgrounds` : fonds d’écran GNOME.
- `gnome-weather` : application météo.
- `totem` : lecteur vidéo GNOME.
- `baobab` : analyseur d’espace disque.
- `gnome-usage` : vue d’usage CPU, RAM et disque.
- `gedit` : éditeur de texte GNOME.
- `gnome-screenshot` : captures d’écran.
- `sushi` : prévisualisation rapide dans Nautilus.
- `cachyos-gnome-settings` : réglages GNOME fournis par CachyOS ; suppression à décider séparément, ce paquet n’est pas inclus dans la commande ci-dessous.

```
sudo pacman -Rns gnome-remote-desktop gnome-backgrounds gnome-weather totem baobab gnome-usage gedit gnome-screenshot sushi
```

### Partage réseau, découverte et montage de périphériques

- `apache` : serveur web HTTP.
- `mod_dnssd` : annonce Apache via DNS-SD/Zeroconf.
- `gnome-user-share` : partage de fichiers et médias dans GNOME.
- `rygel` : serveur DLNA/UPnP.
- `gvfs-dnssd` : découverte réseau GNOME.
- `gvfs-smb` : accès aux partages Windows/NAS dans Nautilus.
- `nss-mdns` : résolution des noms `.local`.
- `gvfs-afc` : accès iPhone/iPad dans Nautilus.
- `gvfs-gphoto2` : accès aux appareils photo/PTP.
- `netctl` : alternative à NetworkManager.
- `nfs-utils` : outils et services NFS, pour monter un dossier distant comme un dossier local sur un réseau Linux/Unix.
- `gvfs-nfs` : accès NFS via Nautilus et GNOME.
- `cifs-utils` : outils de montage SMB/CIFS côté système.
- `usb_modeswitch` et `tcl` : cités pour les clés USB modem 4G.
- `db` : rôle à vérifier sur la version installée ; le mémo le mentionne comme dépendance optionnelle d’`iproute2`.
```
sudo pacman -Rns apache mod_dnssd gnome-user-share rygel gvfs-dnssd gvfs-smb nss-mdns gvfs-afc gvfs-gphoto2 netctl nfs-utils gvfs-nfs usb_modeswitch tcl db

```

### VPN

- `openvpn` : client/protocole VPN OpenVPN.
- `networkmanager-openvpn` : intégration OpenVPN dans NetworkManager.
- `networkmanager-vpn-plugin-openvpn` : plugin OpenVPN pour NetworkManager.

```
sudo pacman -Rns openvpn networkmanager-openvpn networkmanager-vpn-plugin-openvpn
```

### Systèmes de fichiers et scanners

- `f2fs-tools` : outils pour partitions F2FS.
- `xfsprogs` : outils pour partitions XFS.
- `sane` : support des scanners.
- `colord-sane` : lien entre scanners et gestion couleur.
- `hwinfo` : inventaire matériel.
- `djvulibre` : prise en charge de DjVu, inutilisée dans ce mémo, mais dont Papers dépend ; la suppression forcée proposée ci-dessous contourne cette dépendance.
```
sudo pacman -Rns f2fs-tools xfsprogs sane colord-sane hwinfo && sudo pacman -Rdd djvulibre

```

### Polices

- `noto-fonts-cjk` : polices chinois, japonais, coréen.
- `noto-fonts-extra` : variantes supplémentaires Noto.
- `ttf-meslo-nerd` : police Nerd Font.
- `cantarell-fonts` : police d’interface GNOME.
- `noto-fonts`

```
sudo pacman -Rns noto-fonts-cjk noto-fonts-extra ttf-meslo-nerd noto-fonts
```

Retirer également Fastfetch si son affichage d’accueil n’est plus utilisé :

```
sudo pacman -Rdd fastfetch
```

### Développement et compilation

- `ninja` : outil de build.
- `tesseract` : OCR.
- `tesseract-data-fra` : données OCR français.
- `tesseract-data-osd` : détection orientation/script.
- `autoconf` : génération de scripts de configuration.
- `base-devel` : groupe d’outils de compilation Arch.
- `rust` : toolchain Rust.
- `lld` : linker LLVM
- `llvm` : infrastructure de compilation LLVM.
- `pahole` : outil lié au debug/types noyau.
- `linux-cachyos-headers` : headers noyau pour modules externes.
- `linux-cachyos-lts-headers` : headers noyau LTS pour modules externes.
- `mesa-utils` : outils de test OpenGL/EGL.
- `cachyos-packageinstaller` : mini installeur CachyOS
- `bash-completion`

`base-devel` fournit les outils de compilation nécessaires à de nombreux paquets AUR. Le réinstaller avant une compilation ou mise à jour AUR qui en dépend.

```
sudo pacman -Rns ninja tesseract tesseract-data-fra tesseract-data-osd autoconf base-devel rust lld llvm pahole linux-cachyos-headers linux-cachyos-lts-headers mesa-utils cachyos-packageinstaller bash-completion
```

### Flatpak et contrôle parental

- `flatpak` : gestion d’applications Flatpak.
- `malcontent` : contrôle parental et restrictions d’usage.

```
sudo pacman -Rns flatpak malcontent
```

### Performances, tuning et divers

- `cpupower` : réglages d’énergie et fréquence CPU.
- `bpftune-git` : tuning via eBPF.
- `kguiaddons` : composants KDE/Qt.
- `kcolorscheme` : gestion des schémas de couleurs KDE/Qt.
- `kwallet` : gestionnaire de secrets KDE.
- `octopi` : frontend graphique pacman.
- `nano` : éditeur terminal simple.
- `plocate` : moteur de `locate`.

```
sudo pacman -Rns cpupower bpftune-git kguiaddons kcolorscheme kwallet octopi nano plocate
```

### OpenCL et bibliothèques 32 bits

- `opencl-mesa` : pile OpenCL Mesa, utile pour le calcul GPU/OpenCL, pas pour un usage desktop classique.
- `lib32-opencl-mesa` : version 32 bits d’OpenCL Mesa.
- `lib32-vulkan-radeon` : pile Vulkan Radeon 32 bits, utile surtout pour applis et jeux 32 bits.
- `lib32-mesa` : pile graphique Mesa 32 bits, utile surtout pour applis et jeux 32 bits.

```
sudo pacman -Rns opencl-mesa lib32-opencl-mesa lib32-vulkan-radeon lib32-mesa
```

### Orphelins : recherche puis suppression
```
pacman -Qdtq
```
```
set -l orphelins (pacman -Qdtq)
if test (count $orphelins) -gt 0
    sudo pacman -Rns $orphelins
end
```

<a id="firmwares"></a>

## B2 — Conserver les firmwares nécessaires

```
# installer uniquement les firmwares nécessaires
sudo pacman -S linux-firmware-amdgpu linux-firmware-mediatek linux-firmware-cirrus

# Supprimer le méta-paquet général et les firmwares inutiles
sudo pacman -R linux-firmware linux-firmware-intel linux-firmware-atheros linux-firmware-nvidia linux-firmware-broadcom linux-firmware-realtek linux-firmware-radeon linux-firmware-other sof-firmware alsa-firmware

# Marquer les firmwares utiles comme explicitement installés pour éviter qu'ils soient considérés comme orphelins
sudo pacman -D --asexplicit linux-firmware-amdgpu linux-firmware-cirrus linux-firmware-mediatek
```

<a id="installation-paquets"></a>

## B3 — Installer les logiciels et configurer les outils de paquets

### Logiciels des dépôts

Installer les logiciels suivants :
```
sudo pacman -Syu dconf-editor powertop gst-thumbnailers profile-cleaner seahorse extension-manager fragments papers nicotine+ resources onlyoffice xournal++ jdownloader2 gnome-calendar duf libgda6 shelly inotify-tools libnotify decibels clapper
```
### Paru et AUR

Configurer Paru pour nettoyer les dépendances de compilation et les fichiers de construction :
```
mkdir -p ~/.config/paru
cp /etc/paru.conf ~/.config/paru/paru.conf
gnome-text-editor ~/.config/paru/paru.conf

```
Dans la section `[options]`, activer les réglages suivants :
```
[options]
PgpFetch
Devel
Provides
DevelSuffixes = -git -cvs -svn -bzr -darcs -always -hg -fossil
AurOnly
BottomUp
RemoveMake
SudoLoop
#UseAsk
#SaveChanges
CombinedUpgrade
CleanAfter
UpgradeMenu
#NewsOnUpgrade
#SkipReview

```
```
paru -Syu libre-menu-editor archclean isd gapless

```
### Remplacements de paquets

Le mémo envisage de remplacer `jack` (AUR) par `jack2` des dépôts et de regrouper les paquets `geocode-glib`. La commande historique `sudo pacman -Rd jack geocode-glib-2 geocode-glib-common` est remplacée dans le mémo par :

```fish
sudo pacman -Syu jack2 geocode-glib
```

La mention initiale de « geoclue » désignait ici les paquets `geocode-glib` effectivement cités ; ce ne sont pas les mêmes noms.

Le mémo retient ensuite le remplacement de `sudo` par `sudo-rs` avec le paquet CachyOS et la réutilisation de la configuration existante. Vérifier la transaction proposée par le paquet installé ; cette réorganisation ne revalide pas son comportement pour chaque version.

### Mesurer le volume installé

Le mémo constate environ **900 paquets** et **6,5 Go** de logiciels :

```fish
pacman -Q | wc -l
expac -H M '%m' | awk '{sum += $1} END {printf "%.2f GiB\n", sum/1024}'
```

### Outils optionnels
Installer [PacHub](https://github.com/mrks1469/PacHub) OU
Régler `pacseek` pour inclure paru à la place de yay si besoin, et EnableAutoSuggest=true + ColorScheme=Endeavour OS : soit avec ctrl-s dans Pacseek, soit en éditant le json:

```
gnome-text-editor ~/.config/pacseek/config.json
```

### Beeper et Puls

Installer [l’AppImage de Beeper](https://api.beeper.com/desktop/download/linux/x64/stable/com.automattic.beeper.desktop), la déplacer dans .local/bin, éditer le raccourci avec le chemin de l'exécutable et  `StartupWMClass=Beeper` pour faire apparaître l'icône dans le dash. Idem pour Puls : https://github.com/word-sys/puls, puis renommer en `control` et le CC dans /usr/local/bin/control puis rendre exécutable

Les disponibilités et noms de paquets correspondent au mémo : vérifier les dépôts activés et utiliser l’AUR lorsque le paquet n’existe pas dans les dépôts configurés. Le bilan de **900 paquets et 6,5 Go** est une mesure indicative de l’installation d’origine, pas un résultat garanti.

Les lanceurs Beeper et Puls sont des fichiers `.desktop` à éditer avec l’éditeur de menus. Après avoir placé l’exécutable Puls sous `/usr/local/bin/control`, le rendre exécutable :

```fish
sudo chmod +x /usr/local/bin/control
```

[Accueil](README.md) · [Précédent](A-installation-preparation.md) · [Suivant](C-boot-systemd.md)
