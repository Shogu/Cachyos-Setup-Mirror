# 12 — Shell & terminal

[Accueil](../README.md) · [Précédent](11-applications-vibe-coded.md) · [Suivant](13-vivaldi.md)

> **Dans ce chapitre :** intégration de Ptyxis à Nautilus, configuration de Fish, GNOME Text Editor, Micro et Shelly.

- [12.1 Intégrer Ptyxis à Nautilus et aux outils CachyOS](#121--intégrer-ptyxis-à-nautilus-et-aux-outils-cachyos)
- [12.2 Fish, GNOME Text Editor et Micro](#122--fish-gnome-text-editor-et-micro)
- [12.3 Shelly et le lanceur de mise à jour](#123--shelly-et-le-lanceur-de-mise-à-jour)

## 12.1 — Intégrer Ptyxis à Nautilus et aux outils CachyOS

Installer l'intégration du terminal dans Nautilus :

```fish
paru -S nautilus-open-any-terminal
gsettings set com.github.stunkymonkey.nautilus-open-any-terminal terminal ptyxis
gsettings set com.github.stunkymonkey.nautilus-open-any-terminal new-tab true
```

L'option `new-tab` ouvre un onglet dans la session existante. En cas d'erreur avec GNOME 49, consulter [le ticket du projet](https://github.com/Stunkymonkey/nautilus-open-any-terminal/issues/242).

Pour ajouter Ptyxis aux terminaux proposés par les outils CachyOS, le mémo conserve [ce guide communautaire](https://www.reddit.com/r/cachyos/comments/1rry7qh/guide_add_your_terminal_to_cachyos_tools_like/).

## 12.2 — Fish, GNOME Text Editor et Micro

### Zoxide avec Fish

Installer puis ajouter dans `~/.config/fish/config.fish` :

```fish
sudo pacman -S zoxide
zoxide init fish | source
alias to='z'
```

Recharger : `source ~/.config/fish/config.fish`

`cd` reste le `cd` natif de Fish ; `z` et `to` utilisent zoxide.

```fish
to musique
zi
zoxide query -l
zoxide add ~/MonDossier
```

Configurer Ptyxis et **GNOME Text Editor**, puis installer le fichier **`config.fish` du dépôt** dans `~/.config/fish/config.fish`. Il contient les alias et la désactivation du message d'accueil.

```fish
source ~/.config/fish/config.fish
```

Ajouter les `functions` (à télécharger dans le dépôt) dans `~/.config/fish/functions`.

Dans GNOME Text Editor, ajuster les préférences internes et désactiver la correction orthographique ; le mémo l'utilise pour éviter les avertissements observés lors d'un lancement en ligne de commande.

Pour Micro, créer le dossier puis éditer le fichier :

```fish
mkdir -p ~/.config/micro
gnome-text-editor ~/.config/micro/settings.json
```

Insérer ces valeurs dans l'objet JSON existant, ou utiliser ce contenu si le fichier est neuf :

```json
{
  "keymenu": true,
  "mkparents": true
}
```

## 12.3 — Shelly et le lanceur de mise à jour

Le setup utilise **Shelly** pour les mises à jour des dépôts officiels et de l'AUR. Les opérations de contrôle après mise à jour restent dans [Maintenance](14-maintenance.md).

### Installer le lanceur personnel

Le script versionné dans `Ressources/Scripts/upgrade.sh` ouvre Ptyxis, vérifie si `/boot` est monté, tente de le monter si nécessaire et annule la mise à jour si cette tentative échoue. Si le montage est disponible, il lance les mises à jour Shelly standard puis AUR.

Depuis la racine du dépôt, installer le script dans le dossier personnel :

```fish
mkdir -p ~/.local
install -Dm755 "Ressources/Scripts/upgrade.sh" ~/.local/upgrade.sh
```

Créer ou conserver un lanceur de bureau qui exécute `/home/ogu/.local/upgrade.sh`. Le chemin est celui du compte utilisé pour ce setup ; l'adapter si le nom du dossier personnel diffère.

Le hook Pacman qui protège également les mises à jour lancées en dehors de ce lanceur est documenté dans [Boot & kernel — protection de `/boot`](03-boot-kernel.md#37--protéger-les-transactions-noyau-si-boot-nest-pas-monté).

### Apparence de Shelly

Éditer la configuration :

```fish
gnome-text-editor "$HOME/.config/shelly/config.json"
```

Modifier les valeurs des clés correspondantes, en conservant le reste du JSON :

```json
{
  "ProgressBarStyle": "Pacman",
  "FileSizeDisplay": "Megabytes"
}
```

Pour le thème GTK, le mémo propose :

```fish
shelly install adw-gtk-theme
```

Activer ensuite le thème adw-gtk3 dans Tweaks, selon le nom effectivement installé.

---

[Accueil](../README.md) · [Précédent](11-applications-vibe-coded.md) · [Suivant](13-vivaldi.md)
