# 14 — Maintenance

[Accueil](../README.md) · [Précédent](13-vivaldi.md) · [Suivant](archives.md)

> **Dans ce chapitre :** choix de l'outil de mise à jour et points à vérifier après chaque mise à jour du système.

- [14.1 Choisir Cachy-update ou Shelly](#141--choisir-cachy-update-ou-shelly)
- [14.2 Points à revoir après les mises à jour](#142--points-à-revoir-après-les-mises-à-jour)
- [14.3 Dépannage iwd](#143--dépannage-iwd)

## 14.1 — Choisir Cachy-update ou Shelly

### Option 1 : conserver Cachy-update

Générer puis ouvrir la configuration utilisateur :

```fish
arch-update --gen-config
arch-update --edit-config
```

Choisir `TrayIconStyle=light` et limiter le nombre de sauvegardes à **1**, au lieu de **3**, dans l'option correspondante du fichier. Modifier le lanceur avec Libre Menu si nécessaire.

### Option 2 : utiliser Shelly

Le mémo propose de supprimer Cachy-update et Paru lorsque Shelly couvre les mises à jour des dépôts et de l'AUR :

```fish
sudo pacman -Rns cachy-update paru
```

Cette option vient **après** les installations utilisant Paru dans les autres chapitres. Le gain d'espace dépend des dépendances effectivement retirées.

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

## 14.2 — Points à revoir après les mises à jour

Les opérations détaillées restent dans leur rubrique pour éviter de maintenir plusieurs versions de la même procédure :

- [Paquets orphelins et dépendances de compilation](02-system-cleanup.md#22--alléger-les-logiciels-installés).
- [Profils TuneD et sélection SCX](05-performance-tuning.md#51--coordonner-tuned-les-profils-énergétiques-et-scx), ainsi que [le choix ADIOS](05-performance-tuning.md#55--sélectionner-adios-avec-udev-et-tuned) : les modifications sous `/usr/lib` peuvent être remplacées.
- [Traductions à ne pas réextraire avec pacman](02-system-cleanup.md#28--nettoyer-les-traductions-et-les-fichiers-de-configuration).
- [Extensions GNOME](08-gnome-extensions.md) : vérifier leur compatibilité après changement de version.
- [Extensions Nautilus modifiées](09-nautilus-workflow.md#92--scripts-nautilus-et-extensions-copy-path-admin) et [traduction du bouton énergétique](07-gnome-ui.md#76--actions-de-session-rappels-et-libellé-du-profil-énergétique-menu-dalimentation) : revoir les fichiers modifiés sous `/usr/share`.
- [Reconstruction de l'initramfs](03-boot-kernel.md#33--réduire-linitramfs) avec `limine-mkinitcpio` après changement des hooks, modules ou paramètres de démarrage.
- [Restauration des snapshots](04-filesystems-storage.md#42--configurer-et-restaurer-les-snapshots-limine) avec l'outil adapté à Limine.


## 14.3 - Dépannage iwd


Symptôme : connexion qui échoue avec state change: config → failed (reason 'no-secrets')
Log associé : `GDBus.Error:net.connman.iwd.Failed: Operation failed`
Ou côté nmcli : `« Des secrets étaient requis, mais aucun n'a été fourni »`



1. Lister les profils et repérer les doublons :

```fish
nmcli connection show
```

NetworkManager crée un nouveau profil dupliqué (Xiaomi_03F1_5 1, Xiaomi_03F1_5 2...) à chaque reconnexion via l'interface graphique quand un profil du même nom existe déjà. Ces doublons n'ont souvent pas de mot de passe correctement enregistré.

2. Supprimer TOUS les profils liés au SSID concerné

```fish
nmcli connection delete Xiaomi_03F1_5 "Xiaomi_03F1_5 1" "Xiaomi_03F1_5 2"
```
(adapter la liste des noms selon ce que renvoie `nmcli connection show`)

3. Vérifier que le réseau est bien visible

```fish
nmcli device wifi rescan
nmcli device wifi list
```

4. Recréer le profil proprement, mot de passe fourni en CLI :

```fish
nmcli device wifi connect Xiaomi_03F1_5 password "MOT_DE_PASSE"
```

⚠️ Si un profil "Xiaomi_03F1_5" existe encore (même sans le voir dans la liste des réseaux), nmcli tente de le réactiver tel quel et ignore le mot de passe fourni. Toujours supprimer d'abord (étape 3).

5. Si l'erreur persiste malgré une recréation propre : iwd garde son propre stockage de réseaux, séparé des fichiers NetworkManager :


```fish
sudo ls -la /var/lib/iwd/
```

Si une entrée Xiaomi_03F1_5.psk corrompue/obsolète existe :

```fish
sudo rm "/var/lib/iwd/Xiaomi_03F1_5.psk"
sudo systemctl restart iwd NetworkManager
nmcli device wifi connect Xiaomi_03F1_5 password "MOT_DE_PASSE"
```


7. Reconnexion vi GNOME si le pop-up le propsoe, ou bien avec :

```fish
nmcli connection up Xiaomi_03F1_5
```

Toujours préférer connection up à une reconnexion via l'interface graphique pour éviter que NetworkManager ne recrée un doublon.
---

[Accueil](../README.md) · [Précédent](13-vivaldi.md) · [Suivant](archives.md)
