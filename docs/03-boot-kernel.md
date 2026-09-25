# 3 — Boot & kernel

[Accueil](../README.md) · [Précédent](02-system-cleanup.md) · [Suivant](04-filesystems-storage.md)

> **Dans ce chapitre :** choix Plymouth ou logo firmware, réglage du menu Limine, réduction de l'initramfs et paramètres du noyau.

- [3.1 Retirer Plymouth](#31--retirer-plymouth)
- [3.2 Régler le menu Limine](#32--régler-le-menu-limine)
- [3.3 Réduire l'initramfs](#33--réduire-linitramfs)
- [3.4 Paramètres du noyau](#34--paramètres-du-noyau)
- [3.5 Limiter l'activation automatique des TTY](#35--limiter-lactivation-automatique-des-tty)
- [3.6 Sched-ext (SCX)](#36--sched-ext-scx)

## 3.1 — Retirer Plymouth ou le logo firmware

CachyOS installe initialement Plymouth. Choisir son affichage de démarrage avant de finaliser les paramètres du noyau.


Éditer les deux configurations :

```fish
sudoedit /etc/mkinitcpio.conf
sudoedit /etc/default/limine
```

Retirer `plymouth` de `HOOKS` et `splash` de `LINUX_OPTIONS`. La liste principale des hooks devient :

```bash
HOOKS=(systemd autodetect microcode modconf block)
```

Conserver le complément `sd-btrfs-overlayfs` fourni séparément par Limine. 

Pour le démarrage silencieux et le curseur masqué :

```text
quiet systemd.show_status=false udev.log_level=0 loglevel=0 consoleblank=0 vt.global_cursor_default=0
```

Supprimer Plymouth puis reconstruire :

```fish
sudo pacman -Rns plymouth cachyos-plymouth-bootanimation cachyos-plymouth-theme
sudo limine-mkinitcpio
```

Dans `/boot/limine.conf`, saisir `firmware_logo: yes` pour afficher le logo firmware.


Après reconstruction réussie, redémarrer puis vérifier les arguments appliqués :

```fish
systemctl reboot
```

```fish
cat /proc/cmdline
```

`splash` ne doit plus apparaître.

Une alternative consistant à conserver Plymouth (thème CachyOS personnalisé) est documentée dans les [archives](archives.md#conserver-plymouth-alternative-non-retenue).

## 3.2 — Régler le menu Limine

Éditer la configuration du menu :

```fish
sudoedit /boot/limine.conf
```

```ini
timeout: 0.1
quiet: yes
firmware_logo: yes
mouse: no
```

Le délai visé est de **0,1 seconde**. Utiliser les touches fléchées pendant le démarrage pour tenter de faire apparaître le menu ; vérifier ce comportement avec la version de Limine installée avant de compter dessus pour accéder aux entrées de secours.

La gestion du nombre de snapshots et leur restauration sont regroupées dans [Btrfs et snapshots](04-filesystems-storage.md#42--configurer-et-restaurer-les-snapshots-limine).

## 3.3 — Réduire l'initramfs


Sauvegarder puis éditer la configuration :

```fish
sudo cp -a /etc/mkinitcpio.conf /etc/mkinitcpio.conf.before-initramfs-tuning
sudoedit /etc/mkinitcpio.conf
```

Modifier les rubriques correspondantes :

```bash
MODULES=(btrfs)
HOOKS=(systemd autodetect microcode modconf block)
COMPRESSION="lz4"
COMPRESSION_OPTIONS=(-1)
# MODULES_DECOMPRESS="no"
```


!! Conserver le complément fourni par Limine dans `/etc/mkinitcpio.conf.d/10-limine-snapper-sync.conf` :

```bash
HOOKS+=(sd-btrfs-overlayfs)
```


Reconstruire avec l'intégration Limine :

```fish
sudo limine-mkinitcpio
```




## 3.4 — Paramètres du noyau

### Ligne de paramètres retenue

Éditer les options Linux de Limine :

```fish
sudoedit /etc/default/limine
```

Puis saisir :

```ini
LINUX_OPTIONS="pci=noaer module_blacklist=thunderbolt init_on_alloc=0 page_alloc.shuffle=0 drm_kms_helper.poll=0 systemd.tpm2_wait=false cryptomgr.notests efi=disable_early_pci_dma nomce nowatchdog no_timer_check noresume zswap.enabled=0 systemd.show_status=false quiet 8250.nr_uarts=0 ipv6.disable=1 amd_iommu=off vt.global_cursor_default=0 consoleblank=0 udev.log_level=0 loglevel=0 systemd.watchdog_sec=0 rootflags=subvol=/@,noatime,commit=60,noacl,compress=zstd:1"
```

**Puis gérer les options de la racine dès l'initramfs.** si utilisation de l'option `rootflags` comme flag kernel, alors masquage de `systemd-remount-fs.service` et  commentaire de la ligne `/` dans `/etc/fstab`.

```fish
sudo systemctl mask systemd-remount-fs.service
sudoedit /etc/fstab
```

Commenter la ligne de la racine :

```ini
#UUID=e181248c-3cce-4428-bdc4-b6efd715c470 /              btrfs   subvol=/@,defaults,noatime,commit=60,noacl,compress=zstd:1 0 0
```

Reconstruire l'initramfs et actualiser les entrées Limine :

```fish
sudo limine-mkinitcpio
```

Examiner les paramètres reçus et les messages du noyau :

```fish
cat /proc/cmdline
sudo dmesg
```

**Démarrage silencieux :**

```text
console=tty1 systemd.show_status=false quiet udev.log_level=0 loglevel=0 consoleblank=0 systemd.watchdog_sec=0 vt.global_cursor_default=0
```

**Matériel et vérifications :**

```text
nowatchdog no_timer_check 8250.nr_uarts=0 tpm_crb.disable=1 clearcpuid=rdseed
```

**Sécurité et cryptographie :**

```text
cryptomgr.notests random.trust_cpu=on efi=disable_early_pci_dma nomce
```

**Stockage et systèmes de fichiers :**

```text
noresume  zswap.enabled=0 nvme_core.default_ps_max_latency_us=5500
```

**RCU et ordonnancement :**

```text
rcutree.enable_rcu_lazy=1 rcu_nocbs=0-7
```

**Réseau et autres réglages :**

```text
ipv6.disable=1 amd_iommu=off 
```

## 3.5 — Limiter l'activation automatique des TTY

Éditer la configuration de logind :

```fish
sudoedit /etc/systemd/logind.conf
```

Dans la section `[Login]`, régler :

```ini
NAutoVTs=1
```


## 3.6 — Sched-ext (SCX)

Synchronisation du scheduler sched-ext (SCX) avec TuneD et les profils d'énergie, traités dans [Optimisations & performance](05-performance-tuning.md#51--coordonner-tuned-les-profils-énergétiques-et-scx).

---

[Accueil](../README.md) · [Précédent](02-system-cleanup.md) · [Suivant](04-filesystems-storage.md)
