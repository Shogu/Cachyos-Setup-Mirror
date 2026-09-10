# D — Noyau et ordonnanceurs

[Accueil](README.md) · [Précédent](C-boot-systemd.md) · [Suivant](E-btrfs-snapshots.md)

- [Blacklister les pilotes inutilisés](#pilotes)
- [Paramètres du noyau, SCX et Ananicy](#parametres-kernel)
- [Sélectionner ADIOS avec udev et TuneD](#adios)
- [Pistes split-lock à tester](#split-lock)

<a id="pilotes"></a>

## D1 — Blacklister les pilotes inutilisés

Créer ou éditer le fichier de blacklist :

```fish
sudoedit /etc/modprobe.d/blacklist.conf
```

Reprendre la liste personnelle du mémo :
```
# ==============================
# Intel et watchdog
# ==============================
blacklist iTCO_vendor_support
blacklist iTCO_wdt
blacklist wdat_wdt
blacklist intel_pmc_bxt
blacklist intel_rapl_msr
blacklist intel_rapl_common

# ==============================
# Nvidia
# ==============================
blacklist nouveau

# ==============================
# Drivers inutiles
# ==============================
blacklist btusb
blacklist joydev

# ==============================
# Netbios
# ==============================
blacklist nf_conntrack_netbios_ns
blacklist nf_conntrack_broadcast

# ==============================
# Audio inutilisé
# ==============================
blacklist snd_seq_dummy
blacklist snd_sof_amd_acp70
blacklist snd_sof_amd_acp63
blacklist snd_sof_amd_vangogh
blacklist snd_sof_amd_rembrandt
blacklist snd_sof_amd_renoir

# ==============================
# PS/2 et périphériques anciens
# ==============================
blacklist pcspkr          # bip interne
blacklist mousedev        # souris PS/2

# ==============================
# Crypto inutile si pas de chiffrement (LUKS, WireGuard, etc.)
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
# IA NPU AMD
# ==============================
blacklist amdxdna
```
Reconstruire l’initramfs pour prendre en compte la configuration embarquée :

```fish
sudo limine-mkinitcpio
```
Puis 

```fish
lsmod | grep serial8250
```


<a id="parametres-kernel"></a>

## D2 — Paramètres du noyau, SCX et Ananicy

### Ligne de paramètres retenue

Éditer les options Linux de Limine :
```
sudoedit /etc/default/limine
```

Puis saisir :
```
LINUX_OPTIONS="pci=noaer module_blacklist=thunderbolt init_on_alloc=0 page_alloc.shuffle=0 drm_kms_helper.poll=0 systemd.tpm2_wait=false cryptomgr.notests efi=disable_early_pci_dma nomce nowatchdog no_timer_check noresume zswap.enabled=0 systemd.show_status=false quiet 8250.nr_uarts=0 ipv6.disable=1 amd_iommu=off vt.global_cursor_default=0 consoleblank=0 udev.log_level=0 loglevel=0 systemd.watchdog_sec=0 rootflags=subvol=/@,noatime,commit=60,noacl,compress=zstd:1"
```

**Variante personnelle : gérer les options de la racine dès l’initramfs.** Le README associe `rootflags` au masquage de `systemd-remount-fs.service` et au commentaire de la ligne `/` dans `/etc/fstab`. Ce masquage n’est pas une nécessité générale de `rootflags` ; il est conservé ici comme choix explicite de ce setup.

```fish
sudo systemctl mask systemd-remount-fs.service
sudoedit /etc/fstab
```

Dans cette variante, commenter la ligne de la racine :

```
#UUID=e181248c-3cce-4428-bdc4-b6efd715c470 /              btrfs   subvol=/@,defaults,noatime,commit=60,noacl,compress=zstd:1 0 0
```

Reconstruire l’initramfs et actualiser les entrées Limine :
```
sudo limine-mkinitcpio
```
Examiner les paramètres reçus et les messages du noyau :

```fish
cat /proc/cmdline
sudo dmesg
```




**Démarrage silencieux :**

```
console=tty1 systemd.show_status=false quiet udev.log_level=0 loglevel=0 consoleblank=0 systemd.watchdog_sec=0 vt.global_cursor_default=0
```

**Matériel et vérifications :**

```
nowatchdog no_timer_check 8250.nr_uarts=0 tpm_crb.disable=1 clearcpuid=rdseed
```

**Sécurité et cryptographie :**

```
cryptomgr.notests random.trust_cpu=on efi=disable_early_pci_dma nomce
```

**Stockage et systèmes de fichiers :**

```
noresume  zswap.enabled=0 nvme_core.default_ps_max_latency_us=5500
```

**RCU et ordonnancement :**

```
rcutree.enable_rcu_lazy=1 rcu_nocbs=0-7
```

**Réseau et autres réglages :**

```
ipv6.disable=1 amd_iommu=off transparent_hugepage=madvise
```
### SCX : 
voir https://gitlab.com/Shogu/CACHYOS-Setup/-/blob/Main/H-energie.md?ref_type=heads#tuned-scx


### Ananicy-cpp : installation depuis les sources et dépannage

Le mémo conserve cette installation depuis les sources à la suite d’une erreur rencontrée avec l’installation précédente. La cohabitation avec SCX est à tester sur la configuration utilisée.

Exécuter les étapes séparément et lire les chemins de nettoyage avant de les supprimer. Les retours de journal attendus, dont la mention d’environ 1 800 règles, sont des observations du mémo à vérifier.

Installer les outils puis nettoyer l’ancienne installation :
```
#paquets de build
sudo pacman -Syu --noconfirm base-devel cmake nlohmann-json spdlog fmt gcc make git

#nettoyage install' précédente au cas où
sudo systemctl stop ananicy-cpp || true
sudo rm -f /usr/local/bin/ananicy-cpp /usr/local/lib/systemd/system/ananicy-cpp.service
sudo rm -rf /usr/local/share/ananicy-cpp /etc/ananicy-cpp.conf /etc/ananicy.d /var/lib/ananicy-cpp
sudo systemctl daemon-reload
rm -rf ~/ananicy-cpp

```

Cloner le projet et compiler :

```fish
cd ~
git clone https://gitlab.com/ananicy-cpp/ananicy-cpp.git
cd ananicy-cpp
mkdir -p build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/local -DUSE_EXTERNAL_SPDLOG=ON -DUSE_EXTERNAL_JSON=ON -DUSE_EXTERNAL_FMTLIB=ON
make -j$(nproc)
sudo make install

#lancement du service
sudo systemctl daemon-reload
sudo systemctl enable --now ananicy-cpp

```

Redémarrer à cette étape, puis reprendre les commandes suivantes dans un nouveau terminal :

```fish
systemctl reboot
```

```fish

#install des règles
sudo pacman -S --noconfirm cachyos-ananicy-rules
sudo systemctl restart ananicy-cpp
sudo systemctl daemon-reload

#suppression des paquets de build inutiles et maintien des paquets nécessaires pour les maj d'ananicy
sudo pacman -Rns cmake cppdap rhash --noconfirm

```

Redémarrer à cette étape, puis reprendre les commandes suivantes dans un nouveau terminal :

```fish
systemctl reboot
```

```fish

#relance du service une fois les règles installées
sudo systemctl daemon-reload
sudo systemctl restart ananicy-cpp #pas de problème avec le lancement?

#check du service
sudo systemctl status ananicy-cpp
journalctl -u ananicy-cpp -f #mention des 1800 règles? pas de problème avec cgroup?

```

Quitter le suivi du journal avec **Ctrl+C** avant de poursuivre. Le remplacement du lien ci-dessous n’est envisagé que pour le message **Cgroups are not available on this platform (or are not enabled)**, après vérification de `/etc/mtab` :

```fish
ls -l /etc/mtab
```

```fish
# Piste de dépannage conditionnelle du mémo.
sudo ln -sf /proc/self/mounts /etc/mtab
sudo systemctl restart ananicy-cpp

#check de fonctionnement avec Vivaldi
ps -eo pid,ni,policy,cls,pri,comm | grep vivaldi
# Ou full :
ps -eo pid,ni,cgroup:50,comm | grep vivaldi

# En cas d’échec, contrôler les règles installées et les journaux avant de relancer le service.
```

Les commandes de nettoyage de l’installation Ananicy suppriment les anciens fichiers et règles aux chemins indiqués. Les exécuter seulement si cette réinstallation est voulue. Le remplacement de `/etc/mtab` est une piste de dépannage conditionnelle du mémo, pas une étape systématique.

<a id="adios"></a>

## D3 — Sélectionner ADIOS avec udev et TuneD

En lieu et place de Kyber : override udev avec `sudoedit /etc/udev/rules.d/99-adios.rules` :
```
# HDD
ACTION=="add|change", KERNEL=="sd[a-z]*", ATTR{queue/rotational}=="1", \
    ATTR{queue/scheduler}="bfq"

# SSD
ACTION=="add|change", KERNEL=="sd[a-z]*|mmcblk[0-9]*", ATTR{queue/rotational}=="0", \
    ATTR{queue/scheduler}="adios"

# NVMe SSD
ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{queue/rotational}=="0", \
    ATTR{queue/scheduler}="adios"
```

Recharger les règles et déclencher leur application :

```fish
sudo udevadm control --reload-rules
sudo udevadm trigger
```

TuneD peut rétablir Kyber après l’application de la règle udev. Il faut donc également aligner son profil :

```fish
sudoedit /usr/lib/tuned/profiles/cachyos-common/tuned.conf
```

Dans la section disque concernée, régler :

```ini
elevator=adios
```

Cette méthode du mémo modifie un fichier de paquet : vérifier le réglage après une mise à jour de TuneD. L’alternative est de conserver Kyber dans les deux configurations.

Contrôler les ordonnanceurs proposés et celui entre crochets, actuellement actif :

```fish
cat /sys/block/nvme0n1/queue/scheduler
```

ADIOS doit être disponible dans le noyau utilisé ; une règle udev ne l’ajoute pas à un noyau qui en est dépourvu.

<a id="split-lock"></a>

## D4 — Pistes split-lock à tester

Le mémo conserve deux pistes à tester, sans gain établi sur ce Zenbook AMD :

- Le paramètre kernel `split_lock_detect=off`, signalé comme non opérationnel lors d’un essai avec le noyau 6.18.
- Le réglage sysctl ci-dessous, uniquement si l’interface existe sur le noyau et le matériel utilisés.

Vérifier sa présence :

```fish
sysctl kernel.split_lock_mitigate
```

Si disponible, éditer :

```fish
sudoedit /etc/sysctl.d/99-splitlock.conf
```

```ini
kernel.split_lock_mitigate=0
```

Puis recharger :

```fish
sudo sysctl --system
```

[Accueil](README.md) · [Précédent](C-boot-systemd.md) · [Suivant](E-btrfs-snapshots.md)
