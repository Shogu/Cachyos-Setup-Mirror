# Vivaldi Web Panel Auto Discard

Paquet Arch **vivaldi-webpanel-auto-discard** : décharge automatiquement les web panels Vivaldi qui restent fermés depuis deux minutes, afin de libérer leur mémoire.

## Fonctionnement

Le mod s'exécute dans l'interface de Vivaldi, dans `window.html`, comme un `custom.js`. C'est à cet endroit que les web panels sont identifiables via `vivExtData.panelId`.

Toutes les cinq secondes, il vérifie si la webview de chaque panneau est affichée. Si elle est masquée depuis le délai configuré, il appelle `chrome.tabs.discard()` pour la décharger.

- Délai par défaut : **2 minutes**.
- Un panneau qui joue du son n'est pas déchargé.
- Le panneau se recharge lorsqu'on le rouvre.
- Les onglets ordinaires ne sont jamais concernés, y compris lorsqu'ils affichent le même site qu'un web panel.

Un hook pacman réinjecte le mod après chaque mise à jour de Vivaldi.

## Installation

Déposer manuellement le paquet `vivaldi-webpanel-auto-discard-*.pkg.tar.zst` dans ce dossier, puis exécuter :

```fish
sudo pacman -U ./vivaldi-webpanel-auto-discard-*.pkg.tar.zst
```

Redémarrer Vivaldi après l'installation.

## Outil de suivi — Web Panel Status

Le script complémentaire [vivaldi-webpanel-status.py](Status/README.md) affiche l'état de chaque web panel, notamment le temps restant avant son déchargement. Le script Python lui-même est à déposer manuellement dans le sous-dossier `Status/` ; consulter son README pour les prérequis de lancement et l'avertissement lié au port de débogage distant.

## Désinstallation

```fish
sudo pacman -R vivaldi-webpanel-auto-discard
```

## Modifier le délai

1. Éditer `/usr/share/vivaldi-webpanel-auto-discard/webpanel-auto-discard.js`.
2. Modifier la valeur de `delay`, exprimée en millisecondes. Par exemple, deux minutes :

   ```javascript
   let delay = 2 * 60 * 1000;
   ```

3. Réinjecter le mod dans Vivaldi :

   ```fish
   sudo vivaldi-webpanel-auto-discard install
   ```

4. Redémarrer Vivaldi.

## Vérification

Ouvrir le gestionnaire de tâches de Vivaldi avec **Maj+Échap**. Un web panel déchargé ne doit plus y consommer de mémoire.

---

Le paquet binaire n'est pas versionné dans le dépôt : déposer le fichier `.pkg.tar.zst` manuellement dans ce dossier avant l'installation.
