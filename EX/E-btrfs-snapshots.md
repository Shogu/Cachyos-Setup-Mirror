# E — Btrfs et snapshots

[Accueil](README.md) · [Précédent](D-kernel-schedulers.md) · [Suivant](F-reseau.md)

- [Régler les montages Btrfs et FAT32 et le NoCoW](#e1--régler-les-montages-btrfs-et-fat32-et-le-nocow)
- [Configurer et restaurer les snapshots Limine](#e2--configurer-et-restaurer-les-snapshots-limine)

## E1 — Régler les montages Btrfs et FAT32 et le NoCoW

Éditer `/etc/fstab` en adaptant les UUID si les partitions ont changé :

```fish
sudoedit /etc/fstab
```

Pour FS BTRFS et boot en FAT: suppression de *defaults*, ajout de *noatime*, *commit=60*, *noacl* :
```
# <file system>             <mount point>  <type>  <options>  <dump>  <pass>
UUID=e181248c-3cce-4428-bdc4-b6efd715c470 /             btrfs   subvol=/@,noatime,commit=60,compress=zstd:1 0 0
UUID=e181248c-3cce-4428-bdc4-b6efd715c470 /home          btrfs   subvol=/@home,noatime,commit=60,noacl,compress=zstd:1 0 0
UUID=e181248c-3cce-4428-bdc4-b6efd715c470 /root          btrfs   subvol=/@root,noatime,commit=60,noacl,compress=zstd:1 0 0
UUID=e181248c-3cce-4428-bdc4-b6efd715c470 /srv           btrfs   subvol=/@srv,noatime,commit=60,noacl,compress=zstd:1 0 0
UUID=e181248c-3cce-4428-bdc4-b6efd715c470 /var/cache     btrfs   subvol=/@cache,noatime,commit=60,noacl,compress=zstd:1 0 0
UUID=e181248c-3cce-4428-bdc4-b6efd715c470 /var/tmp       btrfs   subvol=/@tmp,noatime,commit=60,noacl,compress=zstd:1 0 0
UUID=e181248c-3cce-4428-bdc4-b6efd715c470 /var/log       btrfs   subvol=/@log,noatime,commit=60,noacl,compress=zstd:1 0 0
tmpfs                                     /tmp           tmpfs   noatime,mode=1777 0 0
```

Relancer FSTAB avec `sudo systemctl daemon-reload` puis vérifier l'intégrité des lignes FSTAB avec :
```
sudo findmnt --verify
```

Et activer NoCOW avec :
```
sudo chattr -R +C /home/ogu/Musique /home/ogu/Vidéos /home/ogu/Téléchargements ~/.cache /var/cache/pacman/pkg /var/cache/man /var/tmp /var/log/journal /var/abs ~/.local/share/Trash
```

`daemon-reload` recharge les unités générées depuis fstab ; il ne remonte pas les partitions. Les options effectives se vérifient avec :

```fish
findmnt --list --notruncate -o TARGET,SOURCE,FSTYPE,OPTIONS
```

Si l’option de gestion de la racine uniquement par `rootflags` est retenue, voir [les paramètres du noyau](D-kernel-schedulers.md#d2--paramètres-du-noyau-scx-et-ananicy) avant de commenter la ligne `/`.


## E2 — Configurer et restaurer les snapshots Limine

Limiter à 20 le nombre d’entrées de snapshots :

```fish
sudoedit /etc/limine-snapper-sync.conf
```

```ini
MAX_SNAPSHOT_ENTRIES=20
```

Appliquer :

```fish
sudo limine-snapper-sync
```

Le mémo propose d’utiliser Btrfs Assistant pour configurer les services systemd et la planification des snapshots, puis de le retirer si son interface n’est plus nécessaire car BTRFS-assistant peut casser le boot d'apres le developpeur Zesko (Limine-snapper-sync). Dans la configuration testée, les services systemd et la timeline ont été configurés dans Btrfs Assistant avant sa suppression.

Pour restaurer un snapshot démarré depuis Limine, privilégier **`limine-snapper-restore`**. La partition FAT32 de démarrage se trouve hors des snapshots Btrfs : restaurer seulement la racine avec un autre outil peut désynchroniser le noyau et ses modules.

```fish
limine-snapper-restore
```

Si la notification attendue n’apparaît pas après le démarrage sur un snapshot :

```fish
limine-snapper-restore --notify
```

Après une restauration accidentelle avec Btrfs Assistant et une erreur de correspondance noyau/modules, le mémo prévoit de démarrer un autre snapshot fonctionnel depuis Limine, puis de le restaurer avec l’outil Limine.

Limine et systemd-boot attendent ici que les noyaux et leurs initramfs soient stockés sur la partition FAT32 de démarrage, hors des snapshots Btrfs. Btrfs Assistant ne restaure pas cette partie : une restauration de la seule racine peut donc produire un décalage entre le noyau présent dans `/boot` et les fichiers de la racine.

[Accueil](README.md) · [Précédent](D-kernel-schedulers.md) · [Suivant](F-reseau.md)
