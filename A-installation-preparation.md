# A — Installation et préparation

[Accueil](README.md) · [Suivant](B-logiciels.md)

- [Préparer Fish](#a1--préparer-fish)
- [Réglages initiaux dans CachyOS Hello](#a2--réglages-initiaux-dans-cachyos-hello)
- [Nettoyer les entrées UEFI en NVRAM](#a3--nettoyer-les-entrées-uefi-en-nvram)

## A1 — Préparer Fish

Installer dès le début le fichier **`config.fish` du dépôt** dans `~/.config/fish/config.fish` afin de disposer des fonctions personnelles, notamment celles utilisées pour l’édition avec `sudoedit`.

```fish
mkdir -p ~/.config/fish
```

Copier le fichier du dépôt à cet emplacement, puis le charger :

```fish
source ~/.config/fish/config.fish
```

Le fichier reste unique : aucun découpage en fonctions séparées n’est nécessaire. Voir [les réglages Fish et éditeurs](I-reglages-logiciels.md#i3--configurer-fish-gnome-text-editor-et-micro).

Les chemins `/home/ogu`, les UUID, adresses réseau et noms d’interfaces de ce guide sont ceux de cette installation. Les adapter pour une autre machine.

## A2 — Réglages initiaux dans CachyOS Hello

Dans **CachyOS Hello** :

- Désactiver le Bluetooth si inutilisé.
- Ne pas activer l’icône de mise à jour CachyOS dans la zone de notification.
- Classer les miroirs.
- Ne pas installer PSD : cette solution ne fait pas partie de la configuration retenue.

## A3 — Nettoyer les entrées UEFI en NVRAM

Afficher les entrées UEFI enregistrées en NVRAM :

```fish
sudo efibootmgr -v
```

Repérer les entrées devenues inutiles ou redondantes, en conservant l’entrée de démarrage utilisée et les entrées de secours souhaitées. Supprimer uniquement les identifiants vérifiés ; les numéros ci-dessous sont des exemples à adapter, pas une liste à exécuter telle quelle :

```fish
# Exemples : exécuter seulement la ligne correspondant à une entrée à supprimer.
sudo efibootmgr -b 0000 -B
sudo efibootmgr -b 0001 -B
sudo efibootmgr -b 0002 -B
```

[Accueil](README.md) · [Suivant](B-logiciels.md)
