# 6 — Réseau

[Accueil](../README.md) · [Précédent](05-performance-tuning.md) · [Suivant](07-gnome-ui.md)

> **Dans ce chapitre :** pare-feu UFW, réglages Wi-Fi et TCP Fast Open, iwd et désactivation de la géolocalisation Wi-Fi.

- [6.1 Configurer UFW pour Fragments et Nicotine](#61--configurer-ufw-pour-fragments-et-nicotine)
- [6.2 Régler le Wi-Fi et TCP Fast Open](#62--régler-le-wi-fi-et-tcp-fast-open)
- [6.3 iwd pour remplacer wpa_supplicant](#63--iwd-pour-remplacer-wpa_supplicant)
- [6.4 Désactiver la géolocalisation par Wi-Fi dans GeoClue](#64--désactiver-la-géolocalisation-par-wi-fi-dans-geoclue)

## 6.1 — Configurer UFW pour Fragments et Nicotine


```
sudo ufw --force reset

sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw logging low

sudo ufw allow 51413/tcp comment 'Fragments TCP'
sudo ufw allow 51413/udp comment 'Fragments UDP'

sudo ufw allow 2234:2235/tcp comment 'Nicotine TCP'
sudo ufw allow 2234:2235/udp comment 'Nicotine UDP'

sudo ufw --force enable
sudo ufw status numbered
```

Dans Nicotine : sélectionner `wlan0` et le port 2234.

Régler Nicotine et Fragments pour qu'ils utilisent les ports correspondants à UFW — 🔗 voir aussi leur configuration applicative dans [Logiciels](10-logiciels.md#104--téléchargement--grabber-et-fragments).

## 6.2 — Régler le Wi-Fi et TCP Fast Open

### Domaine réglementaire Wi-Fi

Fixer le pays manuellement :

```fish
sudo systemctl mask cachyos-iw-set-regdomain.service cachyos-iw-set-regdomain.path
sudoedit /etc/conf.d/wireless-regdom
```

Décommenter :

```bash
WIRELESS_REGDOM="FR"
```
Supprimer le service systemd regdomain CachyOS :

```fish
sudo systemctl mask cachyos-iw-set-regdomain.service
```


### TCP Fast Open

Créer le réglage client et serveur, avec une commande compatible Fish :

```fish
printf '%s\\n' '# TCP Fast Open : client + serveur' 'net.ipv4.tcp_fastopen = 3' | sudo tee /etc/sysctl.d/99-tcp-fastopen.conf
sudo sysctl --system
sysctl net.ipv4.tcp_fastopen
```

Une piste d'adresse IPv4 fixe pour le profil Wi-Fi 5 GHz, non encore appliquée, est documentée dans les [archives](archives.md#adresse-fixe--piste-à-envisager).

## 6.3 — iwd pour remplacer wpa_supplicant

Installer iwd avec puis créer le fichier de configuration :

```fish
sudo pacman -S iwd
sudo mkdir -p /etc/NetworkManager/conf.d
sudoedit /etc/NetworkManager/conf.d/20-wifi-backend-iwd.conf
```

```ini
[device]
wifi.backend=iwd
```

Basculer les services, puis relancer NetworkManager :

```fish
sudo systemctl enable --now iwd.service
sudo systemctl mask --now wpa_supplicant.service
sudo systemctl restart NetworkManager
```

Vérifiez que la bascule est effective avec ces deux commandes :

```fish
systemctl is-active iwd && systemctl is-active wpa_supplicant && nmcli device show | grep -E "(DEVICE|TYPE|WIRED-PROPERTIES)" -A 10
```

S'assurer que le pilote Wi-Fi est bien en powersave automatique (`disable_aspm= N`) :

```fish
systool -vm mt7921e
```

## 6.4 — Désactiver la géolocalisation par Wi-Fi dans GeoClue

Cette procédure permet de bloquer le scan des réseaux Wi-Fi environnants par le service **GeoClue** tout en conservant la géolocalisation par adresse IP.

### Désactiver la source Wi-Fi

Créer le fichier de configuration :

\`\`\`fish
echo -e "[wifi]\nenable=false" | sudo tee /etc/geoclue/conf.d/90-disable-wifi.conf > /dev/null
\`\`\`

### Exclure Avahi de GeoClue

Pour conserver GeoClue (notamment pour les fonctions GNOME qui s'appuient sur la localisation) sans activer sa source \`network-nmea\`, modifier le fichier principal :

\`\`\`fish
sudo gnome-text-editor /etc/geoclue/geoclue.conf
\`\`\`

Dans la section **[network-nmea] uniquement**, remplacer \`enable=true\` par :

\`\`\`ini
[network-nmea]
enable=false
\`\`\`

Ne pas modifier les paramètres \`enable\` des autres sections.

> Une mise à jour du paquet \`geoclue\` peut remplacer \`/etc/geoclue/geoclue.conf\` (ou créer un \`.pacnew\`) et défaire ce réglage. Pour qu'il survive aux mises à jour, on peut mettre la même chose dans le fichier du dossier \`conf.d\` :
>
> \`\`\`fish
> printf '[network-nmea]\nenable=false\n' | sudo tee -a /etc/geoclue/conf.d/90-disable-wifi.conf > /dev/null
> \`\`\`

Réinitialiser un éventuel état d'échec, puis redémarrer GeoClue :

\`\`\`fish
sudo systemctl reset-failed geoclue.service
sudo systemctl restart geoclue.service
\`\`\`

### Tester si GeoClue démarre correctement

À faire **avant** le test de position : sur certaines installations (constaté avec \`glib2 2.90.1\` et \`linux-cachyos 7.2.9-2\`), GeoClue se fige à l'initialisation du moniteur réseau de GLib et systemd le tue après 15 s. Le test de position ne renvoie alors rien.

1. Regarder l'état du service :
   \`\`\`fish
   systemctl status geoclue --no-pager
   \`\`\`
   - **Sain** : \`Active: active (running)\`.
   - **Bug présent** : \`Active: failed (Result: timeout)\`, et \`journalctl -b -u geoclue --no-pager\` contient \`start operation timed out. Terminating.\`

2. Pour confirmer, lancer GeoClue à la main avec les messages de debug (arrêter avec Ctrl+C après une vingtaine de secondes) :
   \`\`\`fish
   sudo systemctl reset-failed geoclue.service
   sudo -u geoclue env G_MESSAGES_DEBUG=all /usr/lib/geoclue
   \`\`\`
   - **Bug présent** : la sortie s'arrête sur la ligne \`Found default implementation networkmanager (GNetworkMonitorNM) for 'gio-network-monitor'\`, sans rien après.
   - **Sain** : les lignes continuent, notamment \`Static source monitoring '/etc/geolocation'\` puis plusieurs \`lookup_by_name_with_flags_async: starting new lookup for api.beacondb.net\`. Ces lignes montrent que la recherche de l'adresse IP est bien lancée, puis \`Network changed: Refreshing\`.

#### Correction : forcer le moniteur réseau simple de GLib

Un fichier d'ajout (« drop-in ») systemd règle le problème sans toucher au fichier du paquet, donc il survit aux mises à jour :

\`\`\`fish
sudo mkdir -p /etc/systemd/system/geoclue.service.d
printf '[Service]\nEnvironment=GIO_USE_NETWORK_MONITOR=base\n' | sudo tee /etc/systemd/system/geoclue.service.d/10-network-monitor.conf
sudo systemctl daemon-reload
sudo systemctl restart geoclue.service
systemctl status geoclue --no-pager
\`\`\`

Le statut doit passer à \`active (running)\`. Les valeurs \`netlink\` et \`networkmanager\` bloquent de la même façon ; seule \`base\` a fonctionné. Contrepartie : ce moniteur ne suit pas les changements de réseau, ce qui est sans conséquence avec la seule localisation par IP.

Pour annuler :

\`\`\`fish
sudo rm /etc/systemd/system/geoclue.service.d/10-network-monitor.conf
sudo systemctl daemon-reload
\`\`\`

### Vérifier le bon fonctionnement

1. Dans un premier onglet Fish, lancez l'agent de sécurité :
   \`\`\`fish
   /usr/lib/geoclue-2.0/demos/agent
   \`\`\`
2. Dans un second onglet Fish, demandez votre position actuelle :
   \`\`\`fish
   /usr/lib/geoclue-2.0/demos/where-am-i
   \`\`\`

Résultat attendu :

- **Description** : \`GeoIP (ichnaea)\`
- **Accuracy** : \`25000 meters\`

> La position renvoyée est celle du fournisseur d'accès, parfois à plusieurs centaines de kilomètres de l'utilisateur. C'est normal avec la géolocalisation par IP.

---

[Accueil](../README.md) · [Précédent](05-performance-tuning.md) · [Suivant](07-gnome-ui.md)
