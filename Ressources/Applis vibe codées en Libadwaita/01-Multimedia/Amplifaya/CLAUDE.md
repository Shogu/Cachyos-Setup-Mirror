# Amplifaya

Fork allégé de JamesDSP (JDSP4Linux) pour PipeWire, sans Qt ni icône de notification. Deux paquets issus du même `pkgbase` :

- `amplifaya` (x86_64, **C**, `gcc`/`make`) : moteur headless `usr/lib/amplifaya/amplifayad`, plugin LADSPA `usr/lib/ladspa/amplifaya.so`, CLI `amplifayactl`, service **systemd utilisateur** `amplifaya.service` (activé via `default.target.wants`), preset `usr/share/amplifaya/presets/ClearPenguin.conf`.
- `amplifaya-gui` : télécommande **Python/PyGObject GTK4/libadwaita**, fichier unique `usr/bin/amplifaya-gui` (~140 lignes), app id `io.github.shogu.Amplifaya`. Elle pilote le démon (socket), fermer la fenêtre laisse le moteur actif.

Effets : Bass Boost, Tone EQ, crossfeed BS2B (casque), élargissement stéréo (HP), post-gain, limiteur. Pas de Bluetooth, pas tous les effets JamesDSP.

## Points d'attention

- Les sources C ne sont pas ici. Seule la GUI est lisible dans le paquet.
- Ne pas faire tourner en même temps que JamesDSP ou EasyEffects (double traitement).
- Diagnostic : `amplifayactl status|test|ab|bypass on|off`, `journalctl --user -u amplifaya.service -b`.
- Statut : paquets inspectés, traitement audio non validé sur la machine cible.
- Une nouvelle version = reconstruire **les deux** paquets avec la même version et les mêmes noms dans le readme et `docs/11` §11.23.
