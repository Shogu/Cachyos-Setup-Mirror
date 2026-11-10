# Snapper GTK4

**Snapper GTK4 1.4.0-7** est une interface GTK4/libadwaita pour Snapper et l'intégration Limine. Elle permet de consulter et gérer les snapshots depuis GNOME, sans réimplémenter les opérations système de Snapper/Limine.

## Fonctions

- Affichage et filtrage des snapshots : Tous, Avant et Après.
- Création et suppression de snapshots.
- Restauration via le workflow Snapper/Limine.
- Réglage des nettoyages `number`, `timeline` et des paires Avant/Après vides.
- Activation/désactivation des minuteurs systemd Snapper et lancement manuel du nettoyage.

## Changement en 1.4.0-7

Le code applicatif est désormais installé dans **`/usr/lib/snapper-gtk4/`**. Le fichier **`.pyc` parasite** livré par inadvertance dans une version précédente a été retiré du paquet.

## Installation

Depuis le dossier contenant le paquet :

```fish
sudo pacman -U ./snapper-gtk4-1.4.0-7-any.pkg.tar.zst
```

Lancer ensuite l'application sans privilèges administrateur :

```fish
snapper-gtk4
```

## Désinstallation

```fish
sudo pacman -Rns snapper-gtk4
```

Les opérations privilégiées passent par le helper Polkit fourni par le paquet. La restauration s'appuie sur les outils système Snapper/Limine.
