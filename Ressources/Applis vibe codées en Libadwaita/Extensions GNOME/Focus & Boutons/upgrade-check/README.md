# upgrade-check 1.1.0

Recherche les mises à jour Pacman pour la pilule **Mises à jour** de l’extension GNOME Shell **Focus & Boutons** (v36 et suivantes).

`upgrade-check` n’a pas d’interface graphique : il interroge les dépôts et réagit aux transactions Pacman. Focus & Boutons décide quand vérifier et affiche les résultats. Les deux composants sont nécessaires à la pilule.

Le paquet `upgrade-check-1.1.0-1-any.pkg.tar.zst` présent dans ce dossier est bien le paquet correspondant à la version documentée **1.1.0**. Il n’y a pas de paquet distinct à prévoir pour cette version : les mentions précédentes de `1.1.0-2` étaient une erreur de documentation.

## Répartition des rôles

| Fonction | Paquet système `upgrade-check` | Extension Focus & Boutons |
|---|---|---|
| Interroger les dépôts | `checkupdates` via `upgrade-check.service` | — |
| Écrire la liste des mises à jour | `~/.cache/upgrade-check/updates.txt` | — |
| Signaler une transaction Pacman | Hook → `/var/lib/upgrade-check/last-transaction` | — |
| Planifier les contrôles | — | Intervalle réglable (12 h par défaut), après transaction et au démarrage si le résultat est périmé |
| Lancer une vérification | Service utilisateur systemd | Appel `StartUnit` via D-Bus |
| Afficher le résultat | — | Pilule Quick Settings : nombre, liste et heure du dernier contrôle |
| Lancer la mise à jour | — | Clic sur la pilule : script choisi dans les préférences |

L’extension ne lance aucune commande de vérification dans GNOME Shell : elle lit un fichier, surveille les dossiers prévus et démarre le service systemd utilisateur par D-Bus. Le script de mise à jour n’est exécuté que lorsque l’utilisateur clique sur la pilule.

## Fonctionnement

1. **Vérification des dépôts.** Le programme lance `checkupdates` (fourni par `pacman-contrib`), qui utilise une base temporaire et ne modifie pas la base Pacman du système. La sortie est écrite atomiquement dans `~/.cache/upgrade-check/updates.txt`, une ligne par paquet (`nom ancienne -> nouvelle`). Un fichier vide signifie qu’aucune mise à jour officielle n’est disponible. En cas d’échec, par exemple sans réseau, l’ancien résultat est conservé.
2. **Après une transaction.** Le hook Pacman met à jour `/var/lib/upgrade-check/last-transaction` après une installation, mise à jour ou suppression, y compris les transactions lancées par Shelly. Focus & Boutons attend 30 secondes puis relance une vérification.
3. **À l’ouverture de session.** Si `updates.txt` est plus ancien que la dernière transaction, l’extension le considère périmé et demande un nouveau contrôle après une minute. Sinon, elle reprend son intervalle habituel.
4. **En cas d’échec.** Le contrôle est retenté 30 minutes plus tard.

Seules les mises à jour des **dépôts officiels** sont comptées. Les paquets AUR restent gérés par Shelly.

## Fichiers installés par le paquet

| Chemin | Rôle |
|---|---|
| `/usr/lib/upgrade-check/upgrade-check` | Programme de vérification |
| `/usr/lib/systemd/user/upgrade-check.service` | Service utilisateur ponctuel |
| `/usr/share/libalpm/hooks/upgrade-check.hook` | Hook Pacman de fin de transaction |
| `/var/lib/upgrade-check/` | Dossier du témoin `last-transaction` |

Dépendances : `pacman-contrib` et `systemd`.

## Installation

Depuis ce dossier, le paquet actuellement présent s’installe ainsi :

```bash
sudo pacman -U ./upgrade-check-1.1.0-1-any.pkg.tar.zst
```

Installer ensuite l’archive correspondante de Focus & Boutons (**v36 ou ultérieure**), puis se déconnecter et se reconnecter. Dans les préférences de l’extension, section **Quick Settings**, activer **Pilule Mises à jour**, régler l’intervalle de vérification et sélectionner le script de mise à jour. Choisir le chemin réel du lanceur Shelly installé sur la machine.

Le script versionné dans `Ressources/Scripts/upgrade.sh` déclenche également le service à la fin des mises à jour :

```bash
systemctl --user start --no-block upgrade-check.service
```

## Vérification

```bash
systemctl --user start upgrade-check.service
journalctl --user -u upgrade-check.service --no-pager -n 20
cat ~/.cache/upgrade-check/updates.txt
```

La pilule doit refléter le résultat rapidement. Pour vérifier le hook, réinstaller le paquet crée une transaction Pacman :

```bash
sudo pacman -S upgrade-check
grep upgrade-check /var/log/pacman.log | tail -3
ls -l /var/lib/upgrade-check/
```

Pacman doit signaler la fin de transaction ; Focus & Boutons indique alors la mise à jour en cours puis rafraîchit la pilule après environ 30 secondes.

## Historique

- **1.1.0** : retrait du minuteur systemd périodique ; Focus & Boutons planifie les contrôles avec un intervalle réglable. La mise à jour du paquet désactive l’ancien minuteur ; dans la session en cours, l’arrêter si nécessaire avec `systemctl --user stop upgrade-check.timer`.
- **1.0.0** : première version avec service, minuteur et hook Pacman.
