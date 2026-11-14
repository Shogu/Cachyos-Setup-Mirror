# Always on top, always on top

Extension GNOME Shell libadwaita : une icône dans la topbar active/désactive la fonction native GNOME « Toujours au premier plan » (*always on top*) sur la fenêtre active. Le clic appelle `make_above()` ou `unmake_above()` de Mutter, sans réimplémenter le comportement natif.

## Fonctionnalités

- **État lisible par l'icône** :
  - épinglage possible : `aot-pin-available-symbolic` ;
  - épinglage impossible : `aot-pin-unavailable-symbolic` ;
  - fenêtre épinglée : l'icône de l'application épinglée est affichée.
- Pour l'icône d'une application épinglée, l'extension cherche d'abord sa variante monochrome `<icône>-symbolic`, puis une icône Adwaita générique pour Ptyxis, GNOME Text Editor, Nautilus, Clapper et Grimoire, puis `application-x-executable-symbolic`.
- **Raccourci Super+T facultatif**, désactivé par défaut. L'interrupteur des préférences demande à GNOME Shell d'enregistrer ou de libérer le raccourci. En cas d'échec, une notification apparaît et l'interrupteur revient à désactivé.
- **Au premier plan dès l'ouverture** : liste d'applications dont les fenêtres sont épinglées dès leur apparition. Le bouton **+** ouvre un sélecteur d'applications avec recherche ; la corbeille retire une application. Valise (`io.gitlab.shogu.Valise.desktop`) est inscrite par défaut.
- Une fenêtre maximisée n'est pas épinglée automatiquement et le bouton est inactif pour une fenêtre active maximisée, les types dock/bureau/écran de démarrage ou l'absence de fenêtre active. Une fenêtre déjà épinglée puis maximisée garde son marquage ; la restaurer pour pouvoir la désépingler.
- L'icône suit la fenêtre épinglée, pas le focus ; elle reste visible après changement de fenêtre et se resynchronise si l'état est changé par le menu natif ou si la fenêtre épinglée est fermée. S'il y a plusieurs fenêtres épinglées, la plus récente est représentée.
- Position : avant-dernière place de la zone d'état droite, juste avant le menu système. Cette intégration utilise `Main.panel._rightBox`, membre privé de GNOME Shell susceptible de changer.
- Deux préférences : le raccourci Super+T et la liste des applications à épingler à l'ouverture.

## Évolutions récentes

### v32
- Groupe de préférences « Au premier plan dès l'ouverture », liste des applications, sélecteur avec recherche et icônes, bouton d'ajout et retrait par application.
- La clé `auto-above-apps` stocke des identifiants de fichiers `.desktop` ; Valise (`io.gitlab.shogu.Valise.desktop`) est l'entrée par défaut.
- Correspondance par application reconnue par GNOME Shell, puis identifiant GTK ou `WM_CLASS` ; compatibilité conservée pour les anciennes entrées sans identifiant desktop.
- Huit nouvelles chaînes traduites en français.

### v31
- Ajout du module `autoAbove.js` : épinglage automatique au premier affichage (`shown`), y compris pour les fenêtres déjà ouvertes lors de l'activation.
- Nettoyage des signaux de fenêtre et d'affichage à la désactivation.

## Installation

L'archive v32 est nommée `always-on-top-always-on-top@localhost-v32.zip`. Depuis le dossier de l'extension :

```fish
gnome-extensions install --force "always-on-top-always-on-top@localhost-v32.zip"
# Sous Wayland : déconnexion / reconnexion obligatoire après installation
gnome-extensions enable "always-on-top-always-on-top@localhost"
gnome-extensions prefs "always-on-top-always-on-top@localhost"
```

Journal en cas de souci :

```fish
journalctl --user -b -o cat /usr/bin/gnome-shell | grep -i "always-on-top"
```

## Raccourci Super+T

- Rien n'est lié à Super+T par défaut dans GNOME.
- Si l'ancienne astuce avait été appliquée, réinitialiser la clé pour éviter un double déclenchement :

```fish
gsettings reset org.gnome.desktop.wm.keybindings always-on-top
```

- Si Super+T est déjà utilisé par un raccourci personnalisé, changer l'un des deux.
- Pour modifier la combinaison (exemple avec Super+Maj+T), puis désactiver/réactiver l'interrupteur dans les préférences :

```fish
gsettings --schemadir "$HOME/.local/share/gnome-shell/extensions/always-on-top-always-on-top@localhost/schemas" set org.gnome.shell.extensions.always-on-top-always-on-top aot-toggle-shortcut "['<Super><Shift>t']"
```

Si l'enregistrement échoue, l'extension signale le problème par notification et dans le journal, puis désactive le réglage. Le nom de raccourci utilisé est `aot-toggle-shortcut` ; la v20 avait échoué avec le nom générique `toggle-shortcut`, corrigé en v21.

## Tests

### Hors session GNOME
- Syntaxe JavaScript de `extension.js` et `prefs.js` (`node --check`).
- Schéma GSettings compilé avec `glib-compile-schemas --strict`, XML et `metadata.json) validés.
- Catalogue français recompilé et archive vérifiée avec `unzip -t`.
- Modules v31/v32 (`autoAbove.js`, `prefs/autoAboveGroup.js`, `prefs/appPicker.js`) vérifiés avec `node --check`, schéma `auto-above-apps` compilé en strict.

### En session GNOME
- Jusqu'à v18 : bascule au clic, relais vers l'icône de l'app épinglée, survol aligné sur Copyous, d'après les retours précédents.
- v20 sous GNOME 51 : chargement et préférences constatés ; l'enregistrement du raccourci échouait à cause d'un nom déjà pris, corrigé en v21.
- À vérifier : Super+T en v22+, état sur fenêtre maximisée, épinglage automatique v31/v32, sélecteur d'applications et icône de Valise.

## Compatibilité

Compatibilité déclarée GNOME Shell 45 à 51 (ESM / `gi://`). GNOME 51 est la session de référence ; les versions 45 à 50 sont déclarées mais non toutes vérifiées.
