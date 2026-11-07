# UI Management

Extension GNOME Shell fusionnée pour **Bureau et fenêtres**.

Elle regroupe :
- les réglages d’interface utilisés dans Just Perfection ;
- Auto Activities ;
- Hot Edge ;
- Quick Close in Overview.

Les valeurs par défaut des réglages Just Perfection ont été alignées sur les captures fournies.

## Base et licences

UI Management est un travail dérivé de Just Perfection, Auto Activities, Hot Edge et Quick Close in Overview. Les notices de licence des projets sources sont conservées dans le code dérivé et la distribution est faite sous GPL compatible avec ces sources.

## Version 2

- Les remplacements de méthodes de GNOME Shell passent par un unique `InjectionManager` (créé à l’activation, vidé à la désactivation) : plus de sauvegarde manuelle des prototypes, restauration garantie et aucun patch appliqué deux fois.
- Suppression des réglages sans interface (thème, taille des coins du panneau, taille de Looking Glass, nombre maximal de résultats de recherche, notificateur de support) et du code et des règles CSS qui leur étaient propres.
- Correction d’un plantage possible d’Auto Activities lorsqu’une fenêtre n’a plus d’espace de travail ; au démarrage, les réglages laissés à leur valeur par défaut qui ne changent rien ne sont plus appliqués inutilement.
- Compatibilité GNOME Shell 49, 50 et 51 : sous GNOME 51, `SearchController.startSearch` n’existe plus, donc l’option « Tapez pour rechercher » n’a plus d’effet de désactivation.

## Version 3

- Retrait des réglages « Taille du panneau », « Taille de l’icône du panneau », « Marge intérieure des boutons du panneau » et « Marge intérieure de l’indicateur de panneau » : revenir à « Par thème Shell » ne rétablissait pas toujours l’affichage d’origine. Ces quatre valeurs sont remises à leur défaut au chargement de l’extension, donc le thème Shell s’applique.
- Le décalage du menu de l’horloge ne descend plus sous 0 (valeur minimale du schéma).
