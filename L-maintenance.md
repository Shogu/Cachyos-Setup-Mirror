# L — Maintenance et mises à jour

[Accueil](README.md) · [Précédent](K-vivaldi.md)

- [Choisir Cachy-update ou Shelly](#mises-a-jour)
- [Points à revoir après les mises à jour](#suivi)

<a id="mises-a-jour"></a>

## L1 — Choisir Cachy-update ou Shelly

### Option 1 : conserver Cachy-update

Générer puis ouvrir la configuration utilisateur :

```fish
arch-update --gen-config
arch-update --edit-config
```

Choisir `TrayIconStyle=light` et limiter le nombre de sauvegardes à **1**, au lieu de **3**, dans l’option correspondante du fichier. Modifier le lanceur avec Libre Menu si nécessaire.

### Option 2 : utiliser Shelly

Le mémo propose de supprimer Cachy-update et Paru lorsque Shelly couvre les mises à jour des dépôts et de l’AUR :

```fish
sudo pacman -Rns cachy-update paru
```

Cette option vient **après** les installations utilisant Paru dans les autres chapitres. Le gain d’espace dépend des dépendances effectivement retirées.

Créer le lanceur de mise à jour :

```fish
mkdir -p /home/ogu/.local
gnome-text-editor /home/ogu/.local/upgrade.sh
```

Y placer ce script Bash, qui ouvre Ptyxis et exécute les commandes dans Fish :

```bash
#!/usr/bin/env bash
#update-shelly.sh – Lance une mise à jour Shelly dans Ptyxis

ptyxis --maximize -- fish -c "
set_color 3584e4
echo '╔══════════════════════╗'
echo '║  MISE À JOUR SHELLY  ║'
echo '╚══════════════════════╝'
set_color normal
echo
shelly upgrade standard
shelly upgrade aur
echo
read -P 'Fermer avec ENTRÉE '
"
```

Rendre le script exécutable :

```fish
chmod +x /home/ogu/.local/upgrade.sh
```

Créer un lanceur pointant vers `/home/ogu/.local/upgrade.sh`. Le mémo apprécie aussi la notification de redémarrage nécessaire proposée par Shelly.

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

<a id="suivi"></a>

## L2 — Points à revoir après les mises à jour

Les opérations détaillées restent dans leur rubrique pour éviter de maintenir plusieurs versions de la même procédure :

- [Paquets orphelins et dépendances de compilation](B-logiciels.md#suppression-paquets).
- [Profils TuneD et sélection SCX](H-energie.md#tuned-scx), ainsi que [le choix ADIOS](D-kernel-schedulers.md#adios) : les modifications sous `/usr/lib` peuvent être remplacées.
- [Traductions à ne pas réextraire avec pacman](G-optimisations-systeme.md#locales).
- [Extensions GNOME](J-gnome.md#extensions) : vérifier leur compatibilité après changement de version.
- [Extensions Nautilus modifiées](J-gnome.md#scripts-nautilus) et [traduction du bouton énergétique](J-gnome.md#libelle-energie) : revoir les fichiers modifiés sous `/usr/share`.
- [Reconstruction de l’initramfs](C-boot-systemd.md#initramfs) avec `limine-mkinitcpio` après changement des hooks, modules ou paramètres de démarrage.
- [Restauration des snapshots](E-btrfs-snapshots.md#snapshots-limine) avec l’outil adapté à Limine.

[Accueil](README.md) · [Précédent](K-vivaldi.md)
