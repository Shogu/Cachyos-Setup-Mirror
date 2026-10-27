# Amplifaya

Moteur audio PipeWire sans interface au démarrage ni Qt, basé sur le cœur DSP de JamesDSP. Le profil ClearPenguin est appliqué par défaut. La version documentée ici est **0.5.1**.

## Architecture actuelle (0.5.x)

- PipeWire charge le traitement via `/usr/share/pipewire/pipewire.conf.d/60-amplifaya.conf`.
- WirePlumber insère le filtre avant la sortie audio et exécute la logique de bascule casque/haut-parleurs.
- Il n’y a plus de démon `amplifayad` ni de service systemd utilisateur `amplifaya.service`. Les instructions de service ci-dessous ne s’appliquent qu’à la migration depuis les anciennes versions.
- `amplifayactl` pilote directement le traitement : état, test audio, comparaison A/B, bypass, Bass Boost, élargissement stéréo, marge 0–6 dB et profils.
- `amplifaya-gui` est une interface facultative Python/PyGObject GTK4/libadwaita ; la fermer ne désactive pas le traitement.
- Le paquet `amplifaya-full` regroupe le moteur et l’interface. Le paquet `amplifaya` fournit le moteur seul.

## Effets et limites

Bass Boost, égaliseur, limiteur, crossfeed BS2B au casque et élargissement stéréo sur haut-parleurs, selon le profil et les options activées. Pas de Bluetooth ni de prise en charge de tous les effets JamesDSP.

## Migration depuis 0.4.x

Mettre la musique en pause, installer le paquet 0.5.1, désactiver l’ancien service s’il existe, puis redémarrer PipeWire et WirePlumber :

```sh
sudo pacman -U ./amplifaya-full-0.5.1-1-x86_64.pkg.tar.zst
systemctl --user disable --now amplifaya.service 2>/dev/null
systemctl --user restart pipewire wireplumber pipewire-pulse
```

**Attention :** la version 0.4.0 pouvait forcer la carte son physique à 100 %. Baisser le volume avant de relancer la musique.

## Diagnostics

Lancer un morceau pendant les tests :

```sh
amplifayactl status
amplifayactl test
amplifayactl ab
journalctl --user -b --no-pager | grep -i amplifaya
```

Ne pas utiliser `systemctl --user status amplifaya.service` pour diagnostiquer la version 0.5.x : le service n’existe plus. La détection de la prise jack physique reste à vérifier en session réelle ; le test précédent utilisait un casque USB simulé.

Le dépôt contient encore le paquet 0.4.0. Le paquet 0.5.1 doit être ajouté manuellement au dossier Amplifaya, sans renommer l’ancienne archive.
