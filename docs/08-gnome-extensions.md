# 8 — Extensions GNOME

[Accueil](../README.md) · [Précédent](07-gnome-ui.md) · [Suivant](09-nautilus-workflow.md)

> **Dans ce chapitre :** sélection d'extensions GNOME Shell classées par usage (essentielles, productivité, esthétiques, optionnelles, obsolètes).

- [8.1 Validation des versions d'extensions](#81--validation-des-versions-dextensions)
- [8.2 Essentielles](#82--essentielles)
- [8.3 Productivité](#83--productivité)
- [8.4 Esthétiques](#84--esthétiques)
- [8.5 Optionnelles](#85--optionnelles)
- [8.6 Extension maison : Always on top, always on top](#86--extension-maison--always-on-top-always-on-top)
- [8.7 Quick Settings](#87--quick-settings)
- [8.8 Widget Topbar](#88--widget-topbar)
- [8.9 Power Total](#89--power-total)
- [8.10 UI Management](#810--ui-management)
- [8.11 Classer les extensions avec Extension Manager](#811--classer-les-extensions-avec-extension-manager)

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

- **Quick Settings** — extension maison qui remplace Focus & Boutons et Battery Time Compact — Ogu : personnalisations du panneau des réglages rapides et affichage compact de l'autonomie, du pourcentage et de la puissance instantanée en watts. Voir [8.7](#87--quick-settings), [11.17](11-applications-vibe-coded.md#1117--quick-settings) et [son dossier](../Ressources/Applis%20vibe%20codées%20en%20Libadwaita/Extensions%20GNOME/Quick%20Settings/).
- **Widget Topbar** — extension qui remplace Topbar Center Widget et regroupe les widgets de la barre supérieure et du menu de l'horloge, notamment les notes Grimoire, le lecteur Semitone et l'agenda. Voir [8.8](#88--widget-topbar), [11.18](11-applications-vibe-coded.md#1118--widget-topbar) et [son dossier](../Ressources/Applis%20vibe%20codées%20en%20Libadwaita/Extensions%20GNOME/Widget%20Topbar/).
- **UI Management** — extension maison **GNOME 49/50/51**, classée dans **Bureau et fenêtres**. Elle remplace dans ce setup **Just Perfection**, **AutoActivities**, **Hot Edge** et **Quick Close Overview** en ne conservant que les fonctions réellement utilisées. Voir [8.10](#810--ui-management) et [11.21](11-applications-vibe-coded.md#1120--ui-management).
- [Power Total](#89--power-total) — extension maison GNOME 50, catégorie **Système et énergie** : profils secteur/batterie, luminosité, thème et rétroéclairage. Voir [11.20](11-applications-vibe-coded.md#1119--power-total).
- [Drag'n'Tile](https://extensions.gnome.org/extension/7863/dragntile/)



## 8.3 — Productivité

- [Caffeine](https://extensions.gnome.org/extension/517/caffeine/)
- **Chihito — bascule de lancement dans Quick Settings** : l’extension GNOME Shell `chihiro-quicksettings-launch-toggle@ogu` est intégrée au paquet de l’application. Installer le paquet, se déconnecter puis se reconnecter à GNOME sous Wayland pour que Shell découvre l’extension, puis l’activer :
  ```fish
  sudo pacman -U "Ressources/Applis vibe codées en Libadwaita/01-Multimedia/Chihito/chihiro-0.6.1-1-any.pkg.tar.zst"
  ```
  Après reconnexion :
  ```fish
  gnome-extensions enable chihiro-quicksettings-launch-toggle@ogu
  ```
  Voir le [README de Chihito](../Ressources/Applis%20vibe%20codées%20en%20Libadwaita/01-Multimedia/Chihito/README.md).
- **Copyous — fork corrigé pour GNOME 51** : ajoute le **Multi-Paste Picker**, une fenêtre multi-presse-papiers ouverte par **Super+V** (configurable), avec sélection multiple par Ctrl+clic ou Espace, aperçu des images et collage séquentiel (300 ms entre les entrées). Le raccourci peut être désactivé dans les préférences ou le menu contextuel de l’icône ; le dialogue principal historique reste accessible par **Super+Shift+V**. Le menu propose aussi les interrupteurs **Multi-Paste Picker**, **Mode accumule** et **Mode incognito**. L’archive fournie est à placer dans `Ressources/Applis vibe codées en Libadwaita/Extensions GNOME/Copyous/copyous-gnome51.zip` (fichier à ajouter manuellement au dépôt). Installer la dépendance puis l’extension :
  ```fish
  sudo pacman -S --needed libgda6
  gnome-extensions install --force "Ressources/Applis vibe codées en Libadwaita/Extensions GNOME/Copyous/copyous-gnome51.zip"
  gnome-extensions enable copyous@boerdereinar.dev
  ```
  La copie préparée pour le dépôt ajoute `51` à `shell-version` dans `metadata.json`. Cette correction de métadonnées ne remplace pas un test fonctionnel en session GNOME 51. Voir le [README de Copyous](../Ressources/Applis%20vibe%20codées%20en%20Libadwaita/Extensions%20GNOME/Copyous/README.md) pour les détails.
- **Session Keeper** — extension GNOME Shell de productivité qui sauvegarde en continu la session et restaure rapidement les applications, fenêtres, espaces de travail, disposition et états de fenêtres. Version adaptée à GNOME 50, avec restauration multi-fenêtres et options avancées. Voir [Applications Vibe Coded — Session Keeper](11-applications-vibe-coded.md#1116--session-keeper).


## 8.4 — Esthétiques

- [Panel Corners](https://extensions.gnome.org/extension/4805/panel-corners/)

**Just Perfection n’est plus installée séparément dans ce setup** : les options réellement utilisées ont été reprises dans **UI Management**. Le masquage du bouton Capture d’écran de Quick Settings est désormais intégré à **Quick Settings**.


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


## 8.7 — Quick Settings

Extension GNOME Shell maison qui remplace **Focus & Boutons** et **Battery Time Compact — Ogu**. Elle regroupe les personnalisations de Quick Settings et l'affichage compact de la batterie, notamment l'autonomie, le pourcentage et la puissance instantanée en watts.

Le dossier [Quick Settings](../Ressources/Applis%20vibe%20codées%20en%20Libadwaita/Extensions%20GNOME/Quick%20Settings/) accueillera l'archive, les sources et le README. Les détails d'installation seront ajoutés avec ces fichiers.

## 8.8 — Widget Topbar

Extension GNOME Shell qui remplace **Topbar Center Widget**. Elle regroupe les widgets de la barre supérieure et du menu de l'horloge, notamment les notes épinglées dans Grimoire, le lecteur Semitone et les éléments d'agenda.

Le dossier [Widget Topbar](../Ressources/Applis%20vibe%20codées%20en%20Libadwaita/Extensions%20GNOME/Widget%20Topbar/) accueillera l'archive, les sources et le README. Les détails d'installation seront ajoutés avec ces fichiers.

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

Les contrôles statiques et les tests avec services simulés ne remplacent pas un essai dans une session GNOME réelle.

## 8.10 — UI Management

Extension GNOME Shell maison dédiée à la **gestion du bureau et des fenêtres**, compatible **GNOME Shell 49, 50 et 51** et classée dans **Bureau et fenêtres** par Extension Manager Ogu.

Elle remplace quatre extensions auparavant installées séparément :

- **Just Perfection** — uniquement les options effectivement utilisées dans le setup ;
- **AutoActivities** ;
- **Hot Edge** ;
- **Quick Close Overview** / fermeture rapide d’une fenêtre depuis l’Overview.

Les préférences sont regroupées en quatre pages : **Visibilité**, **Comportement**, **Personnaliser** et **Automatisation**. Les blocs Auto Activities, Hot Edge et Quick Close in Overview restent indépendamment activables.


Voir aussi [Applications Vibe Coded — UI Management](11-applications-vibe-coded.md#1120--ui-management).

## 8.11 — Classer les extensions avec Extension Manager

Le setup utilise [Extension Manager personnalisé](11-applications-vibe-coded.md#1121--extension-manager), une application GTK4/libadwaita installée avec le paquet `extension-manager-ogu`. L’[installation du paquet local](10-logiciels.md#1013--extension-manager) remplace la version standard.

Dans l’onglet **Installées**, les extensions utilisateur sont regroupées en sept catégories : **Interface et apparence**, **Bureau et fenêtres**, **Barre supérieure et réglages rapides**, **Productivité**, **Système et énergie**, **Multimédia**, **Autres**. Les extensions système restent séparées.

Le classement automatique utilise les UUID connus, puis le nom et la description. Le menu de classement d’une extension permet de choisir une catégorie manuellement ; **Catégorie automatique** rétablit la détection. Les choix manuels sont mémorisés et restent prioritaires. Power Total 0.1.1 est reconnue dans **Système et énergie** grâce à sa description.

Le panneau **Parcourir** conserve le mécanisme de recherche de l’application originelle. Aucun filtre de version GNOME N+1/N−1 n’a été ajouté. L’icône personnalisée Ogu est incluse.

La procédure d’installation du paquet local est décrite dans [10.1.3 — Extension Manager](10-logiciels.md#1013--extension-manager).

---

Pour les extensions qui changent les profils d'alimentation : voir [Optimisations & performance](05-performance-tuning.md#51--coordonner-tuned-les-profils-énergétiques-et-scx).

[Accueil](../README.md) · [Précédent](07-gnome-ui.md) · [Suivant](09-nautilus-workflow.md)
