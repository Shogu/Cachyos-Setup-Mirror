# 3 — Boot & kernel

[Accueil](../README.md) · [Précédent](02-system-cleanup.md) · [Suivant](04-filesystems-storage.md)

> **Dans ce chapitre :** choix Plymouth ou logo firmware, réglage du menu Limine, réduction de l'initramfs, paramètres du noyau et protection du montage de `/boot`.

- [3.1 Retirer Plymouth](#31--retirer-plymouth)
- [3.2 Régler le menu Limine](#32--régler-le-menu-limine)
- [3.3 Réduire l'initramfs](#33--réduire-linitramfs)
- [3.4 Paramètres du noyau](#34--paramètres-du-noyau)
- [3.5 Limiter l'activation automatique des TTY](#35--limiter-lactivation-automatique-des-tty)
- [3.6 Sched-ext (SCX)](#36--sched-ext-scx)
- [3.7 Protéger les transactions noyau si `/boot` n'est pas monté](#37--protéger-les-transactions-noyau-si-boot-nest-pas-monté)
- [3.8 Alerte avant la mise à jour des paquets sensibles](#38--alerte-avant-la-mise-à-jour-des-paquets-sensibles)

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

Conserver le complément fourni par Limine dans `/etc/mkinitcpio.conf.d/10-limine-snapper-sync.conf` :

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

**Puis gérer les options de la racine dès l'initramfs.** Si utilisation de l'option `rootflags` comme flag kernel, alors masquage de `systemd-remount-fs.service` et commentaire de la ligne `/` dans `/etc/fstab`.

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
noresume zswap.enabled=0 nvme_core.default_ps_max_latency_us=5500
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

## 3.7 — Protéger les transactions noyau si `/boot` n'est pas monté

Sur cette installation, `/boot` contient l'ESP utilisée par Limine. Une transaction qui installe, met à jour ou supprime un noyau alors que `/boot` n'est pas monté peut modifier les fichiers du système sans actualiser l'ESP. Le hook Pacman ci-dessous refuse la transaction si le point de montage manque.

Créer le hook avec **Bash** (et non en collant la commande dans une session Fish) :

```bash
sudo mkdir -p /etc/pacman.d/hooks
sudo tee /etc/pacman.d/hooks/00-boot-mounted.hook <<'EOF'
[Trigger]
Operation = Install
Operation = Upgrade
Operation = Remove
Type = Path
Target = usr/lib/modules/*/vmlinuz

[Action]
Description = Vérification que /boot est monté...
When = PreTransaction
Exec = /usr/bin/sh -c 'mountpoint -q /boot || { echo "ERREUR : /boot n’est pas monté, transaction annulée." >&2; echo "Monte-le : sudo mount /boot   puis relance la mise à jour." >&2; echo "(Si un noyau a déjà été installé sans /boot : réinstalle-le, puis sudo limine-update.)" >&2; exit 1; }'
AbortOnFail
EOF
```

Le hook vérifie le montage de `/boot` avant une transaction correspondante et affiche un message d'erreur si le point de montage est absent. Si un noyau a déjà été installé alors que l'ESP n'était pas montée, le message conseille de réinstaller le noyau concerné puis d'exécuter `sudo limine-update`.

Le déclencheur de type chemin `usr/lib/modules/*/vmlinuz` doit correspondre aux fichiers touchés par les paquets noyau de cette installation. Si le chemin ne correspond pas, le hook risque de ne pas se déclencher : vérifier ce point avec les paquets installés. Le hook est une protection supplémentaire, pas un substitut à la vérification du montage de `/boot`.

Le lanceur Shelly et son contrôle préalable de `/boot` sont documentés dans [Shell & terminal](12-shell-terminal.md#123--shelly-et-le-lanceur-de-mise-à-jour).


## 3.8 — Alerte avant la mise à jour des paquets sensibles

Le paquet ZIP [`hook-alerte-pacman.zip`](../Ressources/Scripts/hook-alerte-pacman.zip) contient trois fichiers : le hook Pacman, le script d'alerte et `installer.sh`.

Cette alerte est informative : lors d'une transaction de mise à jour (`Upgrade`) touchant `tuned`, les paquets correspondant à `tuned-*`, les noyaux `linux-cachyos*` ou `linux-lts*`, Pacman appelle le script avant la transaction. Celui-ci affiche un avertissement coloré, signale les paquets concernés et tente d'afficher leurs versions installée et disponible. Il ne bloque pas la mise à jour. Le hook fourni ne surveille pas Limine.

### Installation

Télécharger puis extraire l'archive. Depuis le dossier `hook` extrait, lancer :

```bash
bash installer.sh
```

Le script installe le programme dans `/usr/local/bin/alerte-paquets-sensibles` et le hook dans `/etc/pacman.d/hooks/90-alerte-paquets-sensibles.hook`. Il lance ensuite un essai d'affichage avec `tuned` et `linux-cachyos` ; cet essai ne déclenche pas de transaction Pacman.

**À noter :** le contenu a été ajouté au dépôt, mais son installation et son déclenchement sur cette machine n'ont pas été testés ici.

---

[Accueil](../README.md) · [Précédent](02-system-cleanup.md) · [Suivant](04-filesystems-storage.md)
