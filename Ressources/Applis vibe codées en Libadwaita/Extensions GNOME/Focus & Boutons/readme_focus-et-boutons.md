# Focus & Boutons v12

Extension GNOME Shell maison pour **GNOME 50 et 51**.

## Fonctions

- auto-fermeture de **Quick Settings** et du panneau **Calendrier/Notifications** après sortie du pointeur ;
- délai réglable, **350 ms** par défaut ;
- masquage optionnel de **Capture d’écran** ;
- bouton **Réglages scindé** :
  - clic sur la roue dentée : **Paramètres GNOME** ;
  - clic sur le chevron : **Ajustements**, **Éditeur dconf**, **Extensions Manager** ;
  - bleu Adwaita uniquement tant que le sous-menu est ouvert ;
- bouton **Power scindé** :
  - clic principal : dialogue **Éteindre** ;
  - chevron : **Suspendre**, **Redémarrer**, **Redémarrer la session**, **Verrouiller la session** ;
  - bleu Adwaita uniquement tant que le sous-menu est ouvert ;
- libellé **Énergie** ;
- carte RDV bleu Adwaita ;
- masquage optionnel de la grande zone Notifications lorsqu’elle est vide ;
- panneau de préférences.

L’extension ne touche pas au volume, au microphone ni au sélecteur de sortie audio.

## Installation

```fish
gnome-extensions install --force ./Focus-et-Boutons-v12.zip
gnome-extensions enable focus-et-boutons@ogu
```

## Préférences

```fish
gnome-extensions prefs focus-et-boutons@ogu
```

## Désinstallation

```fish
gnome-extensions uninstall focus-et-boutons@ogu
```
