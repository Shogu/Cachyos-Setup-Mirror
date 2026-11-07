# Pusher

Application GTK4/libadwaita de gestion du dépôt GitLab personnel **CACHYOS-Setup**.

Le nom du paquet Arch est **pusher-ogu** pour éviter la collision avec le paquet AUR homonyme. Le nom affiché dans GNOME et la commande restent **Pusher** et `pusher`.

## Installation

Depuis ce dossier :

```fish
sudo pacman -U ./pusher-ogu-1.8.3-1-any.pkg.tar.zst
```

## Changelog

### 1.8.3 — Protection contre les conflits Git résiduels

Pusher vérifie désormais les entrées non fusionnées de l’index avec `git ls-files -u`, en plus des marqueurs de rebase, merge, cherry-pick et revert. Cela couvre le cas où l’index conserve un conflit (par exemple un fichier supprimé par l’autre branche) alors que `.git/MERGE_HEAD` est absent.

Dans cet état, Pusher bloque le push et le pull et affiche un message demandant de résoudre les chemins signalés par `git status`. Cette vérification évite d’appeler `git reset --soft` sur un index encore en conflit, qui provoquait :

```text
fatal: Cannot do a soft reset in the middle of a merge.
```

### 1.8.2 — Séparation UI envoyés/supprimés

La fenêtre distingue deux groupes :
- **Fichiers à envoyer** : ajouts, modifications et nouveaux fichiers (avec taille).
- **Fichiers supprimés** : fichiers effacés localement et à répercuter sur GitLab.

### 1.8.2 — Liste complète des fichiers en attente

La lecture de `git status -z` utilise désormais `Gio.Subprocess.communicate()` en octets bruts. Les séparateurs NUL ne sont plus tronqués et tous les fichiers en attente sont affichés.

## Reconstruction

Depuis ce dossier :

```fish
makepkg -f
```

Le paquet obtenu est `pusher-ogu-1.8.3-1-any.pkg.tar.zst`. Pour l’installer :

```fish
sudo pacman -U ./pusher-ogu-1.8.3-1-any.pkg.tar.zst
```

Dépendances d’exécution : `python`, `python-gobject`, `gtk4`, `libadwaita`, `libsecret`, `git` et `openssh`.

## Désinstallation

```fish
sudo pacman -Rns pusher-ogu
```
