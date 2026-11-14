# Sismographe 1.0.0

Application GTK4/libadwaita de diagnostic du système GNOME. Elle regroupe les vues Santé, Journaux, Démarrage et Stockage : erreurs par service, plantages, analyse du boot, état SMART, compteurs d’erreurs btrfs et contrôle FAT. Elle permet d’exporter un rapport texte. Les opérations privilégiées passent par polkit ; les outils de stockage sont optionnels.

Depuis la racine du dépôt, installer le paquet fourni :

```fish
sudo pacman -U "Ressources/Applis vibe codées en Libadwaita/05-Systeme-et-utilitaires/Sismographe/sismographe-1.0.0-6-any.pkg.tar.zst"
sismographe
```

Pour les diagnostics de stockage optionnels :

```fish
sudo pacman -Syu --needed smartmontools btrfs-progs dosfstools
```

Désinstallation :

```fish
sudo pacman -Rns sismographe
```

Le paquet a été reconstruit le 14/11/2026 avec un contenu identique : il contenait deux `.PKGINFO`, ce qui doublait les dépendances dans pacman. Packager : Ogu. Le paquet ne déclare plus `stethoscope` dans replaces ni dans conflicts.

Le paquet fourni et son contenu ont été inspectés ; les diagnostics restent à tester sur la machine cible.
