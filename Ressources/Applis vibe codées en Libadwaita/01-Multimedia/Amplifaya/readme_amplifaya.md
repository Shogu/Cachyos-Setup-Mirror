# Amplifaya — moteur audio PipeWire

**Amplifaya** est un moteur de traitement audio pour PipeWire, sans interface graphique au démarrage et sans Qt, construit sur le cœur DSP de [JamesDSP](https://github.com/Audio4Linux/JDSP4Linux). Il applique le profil **ClearPenguin** (Bass Boost, égaliseur et limiteur) au son de la machine. Une interface GTK4/libadwaita est disponible à la demande.

Depuis la version **0.5.0**, PipeWire charge directement le traitement et WirePlumber l’insère devant la sortie audio. Il n’y a plus de démon Amplifaya ni de service systemd utilisateur à maintenir : le moteur peut rester actif sans processus de contrôle permanent. La commande `amplifayactl` pilote directement le traitement.

## Nouveautés et corrections

Ce récapitulatif suit l’évolution depuis la version 0.1.1, qui restait muette.

### 0.5.1 — casque automatique et marge avant traitement

- **Bascule automatique casque/haut-parleurs sans service dédié :** un script exécuté par WirePlumber retire Amplifaya lorsque le casque est détecté, pour retrouver le son natif, puis réactive le traitement lorsque la sortie repasse sur les haut-parleurs. `amplifayactl test` indique notamment « Casque détecté ». La détection sur la prise jack physique reste à vérifier en session réelle.
- **Marge avant traitement réglable de 0 à 6 dB**, depuis l’interface ou avec `amplifayactl marge N`. La valeur par défaut est 0 dB : aucune marge supplémentaire n’est appliquée.

### 0.5.0 — architecture PipeWire, sans démon ni service

- **PipeWire charge lui-même le traitement** via `/usr/share/pipewire/pipewire.conf.d/60-amplifaya.conf`. WirePlumber l’insère devant la sortie à l’aide de ses filtres intelligents. Si un ancien démon de contrôle est tué, cela ne doit plus provoquer la coupure sonore qui affectait l’ancienne architecture.
- **Un seul volume :** le curseur GNOME règle directement le volume de la carte son. La compensation de volume introduite en 0.4.0 est supprimée.
- **Contrôle direct avec `amplifayactl` :** bypass, Bass Boost, élargissement stéréo et changement de profil à chaud. L’état est mémorisé dans `~/.config/amplifaya/state.conf`.
- **Éléments retirés :** le service `amplifaya.service`, le démon `amplifayad`, l’ancien automatisme casque et le choix de sortie dans l’interface. La détection automatique du casque revient dans la 0.5.1 via WirePlumber, sans service Amplifaya distinct.
- **Nouvelle icône** à couronne de segments et icône symbolique de 16 px.

### Mise à jour depuis la 0.4.x

La version 0.4.0 pouvait laisser la carte son à 100 %. **Baisse le volume avant de relancer la musique** après la mise à jour.

1. Mets la musique en pause.
2. Installe le nouveau paquet.
3. Désactive l’ancien service s’il existe, puis redémarre PipeWire et WirePlumber :

```sh
sudo pacman -U ./amplifaya-full-0.5.1-1-x86_64.pkg.tar.zst
systemctl --user disable --now amplifaya.service 2>/dev/null
systemctl --user restart pipewire wireplumber pipewire-pulse
```

4. Baisse le volume avant de reprendre la lecture, puis vérifie le résultat avec `amplifayactl status` et `amplifayactl test`.

Le paquet moteur seul s’appelle `amplifaya-0.5.1-1-x86_64.pkg.tar.zst`. Le paquet `amplifaya-full` inclut le moteur et l’interface.

### 0.4.0 — volume matériel et curseur GNOME

Deux volumes se multipliaient : le curseur GNOME et celui de la carte son physique, qui pouvait rester à 40 % (−24 dB). La version 0.4.0 mettait la carte à 100 % au démarrage et lors d’un changement de sortie, puis reportait le volume total sur le curseur GNOME. Cette compensation a été retirée en 0.5.0 au profit d’un volume unique.

### 0.3.0 — nouveau nom et icône

- **Nom : Amplifaya**, jeu de mots autour d’« amplifier » et de *faya* (« feu »).
- Commande : `amplifayactl` ; interface : `amplifaya-gui` ; sortie audio : « Amplifaya ».
- ClearPenguin est intégré et chargé par défaut depuis `/usr/share/amplifaya/presets/ClearPenguin.conf`.

### 0.2.0 — diagnostic audio et comparaison A/B

- **`amplifayactl test`** compare, musique en cours, le signal d’entrée et celui de sortie du moteur. Il distingue son modifié, bypass (écart exactement nul), silence et absence de signal.
- **`amplifayactl ab`** alterne le traitement Amplifaya et le son d’origine, puis restaure l’état initial, y compris après Ctrl+C.
- La commande de contrôle a été réécrite en C : le moteur ne dépend plus de Python.

### 0.1.2 — correction du silence

Le fichier `ladspa.h` fourni déclarait des types de 8 octets au lieu des 4 octets imposés par la norme LADSPA. PipeWire interprétait mal les ports et détectait deux entrées et aucune sortie, produisant un silence total même en bypass. La déclaration a été corrigée et la compilation échoue désormais si cette erreur réapparaît. Ctrl+C ferme également l’interface proprement.

## Commandes utiles

| Commande | Effet |
|---|---|
| `amplifayactl status` | État du traitement |
| `amplifayactl test` | Vérifie le traitement audio (musique en cours) |
| `amplifayactl ab` | Compare le son traité au son d’origine |
| `amplifayactl bypass on|off` | Active ou désactive le bypass |
| `amplifayactl bass on|off` | Active ou désactive Bass Boost |
| `amplifayactl wide on|off` | Active ou désactive l’élargissement stéréo |
| `amplifayactl marge 0…6` | Règle la marge avant traitement en dB |
| `amplifayactl presets` | Liste les profils disponibles |
| `amplifayactl preset NOM` | Charge un profil sans redémarrer |

L’interface est facultative : lance-la avec `amplifaya-gui`. Le moteur reste actif lorsque la fenêtre est fermée.

## Vérification et diagnostic

Lance un morceau et laisse-le jouer pendant les tests :

```sh
amplifayactl status
amplifayactl test
amplifayactl ab
pactl get-default-sink
journalctl --user -b --no-pager | grep -i amplifaya
```

Le nom de la sortie audio et les lignes de journal dépendent de la configuration. Pour lister les sorties disponibles :

```sh
pactl list short sinks
```

Depuis la version 0.5.0, ne cherche pas à diagnostiquer le fonctionnement normal au moyen de `systemctl --user status amplifaya.service` : ce service a été supprimé. Après installation, le redémarrage de PipeWire et WirePlumber permet de charger la nouvelle configuration.

## Dépendances et architecture

- Moteur C et plugin LADSPA, chargés par PipeWire.
- WirePlumber pour l’insertion du filtre et la bascule automatique casque/haut-parleurs.
- Interface facultative Python/PyGObject avec GTK4/libadwaita.
- Preset ClearPenguin fourni avec le paquet.

Le moteur utilise environ **2 Mo** de mémoire. L’interface utilise environ **100 Mo lorsqu’elle est ouverte**, et aucune mémoire d’interface lorsqu’elle est fermée.

## Limites connues

- **Bluetooth non pris en charge**, volontairement.
- Amplifaya ne reprend pas tous les effets de JamesDSP.
- La bascule casque a été essayée avec un casque USB simulé ; le comportement de la prise jack physique n’a pas encore été validé en session réelle.

## Emplacement du paquet

Le dossier de l’application dans le dépôt est :

`Ressources/Applis vibe codées en Libadwaita/01-Multimedia/Amplifaya/`

Le dépôt contient encore le paquet historique **0.4.0**. Ajoute manuellement le paquet 0.5.1 dans ce dossier lorsqu’il est prêt ; ne renomme pas l’ancien fichier pour lui donner la nouvelle version.
