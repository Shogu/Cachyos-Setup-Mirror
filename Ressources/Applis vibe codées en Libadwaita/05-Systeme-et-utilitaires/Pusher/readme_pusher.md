# Pusher

Application libadwaita « vibe codée » de gestion ultra-basique du dépôt GitLab personnel.

**Paquet actuel : `pusher-1.8.2-1-any.pkg.tar.zst`.**

## Installation

```fish
sudo pacman -U ./pusher-1.8.2-1-any.pkg.tar.zst
```

## Changelog

### 1.8.2 — Séparation UI envoyés/supprimés
La fenêtre distingue désormais deux groupes :
- **Fichiers à envoyer** : ajouts, modifications, nouveaux fichiers (avec taille).
- **Fichiers supprimés** : fichiers effacés du dépôt local (à pousser sur GitLab).

### 1.8.2 — Correctif : liste tronquée au premier fichier (NUL)
**Symptôme** : Pusher n'affichait qu'**un seul** fichier en attente, même quand il y en
avait plusieurs, alors que le push envoyait bien **tout** sur GitLab.

**Cause** : `pending_changes()` utilisait `git status -z` (séparateur NUL `\0`) mais lisait la
sortie via `Gio.communicate_utf8()`, qui **tronque la chaîne au premier octet NUL**. Résultat :
seul le premier fichier restait visible ; le push (`git add --all`) envoyait pourtant l'arbre complet.

**Correctif** : nouvelle fonction `run_git_bytes()` qui lit la sortie **en octets bruts**
(`Gio.Subprocess.communicate()`) et préserve les `\0`, puis `pending_changes()` découpe proprement
sur `\0`. La liste affiche désormais **tous** les fichiers en attente.

### 1.8.1 — précédente version
Correctif initial du défaut NUL (premier build corrigé).

## Rebuild depuis le `.zst` (pas de source amont)

Le projet n'a pas de source locale : le paquet `any` se reconstruit depuis le `.zst` lui-même.

```fish
mkdir build && cd build
bsdtar -xf ../pusher-1.8.2-1-any.pkg.tar.zst
# modifier usr/lib/pusher/pusher.py, puis :
rm -f usr/lib/pusher/__pycache__   # si présent
bsdtar -czf .MTREE --format=mtree \
  --options='!all,use-set,type,uid,gid,mode,time,size,md5,sha256,link' .
cd ..
bsdtar -cf - --uid=0 --gid=0 -C build .MTREE .PKGINFO .BUILDINFO usr \
  | zstd -19 -o pusher-X.Y.Z-1-any.pkg.tar.zst
```

> ⚠️ La version dans le fichier et dans `.PKGINFO` doit être alignée (constante `VERSION` de
> `pusher.py` + ligne `pkgver`). La source corrigée à jour est fournie ici :
> `pusher-1.8.2-pusher.py`.

## Désinstallation

```fish
sudo pacman -Rns pusher
```
