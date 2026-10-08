# CachyOS Setup

Setup, conseils et réglages personnels pour **CachyOS** sur **ASUS Zenbook 14 OLED UM3406KA**.

> **Interface 100 % GTK / Adwaita** — ce setup privilégie exclusivement les applications GTK et libadwaita afin de conserver une intégration GNOME cohérente. **Aucune application ni dépendance Qt n’est utilisée.** Lorsque certaines applications GTK4/Adwaita ou extensions GNOME Shell manquaient pour répondre aux besoins du setup, elles ont été **vibe codées** afin de fournir des alternatives natives et cohérentes avec GNOME, notamment [**Extension Manager**](docs/11-applications-vibe-coded.md#1122--extension-manager) avec classement des extensions par catégorie et icône personnalisée, **Focus & Boutons** pour rationaliser Quick Settings et le panneau Calendrier/Notifications, **UI Management** pour réunir les réglages de bureau et de fenêtres auparavant répartis entre Just Perfection, AutoActivities, Hot Edge et Quick Close Overview, [**Battery Time Compact — Ogu v54**](docs/08-gnome-extensions.md#88--battery-time-compact--ogu) pour l’affichage autonomie/pourcentage/watts, **Musicäa** pour l’intégration de Gapless, [**Power Total**](docs/11-applications-vibe-coded.md#1120--power-total) pour réunir les profils énergétiques, la luminosité, le thème et le rétroéclairage, et **Session Keeper** pour la sauvegarde et la restauration rapide des applications et fenêtres GNOME. Le setup utilise aussi ponctuellement des builds GTK4 compilés directement depuis les **sources officielles upstream** lorsqu’un portage est encore en cours, comme **dconf-editor GTK4** ; ils sont distingués des applications vibe codées.

**Messagerie :** [**Mail (`mail-postcard`)**](docs/10-logiciels.md#1014--messagerie--mail), compilé avec **Claude** depuis les sources de Postcard, avec recherche et affichage des pièces jointes, aperçu des pièces jointes dans le panneau de droite (PDF, images, texte et documents Word/LibreOffice), vue à trois volets avec sélection multiple et menu au clic droit, et purge des copies locales à la fermeture, contraste entre panneaux et francisation complète. La base est issue du projet upstream ; le paquet est ajouté manuellement dans `Ressources/Logiciels/Mail/`.

<p>
  <img src="https://gitlab.com/Shogu/CACHYOS-Setup/-/raw/Main/Ressources/Icons%20%26%20background/.user-astronaut.png" alt="Avatar astronaute" width="120">
  <img src="https://raw.githubusercontent.com/CachyOS/calamares-config/grub-3.2/etc/calamares/branding/cachyos/logo.png" alt="Logo officiel CachyOS" width="120">
</p>



## Focus & Boutons v16

**Focus & Boutons v16 remplace « Redémarrer la session » par « Reconnexion ».**

- **Menu du bouton Power** : l’entrée s’appelle maintenant « Reconnexion ».
- **Fenêtre de confirmation** : le titre et le bouton affichent « Reconnexion », tant que l’option des préférences est activée.
- **Préférences** : l’interrupteur s’appelle « Fenêtre « Reconnexion » ».
- **Sans l’option** : la fenêtre de confirmation revient au texte de GNOME (« Fermer la session »).

**Vérifications rapportées pour cette version :** `node --check` et compilation du schéma. **Aucun test dans un vrai GNOME Shell n’a été effectué.**

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
10. [Logiciels](docs/10-logiciels.md) — [Dropbox sans interface](docs/10-logiciels.md#103--dropbox) · [Claude Code](docs/10-logiciels.md#107--claude-code)
11. [Applications Vibe Coded](docs/11-applications-vibe-coded.md) — [Sismographe](docs/11-applications-vibe-coded.md#1113--sismographe) · [Amplifaya](docs/11-applications-vibe-coded.md#1123--amplifaya--moteur-headless-et-interface) · [Samizdat](docs/11-applications-vibe-coded.md#1125--samizdat)
12. [Shell & terminal](docs/12-shell-terminal.md)
13. [Vivaldi](docs/13-vivaldi.md)
14. [Maintenance](docs/14-maintenance.md)
15. [Archives — alternatives et réglages optionnels](docs/archives.md)
