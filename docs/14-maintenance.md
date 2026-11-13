# 14 — Maintenance

[Accueil](../README.md) · [Précédent](13-vivaldi.md) · [Suivant](archives.md)

> **Dans ce chapitre :** tâches ponctuelles de maintenance, vérifications après mise à jour et dépannage réseau. Les réglages permanents sont documentés dans leur rubrique dédiée.

- [14.1 Retirer Cachy-update](#141--retirer-cachy-update)
- [14.2 Points à revoir après les mises à jour](#142--points-à-revoir-après-les-mises-à-jour)
- [14.3 Dépannage iwd](#143--dépannage-iwd)
- [14.4 Maintenir les applications GNOME maison](#144--maintenir-les-applications-gnome-maison)

## 14.1 — Retirer Cachy-update

Shelly est l'outil de mise à jour retenu pour ce setup. Pour supprimer Cachy-update, lancer :

```fish
sudo pacman -Rns cachy-update
```

Lire attentivement la liste des paquets proposés par Pacman avant de confirmer. Cette commande retire Cachy-update et les dépendances devenues inutiles ; elle ne désinstalle pas Paru.

La configuration de Shelly et son lanceur sont documentés dans [Shell & terminal](12-shell-terminal.md#123--shelly-et-le-lanceur-de-mise-à-jour). Le hook de protection de `/boot` est documenté dans [Boot & kernel](03-boot-kernel.md#37--protéger-les-transactions-noyau-si-boot-nest-pas-monté).

## 14.2 — Points à revoir après les mises à jour

Les procédures détaillées restent dans leur rubrique pour éviter de maintenir plusieurs versions des mêmes instructions :

- [Paquets orphelins et dépendances de compilation](02-system-cleanup.md#22--alléger-les-logiciels-installés).
- [Profils TuneD et sélection SCX](05-performance-tuning.md#51--coordonner-tuned-les-profils-énergétiques-et-scx), ainsi que [le choix ADIOS](05-performance-tuning.md#55--sélectionner-adios-avec-udev-et-tuned) : les modifications sous `/usr/lib` peuvent être remplacées.
- [Traductions à ne pas réextraire avec pacman](02-system-cleanup.md#28--nettoyer-les-traductions-et-les-fichiers-de-configuration).
- [Extensions GNOME](08-gnome-extensions.md) : vérifier leur compatibilité après changement de version.
- [Extensions Nautilus modifiées](09-nautilus-workflow.md#92--scripts-nautilus-et-extensions-copy-path-admin) et [traduction du bouton énergétique](07-gnome-ui.md#76--actions-de-session-rappels-et-libellé-du-profil-énergétique-menu-dalimentation) : revoir les fichiers modifiés sous `/usr/share`.
- [Reconstruction de l'initramfs](03-boot-kernel.md#33--réduire-linitramfs) avec `limine-mkinitcpio` après changement des hooks, modules ou paramètres de démarrage.
- [Restauration des snapshots](04-filesystems-storage.md#42--configurer-et-restaurer-les-snapshots-limine) avec l'outil adapté à Limine.

## 14.3 — Dépannage iwd

Symptôme : connexion qui échoue avec `state change: config → failed (reason 'no-secrets')`.

Log associé : `GDBus.Error:net.connman.iwd.Failed: Operation failed`.

Ou côté nmcli : « Des secrets étaient requis, mais aucun n'a été fourni ».

1. **Lister les profils et repérer les doublons :**

   ```fish
   nmcli connection show
   ```

   NetworkManager peut créer un nouveau profil dupliqué (`Xiaomi_03F1_5 1`, `Xiaomi_03F1_5 2`, etc.) à chaque reconnexion via l'interface graphique quand un profil du même nom existe déjà. Ces doublons n'ont souvent pas de mot de passe correctement enregistré.

2. **Supprimer les profils liés au SSID concerné.** Adapter la liste selon ce que renvoie `nmcli connection show` :

   ```fish
   nmcli connection delete Xiaomi_03F1_5 "Xiaomi_03F1_5 1" "Xiaomi_03F1_5 2"
   ```

3. **Vérifier que le réseau est visible :**

   ```fish
   nmcli device wifi rescan
   nmcli device wifi list
   ```

4. **Recréer le profil proprement, mot de passe fourni en CLI :**

   ```fish
   nmcli device wifi connect Xiaomi_03F1_5 password "MOT_DE_PASSE"
   ```

   Si un profil `Xiaomi_03F1_5` existe encore, même s'il n'apparaît pas dans la liste des réseaux, nmcli peut tenter de le réactiver tel quel et ignorer le mot de passe fourni. Supprimer d'abord les profils existants.

5. **Si l'erreur persiste, vérifier le stockage propre à iwd.** Il est distinct des fichiers NetworkManager :

   ```fish
   sudo ls -la /var/lib/iwd/
   ```

   Si une entrée `Xiaomi_03F1_5.psk` corrompue ou obsolète existe, la supprimer puis recréer la connexion :

   ```fish
   sudo rm "/var/lib/iwd/Xiaomi_03F1_5.psk"
   sudo systemctl restart iwd NetworkManager
   nmcli device wifi connect Xiaomi_03F1_5 password "MOT_DE_PASSE"
   ```

6. **Reconnecter le profil**, depuis GNOME si le dialogue le propose, ou en CLI :

   ```fish
   nmcli connection up Xiaomi_03F1_5
   ```

   Préférer `connection up` à une reconnexion via l'interface graphique pour éviter que NetworkManager ne crée un doublon.

## 14.4 — Maintenir les applications GNOME maison

*Applications GTK4/libadwaita en Python (et C pour Notepad) et extensions GNOME Shell, sous CachyOS/Arch.*

### 14.4.1 — Le calendrier à connaître

| Quoi | Rythme | Conséquence |
|---|---|---|
| GNOME | Deux versions par an, généralement en mars et septembre | Nouvelles versions de GTK 4 et libadwaita |
| GTK 4 / libadwaita 1 | Versions mineures au fil des cycles | Des API peuvent être dépréciées ; surveiller les notes de version |
| Python sur Arch | Environ une version majeure par an | Les modules installés dans un répertoire Python numéroté peuvent devenir invisibles |
| GNOME Shell | Deux versions par an | Les extensions peuvent nécessiter un portage |

Pour les applications GTK4/libadwaita, vérifier après chaque nouvelle version de GNOME est une bonne routine de base. Ce n'est pas une garantie d'absence de régression : consulter les notes de version si l'application utilise des API dépréciées.

### 14.4.2 — Ce qui peut arriver à une application GTK4/libadwaita

1. **Avertissements de dépréciation.** Le widget fonctionne encore, mais un remplaçant est recommandé.

   | Ancien | Remplaçant possible |
   |---|---|
   | `Gtk.TreeView` | `Gtk.ColumnView` / `Gtk.ListView` |
   | `Gtk.FileChooserDialog` | `Gtk.FileDialog` lorsque disponible dans la version ciblée |
   | `Gtk.Dialog`, `Adw.MessageDialog` | `Adw.Dialog`, `Adw.AlertDialog` selon le cas |
   | `Adw.Leaflet`, `Adw.Flap` | `Adw.NavigationSplitView`, `Adw.OverlaySplitView` selon le besoin |

   Ne pas migrer uniquement pour faire disparaître un avertissement : vérifier l'API de remplacement et les versions prises en charge.
2. **Changements visuels.** Une règle CSS personnalisée peut ne plus s'appliquer ou rendre différemment.
3. **Changements de comportement.** Le focus, les dimensions initiales ou les animations peuvent varier. Reproduire le problème et consulter les notes de version.

### 14.4.3 — Le piège des mises à jour de Python

Python cherche les modules dans un répertoire dépendant de sa version, par exemple :

`/usr/lib/python3.13/site-packages/`

Après une migration vers Python 3.14, ce répertoire n'est plus celui recherché par l'interpréteur 3.14. Une application qui y a installé son propre code peut échouer avec `ModuleNotFoundError`.

**Disposition préférable pour une application maison :** placer son code dans son propre répertoire et utiliser un lanceur minimal, par exemple :

- `/usr/lib/fret/fret.py` : code de l'application.
- `/usr/bin/fret` : lanceur contenant `exec python3 /usr/lib/fret/fret.py "$@"`.

Les dépendances Python fournies par Arch doivent être reconstruites ou mises à jour par le paquetage lorsque nécessaire.

#### Repérer les paquets maison liés à une version de Python

```fish
pacman -Qlm | grep -E ' /usr/lib/python3\.[0-9]+/' | cut -d' ' -f1 | sort -u
```

- **Aucune sortie :** aucun paquet local listé par cette commande n'a de fichier correspondant à ce chemin.
- **Des paquets apparaissent :** inspecter les fichiers concernés et envisager de les reconstruire ou de déplacer le code applicatif dans `/usr/lib/<application>/`.

Pour retrouver les paquets possédant des fichiers sous l'ancien répertoire Python, adapter la version à celle qui est remplacée :

```fish
pacman -Qoq /usr/lib/python3.13
```

Tout paquet retourné mérite une vérification et, si nécessaire, une reconstruction.

### 14.4.4 — Les applications compilées en C

Python ne concerne pas les applications compilées en C, comme Notepad. Elles dépendent des bibliothèques système. Si une bibliothèque partagée change d'ABI, le lancement peut échouer avec un message tel que :

`error while loading shared libraries: libxxx.so.N`

Il faut alors reconstruire le paquet contre les bibliothèques disponibles, après avoir identifié la dépendance concernée.

### 14.4.5 — Les extensions GNOME Shell

C'est généralement la partie qui demande le plus de suivi. Après une mise à jour majeure de GNOME Shell :

1. Vérifier les versions déclarées dans `metadata.json` et ajouter la nouvelle version de Shell uniquement après l'avoir testée.
2. Tester les fonctions de l'extension : l'ajout d'une version à `shell-version` ne garantit pas la compatibilité.
3. Consulter les guides de portage de [gjs.guide](https://gjs.guide/) et les notes de version de GNOME.

Pour suivre les erreurs du Shell en direct :

```fish
journalctl -f -o cat /usr/bin/gnome-shell
```

### 14.4.6 — Repérer les problèmes après une mise à jour

| Méthode | Commande |
|---|---|
| Lancer l'application depuis un terminal | Exemple : `fret`, puis lire les avertissements `Gtk-WARNING`, `Adwaita-WARNING` et `CRITICAL` |
| Afficher les avertissements Python | `python -W default /usr/lib/fret/fret.py` |
| Voir les versions installées | `pacman -Qi gtk4 libadwaita python` |
| Suivre l'évolution de GNOME | Consulter les notes de version de GNOME, GTK et libadwaita |

### 14.4.7 — Routine conseillée

**Deux fois par an, après chaque nouvelle version de GNOME :**

- [ ] Lancer chaque application depuis un terminal.
- [ ] Examiner les avertissements et reproduire les problèmes avant de modifier le code.
- [ ] Corriger le CSS personnalisé si nécessaire et planifier le remplacement des API dépréciées.
- [ ] Mettre à jour les extensions GNOME Shell et tester leurs fonctions.

**Lors d'un changement majeur de Python :**

- [ ] Exécuter `pacman -Qoq /usr/lib/python3.<ancienne-version>` en adaptant l'ancienne version.
- [ ] Inspecter les paquets retournés et reconstruire ceux qui en ont besoin.

**À chaque reconstruction d'un paquet maison :**

- [ ] Incrémenter au minimum `pkgrel` dans le PKGBUILD afin que le gestionnaire de paquets reconnaisse la nouvelle version.

---

[Accueil](../README.md) · [Précédent](13-vivaldi.md) · [Suivant](archives.md)
