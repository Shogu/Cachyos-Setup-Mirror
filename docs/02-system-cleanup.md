# 2 — Allégement système

[Accueil](../README.md) · [Précédent](01-installation.md) · [Suivant](03-boot-kernel.md)

> **Dans ce chapitre :** nettoyage du système après installation — NVRAM, paquets superflus, services et pilotes désactivés, journaux, traductions, et désactivation de XWayland au démarrage.

- [2.1 Nettoyer les entrées UEFI en NVRAM](#21--nettoyer-les-entrées-uefi-en-nvram)
- [2.2 Alléger les logiciels installés](#22--alléger-les-logiciels-installés)
- [2.3 Conserver les firmwares nécessaires](#23--conserver-les-firmwares-nécessaires)
- [2.4 Masquer les services système et utilisateur inutilisés](#24--masquer-les-services-système-et-utilisateur-inutilisés)
- [2.5 Blacklister les pilotes inutilisés](#25--blacklister-les-pilotes-inutilisés)
- [2.6 Alléger les journaux et les stocker en RAM](#26--alléger-les-journaux-et-les-stocker-en-ram)
- [2.7 Désactiver les coredumps](#27--désactiver-les-coredumps)
- [2.8 Nettoyer les traductions et les fichiers de configuration](#28--nettoyer-les-traductions-et-les-fichiers-de-configuration)
- [2.9 Désactiver Xwayland au démarrage](#29--désactiver-xwayland-au-démarrage)

## 2.1 — Nettoyer les entrées UEFI en NVRAM

Afficher les entrées UEFI enregistrées en NVRAM :

```fish
sudo efibootmgr -v
```

Repérer les entrées devenues inutiles ou redondantes, en conservant l'entrée de démarrage utilisée et les entrées de secours souhaitées. Supprimer uniquement les identifiants vérifiés ; les numéros ci-dessous sont des exemples à adapter, pas une liste à exécuter telle quelle :

```fish
# : exécuter seulement la ligne correspondant à une entrée à supprimer.
sudo efibootmgr -b 0000 -B
sudo efibootmgr -b 0001 -B
sudo efibootmgr -b 0002 -B
```

## 2.2 — Alléger les logiciels installés


### Accessibilité et aide

- `speech-dispatcher` : synthèse vocale.
- `brltty` : support des afficheurs braille.
- `orca` : lecteur d'écran GNOME.
- `yelp` : visionneuse d'aide GNOME.
- `gnome-user-docs` : documentation utilisateur GNOME.
- `tealdeer` : alternative à man

```
sudo pacman -Rns speech-dispatcher brltty orca yelp gnome-user-docs && sudo pacman -Rdd tealdeer
```

### Composants GNOME optionnels

- `gnome-remote-desktop` : partage et contrôle du bureau à distance.
- `gnome-backgrounds` : fonds d'écran GNOME.
- `gnome-weather` : application météo.
- `totem` : lecteur vidéo GNOME.
- `baobab` : analyseur d'espace disque.
- `gnome-usage` : vue d'usage CPU, RAM et disque.
- `gedit` : éditeur de texte GNOME.
- `gnome-screenshot` : captures d'écran.
- `sushi` : prévisualisation rapide dans Nautilus.
- `cachyos-gnome-settings` : réglages GNOME fournis par CachyOS 
- `cachyos-v3-mirrorlist` : paquets V3
- `chwd` : détecteur de nouveau matériel
- `unrar` : archives RAR

```
sudo pacman -Rns gnome-remote-desktop gnome-backgrounds gnome-weather totem baobab gnome-usage gedit gnome-screenshot sushi unrar chwd cachyos-v3-mirrorlist
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
- `db` : rôle à vérifier sur la version installée ; le mémo le mentionne comme dépendance optionnelle d'`iproute2`.

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
- `cantarell-fonts` : police d'interface GNOME.
- `noto-fonts`

```
sudo pacman -Rns noto-fonts-cjk noto-fonts-extra ttf-meslo-nerd noto-fonts
```

Retirer également Fastfetch:

```
sudo pacman -Rdd fastfetch
```

### Développement et compilation

- `ninja` : outil de build.
- `tesseract` : OCR.
- `tesseract-data-fra` : données OCR français.
- `tesseract-data-osd` : détection orientation/script.
- `autoconf` : génération de scripts de configuration.
- `base-devel` : groupe d'outils de compilation Arch.
- `rust` : toolchain Rust.
- `lld` : linker LLVM
- `llvm` : infrastructure de compilation LLVM.
- `pahole` : outil lié au debug/types noyau.
- `linux-cachyos-headers` : headers noyau pour modules externes.
- `linux-cachyos-lts-headers` : headers noyau LTS pour modules externes.
- `mesa-utils` : outils de test OpenGL/EGL.
- `cachyos-packageinstaller` : mini installeur CachyOS
- `bash-completion`
-`fwupd` : la function Fish l'installe puis le désinstalle à la volée

`base-devel` fournit les outils de compilation nécessaires à de nombreux paquets AUR. Le réinstaller avant une compilation ou mise à jour AUR qui en dépend.

```
sudo pacman -Rns ninja tesseract tesseract-data-fra tesseract-data-osd autoconf base-devel rust lld llvm pahole linux-cachyos-headers linux-cachyos-lts-headers mesa-utils cachyos-packageinstaller bash-completion
```

### Flatpak et contrôle parental

- `flatpak` : gestion d'applications Flatpak.
- `malcontent` : contrôle parental et restrictions d'usage.

```
sudo pacman -Rns flatpak malcontent
```

### Performances, tuning et divers

- `cpupower` : réglages d'énergie et fréquence CPU.
- `bpftune-git` : tuning via eBPF.
- `kguiaddons` : composants KDE/Qt.
- `kcolorscheme` : gestion des schémas de couleurs KDE/Qt.
- `kwallet` : gestionnaire de secrets KDE.
- `nano` : éditeur terminal simple.
- `plocate` : moteur de `locate`.

```
sudo pacman -Rns cpupower bpftune-git kguiaddons kcolorscheme kwallet nano plocate
```

### OpenCL et bibliothèques 32 bits

- `opencl-mesa` : pile OpenCL Mesa, utile pour le calcul GPU/OpenCL, pas pour un usage desktop classique.
- `lib32-opencl-mesa` : version 32 bits d'OpenCL Mesa.
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

## 2.3 — Conserver les firmwares nécessaires

```
# Installer uniquement les firmwares nécessaires
sudo pacman -S linux-firmware-amdgpu linux-firmware-mediatek linux-firmware-cirrus

# Supprimer le méta-paquet général et les firmwares inutiles
sudo pacman -R linux-firmware linux-firmware-intel linux-firmware-atheros linux-firmware-nvidia linux-firmware-broadcom linux-firmware-realtek linux-firmware-radeon linux-firmware-other sof-firmware alsa-firmware

# Marquer les firmwares utiles comme explicitement installés pour éviter qu'ils soient considérés comme orphelins
sudo pacman -D --asexplicit linux-firmware-amdgpu linux-firmware-cirrus linux-firmware-mediatek
```

## 2.4 — Masquer les services système et utilisateur inutilisés


### Unités système

**TPM** :

```
sudo systemctl mask dev-tpmrm0.device dev-tpm0.device
sudo systemctl mask systemd-tpm2-setup-early.service systemd-tpm2-setup.service systemd-tpm2-clear.service
sudo systemctl mask tpm2.target
sudo systemctl mask systemd-pcrmachine.service systemd-pcrphase-initrd.service systemd-pcrphase-sysinit.service systemd-pcrphase.service
```

**Réseau de proximité et Bluetooth** :

```
sudo systemctl mask bolt.service
sudo systemctl mask avahi-daemon.service avahi-daemon.socket
sudo systemctl mask NetworkManager-wait-online.service
sudo systemctl mask bluetooth.service
```

**Boot et hibernation** :

```
sudo systemctl mask plymouth-quit-wait.service
sudo systemctl mask systemd-hibernate-resume.service
sudo systemctl mask systemd-vconsole-setup.service
```

**LVM** :

```
sudo systemctl mask lvm2-lvmpolld.service lvm2-monitor.service lvm2-lvmpolld.socket
```

**Outils CachyOS** :

```
sudo systemctl mask cachyos-rate-mirrors.service cachyos-rate-mirrors.timer
```

**Divers** :

```
sudo systemctl mask fwupd
sudo systemctl mask sys-kernel-tracing.mount
sudo systemctl mask flatpak-system-helper.service
```

Après redémarrage, examiner les durées de démarrage :

```
systemd-analyze blame | grep -v '\.device$'
```

Puis lister les services activés :

```
systemctl list-unit-files --type=service --state=enabled
```

### Unités utilisateur

**GNOME Settings Daemon inutilisés** :

```
systemctl --user mask org.gnome.SettingsDaemon.A11ySettings.service
systemctl --user mask org.gnome.SettingsDaemon.PrintNotifications.service
systemctl --user mask org.gnome.SettingsDaemon.Wacom.service
systemctl --user mask org.gnome.SettingsDaemon.Smartcard.service
systemctl --user mask gsd-wwan.service
```

**Evolution** :

```
systemctl --user mask evolution-addressbook-factory.service
systemctl --user mask evolution-alarm-notify.service #désactive les notifications d'Agenda - à compléter avec suppression de l'autostart système - voir 7.12 Autostarts
```

**Arch-update** :

```
systemctl --user mask arch-update.service
systemctl --user mask arch-update.timer
systemctl --user disable arch-update-tray.service
```
Ou supprimer carrément `Arch-update`


Contrôler également la session utilisateur :

```
systemd-analyze --user blame
```

## 2.5 — Blacklister les pilotes inutilisés

Créer ou éditer le fichier de blacklist :

```fish
sudoedit /etc/modprobe.d/blacklist.conf
```

```conf
# ==============================
# et watchdog
# ==============================
blacklist iTCO_vendor_support
blacklist iTCO_wdt
blacklist wdat_wdt
blacklist intel_pmc_bxt

# ==============================
# Nvidia
# ==============================
blacklist nouveau

# ==============================
# inutiles
# ==============================
blacklist btusb
blacklist joydev

# ==============================
# Netbios
# ==============================
blacklist nf_conntrack_netbios_ns
blacklist nf_conntrack_broadcast

# ==============================
# inutilisé
# ==============================
blacklist snd_seq_dummy
blacklist snd_sof_amd_acp70
blacklist snd_sof_amd_acp63
blacklist snd_sof_amd_vangogh
blacklist snd_sof_amd_rembrandt
blacklist snd_sof_amd_renoir

# ==============================
# et périphériques anciens
# ==============================
blacklist pcspkr          # bip interne
blacklist mousedev        # souris PS/2

# ==============================
# inutile si pas de chiffrement (LUKS, WireGuard, etc.)
# ==============================
blacklist aesni_intel
blacklist polyval_clmulni
blacklist ghash_clmulni_intel
blacklist sha1_ssse3
blacklist sha512_ssse3

# ==============================
# capteurs
# ==============================
blacklist hid_sensor_als
blacklist industrialio
blacklist industrialio_triggered_buffer

# ==============================
# tty
# ==============================
blacklist serial8250
blacklist 8250_pci

# ==============================
# TPM
# ==============================
blacklist tpm
blacklist tpm_tis
blacklist tpm_crb
blacklist tpm_tis_core
blacklist tpm_vtpm_proxy

# ==============================
# NPU AMD
# ==============================
blacklist amdxdna
```

Reconstruire l'initramfs pour prendre en compte la configuration embarquée :

```fish
sudo limine-mkinitcpio
```

Après redémarrage, contrôler avec :

```fish
lsmod | grep serial8250
```


## 2.6 — Alléger les journaux et les stocker en RAM

Ouvrir la configuration de journald :

```fish
sudoedit /etc/systemd/journald.conf
```

Reprendre le contenu du fichier **`journald.conf.txt` fourni dans le dépôt**, qui définit l'allégement des journaux.

Relancer ensuite le service :

```fish
sudo systemctl restart systemd-journald
```

## 2.7 — Désactiver les coredumps

Désactiver et masquer les unités de collecte des coredumps retenues dans le mémo :

```fish
sudo systemctl disable --now systemd-coredump.socket
sudo systemctl mask systemd-coredump
sudo systemctl mask systemd-coredump.socket
```

Ajouter la limite maximale de taille des fichiers core dans `limits.conf` si elle n'y figure pas déjà :

```fish
echo '* hard core 0' | sudo tee -a /etc/security/limits.conf
```


## 2.8 — Nettoyer les traductions et les fichiers de configuration

Le nettoyage concerne les traductions sous `/usr/share/locale` et aussi un tri de `~/.local/share`, `~/.config` et `/etc.

### Conserver les traductions françaises et anglaises

Les fichiers placés sous `/usr/share/locale` appartiennent aux paquets installés. Une suppression manuelle n'est donc pas permanente : ils sont recréés lors des mises à jour.

Pacman permet d'empêcher leur réinstallation avec la directive `NoExtract`.

### Sauvegarder les locales actuelles

```bash
mkdir -p "$HOME/Sauvegardes"

sudo tar -C /usr/share \
  -caf "$HOME/Sauvegardes/locales-avant-nettoyage.tar.zst" \
  locale
```

Vérifier la sauvegarde :

```bash
tar -tf "$HOME/Sauvegardes/locales-avant-nettoyage.tar.zst" | head
```

### Configurer pacman

Éditer :

```bash
sudoedit /etc/pacman.conf
```

Dans la section `[options]`, ajouter :

```ini
# pas extraire les traductions, sauf français et anglais
NoExtract = usr/share/locale/*
NoExtract = !usr/share/locale/fr*
NoExtract = !usr/share/locale/en*
NoExtract = !usr/share/locale/locale.alias
```

Les règles commençant par `!` réautorisent les chemins français et anglais après l'exclusion générale.

### Afficher les répertoires qui seront supprimés

```bash
sudo find /usr/share/locale \
  -mindepth 1 \
  -maxdepth 1 \
  -type d \
  ! -name 'fr*' \
  ! -name 'en*' \
  -print
```

Examiner complètement la liste avant de continuer.

### Supprimer les locales inutilisées

```bash
sudo find /usr/share/locale \
  -mindepth 1 \
  -maxdepth 1 \
  -type d \
  ! -name 'fr*' \
  ! -name 'en*' \
  -exec rm -rf -- {} +
```

### Vérifier le résultat

```bash
find /usr/share/locale \
  -mindepth 1 \
  -maxdepth 1 \
  -type d \
  -printf '%f\n' |
  sort
```

Vérifier les locales système actives :

```bash
locale
localectl status
```

### Restaurer en cas de problème

```bash
sudo tar -C /usr/share \
  -xaf "$HOME/Sauvegardes/locales-avant-nettoyage.tar.zst"
```

Pour autoriser de nouveau toutes les traductions, supprimer les lignes `NoExtract` ajoutées à `/etc/pacman.conf`, puis réinstaller le paquet concerné :

```bash
sudo pacman -S nom-du-paquet
```


## 2.9 — Désactiver Xwayland au démarrage

Désactiver XWayland sur GNOME avec un script (à faire en *bash*) :

```fish
mkdir -p ~/.local/bin
cat > ~/.local/bin/kill-xwayland.sh << 'SCRIPTEOF'
#!/bin/bash
# que GNOME soit stable
sleep 10

# XWayland proprement
pkill -TERM Xwayland 2>/dev/null
sleep 2
# si résiste
pkill -9 Xwayland 2>/dev/null
SCRIPTEOF
```

Lui donner les permissions :

```fish
chmod +x ~/.local/bin/kill-xwayland.sh
```

Créer un lanceur au boot :

```fish
mkdir -p ~/.config/autostart
cat > ~/.config/autostart/kill-xwayland.desktop << DESKTOPEOF
[Desktop Entry]
Type=Application
Name=Kill XWayland
Exec=$HOME/.local/bin/kill-xwayland.sh
X-GNOME-Autostart-enabled=true
NoDisplay=false
Hidden=false
Comment=Désactiver XWayland après login
DESKTOPEOF
```

Contrôler au reboot avec `pgrep Xwayland`.

Les fonctions expérimentales de Mutter (mise à l'échelle fractionnaire) sont réglées séparément dans [GNOME — interface](07-gnome-ui.md#75--fonctions-expérimentales-de-mutter).

---

[Accueil](../README.md) · [Précédent](01-installation.md) · [Suivant](03-boot-kernel.md)
