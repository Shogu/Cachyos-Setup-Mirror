# F — Réseau

[Accueil](README.md) · [Précédent](E-btrfs-snapshots.md) · [Suivant](G-optimisations-systeme.md)

- [Configurer UFW pour Fragments et Nicotine](#f1--configurer-ufw-pour-fragments-et-nicotine)
- [Régler le Wi-Fi et TCP Fast Open](#f2--régler-le-wi-fi-et-tcp-fast-open)
- [iwd pour remplacer wpa_supplicant](#f3--iwd-pour-remplacer-wpa_supplicant)
- [Désactiver la géolocalisation par Wi-Fi dans GeoClue](#f4--désactiver-la-géolocalisation-par-wi-fi-dans-GeoClue)

## F1 — Configurer UFW pour Fragments et Nicotine

La réinitialisation ci-dessous efface les règles UFW existantes. La plage Nicotine `2234:2235` en TCP et UDP est celle du README ; elle est conservée ici, sans prétendre que tous ces ports soient nécessaires. Le port d’écoute actuellement indiqué par l’utilisateur est **2234** ; `server.slsknet.org:2242` est la destination serveur et ne nécessite pas une ouverture entrante supplémentaire avec cette politique sortante.

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
Sur cette installation, le mémo rapporte une connexion Nicotine plus rapide en sélectionnant explicitement `wlan0`. Vérifier que c’est bien le nom de l’interface ; ce résultat n’est pas généralisé à toutes les machines.

Régler Nicotine et Fragments pour qu’ils utilisent les ports correspondants à UFW.

## F2 — Régler le Wi-Fi et TCP Fast Open

### Domaine réglementaire Wi-Fi

Fixer le pays manuellement:

```fish
sudo systemctl mask cachyos-iw-set-regdomain.service cachyos-iw-set-regdomain.path
sudoedit /etc/conf.d/wireless-regdom
```

Décommenter :

```bash
WIRELESS_REGDOM="FR"
```

### TCP Fast Open

Créer le réglage client et serveur, avec une commande compatible Fish :

```fish
printf '%s\n' '# TCP Fast Open : client + serveur' 'net.ipv4.tcp_fastopen = 3' | sudo tee /etc/sysctl.d/99-tcp-fastopen.conf
sudo sysctl --system
sysctl net.ipv4.tcp_fastopen
```

### Adresse fixe : piste à envisager

Dans le profil NetworkManager de la connexion Wi-Fi 5 GHz, le mémo propose :

| Champ | Valeur personnelle |
|---|---|
| IPv4 | `192.168.31.102` |
| Masque | `255.255.255.0` (`/24`) |
| Passerelle | `192.168.31.1` |
| DNS | `1.1.1.1`, `1.0.0.1` |
| IPv6 | Désactivé dans cette variante |

Adapter ces valeurs au réseau et vérifier que l’adresse n’est pas attribuée à un autre appareil.


## F3 — iwd pour remplacer wpa_supplicant

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

S'assurer que le pilote WI-Fi est bien en powersave automatique (`disable_aspm= N`):

```fish
systool -vm mt7921e
```

## F4 — Désactiver la géolocalisation par Wi-Fi dans GeoClue

Cette procédure permet de bloquer le scan des réseaux Wi-Fi environnants par le service **GeoClue** tout en conservant la géolocalisation par adresse IP.

Créer le fichier de configuration:

```fish
echo -e "[wifi]\nenable=false" | sudo tee /etc/geoclue/conf.d/90-disable-wifi.conf > /dev/null
```

Redémarrer le service GeoClue

```fish
sudo systemctl restart geoclue
```

Vérifier le bon fonctionnement


1. Dans un premier onglet Fish, lancez l'agent de sécurité :
   ```fish
   /usr/lib/geoclue-2.0/demos/agent
   ```
2. Dans un second onglet Fish, demandez votre position actuelle :
   ```fish
   /usr/lib/geoclue-2.0/demos/where-am-i
   ```

Résultat attendu
* **Description** : `GeoIP (ichnaea)`
* **Accuracy** : `25000 meters` 


[Accueil](README.md) · [Précédent](E-btrfs-snapshots.md) · [Suivant](G-optimisations-systeme.md)
