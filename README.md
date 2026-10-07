# CachyOS Setup

Setup, conseils et réglages personnels pour **CachyOS** sur **ASUS Zenbook 14 OLED UM3406KA**.

> **Interface 100 % GTK / Adwaita** — ce setup privilégie exclusivement les applications GTK et libadwaita afin de conserver une intégration GNOME cohérente. **Aucune application ni dépendance Qt n’est utilisée.** Lorsque certaines applications GTK4/Adwaita ou extensions GNOME Shell manquaient pour répondre aux besoins du setup, elles ont été **vibe codées** afin de fournir des alternatives natives et cohérentes avec GNOME, notamment **Focus & Boutons** pour rationaliser Quick Settings et le panneau Calendrier/Notifications, **UI Management** pour réunir les réglages de bureau et de fenêtres auparavant répartis entre Just Perfection, AutoActivities, Hot Edge et Quick Close Overview, **Battery Time Compact — Ogu** pour l’affichage autonomie/pourcentage/watts, **Musicäa** pour l’intégration de Gapless, [**Power Total**](docs/11-applications-vibe-coded.md#1120--power-total) pour réunir les profils énergétiques, la luminosité, le thème et le rétroéclairage, et **Session Keeper** pour la sauvegarde et la restauration rapide des applications et fenêtres GNOME. Le setup utilise aussi ponctuellement des builds GTK4 compilés directement depuis les **sources officielles upstream** lorsqu’un portage est encore en cours, comme **dconf-editor GTK4** ; ils sont distingués des applications vibe codées.

<p>
  <img src="https://gitlab.com/Shogu/CACHYOS-Setup/-/raw/Main/Ressources/Icons%20%26%20background/.user-astronaut.png" alt="Avatar astronaute" width="120">
  <img src="https://raw.githubusercontent.com/CachyOS/calamares-config/grub-3.2/etc/calamares/branding/cachyos/logo.png" alt="Logo officiel CachyOS" width="120">
</p>



## Philosophie

Ce dépôt est un mémo personnel qui documente la configuration & les procédures retenues pour ce setup CachyOS, sur ce matériel précis.

## ⚠️ Avertissement

Ce setup applique des **optimisations agressives** : allègement système, désactivation de nombreux services, paramètres noyau non standards, réglages de sécurité assouplis (TPM désactivé, vérifications systemd masquées, etc.). Certains choix réduisent la stabilité ou la sécurité par défaut du système, au profit de la vitesse, de l'ergonomie et de la légéreté.

## Table des matières

1. [Installation & préparation](docs/01-installation.md)
2. [Allégement système](docs/02-system-cleanup.md)
3. [Boot & kernel](docs/03-boot-kernel.md)
4. [Filesystems & stockage](docs/04-filesystems-storage.md)
5. [Optimisations & performance](docs/05-performance-tuning.md)
6. [Réseau](docs/06-network.md)
7. [GNOME — interface](docs/07-gnome-ui.md)
8. [Extensions GNOME](docs/08-gnome-extensions.md)
9. [Nautilus — workflow](docs/09-nautilus-workflow.md)
10. [Logiciels](docs/10-logiciels.md)
11. [Applications Vibe Coded](docs/11-applications-vibe-coded.md)
12. [Shell & terminal](docs/12-shell-terminal.md)
13. [Vivaldi](docs/13-vivaldi.md)
14. [Maintenance](docs/14-maintenance.md)
15. [Archives — alternatives et réglages optionnels](docs/archives.md)
