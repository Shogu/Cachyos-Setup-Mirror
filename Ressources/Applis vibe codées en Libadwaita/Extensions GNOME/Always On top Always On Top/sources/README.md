# Always on top always on top

Une extension GNOME Shell libadwaita ultra-basique : **une seule icône native**
dans la topbar qui active/désactive la fonction native GNOME « Toujours au
premier plan » (*always on top*) sur la fenêtre active — et, en option, un
raccourci clavier **Super+T** qui fait la même chose.

Clin d'œil au nom : l'extension est elle-même « toujours au premier plan » dans
la liste... et son unique boulot, c'est le *always on top*. 😄

## Ce que ça fait

- **Une icône, un rôle.** Clic gauche = bascule `make_above()` / `unmake_above()`
  de Mutter sur la fenêtre active — exactement la fonction native derrière le
  clic droit sur la barre de titre → « Toujours au premier plan ». Zéro
  réinvention.
- **État lisible par l'icône elle-même :**
  - *Rien d'épinglé, épinglage possible* → icône embarquée
    **`aot-pin-available-symbolic`** (carré avec carré plein central).
  - *Rien d'épinglé, épinglage impossible* (fenêtre active maximisée, ou
    aucune fenêtre active) → icône embarquée **`aot-pin-unavailable-symbolic`**
    (carré avec deux crochets opposés « [ ] » au centre). Plus de grisage : c'est la forme de
    l'icône qui parle.
  - Les deux icônes sont dessinées au gabarit de `clipboard-symbolic` de
    Copyous (16×16, contour 2 px, coins r=3) et chargées comme Copyous
    (`icons/hicolor/scalable/actions/`, `system-status-icon`).
  - *Actif (fenêtre épinglée)* → l'icône **passe le relais à l'icône de
    l'application épinglée**, cherchée dans le thème d'icônes dans cet ordre :
    1. la variante monochrome `<icône déclarée par l'app>-symbolic` si elle
       existe (y compris une icône ajoutée à la main) ;
    2. sinon une icône Adwaita générique choisie pour quelques apps (Ptyxis,
       GNOME Text Editor, Nautilus, Clapper, Grimoire) ;
    3. sinon repli générique (`application-x-executable-symbolic`).
- **Raccourci clavier Super+T (optionnel, désactivé par défaut).** Un
  interrupteur dans les préférences de l'extension (« Activer le raccourci
  Super+T »). Une fois activé, c'est l'extension qui enregistre le raccourci
  auprès de GNOME Shell ; elle le retire dès que tu coupes l'interrupteur ou
  que tu désactives l'extension. Le bouton et le raccourci passent par le même
  code : même résultat, mêmes règles.
- **Fenêtre maximisée = épinglage impossible.** Comme l'entrée « Toujours au
  premier plan » du menu natif de la fenêtre, le bouton est inactif (non
  cliquable, pas de cartouche de survol) quand la fenêtre active est
  maximisée — Mutter ne la placerait de toute façon pas au-dessus des autres —
  ainsi que pour les types de fenêtre dock, bureau et écran de démarrage, et
  quand aucune fenêtre n'a le focus. L'icône passe alors au rond vide. Le
  raccourci Super+T ne fait alors rien. Si une autre fenêtre est déjà
  épinglée, l'icône de son app reste affichée (c'est l'information qui compte),
  mais le bouton est quand même inactif tant que la fenêtre active est
  maximisée. Une fenêtre déjà épinglée puis maximisée garde son marquage
  « au-dessus » ; pour la désépingler, restaure-la d'abord, puis clique.
- **Géométrie de panel native**, calée sur Copyous : le bouton garde les
  espacements standards de `PanelMenu.Button`; seul le `padding/margin` de
  l'icône est neutralisé, comme dans Copyous.
- **Suit la fenêtre épinglée, pas le focus** : l'icône reste sur l'app
  épinglée même quand tu changes de fenêtre, et se resynchronise si l'état
  est changé autrement (menu de la fenêtre, fermeture de la fenêtre
  épinglée). S'il y a plusieurs fenêtres épinglées, l'icône montre la plus
  récente.
- **Zéro dépendance, zéro menu, une seule préférence** (l'interrupteur du
  raccourci).
- **Position** : avant-dernière place de la zone d'état de droite, juste avant
  le menu système, calculée à partir de `Main.panel._rightBox`. C'est un
  membre privé de GNOME Shell, pas une API documentée : si une version future
  le renomme, l'extension devra être adaptée.

## Installation

