# H — Powersave

[Accueil](README.md) · [Précédent](G-optimisations-systeme.md) · [Suivant](J-gnome.md)

- [Coordonner TuneD, les profils énergétiques et SCX](#h1--coordonner-tuned-les-profils-énergétiques-et-scx)
- [Configurer le bouton d’alimentation et le capot](#h2--configurer-le-bouton-dalimentation-et-le-capot)
- [Désactiver la luminosité automatique et régler la veille](#h3--désactiver-la-luminosité-automatique-et-régler-la-veille)

## H1 — Coordonner TuneD, les profils énergétiques et SCX

### Installer TuneD et son interface PPD

Remplacer power-profiles-daemon par les paquets TuneD retenus pour CachyOS :

```fish
sudo pacman -Syu tuned-cachy tuned-cachy-ppd
```

Redémarrer après installation :

```fish
systemctl reboot
```

### Associer les profils aux schedulers

La méthode du README modifie directement les profils installés sous `/usr/lib/tuned/profiles`. Elle est conservée ici : **les mises à jour peuvent remplacer ces modifications**. Des profils locaux sous `/etc/tuned` constitueraient une autre organisation, qui n’est pas développée dans le fichier source.

Ouvrir les profils, en vérifiant d’abord leurs noms sur la version installée :

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

Autre piste du mémo : utiliser LAVD en mode automatique avec `--autopower` pour son adaptation énergétique. Vérifier que le scheduler et le plugin installés acceptent cette combinaison.

Changer de profil avec le bouton GNOME, puis vérifier :

```fish
scxctl get
```

Ou utiliser la fonction personnelle du fichier Fish :

```fish
scx
```

### Alternative : utiliser EEVDF sans SCX

Désactiver le scheduler SCX actif avec l’outil qui le gère, puis empêcher le chargement automatique et retirer les paquets indiqués dans le mémo si inutilisés :

```fish
sudo systemctl mask scx_loader.service
sudo pacman -Rns scx-manager scx-tools scx-scheds cachyos-kernel-manager
```

Retirer aussi les sections SCX des profils TuneD si elles relancent un scheduler. Le masquage seul n’arrête pas nécessairement un scheduler déjà actif.

Dans la fonction Fish `scx`, le mémo utilise ce garde-fou :

```fish
if not set -q USE_SCX
    return 0
end
```

Le test `set -q USE_SCX` vérifie l’existence de la variable, pas la présence d’un paquet ni la valeur booléenne de la variable. Ne la définir que lorsque cette branche SCX est utilisée.

Le libellé initial `power_performance` n’est pas repris comme valeur EPP à appliquer : vérifier les valeurs réellement proposées par le pilote, notamment `balance_performance` :

```fish
cat /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_available_preferences
cat /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference
```

Les rôles sont distincts : l’extension GNOME peut changer le profil selon secteur/batterie, TuneD applique le profil et son EPP, puis le plugin SCX choisit le scheduler. Le mode `--autopower` d’un scheduler constitue une variante à configurer selon ce scheduler, pas un argument à appliquer à tous.

## H2 — Configurer le bouton d’alimentation et le capot

Éditer la configuration de logind :

```fish
sudoedit /etc/systemd/logind.conf
```

Dans `[Login]`, régler :

```ini
HandlePowerKey=suspend
HandlePowerKeyLongPress=poweroff
HandleLidSwitch=suspend
HandleLidSwitchExternalPower=suspend
```

Appliquer au prochain redémarrage, puis tester le bouton d’alimentation et la fermeture du capot sur secteur et sur batterie.

## H3 — Désactiver la luminosité automatique et régler la veille

Désactiver l’ajustement automatique de luminosité :

```fish
gsettings set org.gnome.settings-daemon.plugins.power ambient-enabled false
```

Dans les paramètres d’alimentation GNOME, régler ensuite le délai avant mise en veille à **600 secondes**, soit **10 minutes**, pour le mode d’alimentation souhaité.

[Accueil](README.md) · [Précédent](G-optimisations-systeme.md) · [Suivant](J-gnome.md)
