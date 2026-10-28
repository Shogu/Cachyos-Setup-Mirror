# CachyOS Setup

Setup, conseils et réglages personnels pour **CachyOS** sur **ASUS Zenbook 14 OLED UM3406KA**.

> **Interface GTK4/libadwaita cohérente avec GNOME** — le setup privilégie les applications natives GTK/Adwaita et les extensions GNOME Shell. Les outils développés ou adaptés par vibe coding sont présentés dans [le chapitre 11](docs/11-applications-vibe-coded.md) ; les portages upstream et logiciels tiers sont documentés séparément. Les fonctions, dépendances et procédures d’installation sont décrites dans les entrées consacrées à chaque application ou usage.
<p>
  <img src="https://gitlab.com/Shogu/CACHYOS-Setup/-/raw/Main/Ressources/Icons%20%26%20background/.user-astronaut.png" alt="Avatar astronaute" width="120">
  <img src="https://raw.githubusercontent.com/CachyOS/calamares-config/grub-3.2/etc/calamares/branding/cachyos/logo.png" alt="Logo officiel CachyOS" width="120">
</p>



## Applications et extensions maison

Les applications et extensions GTK4/libadwaita développées ou adaptées pour ce setup, leurs fonctions et leurs procédures d’installation sont documentées dans [le chapitre 11](docs/11-applications-vibe-coded.md). Les réglages GNOME et les logiciels tiers sont détaillés dans leurs chapitres respectifs.

## Philosophie

Ce dépôt est un mémo personnel qui documente la configuration & les procédures retenues pour ce setup CachyOS, sur ce matériel précis.

## ⚠️ Avertissement

Ce setup applique des **optimisations agressives** : allègement système, désactivation de nombreux services, paramètres noyau non standards, réglages de sécurité assouplis (TPM désactivé, vérifications systemd masquées, etc.). Certains choix réduisent la stabilité ou la sécurité par défaut du système, au profit de la vitesse, de l'ergonomie et de la légéreté.

## Table des matières

1. [Installation & préparation](docs/01-installation.md)
2. [Allégement système](docs/02-system-cleanup.md) · [Audit complémentaire des paquets supprimables](docs/15-paquets-a-supprimer.md)
3. [Boot & kernel](docs/03-boot-kernel.md)
4. [Filesystems & stockage](docs/04-filesystems-storage.md)
5. [Optimisations & performance](docs/05-performance-tuning.md)
6. [Réseau](docs/06-network.md)
7. [GNOME — interface](docs/07-gnome-ui.md)
8. [Extensions GNOME](docs/08-gnome-extensions.md)
9. [Nautilus — workflow](docs/09-nautilus-workflow.md)
10. [Logiciels](docs/10-logiciels.md) — [Dropbox sans interface](docs/10-logiciels.md#103--dropbox) · [Claude Code](docs/10-logiciels.md#107--claude-code)
11. [Applications Vibe Coded](docs/11-applications-vibe-coded.md) — [Sismographe](docs/11-applications-vibe-coded.md#1113--sismographe) · [Amplifaya](docs/11-applications-vibe-coded.md#1122--amplifaya--moteur-headless-et-interface) · [Semitone](docs/11-applications-vibe-coded.md#1129--semitone) · [Dactylo](docs/11-applications-vibe-coded.md#1124--dactylo) · [Alexandrie](docs/11-applications-vibe-coded.md#1130--alexandrie) · [Polaroid](docs/11-applications-vibe-coded.md#1132--polaroid)
12. [Shell & terminal](docs/12-shell-terminal.md)
13. [Vivaldi](docs/13-vivaldi.md)
14. [Maintenance](docs/14-maintenance.md)
15. [Archives — alternatives et réglages optionnels](docs/archives.md)
