# Extension Manager

Version personnalisée **0.6.5.ogu2-1**, paquet Arch natif **x86_64** : `extension-manager-ogu`.

Basée sur [Extension Manager de Matt Jakeman](https://github.com/mjakeman/extension-manager), avec classement local des extensions installées et icône personnalisée Ogu. C’est une application GTK4/libadwaita qui gère les extensions GNOME Shell.

## Fonctions ajoutées

- classement automatique en sept catégories : **Interface et apparence**, **Bureau et fenêtres**, **Barre supérieure et réglages rapides**, **Productivité**, **Système et énergie**, **Multimédia**, **Autres** ;
- menu de classement sur chaque extension pour changer manuellement sa catégorie ;
- option **Catégorie automatique** pour revenir au classement proposé ;
- mémorisation des choix manuels, prioritaires sur la détection automatique ;
- extensions système présentées séparément ;
- icône personnalisée fournie pour l’application.

Le classement automatique s’appuie sur des UUID connus, puis le nom et la description de l’extension. Il s’agit d’un classement local au gestionnaire.

La version ogu2 repart de l’application originelle pour conserver le panneau **Parcourir** et son mécanisme de recherche, tout en ajoutant le classement. Aucun filtre supplémentaire GNOME N+1/N−1 n’est ajouté.

## Installation

Depuis la racine du dépôt :

```fish
sudo pacman -U "Ressources/Applis vibe codées en Libadwaita/Extension Manager/extension-manager-ogu-0.6.5.ogu2-1-x86_64.pkg.tar.zst"
```

Si la version des dépôts `extension-manager` est installée, accepter son remplacement proposé par pacman. Le paquet local s’appelle `extension-manager-ogu`, fournit `extension-manager` et entre en conflit avec la version des dépôts.

Fermer complètement l’ancienne instance, puis lancer l’application :

```fish
extension-manager
```

Les dépendances sont déclarées dans le paquet, dont **libadwaita ≥ 1.8**, GTK4, libsoup3, glycin et glycin-gtk4. Les catégories personnalisées déjà enregistrées sont conservées lors de la mise à jour.

## Utilisation

Ouvrir **Installées**, puis le menu de classement de l’extension concernée. Choisir une catégorie, ou **Catégorie automatique** pour laisser le gestionnaire la déterminer. Par exemple, la description de Power Total 0.1.1 permet son classement dans **Système et énergie**.

## Désinstallation

```fish
sudo pacman -R extension-manager-ogu
```

Pour revenir ensuite à la version des dépôts :

```fish
sudo pacman -S extension-manager
```

## Vérifications

L’archive jointe a été contrôlée : métadonnées Arch, exécutable, lanceur et icônes présents. Le paquet est publié sans modification de son contenu. Aucun test de lancement en session GNOME réelle n’a été effectué pour cette intégration au dépôt.

Licence déclarée par le paquet : **GPL-3.0-or-later**. Ce dossier contient le paquet installable et ce README.
