# 12 — Shell & terminal

[Accueil](../README.md) · [Précédent](11-applications-vibe-coded.md) · [Suivant](13-vivaldi.md)

> **Dans ce chapitre :** intégration de Ptyxis à Nautilus, configuration de Fish, GNOME Text Editor, Micro et Pamac.

- [12.1 Intégrer Ptyxis à Nautilus et aux outils CachyOS](#121--intégrer-ptyxis-à-nautilus-et-aux-outils-cachyos)
- [12.2 Fish, GNOME Text Editor et Micro](#122--fish-gnome-text-editor-et-micro)
- [12.3 Pamac et le lanceur de mise à jour](#123--pamac-et-le-lanceur-de-mise-à-jour)

## 12.1 — Intégrer Ptyxis à Nautilus et aux outils CachyOS

Installer **nautilus-tools-ogu** pour intégrer directement Ptyxis à Nautilus et étendre son menu contextuel. L'extension native ajoute notamment :

- **Ouvrir dans un terminal** : lance Ptyxis dans le dossier affiché ou sélectionné.
- **Ouvrir en root** : ouvre le dossier avec les droits administrateur.
- **Terminal intégré** : affiche un terminal dans le panneau inférieur de Nautilus ; l'affichage se bascule avec **F4** ou le bouton dédié.
- **Copier le chemin** : clic droit sur un ou plusieurs éléments copie leur chemin complet dans le presse-papiers. Avec plusieurs éléments, chaque chemin occupe une ligne.
- **Ouvrir dans OpenCode** : clic droit sur un dossier (ou en zone vide) → ouvre une session `opencode` dans ce dossier.
- **Changer l'icône des favoris** : clic droit sur un favori de la sidebar → choisir une icône symbolique ; **Réinitialiser** restaure l'icône native.

Le paquet compilé sera déposé manuellement dans [Ressources/Logiciels/Nautilus/Outils/Nautilus-tools](../Ressources/Logiciels/Nautilus/Outils/Nautilus-tools/). Une fois le fichier `.pkg.tar.zst` ajouté dans ce dossier, l'installer depuis la racine du dépôt :

```fish
sudo pacman -U "Ressources/Logiciels/Nautilus/Outils/Nautilus-tools/"*.pkg.tar.zst
nautilus -q
```

Rouvrir Nautilus pour retrouver les actions. Le dossier de dépôt contient un README avec la procédure.

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

- `Ressources/Logiciels/Fish/config.fish` → `~/.config/fish/config.fish` : alias (dont `upgrade` → mise à jour Pamac + AUR), abréviations, éditeurs et configuration générale ;
- `Ressources/Logiciels/Fish/functions/` → `~/.config/fish/functions/` : fonctions personnelles autoloadées (dont `rosetta`, l'aide-mémoire Pacman ↔ Pamac) ;

Créer le répertoire puis copier les fichiers depuis la racine du dépôt :

```fish
mkdir -p ~/.config/fish/functions
cp "Ressources/Logiciels/Fish/config.fish" ~/.config/fish/config.fish
cp Ressources/Logiciels/Fish/functions/*.fish ~/.config/fish/functions/
```

Recharger la configuration :

```fish
source ~/.config/fish/config.fish
```

Les fonctions Fish (dont `rosetta` et les alias AUR) sont chargées automatiquement au démarrage. Saisir `rosetta -p` dans une nouvelle commande pour afficher l'aide-mémoire Pacman ↔ Pamac (recherche, installation dépôt/AUR, mise à jour, nettoyage du cache).

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

## 12.3 — Pamac et le lanceur de mise à jour

Le setup met à jour le système via **Pamac** : dépôts officiels par Pacman, AUR par Pamac. Les opérations de contrôle après mise à jour restent dans [Maintenance](14-maintenance.md).

### Installer le lanceur personnel

Le script versionné dans `Ressources/Scripts/update-system.sh` ouvre Ptyxis, vérifie si `/boot` est monté, tente de le monter si nécessaire et annule la mise à jour si cette tentative échoue. Si le montage est disponible, il lance les mises à jour des dépôts officiels (pacman) puis de l'AUR (pamac). La tuile **Mise à jour** de Quick Settings est le point d'entrée graphique vers ce script ; le chemin du script (`~/.local/bin/update-system.sh`) est sélectionnable dans les préférences de Quick Settings. Pour les contrôles après mise à jour, voir [14 — Maintenance](14-maintenance.md).

Depuis la racine du dépôt, installer le script dans le dossier personnel :

```fish
mkdir -p ~/.local/bin
install -Dm755 "Ressources/Scripts/update-system.sh" ~/.local/bin/update-system.sh
```

Créer ou conserver un lanceur de bureau qui exécute `/home/ogu/.local/bin/update-system.sh`, ou lier la tuile Mise à jour de Quick Settings à ce chemin. L'adapter si le nom du dossier personnel diffère.

Le hook Pacman qui protège également les mises à jour lancées en dehors de ce lanceur est documenté dans [Boot & kernel — protection de `/boot`](03-boot-kernel.md#37--protéger-les-transactions-noyau-si-boot-nest-pas-monté).

### Mises à jour AUR

Les paquets AUR sont gérés par Pamac : `pamac upgrade --aur` met à jour l'AUR après `pacman -Syu` pour les dépôts officiels. L'alias Fish `upgrade` enchaîne les deux.

---

[Accueil](../README.md) · [Précédent](11-applications-vibe-coded.md) · [Suivant](13-vivaldi.md)
