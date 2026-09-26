# 5 — Optimisations & performance

[Accueil](../README.md) · [Précédent](04-filesystems-storage.md) · [Suivant](06-network.md)

> **Dans ce chapitre :** coordination TuneD/SCX, Ananicy-cpp, ADIOS, split lock et compilation optimisée znver4.

> ⚠️ **Avertissement** : certaines optimisations de ce chapitre réduisent la stabilité ou la sécurité par défaut du système (modification de fichiers de paquets sous `/usr/lib`, désactivation de mitigations noyau comme le split lock, etc.).

- [5.1 Coordonner TuneD, les profils énergétiques et SCX](#51--coordonner-tuned-les-profils-énergétiques-et-scx)
- [5.2 Installer et gérer SCX Manager](#52--installer-et-gérer-scx-manager)
- [5.3 Ananicy-cpp : installation depuis les sources et dépannage](#53--ananicy-cpp--installation-depuis-les-sources-et-dépannage)
- [5.4 Désactiver le Split Lock](#54--désactiver-le-split-lock)
- [5.5 Sélectionner ADIOS avec udev et TuneD](#55--sélectionner-adios-avec-udev-et-tuned)
- [5.6 Configurer makepkg pour znver4](#56--configurer-makepkg-pour-znver4)

## 5.1 — Coordonner TuneD, les profils énergétiques et SCX

### Installer TuneD et son interface PPD

Remplacer power-profiles-daemon par les paquets TuneD CachyOS :

```fish
sudo pacman -Syu tuned-cachy tuned-cachy-ppd
```

Redémarrer après installation :

```fish
systemctl reboot
```

### Associer les profils aux schedulers

Modifier directement les profils installés sous `/usr/lib/tuned/profiles`. Elle est conservée ici : **les mises à jour peuvent remplacer ces modifications**. Des profils locaux sous `/etc/tuned` constitueraient une meilleure option.

Ouvrir les profils, en vérifiant d'abord leurs noms sur la version installée :

```fish
ls /usr/lib/tuned/profiles
sudoedit /usr/lib/tuned/profiles/cachyos-gaming/tuned.conf
sudoedit /usr/lib/tuned/profiles/cachyos-desktop/tuned.conf
sudoedit /usr/lib/tuned/profiles/cachyos-balanced-battery/tuned.conf
sudoedit /usr/lib/tuned/profiles/cachyos-powersave/tuned.conf
```

Dans **cachyos-gaming**, ajouter ou décommenter :

```ini
[scx]
scheduler=scx_lavd
mode=gaming
```

Dans **cachyos-desktop** :

```ini
[scx]
scheduler=scx_pandemonium
# mode=auto
```

Dans **cachyos-balanced-battery** :

```ini
[scx]
scheduler=scx_pandemonium
# mode=auto
```

Dans **cachyos-powersave** :

```ini
[scx]
scheduler=scx_cosmos
mode=powersave
```


Changer de profil avec le bouton GNOME, puis vérifier :

```fish
scxctl get
```

Ou utiliser la fonction personnelle du fichier Fish :

```fish
scx
```

Une alternative consistant à utiliser LAVD en mode automatique avec `--autopower` pour son adaptation énergétique ou à désactiver SCX et repasser sur EEVDF est documentée dans les archives : [LAVD automatique](archives.md#utiliser-lavd-en-mode-automatique) et [EEVDF sans SCX](archives.md#utiliser-eevdf-sans-scx-alternative-non-retenue).

Les rôles sont distincts : l'extension GNOME peut changer le profil selon secteur/batterie, TuneD applique le profil et son EPP, puis le plugin SCX choisit le scheduler.


## 5.2 — Installer et gérer SCX Manager

Installer SCX Manager Libadwaita (paquet Arch créé par ChatGPT & Claude) afin de supprimer complètement sched-ext et les paquets Qt devenus inutiles. Le readme du projet donne la marche à suivre.

### Changer l'icône et le chemin d'exécution dans le menu

- Icône : `/home/ogu/.local/Icones/Apps/mixxx.svg`
- Chemin de l'exécutable : `scx-manager-adwaita`

### Supprimer l'ancien gestionnaire Qt, les outils CachyOS, les dépendances Qt et les dépendances de build éventuelles

```fish
sudo pacman -Rns scx-manager kernel-manager qt6-base qt6-translations qt6-svg meson ninja
```

Pour désinstaller scx-manager :

```fish
sudo pacman -R scx-manager-adwaita
```

## 5.3 — Ananicy-cpp : installation depuis les sources et dépannage

Installation depuis les sources à la suite d'une erreur rencontrée avec l'installation native. 
Installer les outils puis nettoyer l'ancienne installation :

```fish
# de build
sudo pacman -Syu --noconfirm base-devel cmake nlohmann-json spdlog fmt gcc make git

# de l'installation précédente, au cas où
sudo systemctl stop ananicy-cpp || true
sudo rm -f /usr/local/bin/ananicy-cpp /usr/local/lib/systemd/system/ananicy-cpp.service
sudo rm -rf /usr/local/share/ananicy-cpp /etc/ananicy-cpp.conf /etc/ananicy.d /var/lib/ananicy-cpp
sudo systemctl daemon-reload
rm -rf ~/ananicy-cpp
```

Cloner le projet et compiler :

```fish
cd ~
git clone https://gitlab.com/ananicy-cpp/ananicy-cpp.git
cd ananicy-cpp
mkdir -p build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/local -DUSE_EXTERNAL_SPDLOG=ON -DUSE_EXTERNAL_JSON=ON -DUSE_EXTERNAL_FMTLIB=ON
make -j$(nproc)
sudo make install

# du service
sudo systemctl daemon-reload
sudo systemctl enable --now ananicy-cpp
```

Redémarrer à cette étape, puis reprendre les commandes suivantes dans un nouveau terminal :

```fish
systemctl reboot
```

```fish
# des règles
sudo pacman -S --noconfirm cachyos-ananicy-rules
sudo systemctl restart ananicy-cpp
sudo systemctl daemon-reload

# des paquets de build inutiles ; conservation des paquets nécessaires aux mises à jour d'Ananicy
sudo pacman -Rns cmake cppdap rhash --noconfirm
```

Redémarrer à cette étape, puis reprendre les commandes suivantes dans un nouveau terminal :

```fish
systemctl reboot
```

```fish
# du service une fois les règles installées
sudo systemctl daemon-reload
sudo systemctl restart ananicy-cpp # Pas de problème au lancement ?

# du service
sudo systemctl status ananicy-cpp
journalctl -u ananicy-cpp -f # Mention des 1 800 règles ? Pas de problème avec cgroup ?
```

Quitter le suivi du journal avec **Ctrl+C** avant de poursuivre. Le remplacement du lien ci-dessous n'est envisagé que pour le message **Cgroups are not available on this platform (or are not enabled)**, après vérification de `/etc/mtab` :

```fish
ls -l /etc/mtab
```

```fish
# de dépannage conditionnelle du mémo
sudo ln -sf /proc/self/mounts /etc/mtab
sudo systemctl restart ananicy-cpp

# du fonctionnement avec Vivaldi
ps -eo pid,ni,policy,cls,pri,comm | grep vivaldi
# version complète :
ps -eo pid,ni,cgroup:50,comm | grep vivaldi

# cas d'échec, contrôler les règles installées et les journaux avant de relancer le service
```

Les commandes de nettoyage de l'installation Ananicy suppriment les anciens fichiers et règles aux chemins indiqués. 


## 5.4 — Désactiver le Split Lock

```fish
sudoedit /etc/sysctl.d/99-splitlock.conf
```

```ini
kernel.split_lock_mitigate=0
```

Puis recharger :

```fish
sudo sysctl --system
```

## 5.5 — Sélectionner ADIOS avec udev et TuneD

En lieu et place de Kyber, créer ou éditer la règle udev :

```fish
sudoedit /etc/udev/rules.d/99-adios.rules
```

Y saisir :

```udev
# HDD
ACTION=="add|change", KERNEL=="sd[a-z]*", ATTR{queue/rotational}=="1", \
    ATTR{queue/scheduler}="bfq"

# SSD
ACTION=="add|change", KERNEL=="sd[a-z]*|mmcblk[0-9]*", ATTR{queue/rotational}=="0", \
    ATTR{queue/scheduler}="adios"

# SSD
ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{queue/rotational}=="0", \
    ATTR{queue/scheduler}="adios"
```

Recharger les règles et déclencher leur application :

```fish
sudo udevadm control --reload-rules
sudo udevadm trigger
```

TuneD peut rétablir Kyber après l'application de la règle udev. Il faut donc également aligner son profil :

```fish
sudoedit /usr/lib/tuned/profiles/cachyos-common/tuned.conf
```

Dans la section disque concernée, régler :

```ini
elevator=adios
```

!! Vérifier le réglage après une mise à jour de TuneD.

Contrôler les ordonnanceurs proposés et celui entre crochets, actuellement actif :

```fish
cat /sys/block/nvme0n1/queue/scheduler
```


## 5.6 — Configurer makepkg pour znver4

Éditer la configuration de makepkg :

```fish
sudoedit /etc/makepkg.conf
```

Dans `CFLAGS` :

```
CFLAGS="-march=znver4 -mtune=znver4 -pipe -fno-plt -fexceptions \
        -Wp,-D_FORTIFY_SOURCE=3 -Wformat -Werror=format-security \
        -fstack-clash-protection -fcf-protection"
```

---

[Accueil](../README.md) · [Précédent](04-filesystems-storage.md) · [Suivant](06-network.md)
