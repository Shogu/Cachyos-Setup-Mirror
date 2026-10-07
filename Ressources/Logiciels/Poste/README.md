# Poste

Client de messagerie GNOME issu de [Hylki 1.42.0](https://github.com/hyprlab/hylki/tree/v1.42.0), anciennement nommé **Mail** dans ce setup.

**Application non vibe codée**, compilée par ChatGPT à partir des sources d’origine avec adaptation du nom dans le code, l’interface et le paquet Arch. Crédits et licence upstream conservés.

**Mail et Poste sont concurrentes ; le choix privilégié du setup est Mail**, Poste étant l’alternative.

## Paquet à ajouter manuellement

Ogu déposera ici `poste-ogu-1.42.0-3-x86_64.pkg.tar.zst`. À cette étape, le dossier contient uniquement ce README.

## Installation

Depuis ce dossier, après ajout du paquet :

```fish
sudo pacman -U ./poste-ogu-1.42.0-3-x86_64.pkg.tar.zst
poste
```

Accepter le remplacement de l’ancien `mail-ogu` ou `hylki` s’ils sont installés. Fermer l’ancienne instance avant de relancer. Les identifiants techniques, réglages et emplacements de comptes restent ceux du projet d’origine.

## Vérification

Paquet et métadonnées contrôlés. Fonctionnement complet en session GNOME avec un compte réel **non testé** lors de cette reconstruction.

Voir [10.1.4 — Mail ou Poste](../../../docs/10-logiciels.md#1014--messagerie--mail-ou-poste) pour la correspondance des noms et la migration des deux anciens paquets.
