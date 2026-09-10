# G — Optimisations système

[Accueil](README.md) · [Précédent](F-reseau.md) · [Suivant](H-powersave.md)

- [Alléger les journaux et les stocker en RAM](#g1--alléger-les-journaux-et-les-stocker-en-ram)
- [Désactiver les coredumps](#g2--désactiver-les-coredumps)
- [Configurer makepkg pour znver4](#g3--configurer-makepkg-pour-znver4)
- [Nettoyer les traductions et les fichiers de configuration](#g4--nettoyer-les-traductions-et-les-fichiers-de-configuration)

## G1 — Alléger les journaux et les stocker en RAM

Ouvrir la configuration de journald :

```fish
sudoedit /etc/systemd/journald.conf
```

Reprendre le contenu du fichier **`journald.conf.txt` fourni dans le dépôt**, qui définit l’allégement des journaux et leur stockage en RAM. Ce fichier annexe n’est pas inclus dans les deux pièces jointes utilisées pour cette réorganisation.

Relancer ensuite le service :

```fish
sudo systemctl restart systemd-journald
```

## G2 — Désactiver les coredumps

Désactiver et masquer les unités de collecte des coredumps retenues dans le mémo :

```fish
sudo systemctl disable --now systemd-coredump.socket
sudo systemctl mask systemd-coredump
sudo systemctl mask systemd-coredump.socket
```

Ajouter la limite maximale de taille des fichiers core dans `limits.conf` si elle n’y figure pas déjà :

```fish
echo '* hard core 0' | sudo tee -a /etc/security/limits.conf
```

Cette dernière ligne concerne les sessions auxquelles les limites PAM s’appliquent ; elle ne constitue pas à elle seule un réglage global de tous les services systemd.

## G3 — Configurer makepkg pour znver4

Éditer la configuration de makepkg :

```fish
sudoedit /etc/makepkg.conf
```

Le mémo retient les options suivantes dans `CFLAGS` :
```
CFLAGS="-march=znver4 -mtune=znver4 -pipe -fno-plt -fexceptions \
        -Wp,-D_FORTIFY_SOURCE=3 -Wformat -Werror=format-security \
        -fstack-clash-protection -fcf-protection"
```

## G4 — Nettoyer les traductions et les fichiers de configuration

Le nettoyage détaillé ici concerne les traductions sous `/usr/share/locale`. Le README évoque aussi un tri de `~/.local/share`, `~/.config` et `/etc`, sans donner de liste de fichiers à supprimer : examiner ces dossiers au cas par cas.

### Conserver les traductions françaises et anglaises

Les fichiers placés sous `/usr/share/locale` appartiennent aux paquets installés. Une suppression manuelle n’est donc pas permanente : ils sont recréés lors des mises à jour.

Pacman permet d’empêcher leur réinstallation avec la directive `NoExtract`.

### Sauvegarder les locales actuelles

```bash
mkdir -p "$HOME/Sauvegardes"

sudo tar -C /usr/share \
  -caf "$HOME/Sauvegardes/locales-avant-nettoyage.tar.zst" \
  locale
```

Vérifier la sauvegarde :

```bash
tar -tf "$HOME/Sauvegardes/locales-avant-nettoyage.tar.zst" | head
```

### Configurer pacman

Éditer :

```bash
sudoedit /etc/pacman.conf
```

Dans la section `[options]`, ajouter :

```ini
# Ne pas extraire les traductions, sauf français et anglais
NoExtract = usr/share/locale/*
NoExtract = !usr/share/locale/fr*
NoExtract = !usr/share/locale/en*
NoExtract = !usr/share/locale/locale.alias
```

Les règles commençant par `!` réautorisent les chemins français et anglais après l’exclusion générale.

### Afficher les répertoires qui seront supprimés

```bash
sudo find /usr/share/locale \
  -mindepth 1 \
  -maxdepth 1 \
  -type d \
  ! -name 'fr*' \
  ! -name 'en*' \
  -print
```

Examiner complètement la liste avant de continuer.

### Supprimer les locales inutilisées

```bash
sudo find /usr/share/locale \
  -mindepth 1 \
  -maxdepth 1 \
  -type d \
  ! -name 'fr*' \
  ! -name 'en*' \
  -exec rm -rf -- {} +
```

### Vérifier le résultat

```bash
find /usr/share/locale \
  -mindepth 1 \
  -maxdepth 1 \
  -type d \
  -printf '%f\n' |
  sort
```

Vérifier les locales système actives :

```bash
locale
localectl status
```

### Restaurer en cas de problème

```bash
sudo tar -C /usr/share \
  -xaf "$HOME/Sauvegardes/locales-avant-nettoyage.tar.zst"
```

Pour autoriser de nouveau toutes les traductions, supprimer les lignes `NoExtract` ajoutées à `/etc/pacman.conf`, puis réinstaller le paquet concerné :

```bash
sudo pacman -S nom-du-paquet
```

Cette optimisation économise uniquement de l’espace disque. Elle n’améliore pas sensiblement le démarrage ou les performances du système.

[Accueil](README.md) · [Précédent](F-reseau.md) · [Suivant](H-powersave.md)