```fish
gnome-extensions install --force "always-on-top-always-on-top-v24-icones-copyous.shell-extension.zip"
# Wayland : déconnexion / reconnexion OBLIGATOIRE (GNOME Shell garde en mémoire
# l'ancien extension.js et les anciennes icônes tant que la session tourne)
gnome-extensions enable "always-on-top-always-on-top@localhost"
gnome-extensions prefs "always-on-top-always-on-top@localhost"
```

Journal en cas de souci :

```fish
journalctl --user -b -o cat /usr/bin/gnome-shell | grep -i "always-on-top"
```

## Le raccourci Super+T

- Rien n'est lié à Super+T par défaut dans GNOME.
- Si tu avais appliqué l'astuce vue sur Reddit
  (`gsettings set org.gnome.desktop.wm.keybindings always-on-top "['<Super>t']"`),
  remets cette clé à zéro pour éviter un double déclenchement :

  ```fish
  gsettings reset org.gnome.desktop.wm.keybindings always-on-top
  ```
- Si Super+T est déjà pris par un raccourci personnalisé (Paramètres →
  Clavier), les deux se disputent la touche : change l'un des deux.
- Si l'enregistrement du raccourci échoue, l'extension le signale par une
  notification, écrit une ligne dans le journal et repasse l'interrupteur sur
  « désactivé ». Mutter n'échoue ici que si un raccourci du même *nom* est déjà
  enregistré (noms partagés entre GNOME Shell et toutes les extensions) :
  `journalctl --user -b -o cat /usr/bin/gnome-shell | grep "re-add keybinding"`
  donne alors le nom en conflit. La v20 utilisait le nom générique
  `toggle-shortcut` et a échoué ainsi ; la v21 utilise `aot-toggle-shortcut`.
- La combinaison n'est pas modifiable dans la fenêtre de préférences (une
  seule option, volontairement). Pour en changer, puis couper/rallumer
  l'interrupteur :

  ```fish
  gsettings --schemadir "$HOME/.local/share/gnome-shell/extensions/always-on-top-always-on-top@localhost/schemas" set org.gnome.shell.extensions.always-on-top-always-on-top aot-toggle-shortcut "['<Super><Shift>t']"
  ```

## Ce qui a été testé

### Testé hors session (environnement de build, sans GNOME Shell)

- Syntaxe JavaScript de `extension.js` et `prefs.js` (`node --check`).
- Schéma GSettings compilé avec `glib-compile-schemas --strict` ; XML du
  schéma bien formé ; `metadata.json` valide.
- Catalogue de traduction française recompilé : 6 chaînes sur 6 traduites.
- Intégrité de l'archive (`unzip -t`).

### Testé en session GNOME réelle

- **Versions précédentes (d'après tes retours, jusqu'à v18) :** bascule au
  clic, relais vers l'icône de l'app épinglée, cartouche de survol aligné sur
  Copyous.
- **v20 (d'après ta capture) :** l'extension se charge sous GNOME 51 avec
  `"51"` dans `shell-version` (la notification vient de son code, exécuté par
  le shell) ; la fenêtre de préférences s'affiche, en français, avec
  l'interrupteur coupé par défaut ; le chemin d'échec fonctionne
  (notification « Impossible d'enregistrer le raccourci Super+T. » et
  interrupteur qui revient sur « désactivé »). En revanche **le raccourci
  lui-même a échoué à s'enregistrer** : nom de clé `toggle-shortcut` déjà
  pris. Corrigé en v21 ; l'origine exacte du conflit n'a pas été identifiée.
- **Journal (v20) :** deux lignes `Trying to re-add keybinding
  "toggle-shortcut"` confirment que le nom était déjà pris ; qui le détenait
  reste inconnu.
- **Non testés en session :** l'ordre de recherche des icônes de la v19, et
  en v22 le raccourci Super+T avec son nouveau nom, le passage au rond vide
  sur fenêtre maximisée et le retour au rond avec point.

### À vérifier en session

1. Interrupteur allumé : plus de notification d'échec.
2. Interrupteur allumé → Super+T bascule « toujours au premier plan » sur la
   fenêtre active ; interrupteur coupé → Super+T ne fait plus rien.
3. Super+↑ (maximiser) → l'icône passe au rond vide et le bouton ne réagit
   plus, Super+T est sans effet ; restaurer → rond avec point, bouton actif.
4. Désactiver l'extension → le raccourci est libéré.

## Notes

- Déclarée compatible GNOME Shell 45 → 51 (ESM / `gi://`). Ta session de
  référence est GNOME 51 ; les versions 45 → 50 sont déclarées mais jamais
  vérifiées.
- L'icône inactive et les icônes d'apps viennent toutes du thème d'icônes
  système (Adwaita ou équivalent) : l'extension n'embarque aucune icône.
