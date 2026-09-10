# F — Réseau

[Accueil](README.md) · [Précédent](E-btrfs-snapshots.md) · [Suivant](G-optimisations-systeme.md)

- [Configurer UFW pour Fragments et Nicotine](#f1--configurer-ufw-pour-fragments-et-nicotine)
- [Régler le Wi-Fi et TCP Fast Open](#f2--régler-le-wi-fi-et-tcp-fast-open)

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

Deux méthodes sont envisagées : garder le service `cachyos-iw-set-regdomain`, ou fixer le pays manuellement. Le mémo propose la seconde pour cette machine utilisée en France.

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

### Variante : iwd comme backend de NetworkManager

Le mémo signale une reconnexion lente après veille avec iwd. Cette variante reste donc un essai, pas un remplacement obligatoire de wpa_supplicant.

Installer iwd et créer le fichier de configuration :

```fish
sudo pacman -S iwd
sudo mkdir -p /etc/NetworkManager/conf.d
sudoedit /etc/NetworkManager/conf.d/20-wifi-backend.conf
```

```ini
[device]
wifi.backend=iwd
```

Basculer les services, puis relancer NetworkManager ; la connexion Wi-Fi sera interrompue pendant l’opération :

```fish
sudo systemctl enable --now iwd.service
sudo systemctl disable --now wpa_supplicant.service
sudo systemctl restart NetworkManager.service
```

Le mémo envisage ensuite `sudo pacman -Rdd wpa_supplicant` si tout fonctionne. Cette suppression forcée est distincte du choix de backend et ignore les dépendances : conserver le paquet pendant les essais facilite le retour arrière.

[Accueil](README.md) · [Précédent](E-btrfs-snapshots.md) · [Suivant](G-optimisations-systeme.md)
