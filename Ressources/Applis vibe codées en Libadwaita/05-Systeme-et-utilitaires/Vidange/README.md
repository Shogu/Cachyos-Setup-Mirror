# Vidange

**Vidange** est une application de nettoyage système pour CachyOS et GNOME, développée en Python avec GTK4/libadwaita. Toute l'interface et les messages sont en français. Elle rassemble dans une fenêtre les opérations courantes de maintenance et affiche une estimation de l'espace récupérable avant chaque nettoyage.

## Fonctions

| Catégorie | Fonctionnement |
|---|---|
| Paquets orphelins | Trois niveaux de vérification : `pacman -Qtdq`, dépendances qui ne servent qu'entre elles (`-Qdq` avec simulation `-Rsu --print`) et paquets explicitement installés (`-Qetq`) |
| Cache pacman | Conservation des deux versions récentes, suppression des versions désinstallées ou vidage complet |
| Cache AUR | Nettoyage des caches de Shelly, yay et paru lorsqu'ils sont disponibles |
| Journaux systemd | Réduction de la taille des journaux selon une limite réglable |
| Miniatures et corbeille | Cache `~/.cache/thumbnails` et corbeille via `gio trash --empty` |
| Développement | Caches pip, npm, yarn et Go |
| Navigateurs | Nettoyage via `profile-cleaner` |

Les vues de paquets inutilisés et explicitement installés sont des **vues de vérification** : rien n'y est coché par défaut et elles ne font pas partie de « Tout nettoyer ». Le bouton « Tout nettoyer » enchaîne les catégories de nettoyage sélectionnées et présente un récapitulatif à la fin.

Vidange remplace une fonction Fish `clean` et le paquet AUR `archclean`. Elle ne cherche volontairement pas les gros fichiers.

## Sécurité

L'application ne tourne jamais en root. Les opérations privilégiées passent par `/usr/lib/vidange/vidange-helper`, lancé via `pkexec` et protégé par Polkit. Le helper n'accepte qu'une liste fermée d'actions et valide les paramètres ; les commandes sont lancées sans shell. Un seul dialogue d'authentification suffit pour les opérations système d'une session de nettoyage.

## Installation

Le paquet compilé sera ajouté manuellement dans ce dossier. Depuis la racine du dépôt, une fois le paquet présent :

```fish
sudo pacman -U "Ressources/Applis vibe codées en Libadwaita/05-Systeme-et-utilitaires/Vidange/vidange-1.0.0-1-any.pkg.tar.zst"
```

Ou depuis les sources du projet :

```fish
makepkg -si
```

**Dépendances requises :** `python-gobject`, `gtk4`, `libadwaita >= 1.6`, `pacman-contrib` et `polkit`.

**Dépendances optionnelles :** `profile-cleaner`, `shelly`, ainsi que les outils de développement dont on souhaite vider les caches. Les catégories correspondantes dépendent des outils réellement installés.

## Précautions

Le nettoyage peut être irréversible, notamment pour les caches et les versions de paquets supprimées. Vérifie les catégories et les estimations avant de lancer une action. Les deux vues de vérification ne sont pas sélectionnées par défaut ; « Tout nettoyer » ne doit pas les inclure.

## Documentation technique

Le fichier [CLAUDE.md](CLAUDE.md) décrit l'architecture, le protocole du helper, les contraintes de sécurité et les vérifications à effectuer.

Licence GPL-3.0-or-later · identifiant d'application `io.gitlab.shogu.Vidange`.
