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

Régler Nicotine et Fragments pour qu'ils utilisent les ports correspondants à UFW — 🔗 voir aussi leur configuration applicative dans [Logiciels](#105--téléchargement--grabber-et-fragments).

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
printf '%s\n' '# TCP Fast Open : client + serveur' 'net.ipv4.tcp_fastopen = 3' | sudo tee /etc/sysctl.d/99-tcp-fastopen.conf
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

Créer le fichier de configuration :

```fish
echo -e "[wifi]\nenable=false" | sudo tee /etc/geoclue/conf.d/90-disable-wifi.conf > /dev/null
```

Redémarrer le service GeoClue :

```fish
sudo systemctl restart geoclue
```

Vérifier le bon fonctionnement :

1. Dans un premier onglet Fish, lancez l'agent de sécurité :
   ```fish
   /usr/lib/geoclue-2.0/demos/agent
   ```
2. Dans un second onglet Fish, demandez votre position actuelle :
   ```fish
   /usr/lib/geoclue-2.0/demos/where-am-i
   ```

Résultat attendu :

- **Description** : `GeoIP (ichnaea)`
- **Accuracy** : `25000 meters`

---

[Accueil](../README.md) · [Précédent](05-performance-tuning.md) · [Suivant](07-gnome-ui.md)
