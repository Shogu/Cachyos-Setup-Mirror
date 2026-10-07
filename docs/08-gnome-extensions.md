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
- [8.9 Power Total](#89--power-total)
- [8.10 UI Management](#810--ui-management)

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
- **UI Management** — extension maison **GNOME 49/50/51**, classée dans **Bureau et fenêtres**. Elle remplace dans ce setup **Just Perfection**, **AutoActivities**, **Hot Edge** et **Quick Close Overview** en ne conservant que les fonctions réellement utilisées. Voir [8.10](#810--ui-management) et [11.21](11-applications-vibe-coded.md#1121--ui-management).
- [Power Total](#89--power-total) — extension maison GNOME 50, catégorie **Système et énergie** : profils secteur/batterie, luminosité, thème et rétroéclairage. Voir [11.20](11-applications-vibe-coded.md#1120--power-total).
- [Drag'n'Tile](https://extensions.gnome.org/extension/7863/dragntile/)



## 8.3 — Productivité

- [Caffeine](https://extensions.gnome.org/extension/517/caffeine/)
- [Copyous](https://extensions.gnome.org/extension/8834/copyous/) : penser à installer la dépendance libgda6 `sudo pacman -S libgda6`
- [Now Playing Card](https://extensions.gnome.org/extension/10736/now-playing-card/) — solution générique pour les lecteurs MPRIS ; dans les préférences, régler **Location** sur **Quick Settings** plutôt que **Panel**.
- **Musicäa** — alternative maison dédiée à **Gapless (G4Music)** : conserve le lecteur média GNOME dans le panneau Calendrier/Notifications et ajoute seulement un indicateur à trois barres dans Quick Settings. Choisir **Now Playing Card** pour une solution générique multi-lecteurs, ou **Musicäa** pour une intégration spécifiquement pensée pour Gapless. Voir [Applications Vibe Coded — Musicäa](11-applications-vibe-coded.md#1116--musicäa).
- **Session Keeper** — extension GNOME Shell de productivité qui sauvegarde en continu la session et restaure rapidement les applications, fenêtres, espaces de travail, disposition et états de fenêtres. Version adaptée à GNOME 50, avec restauration multi-fenêtres et options avancées. Voir [Applications Vibe Coded — Session Keeper](11-applications-vibe-coded.md#1117--session-keeper).


## 8.4 — Esthétiques

- [Panel Corners](https://extensions.gnome.org/extension/4805/panel-corners/)

**Just Perfection n’est plus installée séparément dans ce setup** : les options réellement utilisées ont été reprises dans **UI Management**. Le masquage du bouton Capture d’écran de Quick Settings reste, lui, géré par **Focus & Boutons**.


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

## 8.9 — Power Total

Extension GNOME Shell **50**, version **0.1.1**, remplaçant **Auto Power Profile** et **Power Switching Manager** dans ce setup. Classée automatiquement dans **Système et énergie** par Extension Manager Ogu.

Elle regroupe les profils énergétiques sur secteur/batterie et par application, la luminosité de l’écran, le thème clair/sombre et le rétroéclairage du clavier. Chaque module peut être activé séparément. Seul le changement de profil est actif par défaut : **Performance sur secteur**, **Équilibré sur batterie**.

Depuis la racine du dépôt, installer l’archive :

```fish
gnome-extensions install --force "Ressources/Applis vibe codées en Libadwaita/Extensions GNOME/Power Total/Power-Total.zip"
```

Se déconnecter puis se reconnecter à GNOME. Désactiver les deux anciennes extensions avant d’activer Power Total :

```fish
gnome-extensions disable auto-power-profile@dmy3k.github.io
gnome-extensions disable power-switching-manager@joseruibarros.com
gnome-extensions enable power-total@ogu
gnome-extensions prefs power-total@ogu
```

Si une ancienne extension n’est pas installée, sa commande de désactivation peut signaler qu’elle est introuvable. Le bouton **Importer** des préférences permet de récupérer ses réglages personnalisés ; les modules supplémentaires restent à activer séparément.

Si la gestion de luminosité de Power Total est activée, désactiver la luminosité automatique de GNOME :

```fish
gsettings set org.gnome.settings-daemon.plugins.power ambient-enabled false
```

[README et archive Power Total](../Ressources/Applis%20vibe%20codées%20en%20Libadwaita/Extensions%20GNOME/Power%20Total/readme_power-total.md). Les contrôles statiques et les tests avec services simulés ne remplacent pas un essai dans une session GNOME réelle.

## 8.10 — UI Management

Extension GNOME Shell maison dédiée à la **gestion du bureau et des fenêtres**, compatible **GNOME Shell 49, 50 et 51** et classée dans **Bureau et fenêtres** par Extension Manager Ogu.

Elle remplace quatre extensions auparavant installées séparément :

- **Just Perfection** — uniquement les options effectivement utilisées dans le setup ;
- **AutoActivities** ;
- **Hot Edge** ;
- **Quick Close Overview** / fermeture rapide d’une fenêtre depuis l’Overview.

Les préférences sont regroupées en quatre pages : **Visibilité**, **Comportement**, **Personnaliser** et **Automatisation**. Les blocs Auto Activities, Hot Edge et Quick Close in Overview restent indépendamment activables.

Cette fusion évite de maintenir plusieurs extensions qui modifient des zones proches du Shell et réduit la liste d’extensions sans créer une méga-extension générale : **Focus & Boutons**, **Power Total**, **Session Keeper** et **Musicäa** restent séparées car leurs rôles sont distincts.

Voir aussi [Applications Vibe Coded — UI Management](11-applications-vibe-coded.md#1121--ui-management).

---

Pour les extensions qui changent les profils d'alimentation : voir [Optimisations & performance](05-performance-tuning.md#51--coordonner-tuned-les-profils-énergétiques-et-scx).

[Accueil](../README.md) · [Précédent](07-gnome-ui.md) · [Suivant](09-nautilus-workflow.md)
