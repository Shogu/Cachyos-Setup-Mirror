# Stethoscope 0.6.4

Application GNOME GTK4/libadwaita pour analyser les erreurs du démarrage actuel et consulter les journaux. Le paquet binaire Arch est livré dans ce dossier, sans les sources.

- **Diagnostic** : événements de priorité 0 à 3 regroupés par service et signature, avec fiche de détail et contexte.
- **Journaux** : catégories noyau, réseau, GNOME, audio, matériel et pacman ; filtres par gravité et recherche avec surlignage.
- **Système** : aperçu du démarrage, de la mémoire, du stockage et des ordonnanceurs, visible sans ouvrir chaque ligne.
- **Export** : rapport local `.txt` accessible par le bouton icône. Aucune donnée n'est transmise automatiquement.

La présence d'un message de priorité élevée ne signifie pas nécessairement une panne. Le contrôle des paramètres noyau ne détecte que les paramètres signalés comme inconnus ou ignorés dans les messages conservés. La collecte du journal dépend des droits de lecture de l'utilisateur. Snapper a été retiré de cette version.

## Installation

Depuis la racine du dépôt (commande compatible fish) :

```fish
sudo pacman -U "Ressources/Applis vibe codées en Libadwaita/Stethoscope/stethoscope-0.6.4-1-any.pkg.tar.zst"
stethoscope
```

## Désinstallation

```fish
sudo pacman -Rns stethoscope
```
