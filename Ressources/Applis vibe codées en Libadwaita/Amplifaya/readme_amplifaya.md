# Amplifaya 0.3.0

**Amplifaya** est le fork maison allégé de [JamesDSP](https://github.com/Audio4Linux/JDSP4Linux), conçu pour PipeWire et GNOME sans Qt ni icône de notification.

- `amplifaya` : moteur headless en C, plugin LADSPA, commande `amplifayactl` et service systemd utilisateur.
- `amplifaya-gui` : télécommande facultative GTK4/libadwaita ; fermer la fenêtre laisse le moteur actif.
- Preset **ClearPenguin** fourni ; Bass Boost, Tone EQ, crossfeed BS2B au casque, élargissement stéréo sur haut-parleurs, post-gain et limiteur.
- Cette version ne prend pas en charge l’audio Bluetooth et ne reprend pas tous les effets de JamesDSP.

Fermer et désactiver l’ancien traitement global JamesDSP ou EasyEffects avant l’activation, pour éviter un double traitement. Depuis la racine du dépôt :

```fish
sudo pacman -U "Ressources/Applis vibe codées en Libadwaita/Amplifaya/amplifaya-0.3.0-1-x86_64.pkg.tar.zst" "Ressources/Applis vibe codées en Libadwaita/Amplifaya/amplifaya-gui-0.3.0-1-x86_64.pkg.tar.zst"
systemctl --user daemon-reload
systemctl --user enable --now amplifaya.service
systemctl --user status amplifaya.service
amplifayactl status
```

Pour le moteur seul, installer uniquement le premier paquet. Ouvrir l’interface à la demande :

```fish
amplifaya-gui
```

Avec un morceau en lecture, vérifier le passage dans le moteur et comparer le traitement :

```fish
amplifayactl test
amplifayactl ab
```

Gestion du moteur :

```fish
amplifayactl bypass on
amplifayactl bypass off
systemctl --user stop amplifaya.service
systemctl --user start amplifaya.service
journalctl --user -u amplifaya.service -b
```

Le README complet installé se trouve dans `/usr/share/doc/amplifaya/README.md`. Les paquets ont été inspectés ; le traitement audio reste à tester sur la machine cible.
