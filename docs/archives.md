# Archives

[Accueil](../README.md) · [Précédent](14-maintenance.md)

> **Dans ce chapitre :** alternatives écartées et pistes non retenues, conservées pour mémoire.

Ce chapitre regroupe les alternatives écartées et les pistes non encore appliquées, pour ne pas alourdir les guides principaux. Rien ici n'est nécessaire au suivi du parcours conseillé dans le [README](../README.md).

- [Conserver Plymouth (alternative non retenue)](#conserver-plymouth-alternative-non-retenue)
- [Utiliser EEVDF sans SCX (alternative non retenue)](#utiliser-eevdf-sans-scx-alternative-non-retenue)
- [Adresse fixe : piste à envisager](#adresse-fixe--piste-à-envisager)

## Conserver Plymouth (alternative non retenue)

Contexte : [3.1 — Choisir Plymouth ou le logo firmware](03-boot-kernel.md#31--choisir-plymouth-ou-le-logo-firmware). Le choix retenu sur cette machine est de retirer Plymouth ; cette alternative documente comment le conserver si ce choix devait être inversé.

Conserver le hook `plymouth` et le paramètre `splash`. Le mémo propose de retirer l'animation **Cachy-boot-animation** avec Pamac, puis d'installer le thème **CachyOS** et de le sélectionner :

```fish
sudo plymouth-set-default-theme cachyos
```

Remplacer `watermark.png` dans `/usr/share/plymouth/themes/cachyos/` par le logo CachyOS blanc du dépôt, puis reconstruire :

```fish
sudo limine-mkinitcpio
```

## Utiliser EEVDF sans SCX (alternative non retenue)

Contexte : [5.1 — Coordonner TuneD, les profils énergétiques et SCX](05-performance-tuning.md#51--coordonner-tuned-les-profils-énergétiques-et-scx). Le choix retenu utilise sched-ext (SCX) ; cette alternative documente le retour à EEVDF si SCX devait être désactivé.

Désactiver le scheduler SCX actif avec l'outil qui le gère, puis empêcher le chargement automatique et retirer les paquets indiqués dans le mémo si inutilisés :

```fish
sudo systemctl mask scx_loader.service
sudo pacman -Rns scx-manager scx-tools scx-scheds cachyos-kernel-manager
```

Retirer aussi les sections SCX des profils TuneD si elles relancent un scheduler. Le masquage seul n'arrête pas nécessairement un scheduler déjà actif.

Dans la fonction Fish `scx`, le mémo utilise ce garde-fou :

```fish
if not set -q USE_SCX
    return 0
end
```

Le test `set -q USE_SCX` vérifie l'existence de la variable, pas la présence d'un paquet ni la valeur booléenne de la variable. Ne la définir que lorsque cette branche SCX est utilisée.

Le libellé initial `power_performance` n'est pas repris comme valeur EPP à appliquer : vérifier les valeurs réellement proposées par le pilote, notamment `balance_performance` :

```fish
cat /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_available_preferences
cat /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference
```

## Adresse fixe : piste à envisager

Contexte : [6.2 — Régler le Wi-Fi et TCP Fast Open](06-network.md#62--régler-le-wi-fi-et-tcp-fast-open). Piste non appliquée à la date de cette réorganisation.

Dans le profil NetworkManager de la connexion Wi-Fi 5 GHz, le mémo propose :

| Champ | Valeur personnelle |
|---|---|
| IPv4 | `192.168.31.102` |
| Masque | `255.255.255.0` (`/24`) |
| Passerelle | `192.168.31.1` |
| DNS | `1.1.1.1`, `1.0.0.1` |
| IPv6 | Désactivé dans cette variante |

Adapter ces valeurs au réseau et vérifier que l'adresse n'est pas attribuée à un autre appareil.

---

[Accueil](../README.md) · [Précédent](14-maintenance.md)
