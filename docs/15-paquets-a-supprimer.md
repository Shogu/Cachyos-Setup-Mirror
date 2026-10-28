# Paquets supprimables — audit Z.ai

[Accueil](../README.md) · [Allégement système](02-system-cleanup.md)

Cette liste complète le chapitre **[2 — Allégement système](02-system-cleanup.md)**. Elle repose sur l'analyse communiquée par Z.ai du système et du dépôt ; elle ne remplace pas une simulation sur le système au moment de la désinstallation.

## 1. Candidats à la suppression

Ces paquets semblent inutiles pour la configuration documentée : Btrfs sans LVM, démarrage Limine, pas de VPN L2TP ni de serveur DNS local configuré, et utilisation de `cachyos-rate-mirrors`.

```bash
sudo pacman -Rns jfsutils nilfs-utils lvm2 bind dnssec-anchors dnsmasq s-nail inetutils efitools os-prober xl2tpd reflector
```

La commande vise **12 paquets explicitement nommés**. Selon la simulation réalisée lors de l'audit, cinq dépendances supplémentaires pouvaient aussi être retirées parce qu'elles n'étaient plus nécessaires : `ppp`, `thin-provisioning-tools`, `libaio`, `liburcu` et `libmaxminddb`. Vérifier la transaction proposée par Pacman avant de confirmer.

| Paquet | Motif |
|---|---|
| `jfsutils`, `nilfs-utils` | Outils pour JFS et NILFS, systèmes de fichiers non utilisés dans le setup documenté. |
| `lvm2` | Gestion des volumes logiques, non utilisée sur l'installation Btrfs décrite. |
| `bind`, `dnssec-anchors` | Outils DNS, notamment `dig` et `delv`, sans usage documenté. |
| `dnsmasq` | Principalement utile au partage de connexion/hotspot NetworkManager. |
| `s-nail` | Client mail en ligne de commande ; à garder si des alertes locales par courriel sont utilisées. |
| `inetutils` | Fournit divers outils réseau, dont `hostname`. `hostnamectl` peut remplacer certaines opérations, mais pas forcément tous les usages de ces outils. |
| `efitools` | Outils Secure Boot/EFI, non nécessaires au démarrage Limine documenté si aucune gestion Secure Boot n'est requise. |
| `os-prober` | Détection d'autres systèmes pour les menus de démarrage ; inutile si l'on n'en a pas besoin avec Limine. |
| `xl2tpd` | Client/serveur L2TP, sans usage VPN L2TP documenté. |
| `reflector` | Doublon fonctionnel si `cachyos-rate-mirrors` est bien l'outil conservé pour les miroirs. |

## 2. À supprimer seulement si la fonction n'est pas utilisée

- **`fuse2`** — environ 0,5 Mio selon l'audit. Le conserver tant qu'une AppImage utilisée en dépend. Pour l'AppImage de LeLivreScolaire, ne le supprimer qu'après adaptation à FUSE 3 et test concluant du lancement.
- **`libopenraw`** — environ 3,1 Mio. À conserver pour les aperçus et la prise en charge des photos RAW dans Nautilus ou les applications concernées.
- **`nlohmann-json`** — environ 1 Mio. En-têtes C++ utiles si l'on compile des applications qui en dépendent.
- **`lua-luv`** — petite bibliothèque Lua, à garder si une configuration ou application Lua l'utilise.
- **`inotify-tools`** — à conserver tant que le script/service de synchronisation des snapshots Limine/Snapper peut en avoir besoin.

## 3. Ne pas supprimer manuellement : dépendances utilisées

L'audit a signalé plusieurs paquets apparemment superflus qui sont en fait requis par d'autres éléments installés. Ne pas forcer leur suppression avec `-Rdd` :

- **`wpa_supplicant`** : dépendance de NetworkManager, même si son service est masqué et que le système utilise iwd.
- **`smbclient` et `cifs-utils`** : dépendances signalées dans la chaîne de GNOME Control Center ; vérifier à nouveau les dépendances si cette chaîne évolue.
- **`transmission-cli`** : requis par Fragments selon l'audit.
- **`js140`** : requis par GJS/GNOME Shell.
- **`guile`** : utilisé par des outils de développement installés, notamment dans la chaîne make/gdb selon l'audit.
- **`jack2`, `sndio`, `vapoursynth`, `portaudio`, `sdl3`, `aalib`, `gpm`, `libnewt`, `mdadm`, `bolt`, `iio-sensor-proxy`, `cryptsetup`, `avahi` et les composants multimédias associés : des dépendances inverses ont été identifiées. Ne pas les retirer sur la seule base de leur nom ou de l'absence d'utilisation directe.

Les chaînes de dépendances peuvent changer avec les mises à jour. Pour contrôler un paquet avant de le retirer :

```bash
pacman -Qi nom-du-paquet
pactree -r nom-du-paquet
```

## 4. Option d'allègement importante : outils de développement

Le dépôt prévoit déjà de retirer temporairement les outils de compilation entre deux périodes de développement. C'est le levier qui peut libérer le plus d'espace, mais il est **inadapté si l'on compile régulièrement les applications maison ou des paquets AUR**.

Avant toute suppression, relire la liste et la procédure de la section **« Développement et compilation »** du [chapitre 2](02-system-cleanup.md). Réinstaller les outils nécessaires avant la prochaine compilation. Ne pas retirer à l'aveugle les en-têtes du noyau si des modules externes doivent être compilés.

## 5. Contrôle avant et après

Afficher les orphelins actuels :

```bash
pacman -Qdt
```

Simuler la transaction avant de confirmer la suppression :

```bash
sudo pacman -Rns --print jfsutils nilfs-utils lvm2 bind dnssec-anchors dnsmasq s-nail inetutils efitools os-prober xl2tpd reflector
```

Après la désinstallation, vérifier les orphelins et les fonctions essentielles (réseau, GNOME, audio, montage de fichiers et démarrage) :

```bash
pacman -Qdt
systemctl --failed
```

**Règle :** lire la liste complète de suppression affichée par Pacman. Annuler avec `n` si elle inclut un composant dont le rôle n'est pas clair.
