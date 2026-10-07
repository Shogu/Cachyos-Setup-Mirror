# Mail

Client de messagerie GNOME issu de [Postcard 1.13.0](https://github.com/gxanshu/postcard/tree/v1.13.0), anciennement nommé **Mails** dans ce setup.

**Application non vibe codée**, compilée par ChatGPT à partir des sources d’origine avec adaptation du nom dans le code, l’interface et le paquet Arch. Crédits et licence upstream conservés.

**Mail et Poste sont concurrentes ; le choix privilégié du setup est Mail**, Poste étant l’alternative.

## Paquet à ajouter manuellement

Ogu déposera ici `mail-postcard-ogu-1.13.0-2-any.pkg.tar.zst`. À cette étape, le dossier contient uniquement ce README.

## Installation

Depuis ce dossier, après ajout du paquet :

```fish
sudo pacman -U ./mail-postcard-ogu-1.13.0-2-any.pkg.tar.zst
mail-postcard
```

Accepter le remplacement de `mails-ogu` ou `postcard` s’ils sont installés. Fermer l’ancienne instance avant de relancer. Les identifiants techniques, réglages et emplacements de comptes restent ceux du projet d’origine.

## Vérification

Paquet et métadonnées contrôlés. Fonctionnement complet en session GNOME avec un compte réel **non testé** lors de cette reconstruction.

Voir [10.1.4 — Mail ou Poste](../../../docs/10-logiciels.md#1014--messagerie--mail-ou-poste) pour la correspondance des noms et la migration des deux anciens paquets.
