# Power Total — 0.1.2

Extension GNOME Shell réunissant Auto Power Profile et Power Switching Manager.
Nom : **Power Total**. UUID : `power-total@ogu`. Cible déclarée : **GNOME 50 et 51**.

## Fonctions

Une détection UPower partagée alimente quatre modules indépendants, chacun
activable dans une unique fenêtre de préférences Libadwaita en français :

- profil énergétique sur secteur / batterie ;
- luminosité globale de l’écran sur secteur / batterie ;
- thème clair / sombre sur secteur / batterie ;
- rétroéclairage du clavier sur secteur / batterie, si pris en charge par GNOME.

Les profils par application disposent d’une page avec sélection des applications.
Ils restent actifs tant qu’une application choisie possède une fenêtre.
La mémorisation des changements manuels est optionnelle. Sans mémorisation,
un choix manuel reste temporairement en place jusqu’au prochain changement
pertinent d’alimentation, d’application ou de réglage des profils.

La protection expérimentale contre un chargeur insuffisant exige 30 secondes de
décharge supérieure à 1 W sur secteur, puis conserve le profil économe jusqu’au
débranchement. L’économie à batterie faible respecte le réglage GNOME et prend
priorité sur les profils par application. La relance automatique du profil
Performance en cas de signal « lap-detected » de l’ancienne extension n’est pas
reprise : Power Total laisse le service système gérer cette limitation matérielle.

Par défaut, seul le changement automatique de profil est activé : Performance
sur secteur, Équilibré sur batterie. Les autres modules s’activent séparément.
Si Performance n’est pas proposé par le service, le module utilise Équilibré,
puis Économie si nécessaire. Aucun daemon énergétique supplémentaire n’est installé.

## Classement dans Extension Manager Ogu

Depuis la version 0.1.1, la description contient « énergie », reconnu par le
classement automatique d’Extension Manager Ogu 0.6.5.ogu2. Power Total est ainsi
classée dans « Système et énergie », sans modification du gestionnaire.
Une catégorie choisie manuellement reste prioritaire : sélectionner
« Catégorie automatique » dans le menu de classement de Power Total si nécessaire.
Après mise à jour, fermer puis rouvrir la session GNOME et relancer le gestionnaire
pour charger les nouvelles métadonnées. Les fonctions et réglages sont inchangés.

## Installation

Ouvrir un terminal dans le dossier contenant `Power-Total.zip` :

```sh
gnome-extensions install --force ./Power-Total.zip
```

Fermer puis rouvrir la session GNOME pour faire reconnaître la nouvelle extension.
Désactiver ensuite les deux anciennes extensions avant d’activer Power Total :

```sh
gnome-extensions disable auto-power-profile@dmy3k.github.io
gnome-extensions disable power-switching-manager@joseruibarros.com
gnome-extensions enable power-total@ogu
gnome-extensions prefs power-total@ogu
```

Si une ancienne extension n’est pas installée, sa commande de désactivation peut
signaler qu’elle est introuvable.

Pour désactiver Power Total :

```sh
gnome-extensions disable power-total@ogu
```

Les derniers profil, thème et niveaux de luminosité restent en place.
La désactivation n’impose pas arbitrairement un retour à Équilibré. Les appels
D-Bus encore en attente sont annulés côté client ; une écriture déjà traitée par
le service ne peut pas être annulée rétroactivement.

## Vérifications réalisées

- Syntaxe JavaScript contrôlée avec Node.
- Schémas GSettings compilés avec `glib-compile-schemas --strict`.
- Structure du ZIP et présence du schéma compilé contrôlées.

**Non testé dans une session GNOME réelle.** En particulier, le branchement /
débranchement, les accès matériels à la luminosité, le clavier, le verrouillage
et la fenêtre de préférences restent à essayer sur la machine cible. Ces tests
simulés ne constituent pas une validation matérielle.

Le code de luminosité utilise `Main.brightnessManager.globalScale` (présent dans GNOME 50 et 51).
Un moniteur non pilotable par GNOME n’est pas pris en charge automatiquement.
L’extension conserve le fonctionnement en session verrouillée (`unlock-dialog`).
Il n’y a pas de boucle de surveillance permanente : signaux UPower, D-Bus et
fenêtres, plus une temporisation uniquement pour la protection expérimentale.

## Sources et maintenance

Tous les fichiers JavaScript lisibles sont inclus dans ce ZIP.

Pour reconstruire le schéma depuis les sources extraites :

```sh
glib-compile-schemas --strict schemas
```

Origines :

- Auto Power Profile, dmy3k — https://github.com/dmy3k/auto-power-profile
  Archive source fournie : commit `44e33b2f0eb0c0a850c6b5cf055e37ed0ed0913d`, licence GPL version 3.
- Power Switching Manager, José Rui Barros — https://github.com/josbarros/power-switching-manager
  Archive source fournie : commit `b7974663bbb12f88eff331b629f82b1b05392871`, licence GPL-2.0-or-later.

Fusion distribuée sous GPL version 3. Voir `LICENSE` et `licenses/`.
