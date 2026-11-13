<div align="center">

<img src="data/icons/io.gitlab.shogu.Vidange.svg" width="128" alt="Icône de Vidange">

# Vidange

<<<<<<< Updated upstream
**Version : 1.4.2-1**

La version 1.4.2-1 ajoute une page **« Bilan après une mise à jour »**, accessible depuis l'application et en ligne de commande avec `vidange --bilan`. Un hook pacman permet de présenter ce bilan après une mise à jour des paquets. Les textes affichés par cette page sont traités comme du texte brut, et non comme du balisage.

**Vidange** est une application de nettoyage système pour CachyOS et GNOME, développée en Python avec GTK4/libadwaita. Toute l'interface et les messages sont en français. Elle rassemble dans une fenêtre les opérations courantes de maintenance et affiche une estimation de l'espace récupérable avant chaque nettoyage.
=======
**Nettoyage du système pour CachyOS et GNOME, en GTK4 / libadwaita**
>>>>>>> Stashed changes

</div>

Vidange réunit en une fenêtre tout ce qu'on fait d'habitude à la main pour alléger un système Arch : paquets orphelins, caches, journaux, navigateurs. Chaque catégorie affiche la place qu'elle libérera **avant** le nettoyage, et un bouton « Tout nettoyer » enchaîne le tout avec un récapitulatif à la fin. Un **mode simulation** montre ce qui serait supprimé, sans rien toucher.

## Ce qu'elle nettoie

| Catégorie | Outil |
|---|---|
| Orphelins sûrs | `pacman -Qtdq` |
| Cache pacman | `paccache -rk2` (ou `-ruk0`, ou `pacman -Scc`) |
| Cache AUR | `shelly purify standard --aur-cache` |
| Flatpak inutilisés | `flatpak uninstall --unused` |
| Journaux systemd | `journalctl --vacuum-size` (taille réglable) |
| Cache des micrologiciels | `/var/cache/fwupd` |
| Miniatures et corbeille | `~/.cache/thumbnails`, `gio trash --empty` |
| Cache web des navigateurs | `~/.cache/vivaldi`, Firefox, Chromium, Chrome (navigateur fermé) |
| Caches de shaders | Mesa, RADV, NVIDIA |
| Caches de développement | pip, npm, yarn, pnpm, Bun, Deno, uv, Go, Rust, Zig, ccache, sccache, Gradle, Electron, node-gyp |
| Conteneurs | Docker, Podman : cache de build et images orphelines |
| Navigateurs | `profile-cleaner` |

Le groupe **Vérification** réunit les orphelins sûrs et trois vues à examiner au cas par cas, où rien n'est coché par défaut :

- **Orphelins à vérifier** : dépendances qui ne servent qu'entre elles ou en option (`pacman -Qdq` puis `-Rsu --print`) ;
- **Installés explicitement, à vérifier** : `pacman -Qetq`, avec « Marquer comme dépendance » ;
- **Dossiers de configuration orphelins, à vérifier** : dossiers de `~/.config`, `~/.local/share`, `~/.cache` et `~/.var/app` dont l'appli semble désinstallée. Un clic les ouvre dans Fichiers, et ceux qu'on coche partent à la corbeille.

Vidange remplace une fonction fish `clean` et le paquet AUR `archclean`. Pas d'analyse des gros fichiers : c'est voulu.

## Bilan après une mise à jour

Après chaque version de GNOME, de GTK, de libadwaita ou de Python, la page **Bilan** (ou `vidange --bilan`) passe en revue les applis maison, les AppImage, les greffons Nautilus et les extensions GNOME Shell : bibliothèques manquantes, paquets restés sur un ancien Python, lancement de quelques secondes avec relevé des avertissements GTK/Adwaita, erreurs d'extensions, widgets dépréciés. Un hook pacman rappelle de le faire quand une de ces briques change de branche. Détails dans le [guide](GUIDE.md).

## Sécurité

L'appli ne tourne jamais en root. Les opérations système passent par un petit helper (`/usr/lib/vidange/vidange-helper`) lancé par `pkexec`, qui n'accepte qu'une liste fermée d'actions. Un seul mot de passe pour tout le nettoyage. Aucune commande ne passe par un shell.

## Installation

```fish
# paquet compilé
sudo pacman -U vidange-1.3.1-1-any.pkg.tar.zst

# ou depuis les sources
makepkg -si
```

Dépendances : `python-gobject`, `gtk4`, `libadwaita` ≥ 1.6, `pacman-contrib`, `polkit`.
Optionnelles : `profile-cleaner`, `shelly`, et les outils de développement dont on veut vider le cache.

## En savoir plus

Le détail de chaque opération est dans [GUIDE.md](GUIDE.md).

---

Licence GPL-3.0-or-later · `io.gitlab.shogu.Vidange`
