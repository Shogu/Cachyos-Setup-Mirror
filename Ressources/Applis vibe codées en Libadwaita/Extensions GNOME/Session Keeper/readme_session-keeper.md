# Session Keeper

Extension GNOME Shell de sauvegarde et de restauration de session, adaptée pour **GNOME 50**.

- **Nom :** Session Keeper
- **UUID :** `session-keeper@altlinux.org`
- **Version :** 1.3.1-2
- **Paquet Arch fourni :** `gnome-shell-extension-session-keeper-1.3.1-2-any.pkg.tar.zst`
- **Base upstream :** Session Keeper 1.0.6 d’ALT Linux
- **Catégorie Manager Extensions :** Productivité

## Principales adaptations

- Le sélecteur d'applications utilise désormais `Adw.Dialog` à la place de `Gtk.AppChooserDialog`, supprimé/inadapté dans l'environnement GNOME ciblé.
- Les classes CSS sont ajoutées avec l'API `add_css_class()`.

- interface et réglages en français ;
- sauvegarde continue événementielle sans polling ;
- sauvegarde atomique et flush synchrone lors d’une fermeture GNOME propre ;
- restauration dès `startup-complete`, sans délai fixe inutile ;
- lancement rapide et légèrement échelonné des applications ;
- restauration multi-fenêtres via les API natives GNOME lorsque disponible ;
- appariement renforcé des fenêtres ;
- restauration de la géométrie, des espaces de travail, de l’écran et des principaux états de fenêtre ;
- nettoyage complet des signaux et timers ;
- validation du format de session et permissions privées ;
- options avancées pour activer ou désactiver les fonctions principales.

L’extension utilise uniquement les mécanismes natifs **GNOME Shell / GJS / Mutter / Gio / GLib**.

## Installation

Depuis la racine du dépôt, installer le paquet Arch fourni :

```fish
sudo pacman -U "./Ressources/Applis vibe codées en Libadwaita/Extensions GNOME/Session Keeper/gnome-shell-extension-session-keeper-1.3.1-2-any.pkg.tar.zst"
```

Sous Wayland, se déconnecter puis se reconnecter, puis activer l’extension :

```fish
gnome-extensions enable session-keeper@altlinux.org
```

Réglages :

```fish
gnome-extensions prefs session-keeper@altlinux.org
```

## Désinstallation

```fish
gnome-extensions uninstall session-keeper@altlinux.org
```

## Limite

L’extension relance les applications et restaure leurs fenêtres. Le contenu interne des applications (onglets, documents, historique de terminal, etc.) ne peut être restauré que si l’application elle-même sait le faire.
