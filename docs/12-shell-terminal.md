# 12 — Shell & terminal

[Accueil](../README.md) · [Précédent](11-applications-vibe-coded.md) · [Suivant](13-vivaldi.md)

> **Dans ce chapitre :** intégration de Ptyxis à Nautilus, configuration de Fish, GNOME Text Editor, Micro et Shelly.

- [12.1 Intégrer Ptyxis à Nautilus et aux outils CachyOS](#121--intégrer-ptyxis-à-nautilus-et-aux-outils-cachyos)
- [12.2 Fish, GNOME Text Editor et Micro](#122--fish-gnome-text-editor-et-micro)
- [12.3 Shelly et le lanceur de mise à jour](#123--shelly-et-le-lanceur-de-mise-à-jour)

## 12.1 — Intégrer Ptyxis à Nautilus et aux outils CachyOS

Installer **nautilus-ptyxis-root** pour intégrer directement Ptyxis à Nautilus. Le paquet ajoute cinq actions :

- **Ouvrir dans un terminal** : lance Ptyxis dans le dossier affiché ou sélectionné.
- **Ouvrir en root** : ouvre le dossier avec les droits administrateur.
- **Terminal intégré** : affiche un terminal dans le panneau inférieur de Nautilus ; l'affichage se bascule avec **F4** ou le bouton dédié.
- **Installer le paquet** : clic droit sur un fichier `.pkg.tar.zst` ; un nouvel onglet Ptyxis lance `sudo pacman -U` sur ce paquet.
- **Copier le chemin** : clic droit sur un ou plusieurs éléments copie leur chemin complet dans le presse-papiers. Avec plusieurs éléments, chaque chemin occupe une ligne.

Le paquet compilé sera déposé manuellement dans [Ressources/Logiciels/Nautilus Ptyxis Root](../Ressources/Logiciels/Nautilus%20Ptyxis%20Root/). Une fois le fichier `.pkg.tar.zst` ajouté dans ce dossier, l'installer depuis la racine du dépôt :

```fish
sudo pacman -U "Ressources/Logiciels/Nautilus Ptyxis Root/"*.pkg.tar.zst
nautilus -q
```

Rouvrir Nautilus pour retrouver les trois actions. Le dossier de dépôt contient un README avec la procédure.

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

Configurer Ptyxis et **GNOME Text Editor**, puis installer les fichiers Fish du dépôt dans les emplacements correspondants :

- `Ressources/Logiciels/Fish/config.fish` → `~/.config/fish/config.fish` : alias, abréviations, éditeurs et configuration générale ;
- `Ressources/Logiciels/Fish/functions/` → `~/.config/fish/functions/` : fonctions personnelles autoloadées ;
- `Ressources/Logiciels/Fish/conf.d/shelly-local.fish` → `~/.config/fish/conf.d/shelly-local.fish` : autocomplétion des chemins de fichiers locaux pour `shelly install standard`, notamment après `./` ou `../`. Cela facilite la sélection d’un paquet local dans un flux d’installation équivalent à `pacman -U`, sans remplacer ni exécuter `pacman -U`.

Créer les répertoires puis copier les fichiers depuis la racine du dépôt :

```fish
mkdir -p ~/.config/fish/{conf.d,functions}
cp "Ressources/Logiciels/Fish/config.fish" ~/.config/fish/config.fish
cp "Ressources/Logiciels/Fish/conf.d/shelly-local.fish" ~/.config/fish/conf.d/shelly-local.fish
cp Ressources/Logiciels/Fish/functions/*.fish ~/.config/fish/functions/
```

Recharger la configuration :

```fish
source ~/.config/fish/config.fish
```

La complétion `shelly-local.fish` est chargée automatiquement par Fish au démarrage. Pour la tester dans une nouvelle commande, saisir `shelly install standard ./` puis appuyer sur **Tab** : Fish doit proposer les fichiers et paquets locaux correspondants.

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

Le script versionné dans `Ressources/Scripts/upgrade.sh` ouvre Ptyxis, vérifie si `/boot` est monté, tente de le monter si nécessaire et annule la mise à jour si cette tentative échoue. Si le montage est disponible, il lance les mises à jour Shelly standard puis AUR. La pilule est le point d’entrée graphique vers ce script ; le chemin du script doit être sélectionné dans les préférences de Focus & Boutons. Pour les contrôles après mise à jour, voir [14 — Maintenance](14-maintenance.md).

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
