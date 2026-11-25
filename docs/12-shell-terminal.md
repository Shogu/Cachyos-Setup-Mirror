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

### Installer Pamac

Installer la version GTK4 + libadwaita fournie par le dépôt CachyOS :

```fish
sudo pacman -S cachyos/pamac-aur
```

Le paquet `pamac-aur` fournit l'interface graphique et la commande `pamac`. `libpamac-aur` fournit le backend transactionnel. Dans cette version, `libpamac-aur` déclare `flatpak` comme dépendance dure : même si l'on ne souhaite pas gérer d'applications Flatpak, le paquet Flatpak est donc installé avec Pamac.

### Régler les services systemd de Pamac

Objectif : ne lancer aucun service de maintenance Pamac au démarrage, tout en gardant le daemon D-Bus disponible à la demande.

**Ne pas masquer `pamac-daemon.service`.** Pamac, en interface graphique comme en ligne de commande, en a besoin pour les opérations de rafraîchissement. Le service est `static` : il n'est pas activé au démarrage et se lance à la demande.

```fish
sudo systemctl unmask pamac-daemon.service
sudo systemctl disable --now pamac-cleancache.timer
sudo systemctl mask pamac-cleancache.service pamac-offline-upgrade.service
```

État attendu :

| Unité | Réglage | État attendu |
|---|---|---|
| `pamac-daemon.service` | Laisser disponible, non masqué | `static`, à la demande |
| `pamac-cleancache.timer` | Désactiver et arrêter | `disabled` |
| `pamac-cleancache.service` | Masquer | `masked` |
| `pamac-offline-upgrade.service` | Masquer | `masked` |

Contrôler les états :

```fish
systemctl status pamac-daemon.service
systemctl is-enabled pamac-cleancache.timer pamac-cleancache.service pamac-offline-upgrade.service
```

Le daemon D-Bus peut être actif pendant une opération Pamac : c'est normal et ne signifie pas qu'il est lancé en permanence au démarrage.

### Indicateur GNOME de mises à jour

Le paquet installe également l'extension GNOME `pamac-updates@manjaro.org`. Dans cette configuration, elle reste désactivée : elle ne figure pas dans la liste des extensions GNOME activées et n'est donc pas chargée. Il n'est pas nécessaire de supprimer ses fichiers, qui appartiennent au paquet.

### Retirer Flathub et, éventuellement, Flatpak

Si le dépôt Flathub n'est pas utilisé, retirer uniquement le dépôt distant :

```fish
flatpak remote-delete flathub
```

**Attention :** retirer ensuite le paquet `flatpak` avec `pacman -Rdd` contourne la dépendance dure déclarée par `libpamac-aur`. Cela laisse la base Pacman dans un état où une dépendance installée manque. Pamac peut continuer à fonctionner pour les dépôts et l'AUR, mais cette configuration n'est plus cohérente du point de vue des dépendances et peut compliquer les mises à jour. À réserver à un choix délibéré, en sachant qu'il faudra éventuellement réinstaller Flatpak pour rétablir la cohérence :

```fish
sudo pacman -Rdd flatpak
```

La suppression forcée de Flatpak n'est donc pas une étape normale de l'installation de Pamac ; la solution propre est de conserver le paquet Flatpak tout en supprimant le remote Flathub.

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

Les paquets AUR sont gérés par Pamac : `pamac upgrade --aur --devel` met à jour l'AUR après `pacman -Syu` pour les dépôts officiels. L'alias Fish `upgrade` enchaîne les deux. Les mises à jour des paquets AUR distribués sous forme de sources nécessitent une chaîne de compilation (`base-devel`, `fakeroot`, `gcc`). Si ces outils ont été retirés lors du nettoyage, la compilation des paquets AUR concernés échouera ; les paquets binaires du dépôt CachyOS ne sont pas concernés.

---

[Accueil](../README.md) · [Précédent](11-applications-vibe-coded.md) · [Suivant](13-vivaldi.md)
