# Applis vibe codées en Libadwaita — consignes communes

Chaque sous-dossier = un projet. Lire aussi le `CLAUDE.md` du sous-dossier concerné.

## Nature de ce dossier

- Ce dossier contient des **livrables**, pas des arbres de sources : paquets `*.pkg.tar.zst`, ZIP d'extensions, AppImage, et un `readme_<app>.md` (ou `README.md`).
- Aucun `PKGBUILD`, `meson.build` ni test n'est versionné ici (sauf dans l'archive SCX Manager). Les sources « vivantes » ne sont pas sur le disque.
- Pour les projets Python/GJS, le code lisible est **dans le paquet** : `bsdtar -tf <pkg>` pour lister, `bsdtar -xOf <pkg> <chemin>` pour lire. Extraire dans le scratchpad, jamais dans ce dossier.
- Pour modifier une app : extraire → éditer → reconstruire un paquet (PKGBUILD minimal `arch=any` pour Python) → incrémenter `pkgrel` (ou `pkgver`) → remplacer l'ancien `.pkg.tar.zst` → mettre à jour le readme.

## Cible

- Machine : CachyOS, ASUS Zenbook 14 OLED, session GNOME Wayland.
- Pile installée (oct. 2026) : **GNOME Shell 51**, libadwaita 1.10, GTK 4.24, Nautilus 51, GJS 1.90, Python 3.14, PyGObject 3.58, GLib 2.90. Cible déclarée des projets : **GNOME 50/51**. Vérifier avec `pacman -Q gnome-shell libadwaita gtk4`.
- **100 % GTK/libadwaita, aucune dépendance Qt.** Widgets Adw natifs (`Adw.ToolbarView`, `Adw.AlertDialog`, `Adw.PreferencesGroup`, `Adw.*Row`, `Adw.ToastOverlay`…), icônes symboliques du thème, pas de couleurs codées en dur (utiliser les variables CSS libadwaita, accent bleu système). Éviter les API dépréciées (`Adw.MessageDialog` → `Adw.AlertDialog`).
- Opérations root : helper dédié dans `/usr/lib/<app>/` appelé via `pkexec` + action polkit ; jamais l'app entière en root. Commandes via `subprocess.run([...])` sans shell.

## Conventions du dépôt

- Tout en **français** (interface, readmes, messages de commit). Commandes de doc en **fish**, chemins entre guillemets (le dossier contient des espaces et un accent).
- Commandes d'installation documentées depuis la racine du dépôt :
  `sudo pacman -U "Ressources/Applis vibe codées en Libadwaita/<Dossier>/<paquet>"`.
- Toute évolution d'un projet se reflète à **trois endroits** : le readme du sous-dossier, la section correspondante de `docs/11-applications-vibe-coded.md` (et `docs/08-gnome-extensions.md` pour les extensions), et éventuellement le `README.md` racine.
- Les readmes sont souvent **en retard sur le nom de fichier réel du paquet** : toujours vérifier le nom exact avec `ls` avant d'écrire une commande `pacman -U`.
- Honnêteté des vérifications : les readmes distinguent « archive inspectée / tests unitaires » de « testé en session GNOME réelle ». Conserver cette distinction ; ne pas prétendre qu'une chose a été testée en session si ce n'est pas le cas.

## Contrôle d'un paquet avant livraison

```fish
zstd -t <pkg>                       # archive valide (un paquet de 0 octet a déjà été livré une fois)
bsdtar -tf <pkg> | head             # .PKGINFO/.MTREE à la racine exacte
bsdtar -xOf <pkg> .PKGINFO          # nom, version, dépendances
python -m py_compile <fichiers.py>  # pour les apps Python extraites
```

Ne jamais renommer un ancien paquet pour simuler une nouvelle version.
