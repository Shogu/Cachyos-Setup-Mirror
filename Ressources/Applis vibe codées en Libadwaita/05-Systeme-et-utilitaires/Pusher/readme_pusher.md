# Pusher

Application libadwaita « vibe codée » de gestion ultra-basique du dépôt GitLab personnel.

**Paquet installé dans le dépôt :** `pusher-1.8.2-1-any.pkg.tar.zst`.
**Source corrective :** `pusher-1.8.3-pusher.py` (paquet 1.8.3 à reconstruire).

## Installation

Le paquet 1.8.2 fourni reste installable ainsi :

```fish
sudo pacman -U ./pusher-1.8.2-1-any.pkg.tar.zst
```

## Changelog

### 1.8.3 — Détection des conflits Git dans l’index

**Symptôme corrigé :** Pusher pouvait tenter `git reset --soft` alors que l’index contenait encore des entrées non fusionnées. Git refusait alors l’opération avec :

```text
fatal: Cannot do a soft reset in the middle of a merge.
```

Ce cas peut survenir même lorsque `.git/MERGE_HEAD` est absent : la présence d’entrées de conflit est vérifiée directement avec `git ls-files -u`. Pusher bloque alors la synchronisation et indique de résoudre les chemins signalés par `git status` dans le terminal. Le test est appliqué avant le push et avant le pull.

Le fichier `pusher-1.8.3-pusher.py` contient le correctif. **Le paquet binaire fourni est encore en 1.8.2** : reconstruire et installer 1.8.3 pour bénéficier du correctif.

### 1.8.2 — Séparation UI envoyés/supprimés

La fenêtre distingue désormais deux groupes :
- **Fichiers à envoyer** : ajouts, modifications, nouveaux fichiers (avec taille).
- **Fichiers supprimés** : fichiers effacés du dépôt local (à pousser sur GitLab).

### 1.8.2 — Correctif : liste tronquée au premier fichier (NUL)

**Symptôme** : Pusher n'affichait qu'**un seul** fichier en attente, même quand il y en
avait plusieurs, alors que le push envoyait bien **tout** sur GitLab.

**Cause** : `pending_changes()` utilisait `git status -z` (séparateur NUL `\\0`) mais lisait la
sortie via `Gio.communicate_utf8()`, qui **tronque la chaîne au premier octet NUL**.

**Correctif** : nouvelle fonction `run_git_bytes()` qui lit la sortie **en octets bruts**
(`Gio.Subprocess.communicate()`) et préserve les séparateurs NUL.

## Rebuild depuis le paquet fourni

Le dépôt conserve le paquet 1.8.2 comme base. Pour reconstruire la version corrigée depuis ce paquet, depuis le dossier Pusher :

```fish
mkdir -p build
cd build
bsdtar -xf ../pusher-1.8.2-1-any.pkg.tar.zst
cp ../pusher-1.8.3-pusher.py usr/lib/pusher/pusher.py
sed -i 's/^pkgver = 1.8.2$/pkgver = 1.8.3/' .PKGINFO
rm -f usr/lib/pusher/__pycache__/*
bsdtar -czf .MTREE --format=mtree \
  --options='!all,use-set,type,uid,gid,mode,time,size,md5,sha256,link' .
cd ..
bsdtar -cf - --uid=0 --gid=0 -C build .MTREE .PKGINFO .BUILDINFO usr \
  | zstd -19 -o pusher-1.8.3-1-any.pkg.tar.zst
sudo pacman -U ./pusher-1.8.3-1-any.pkg.tar.zst
```

Vérifier que la constante `VERSION` dans le script et `pkgver` dans `.PKGINFO` indiquent toutes deux `1.8.3`.

## Désinstallation

```fish
sudo pacman -Rns pusher
```
