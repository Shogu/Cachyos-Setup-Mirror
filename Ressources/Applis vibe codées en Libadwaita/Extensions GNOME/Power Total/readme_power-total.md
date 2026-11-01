# Power Total

Version **0.1.1** — extension GNOME Shell **50**. UUID : `power-total@ogu`.

Power Total réunit [Auto Power Profile](https://github.com/dmy3k/auto-power-profile) et [Power Switching Manager](https://github.com/joseruibarros/power-switching-manager), qu’elle remplace dans ce setup.

## Fonctions

- profils énergétiques distincts sur secteur et batterie ;
- profils par application et mémorisation optionnelle des changements manuels ;
- économie à batterie faible et protection expérimentale contre un chargeur insuffisant ;
- luminosité de l’écran, thème clair/sombre et rétroéclairage du clavier selon l’alimentation ;
- modules activables séparément dans des préférences Libadwaita en français.

Par défaut, seul le changement de profil est actif : **Performance sur secteur**, **Équilibré sur batterie**. Les autres modules sont désactivés. La luminosité et le rétroéclairage dépendent des capacités exposées par GNOME et le matériel.

## Installation et migration

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

## Classement et réglages

Dans Extension Manager Ogu, sélectionner **Catégorie automatique** pour obtenir **Système et énergie**. La description de la version 0.1.1 contient le mot « énergie » reconnu par le gestionnaire ; un classement manuel reste prioritaire.

Si le module de luminosité est utilisé, désactiver la luminosité automatique de GNOME pour éviter deux réglages concurrents :

```fish
gsettings set org.gnome.settings-daemon.plugins.power ambient-enabled false
```

Power Total demande les profils au service énergétique existant via son interface PPD. Elle n’installe aucun daemon supplémentaire et ne configure pas directement SCX.

## Désinstallation

```fish
gnome-extensions disable power-total@ogu
gnome-extensions uninstall power-total@ogu
```

La désactivation conserve les derniers profil, thème et niveaux de luminosité appliqués.

## Validation et sources

Syntaxe JavaScript, schémas GSettings et tests de profils avec services simulés contrôlés ; classement automatique vérifié selon les règles du gestionnaire. **Non testé en session GNOME réelle.**

Le ZIP contient les sources lisibles, le README détaillé, les tests et les licences des deux projets d’origine. La relance forcée du mode Performance sur le signal « lap-detected » de l’ancienne extension n’est pas reprise.
