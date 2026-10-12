# Amplifaya — moteur audio PipeWire

**Amplifaya** est un moteur audio pour PipeWire, sans interface au démarrage et sans Qt, construit sur le cœur DSP de [JamesDSP](https://github.com/Audio4Linux/JDSP4Linux). Il applique par défaut le profil **ClearPenguin** (Bass Boost, égaliseur, limiteur) à tout le son de la machine. Une interface GTK4/libadwaita est disponible à la demande.

- `amplifaya` : moteur headless en C, plugin LADSPA, commande `amplifayactl` et service systemd utilisateur.
- `amplifaya-gui` : interface facultative ; fermer sa fenêtre laisse le moteur actif.
- ClearPenguin est installé dans `/usr/share/amplifaya/presets/ClearPenguin.conf`.
- Le moteur propose notamment Bass Boost, égaliseur, crossfeed BS2B au casque, élargissement stéréo sur haut-parleurs, post-gain et limiteur.
- Le moteur seul occupe environ 2 Mo de mémoire ; l'interface Python utilise environ 100 Mo lorsqu'elle est ouverte et 0 lorsqu'elle est fermée.

Désactive l'ancien traitement global JamesDSP ou EasyEffects avant d'activer Amplifaya, afin d'éviter un double traitement.

## Ce qui a changé

Ce récapitulatif suit l'évolution depuis la version 0.1.1, qui restait muette.

### 0.4.0 — tout le volume disponible

- **Carte son à 100 % automatiquement.** Deux volumes se multipliaient : le curseur GNOME, qui règle la sortie Amplifaya, et celui de la vraie carte son, restée bloquée à 40 % (−24 dB) sans qu'on le voie. Au démarrage et à chaque changement de sortie, le moteur met maintenant la carte à 100 % et reporte le volume total sur le curseur GNOME. On n'entend aucun saut de volume, et le curseur couvre enfin toute sa plage, jusqu'au vrai maximum.
- **Paquet `amplifaya-full`** : le moteur et l'interface en un seul paquet.

### 0.3.0 — nouveau nom et nouvelle icône

- **Nom : Amplifaya.** C'est « amplifier » prononcé à la jamaïcaine, avec le double sens de *faya*, le feu.

  | Élément | Nom |
  |---|---|
  | Commande | `amplifayactl` |
  | Interface | `amplifaya-gui` |
  | Service | `amplifaya.service` |
  | Sortie son | « Amplifaya » |

- **Icône :** un potard à fond sur une platine verte, avec un cran jaune, deux crans rouges et un index rouge. En 32 et 16 px, une version simplifiée sans crans.
- **ClearPenguin est intégré** et chargé par défaut.

### 0.2.0 — vérifier que le son est vraiment modifié

- **`amplifayactl test`** : avec de la musique en cours, compare le son qui entre dans le moteur et celui qui en sort, puis donne un verdict : modifié, bypass (écart exactement nul), silence ou rien ne passe.
- **`amplifayactl ab`** : écoute comparative. La commande alterne Amplifaya et le son d'origine, puis restaure l'état de départ, y compris après Ctrl+C.
- **`amplifayactl` réécrit en C** : le moteur n'a plus besoin de Python.
- **Moteur et interface séparés :** le paquet `amplifaya` peut tourner seul, sans interface.

### 0.1.2 — la cause du silence

- Le fichier `ladspa.h` livré déclarait des types de 8 octets au lieu des 4 qu'exige la norme LADSPA. PipeWire lisait les ports de travers et voyait 2 entrées et 0 sortie : silence total, même en bypass.
- C'est corrigé, et la compilation échoue désormais si cette erreur revient.
- Ctrl+C ferme l'interface proprement.

## Installation

Pour installer le moteur et l'interface en un seul paquet :

```fish
sudo pacman -U ./amplifaya-full-0.4.0-1-x86_64.pkg.tar.zst
systemctl --user daemon-reload
systemctl --user restart amplifaya.service
amplifayactl status
```

### Vérification après installation

Lance un morceau (MP3 ou autre) et laisse-le jouer pendant toute la vérification. Exécute les commandes suivantes dans un terminal :

```fish
pactl get-sink-volume alsa_output.pci-0000_63_00.6.analog-stereo
pactl get-sink-volume amplifaya
pactl get-default-sink
journalctl --user -u amplifaya -b --no-pager | grep carte
amplifayactl test
amplifayactl ab
```

Sur la configuration testée, le résultat attendu est :
- la carte physique est à **100 %** ;
- le volume de la sortie `amplifaya` est proche de 100 % selon le niveau GNOME ;
- la sortie par défaut est `amplifaya` ;
- le journal contient une ligne du type `carte … mise a 100 % (etait 54%), volume Amplifaya ajuste a 54%` ;
- `amplifayactl test` confirme que le son est bien modifié par Amplifaya ;
- `amplifayactl ab` alterne quatre fois entre Amplifaya actif et le son d'origine (bypass), puis restaure l'état de départ.

Le nom `alsa_output.pci-0000_63_00.6.analog-stereo` dépend du matériel. Si le tien diffère, repère le nom exact avec `pactl list short sinks` et remplace-le dans la première commande.

Pour le moteur seul, installe plutôt `amplifaya-0.4.0-1-x86_64.pkg.tar.zst`.

Depuis la racine du dépôt, les paquets de la version précédemment intégrée se trouvaient dans `Ressources/Applis vibe codées en Libadwaita/01-Multimedia/Amplifaya/`. Ouvre l'interface à la demande :

```fish
amplifaya-gui
```

## Commandes utiles

| Commande | Effet |
|---|---|
| `amplifayactl status` | État du moteur |
| `amplifayactl test` | Vérifie que le son est modifié (musique en cours) |
| `amplifayactl ab` | Écoute comparative avec le son d'origine |
| `amplifayactl bypass on|off` | Contourne le traitement sans arrêter le moteur |
| `amplifayactl bass on|off` | Active ou désactive Bass Boost |
| `amplifayactl wide on|off` | Scène stéréo élargie (refusée au casque) |
| `amplifayactl outputs` / `output NOM` | Liste les sorties / change de sortie |
| `amplifayactl stop` / `start` | Arrête ou relance le moteur |

Diagnostic et gestion du service :

```fish
systemctl --user status amplifaya.service
journalctl --user -u amplifaya.service -b
systemctl --user stop amplifaya.service
systemctl --user start amplifaya.service
```

Le README installé se trouve dans `/usr/share/doc/amplifaya/README.md`.

## Limites connues

- **Pas de Bluetooth :** c'est volontaire, la machine n'en utilise pas.
- Amplifaya ne reprend pas tous les effets de JamesDSP.
- L'interface est en Python et utilise environ 100 Mo lorsqu'elle est ouverte ; le moteur seul reste autour de 2 Mo.
