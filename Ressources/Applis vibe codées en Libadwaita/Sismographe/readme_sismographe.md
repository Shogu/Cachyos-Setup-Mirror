# Sismographe 1.0.0

Application GTK4/libadwaita de diagnostic du système GNOME, remplaçant **Stethoscope**. Elle regroupe les vues Santé, Journaux, Démarrage et Stockage : erreurs par service, plantages, analyse du boot, état SMART, compteurs d’erreurs btrfs et contrôle FAT. Elle permet d’exporter un rapport texte. Les opérations privilégiées passent par polkit ; les outils de stockage sont optionnels.

Depuis la racine du dépôt, retirer l’ancienne application si elle est installée, puis installer le paquet fourni :

```fish
if pacman -Q stethoscope >/dev/null 2>&1
    sudo pacman -Rns stethoscope
end
sudo pacman -U "Ressources/Applis vibe codées en Libadwaita/Sismographe/sismographe-1.0.0-1-any.pkg.tar.zst"
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

Le paquet fourni et son contenu ont été inspectés ; les diagnostics restent à tester sur la machine cible.
