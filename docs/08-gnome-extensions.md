# 8 — Extensions GNOME

[Accueil](../README.md) · [Précédent](07-gnome-ui.md) · [Suivant](09-nautilus-workflow.md)

> **Dans ce chapitre :** sélection d'extensions GNOME Shell classées par usage (essentielles, productivité, esthétiques, optionnelles, obsolètes).

- [8.1 Validation des versions d'extensions](#81--validation-des-versions-dextensions)
- [8.2 Essentielles](#82--essentielles)
- [8.3 Productivité](#83--productivité)
- [8.4 Esthétiques](#84--esthétiques)
- [8.5 Optionnelles](#85--optionnelles)
- [8.6 Extension maison : Always on top, always on top](#86--extension-maison--always-on-top-always-on-top)
- [8.7 Focus & Boutons](#87--focus--boutons)
- [8.8 Battery Time Compact — Ogu](#88--battery-time-compact--ogu)

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

- **Focus & Boutons** — extension maison GNOME 50/51 : auto-fermeture de Quick Settings et du panneau Calendrier/Notifications, boutons Réglages et Power scindés, masquage de Capture d’écran, libellé **Énergie**, carte RDV bleue et masquage des notifications vides. Voir [11.18](11-applications-vibe-coded.md#1118--focus--boutons).
- **Battery Time Compact — Ogu** — fork local GNOME 50/51 : top bar `temps - pourcentage`, bouton batterie Quick Settings `temps - watts`. Voir [11.19](11-applications-vibe-coded.md#1119--battery-time-compact--ogu).
- [AutoActivities](https://extensions.gnome.org/extension/5500/auto-activities/)
- [Power Switching Manager](https://extensions.gnome.org/extension/9178/power-switching-manager/) — supprimer la luminosité automatique dans les réglages GNOME !
- [Hot Edge](https://extensions.gnome.org/extension/4222/hot-edge/)
- [Drag'n'Tile](https://extensions.gnome.org/extension/7863/dragntile/)
- [Quick Close Overview](https://extensions.gnome.org/extension/352/middle-click-to-close-in-overview/)
- [Auto Power Profile](https://extensions.gnome.org/extension/6583/auto-power-profile/)



## 8.3 — Productivité

- [Caffeine](https://extensions.gnome.org/extension/517/caffeine/)
- [Copyous](https://extensions.gnome.org/extension/8834/copyous/) : penser à installer la dépendance libgda6 `sudo pacman -S libgda6`
- [Now Playing Card](https://extensions.gnome.org/extension/10736/now-playing-card/) — solution générique pour les lecteurs MPRIS ; dans les préférences, régler **Location** sur **Quick Settings** plutôt que **Panel**.
- **Musicäa** — alternative maison dédiée à **Gapless (G4Music)** : conserve le lecteur média GNOME dans le panneau Calendrier/Notifications et ajoute seulement un indicateur à trois barres dans Quick Settings. Choisir **Now Playing Card** pour une solution générique multi-lecteurs, ou **Musicäa** pour une intégration spécifiquement pensée pour Gapless. Voir [Applications Vibe Coded — Musicäa](11-applications-vibe-coded.md#1116--musicäa).
- **Session Keeper** — extension GNOME Shell de productivité qui sauvegarde en continu la session et restaure rapidement les applications, fenêtres, espaces de travail, disposition et états de fenêtres. Version adaptée à GNOME 50, avec restauration multi-fenêtres et options avancées. Voir [Applications Vibe Coded — Session Keeper](11-applications-vibe-coded.md#1117--session-keeper).


## 8.4 — Esthétiques

- [Panel Corners](https://extensions.gnome.org/extension/4805/panel-corners/)
- [Just Perfection](https://extensions.gnome.org/extension/3843/just-perfection/) pour les réglages d’interface restant utiles ; le masquage du bouton Capture d’écran de Quick Settings est désormais pris en charge par **Focus & Boutons**.


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


## 8.7 — Focus & Boutons

Extension GNOME Shell maison compatible **GNOME 50 et 51**. Elle regroupe les ajustements de Quick Settings et du panneau Calendrier/Notifications afin d’éviter d’empiler plusieurs petites extensions.

Fonctions principales :

- fermeture automatique de **Quick Settings** et du panneau **Calendrier/Notifications** après sortie du pointeur, avec délai réglable ;
- bouton **Capture d’écran** masquable sans désactiver les raccourcis GNOME ;
- bouton **Réglages scindé** : clic principal vers Paramètres GNOME, chevron vers Ajustements, Éditeur dconf et Extensions Manager ;
- bouton **Power scindé** : clic principal vers Éteindre, chevron vers Suspendre, Redémarrer, Redémarrer la session et Verrouiller la session ;
- les deux boutons scindés deviennent **bleu Adwaita uniquement pendant l’ouverture de leur menu** ;
- libellé du profil de puissance raccourci en **Énergie** ;
- carte des rendez-vous bleue et masquage optionnel de la grande zone Notifications lorsqu’elle est vide ;
- panneau de préférences pour activer ou désactiver les fonctions.

Depuis la racine du dépôt :

```fish
gnome-extensions install --force "Ressources/Applis vibe codées en Libadwaita/Extensions GNOME/Focus & Boutons/Focus-et-Boutons-v12.zip"
gnome-extensions enable focus-et-boutons@ogu
```

Préférences :

```fish
gnome-extensions prefs focus-et-boutons@ogu
```

## 8.8 — Battery Time Compact — Ogu

Fork local de **Battery Time (Percentage) Compact**, adapté à **GNOME 50 et 51**.

- top bar : `9:27 - 56%` ;
- Quick Settings : `9:27 - 4.2 W` ;
- le pourcentage reste toujours visible dans la top bar ;
- la puissance instantanée provient de `UPower.Device.EnergyRate` ;
- la synchronisation v53 réapplique le texte après chaque actualisation UPower.

Installation :

```fish
gnome-extensions install --force "Ressources/Applis vibe codées en Libadwaita/Extensions GNOME/Battery Time Compact Ogu/Battery-Time-Compact-Ogu-v53.zip"
gnome-extensions enable batterytimepercentagecompact@sagrland.de
```

---

Pour les extensions qui changent les profils d'alimentation : voir [Optimisations & performance](05-performance-tuning.md#51--coordonner-tuned-les-profils-énergétiques-et-scx).

[Accueil](../README.md) · [Précédent](07-gnome-ui.md) · [Suivant](09-nautilus-workflow.md)
