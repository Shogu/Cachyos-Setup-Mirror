# Archives

[Accueil](../README.md) · [Précédent](14-maintenance.md)

> **Dans ce chapitre :** alternatives, réglages et logiciels optionnels conservés pour mémoire.

Ce chapitre regroupe les alternatives écartées et les pistes optionnelles, pour ne pas alourdir les guides principaux. Rien ici n'est nécessaire au suivi du parcours conseillé dans le [README](../README.md).

- [Conserver Plymouth (alternative non retenue)](#conserver-plymouth-alternative-non-retenue)
- [Utiliser EEVDF sans SCX (alternative non retenue)](#utiliser-eevdf-sans-scx-alternative-non-retenue)
- [Utiliser LAVD en mode automatique](#utiliser-lavd-en-mode-automatique)
- [Adresse fixe : piste à envisager](#adresse-fixe--piste-à-envisager)
- [Configurer Paru](#configurer-paru)
- [Outils optionnels](#outils-optionnels)
- [Ciné : réglages optionnels](#ciné--réglages-optionnels)
- [Extensions Vivaldi optionnelles](#extensions-vivaldi-optionnelles)
- [Extensions GNOME optionnelles](#extensions-gnome-optionnelles)

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

## Utiliser LAVD en mode automatique

Autre piste du mémo : utiliser LAVD en mode automatique avec `--autopower` pour son adaptation énergétique. Vérifier que le scheduler et le plugin installés acceptent cette combinaison.

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

## Configurer Paru

Configurer Paru pour nettoyer les dépendances de compilation et les fichiers de construction :

```fish
mkdir -p ~/.config/paru
cp /etc/paru.conf ~/.config/paru/paru.conf
gnome-text-editor ~/.config/paru/paru.conf
```

Dans la section `[options]`, activer les réglages suivants :

```ini
[options]
PgpFetch
Devel
Provides
DevelSuffixes = -git -cvs -svn -bzr -darcs -always -hg -fossil
AurOnly
BottomUp
RemoveMake
SudoLoop
#UseAsk
#SaveChanges
CombinedUpgrade
CleanAfter
UpgradeMenu
#NewsOnUpgrade
#SkipReview
```

## Outils optionnels

Installer [PacHub](https://github.com/mrks1469/PacHub) ou régler `pacseek` pour inclure Paru à la place de Yay si besoin, avec `EnableAutoSuggest=true` et `ColorScheme=Endeavour OS`. Utiliser Ctrl+S dans Pacseek, ou éditer sa configuration :

```fish
gnome-text-editor ~/.config/pacseek/config.json
```

## Ciné : réglages optionnels

**Ciné** est une alternative à Celluloid. Créer puis éditer son fichier de raccourcis :

```fish
mkdir -p ~/.config/cine
gnome-text-editor ~/.config/cine/input.conf
```

```text
# Flèches horizontales : 60 secondes ; verticales : 5 minutes.
RIGHT seek 60
LEFT seek -60
UP seek 300
DOWN seek -300
```

Pour le moteur vidéo, le mémo indique `vo=gpu-next` et `gpu-api=vulkan` dans **Paramètres → Divers → Options supplémentaires**. Adapter leur syntaxe au champ proposé par l'application : options MPV et arguments de ligne de commande ne se saisissent pas nécessairement de la même manière.

Activer les options **focus** et **toujours afficher les boutons de titre**. Installer les scripts Lua **Visualizer** et **Delete File** pour l'usage musical ; leurs URL ne sont pas précisées dans le mémo source.

## Extensions Vivaldi optionnelles

- [LocalCDN](https://chromewebstore.google.com/detail/localcdn/njdfdhgcmkocbgbhcioffdbicglldapd)
- [Better Scroll To Bottom](https://chromewebstore.google.com/detail/better-scroll-to-topbotto/ifdjdmipgndncbeopapghbohjdiieibl?hl=es)

## Extensions GNOME optionnelles

- [Custom Command Toggle](https://extensions.gnome.org/extension/7012/custom-command-toggle/)
- [Battery Monitor](https://extensions.gnome.org/extension/8348/battery-monitor/)
- [Media Controls](https://extensions.gnome.org/extension/4470/media-controls/)
- [Quick Settings Audio Device](https://extensions.gnome.org/extension/5964/quick-settings-audio-devices-hider/) pour masquer les périphériques audio inutiles. L'exemple JamesDSP du mémo est sans objet depuis sa désinstallation.
- [Night Light Slider](https://extensions.gnome.org/extension/6781/night-light-slider-updated/)
- [AppIndicator Quick Setting](https://github.com/VaZark/appindicator-quicksetting) : indicateurs d'applications dans les réglages rapides.
- [Appindicator](https://extensions.gnome.org/extension/615/appindicator-support/)
- [Slider percentages](https://extensions.gnome.org/extension/10125/slider-percentages/)
- [Windows Rounded Corners](https://extensions.gnome.org/extension/7048/rounded-window-corners-reborn/)
- [Lilypad Topbar Organizer](https://extensions.gnome.org/extension/7266/lilypad/)

---

[Accueil](../README.md) · [Précédent](14-maintenance.md)
