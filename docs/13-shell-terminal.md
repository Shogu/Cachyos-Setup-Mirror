# 13 — Shell & terminal

[Accueil](../README.md) · [Précédent](12-applications-vibe-coded.md) · [Suivant](14-vivaldi.md)

> **Dans ce chapitre :** intégration de Ptyxis à Nautilus, configuration de Fish, GNOME Text Editor et Micro.

- [13.1 Intégrer Ptyxis à Nautilus et aux outils CachyOS](#131--intégrer-ptyxis-à-nautilus-et-aux-outils-cachyos)
- [13.2 Fish, GNOME Text Editor et Micro](#132--fish-gnome-text-editor-et-micro)

## 13.1 — Intégrer Ptyxis à Nautilus et aux outils CachyOS

Installer l'intégration du terminal dans Nautilus :

```fish
paru -S nautilus-open-any-terminal
gsettings set com.github.stunkymonkey.nautilus-open-any-terminal terminal ptyxis
gsettings set com.github.stunkymonkey.nautilus-open-any-terminal new-tab true
```

L'option `new-tab` ouvre un onglet dans la session existante. En cas d'erreur avec GNOME 49, consulter [le ticket du projet](https://github.com/Stunkymonkey/nautilus-open-any-terminal/issues/242).

Pour ajouter Ptyxis aux terminaux proposés par les outils CachyOS, le mémo conserve [ce guide communautaire](https://www.reddit.com/r/cachyos/comments/1rry7qh/guide_add_your_terminal_to_cachyos_tools_like/).

## 13.2 — Fish, GNOME Text Editor et Micro

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


Configurer Ptyxis et **GNOME Text Editor**, puis installer le fichier **`config.fish` du dépôt** dans `~/.config/fish/config.fish`. Il contient les alias, la désactivation du message d'accueil:


```fish
source ~/.config/fish/config.fish
```
Ajouter les `functions` (à télécharger dans le dépôt) dans `config/fish/functions`.


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

---

[Accueil](../README.md) · [Précédent](12-applications-vibe-coded.md) · [Suivant](14-vivaldi.md)
