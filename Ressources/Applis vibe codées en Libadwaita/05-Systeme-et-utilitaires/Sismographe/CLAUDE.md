# Sismographe

Diagnostic du système GNOME (remplace l'ancien `stethoscope`) : vues **Santé, Journaux, Démarrage, Stockage** — erreurs par service, plantages, analyse du boot, SMART, compteurs d'erreurs btrfs, contrôle de la partition FAT. Export d'un rapport texte.

## Technique

- **Python / PyGObject**, GTK4, libadwaita ≥ 1.5. Paquet `any` 1.0.0-1. App id `io.github.ogu.Sismographe`.
- Package `usr/share/sismographe/sismographe/` : `app.py`, `window.py`, `widgets.py`, `health.py`, `journal.py`, `boot.py`, `storage.py`, `sources.py` (collecte), `report.py` (export).
- Opérations privilégiées : helper root `usr/lib/sismographe/sismographe-helper` (`#!/usr/bin/python3 -I`) via `pkexec`, action polkit `io.github.ogu.Sismographe.policy`. Garder le helper minimal et à arguments validés.
- Outils optionnels : smartmontools, btrfs-progs, dosfstools ; l'UI doit se dégrader proprement s'ils manquent.
- Statut : paquet inspecté, diagnostics non validés sur la machine cible.
