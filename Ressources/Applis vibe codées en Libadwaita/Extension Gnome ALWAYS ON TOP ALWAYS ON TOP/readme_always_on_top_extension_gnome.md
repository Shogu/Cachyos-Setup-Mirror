# Always on top, always on top

Une extension GNOME Shell libadwaita ultra-basique : **une seule icône native**
dans la topbar qui active/désactive la fonction native GNOME « Toujours au
premier plan » (*always on top*) sur la fenêtre active.

Clin d'œil au nom : l'extension est elle-même « toujours au premier plan » dans
la liste... et son unique boulot, c'est le *always on top*. 😄

## Ce que ça fait

- **Une icône, un rôle.** Clic gauche = bascule `make_above()` / `unmake_above()`
  de Mutter sur la fenêtre active — exactement la fonction native derrière le
  clic droit sur la barre de titre → « Toujours au premier plan ». Zéro
  réinvention.
- **État lisible par l'icône elle-même :**
  - *Inactif* → icône symbolique **Adwaita native `radio`** (bouton radio
    non coché — évoque directement un état binaire off/on).
  - *Actif (fenêtre épinglée)* → l'icône **passe le relais à l'icône de
    l'application épinglée** : mapping prioritaire pour quelques apps
    (Ptyxis, GNOME Text Editor, Nautilus, Clapper, Grimoire), sinon variante
    monochrome `-symbolic` de l'icône déclarée par l'app si elle existe, sinon
    repli générique (`application-x-executable-symbolic`).
- **Cartouche de survol resserrée**, alignée sur la géométrie des icônes de
  statut voisines (`stylesheet.css`, classe `aot-indicator`). Le bouton du
  panel calcule sa largeur via les propriétés propres à GNOME Shell
  `-natural-hpadding` / `-minimum-hpadding` (pas la propriété CSS standard
  `padding`, qui n'a aucun effet ici) ; on les ramène à une valeur unique
  symétrique. La couleur/opacité au survol reste celle, 100 % native, du
  thème (`.panel-button:hover`) — seule la géométrie est corrigée.
- **Suit la fenêtre épinglée, pas le focus** : l'icône reste sur l'app
  épinglée même quand tu changes de fenêtre, et se resynchronise si l'état
  est changé autrement (menu de la fenêtre, fermeture de la fenêtre
  épinglée). S'il y a plusieurs fenêtres épinglées, l'icône montre la plus
  récente.
- **Icônes 100 % thème**, aucune couleur codée en dur : piochées dans le
  thème d'icônes système via `Gio.ThemedIcon` (aucun fichier bundlé).
- **Zéro dépendance, zéro préférence, zéro menu.** Un seul fichier
  `extension.js`.
- **Position simple et stable** dans la zone d'état (droite), sans API interne
  non documentée.

## Installation

```bash
gnome-extensions install --force "always-on-top-always-on-top@localhost.shell-extension.zip"
# X11 : Alt+F2 puis « r » — Wayland : déconnexion/reconnexion
gnome-extensions enable always-on-top-always-on-top@localhost
```

## Notes

- Compatible GNOME Shell 45 → 50 (ESM / `gi://`).
- Toutes les icônes viennent du thème système (Adwaita ou son équivalent sur
  le thème actif) : rien n'est embarqué dans le paquet.
