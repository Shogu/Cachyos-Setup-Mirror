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

**Cause** : `pending_changes()` utilisait `git status -z` (séparateur NUL `\\0`) mais lisait la
sortie via `Gio.communicate_utf8()`, qui **tronque la chaîne au premier octet NUL**. Résultat :
seul le premier fichier restait visible ; le push (`git add --all`) envoyait pourtant l'arbre complet.

**Correctif** : nouvelle fonction `run_git_bytes()` qui lit la sortie **en octets bruts**
(`Gio.Subprocess.communicate()`) et préserve les `\\0`, puis `pending_changes()` découpe proprement
sur `\\0`. La liste affiche désormais **tous** les fichiers en attente.

### 1.8.1 — précédente version
Correctif initial du défaut NUL (premier build corrigé).

## Afficher le diff des archives ZIP

Git traite les fichiers `.zip` comme des binaires : il indique qu'une archive a changé, mais
n'en montre pas le contenu du diff. Le mécanisme **textconv** permet de convertir temporairement
chaque archive en manifeste texte (taille décompressée + nom des fichiers) pour rendre les
changements lisibles. **L'archive stockée et envoyée par Git reste strictement inchangée** :
seule la présentation du diff est modifiée.

Cette configuration comporte trois éléments :

### 1. Script local de conversion

Créer `~/.local/bin/zipmanifest.py` sur la machine :

```python
#!/usr/bin/env python3
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1]) as archive:
    for item in archive.infolist():
        print(f"{item.file_size:>9}  {item.filename}")
```

Puis le rendre exécutable :

```fish
mkdir -p ~/.local/bin
chmod +x ~/.local/bin/zipmanifest.py
```

Le script affiche, pour chaque entrée de l'archive, sa taille décompressée et son chemin.

### 2. Déclarer les archives ZIP dans le dépôt

Ajouter cette règle au fichier `.gitattributes` **à la racine du dépôt** (à créer s'il n'existe pas) :

```gitattributes
*.zip diff=zipdiff
```

Ce fichier est versionné : la règle est ainsi partagée avec les clones du dépôt. Elle associe
les archives ZIP au driver de diff nommé `zipdiff`.

### 3. Configurer le driver Git localement

Sur chaque machine, configurer le chemin vers le script. La configuration est globale à l'utilisateur
et le chemin utilise `$HOME` pour éviter de dépendre d'un nom de compte précis :

```fish
git config --global diff.zipdiff.textconv "$HOME/.local/bin/zipmanifest.py"
git config --global diff.zipdiff.binary false
```

Le script et cette configuration restent locaux ; seul `.gitattributes` est commité dans le dépôt.

### Vérifier

Après avoir modifié et commité une archive ZIP, comparer deux révisions :

```fish
git diff HEAD~1 HEAD -- "chemin/vers/fichier.zip"
```

Git affiche alors les différences entre les manifestes : fichiers ajoutés ou supprimés, chemins
modifiés et tailles différentes. Ce procédé ne compare pas le contenu interne des fichiers et ne
remplace pas un outil de comparaison spécialisé pour les documents contenus dans l'archive.

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
