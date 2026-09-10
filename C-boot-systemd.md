# C — Démarrage et systemd

[Accueil](README.md) · [Précédent](B-logiciels.md) · [Suivant](D-kernel-schedulers.md)

- [Choisir Plymouth ou le logo firmware](#c1--choisir-plymouth-ou-le-logo-firmware)
- [Régler le menu Limine](#c2--régler-le-menu-limine)
- [Réduire l’initramfs](#c3--réduire-linitramfs)
- [Masquer les services système et utilisateur inutilisés](#c4--masquer-les-services-système-et-utilisateur-inutilisés)
- [Désactiver les autostarts inutilisés](#c5--désactiver-les-autostarts-inutilisés)
- [Limiter l’activation automatique des TTY](#c6--limiter-lactivation-automatique-des-tty)

## C1 — Choisir Plymouth ou le logo firmware

CachyOS installe initialement Plymouth. Choisir son affichage de démarrage avant de finaliser les paramètres du noyau.

### Sauvegarder les configurations

```fish
sudo cp -a /etc/mkinitcpio.conf /etc/mkinitcpio.conf.before-boot-tuning
sudo cp -a /etc/default/limine /etc/default/limine.before-boot-tuning
sudo cp -a /boot/limine.conf /boot/limine.conf.before-boot-tuning
```

### Choix retenu : retirer Plymouth et garder le logo firmware

Éditer les deux configurations :

```fish
sudoedit /etc/mkinitcpio.conf
sudoedit /etc/default/limine
```

Retirer `plymouth` de `HOOKS` et `splash` de `LINUX_OPTIONS`. La liste principale des hooks devient :

```bash
HOOKS=(systemd autodetect microcode modconf block)
```

Conserver le complément `sd-btrfs-overlayfs` fourni séparément par Limine. Pour le démarrage silencieux et le curseur masqué, les paramètres du mémo sont :

```text
quiet systemd.show_status=false udev.log_level=0 loglevel=0 consoleblank=0 vt.global_cursor_default=0
```

Supprimer Plymouth puis reconstruire :

```fish
sudo pacman -Rns plymouth
sudo limine-mkinitcpio
```

Dans `/boot/limine.conf`, conserver `firmware_logo: yes` comme indiqué dans la section suivante pour afficher le logo firmware.

Pour vérifier l’absence de Plymouth, utiliser le chemin de l’image annoncé par `limine-mkinitcpio`. Exemple seulement si ce fichier existe sur l’installation :

```fish
lsinitcpio /boot/initramfs-linux-cachyos.img | grep -i plymouth
```

L’absence de résultat n’a de sens que si `lsinitcpio` a bien ouvert la bonne image sans erreur.

Après reconstruction réussie, redémarrer puis vérifier les arguments appliqués :

```fish
systemctl reboot
```

```fish
cat /proc/cmdline
```

`splash` ne doit plus apparaître.

### Alternative : conserver Plymouth

Conserver le hook `plymouth` et le paramètre `splash`. Le mémo propose de retirer l’animation **Cachy-boot-animation** avec Pamac, puis d’installer le thème **CachyOS** et de le sélectionner :

```fish
sudo plymouth-set-default-theme cachyos
```

Remplacer `watermark.png` dans `/usr/share/plymouth/themes/cachyos/` par le logo CachyOS blanc du dépôt, puis reconstruire :

```fish
sudo limine-mkinitcpio
```

## C2 — Régler le menu Limine

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

La gestion du nombre de snapshots et leur restauration sont regroupées dans [Btrfs et snapshots](E-btrfs-snapshots.md#e2--configurer-et-restaurer-les-snapshots-limine).

## C3 — Réduire l’initramfs

La configuration retenue utilise Btrfs pour la racine, sans charger explicitement `vfat` dans l’initramfs. Le démarrage sans `vfat` a été testé avec succès sur cette machine.

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

Cette liste de hooks correspond au choix **sans Plymouth**. Si Plymouth est conservé, ajouter `plymouth` à la fin de cette liste.

Conserver le complément fourni par Limine dans `/etc/mkinitcpio.conf.d/10-limine-snapper-sync.conf` :

```bash
HOOKS+=(sd-btrfs-overlayfs)
```

`MODULES_DECOMPRESS` reste désactivé par défaut : les modules et firmwares déjà compressés sont conservés ainsi et placés dans le CPIO initial non compressé pour éviter une double compression. L’activation peut diminuer la taille avec une forte compression globale, au prix de davantage de RAM pendant le démarrage.

Reconstruire avec l’intégration Limine :

```fish
sudo limine-mkinitcpio
```

Le mémo prévoit également le masquage de la vérification de la racine Btrfs :

```fish
sudo systemctl mask systemd-fsck-root.service
```

Cela ne remplace pas la vérification distincte de la partition FAT32. Garder un moyen de démarrer un environnement de secours pour restaurer la configuration et reconstruire les images si nécessaire.

## C4 — Masquer les services système et utilisateur inutilisés

Appliquer les masquages correspondant aux fonctions volontairement désactivées sur ce Zenbook. Le masquage empêche les activations ultérieures ; il n’arrête pas nécessairement une unité déjà active.

### Unités système
```
sudo systemctl mask dev-tpmrm0.device dev-tpm0.device
sudo systemctl mask systemd-tpm2-setup-early.service systemd-tpm2-setup.service
sudo systemctl mask bolt.service
sudo systemctl mask plymouth-quit-wait.service
sudo systemctl mask systemd-hibernate-resume.service
sudo systemctl mask fwupd
sudo systemctl mask avahi-daemon.service
sudo systemctl mask sys-kernel-tracing.mount
sudo systemctl mask avahi-daemon.socket
sudo systemctl mask NetworkManager-wait-online.service
sudo systemctl mask dev-tpmrm0.device
sudo systemctl mask dev-tpm0.device
sudo systemctl mask tpm2.target
sudo systemctl mask lvm2-lvmpolld.service lvm2-monitor.service lvm2-lvmpolld.socket
sudo systemctl mask  pamac-cleancache.service
sudo systemctl mask  pamac-cleancache.timer
sudo systemctl mask  pamac-daemon.service
sudo systemctl mask bluetooth.service
sudo systemctl mask systemd-vconsole-setup.service
sudo systemctl mask systemd-tpm2-clear.service
sudo systemctl mask systemd-tpm2-setup-early.service
sudo systemctl mask systemd-tpm2-setup.service
sudo systemctl mask systemd-pcrmachine.service
sudo systemctl mask systemd-pcrphase-initrd.service
sudo systemctl mask systemd-pcrphase-sysinit.service
sudo systemctl mask systemd-pcrphase.service
sudo systemctl mask flatpak-system-helper.service
sudo systemctl mask cachyos-rate-mirrors.service
sudo systemctl mask cachyos-rate-mirrors.timer

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
```

systemctl --user mask org.gnome.SettingsDaemon.A11ySettings.service
systemctl --user mask org.gnome.SettingsDaemon.PrintNotifications.service
systemctl --user mask evolution-addressbook-factory.service
systemctl --user mask evolution-alarm-notify.service #désactive les notifications d'Agenda - à compléter avec suppression de l'autostart system - voir rubrique Autostarts
systemctl --user mask org.gnome.SettingsDaemon.Wacom.service
systemctl --user mask org.gnome.SettingsDaemon.Smartcard.service
systemctl --user mask arch-update.service
systemctl --user mask arch-update.timer
systemctl --user disable arch-update-tray.service
systemctl --user mask gsd-wwan.service

```
Contrôler également la session utilisateur :
```
systemd-analyze --user blame
```

## C5 — Désactiver les autostarts inutilisés

Deux entrées sont visées : le bus d’accessibilité et les notifications Evolution.

La méthode du mémo consiste à renommer les fichiers système :

```fish
sudo mv /etc/xdg/autostart/at-spi-dbus-bus.desktop \
    /etc/xdg/autostart/at-spi-dbus-bus.desktop.disabled

sudo mv /etc/xdg/autostart/org.gnome.Evolution-alarm-notify.desktop \
    /etc/xdg/autostart/org.gnome.Evolution-alarm-notify.desktop.disabled
```

Ces fichiers peuvent être recréés lors d’une mise à jour des paquets. Ne pas confondre ces entrées avec les services utilisateur masqués dans la section précédente.

## C6 — Limiter l’activation automatique des TTY

Éditer la configuration de logind :

```fish
sudoedit /etc/systemd/logind.conf
```

Dans la section `[Login]`, régler :

```ini
NAutoVTs=1
```

La casse de `NAutoVTs` est importante. Ce paramètre règle l’activation automatique des terminaux virtuels ; il ne garantit pas qu’un seul TTY puisse exister et ne supprime pas le terminal de secours réservé. Appliquer au prochain redémarrage.

[Accueil](README.md) · [Précédent](B-logiciels.md) · [Suivant](D-kernel-schedulers.md)
