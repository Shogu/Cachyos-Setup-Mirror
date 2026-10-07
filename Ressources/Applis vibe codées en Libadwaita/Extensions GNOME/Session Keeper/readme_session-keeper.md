# Session Keeper

Extension GNOME Shell de sauvegarde et de restauration de session, adaptée pour **GNOME 50**.

- **Nom :** Session Keeper
- **UUID :** `session-keeper@altlinux.org`
- **Archive :** `Session-Keeper.zip`
- **Base upstream :** Session Keeper 1.0.6 d’ALT Linux
- **Catégorie Manager Extensions :** Productivité

## Principales adaptations

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

Depuis la racine du dépôt :

```fish
gnome-extensions install --force "Ressources/Applis vibe codées en Libadwaita/Extensions GNOME/Session Keeper/Session-Keeper.zip"
```

Sous Wayland, se déconnecter puis se reconnecter, puis :

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
