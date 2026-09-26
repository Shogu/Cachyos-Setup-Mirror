# 8 — Extensions GNOME

[Accueil](../README.md) · [Précédent](07-gnome-ui.md) · [Suivant](09-nautilus-workflow.md)

> **Dans ce chapitre :** sélection d'extensions GNOME Shell classées par usage (essentielles, productivité, esthétiques, optionnelles, obsolètes).

- [8.1 Validation des versions d'extensions](#81--validation-des-versions-dextensions)
- [8.2 Essentielles](#82--essentielles)
- [8.3 Productivité](#83--productivité)
- [8.4 Esthétiques](#84--esthétiques)
- [8.5 Optionnelles](#85--optionnelles)
- [8.6 Extension maison : Always on top, always on top](#86--extension-maison--always-on-top-always-on-top)

## 8.1 — Validation des versions d'extensions

En cas de mise à jour de GNOME Shell, le mémo propose de désactiver temporairement la validation des versions plutôt que de modifier chaque `metadata.json` :

```fish
gsettings set org.gnome.shell disable-extension-version-validation true
```

Cela ne rend pas une extension incompatible fonctionnelle ; réactiver la validation une fois les extensions adaptées :

```fish
gsettings set org.gnome.shell disable-extension-version-validation false
```

## 8.2 — Essentielles

Extensions apportant des fonctions d'interface ou de système considérées comme centrales dans ce setup :

- [Battery Time Percentage Compact](https://extensions.gnome.org/extension/2929/battery-time-percentage-compact/) ou [Battery Time](https://extensions.gnome.org/extension/5425/battery-time/)
- [AutoActivities](https://extensions.gnome.org/extension/5500/auto-activities/)
- [Power Switching Manager](https://extensions.gnome.org/extension/9178/power-switching-manager/) — supprimer la luminosité automatique dans les réglages GNOME !
- [Hot Edge](https://extensions.gnome.org/extension/4222/hot-edge/)
- [Drag'n'Tile](https://extensions.gnome.org/extension/7863/dragntile/)
- [Quick Close Overview](https://extensions.gnome.org/extension/352/middle-click-to-close-in-overview/)
- [Auto Power Profile](https://extensions.gnome.org/extension/6583/auto-power-profile/)



## 8.3 — Productivité

- [Caffeine](https://extensions.gnome.org/extension/517/caffeine/)
- [Copyous](https://extensions.gnome.org/extension/8834/copyous/) : penser à installer la dépendance libgda6 `sudo pacman -S libgda6`


## 8.4 — Esthétiques

- [Panel Corners](https://extensions.gnome.org/extension/4805/panel-corners/)
- [Just Perfection](https://extensions.gnome.org/extension/3843/just-perfection/) qui permet de réunir en une extension Grand Theft Focus, Hide Worldclocks, Hide Activities Button, Hide Screenshot, Impatience, etc.


## 8.5 — Optionnelles : à retirer après réglage

- [Privacy Settings](https://extensions.gnome.org/extension/4491/privacy-settings-menu/) — installer, effectuer les réglages voulus, puis la supprimer une fois cela fait.

## 8.6 — Extension maison : Always on top, always on top

Une icône dans la barre supérieure active ou désactive **Toujours au premier plan** pour la fenêtre active. Elle affiche l’icône de la dernière fenêtre épinglée et suit son état, même après un changement de fenêtre. Compatible GNOME Shell 45 à 50 ; sans dépendance ni préférences. [Détails et captures](11-applications-vibe-coded.md#111--always-on-top-always-on-top).

Depuis la racine du dépôt, installer [l’archive fournie](../Ressources/Applis%20vibe%20codées%20en%20Libadwaita/Extension%20Gnome%20ALWAYS%20ON%20TOP%20ALWAYS%20ON%20TOP/always-on-top-always-on-top_localhost.shell-extension.zip) :

```bash
gnome-extensions install --force "Ressources/Applis vibe codées en Libadwaita/Extension Gnome ALWAYS ON TOP ALWAYS ON TOP/always-on-top-always-on-top_localhost.shell-extension.zip"
```

Sous Wayland, se déconnecter puis se reconnecter ; ensuite activer l’extension :

```bash
gnome-extensions enable always-on-top-always-on-top@localhost
```

---

Pour les extensions qui changent les profils d'alimentation : voir [Optimisations & performance](05-performance-tuning.md#51--coordonner-tuned-les-profils-énergétiques-et-scx).

[Accueil](../README.md) · [Précédent](07-gnome-ui.md) · [Suivant](09-nautilus-workflow.md)
