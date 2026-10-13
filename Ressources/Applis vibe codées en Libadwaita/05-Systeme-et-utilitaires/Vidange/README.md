# Vidange

**Vidange** est une application GTK4/libadwaita en Python destinée au nettoyage de CachyOS sous GNOME. Son interface et ses messages sont en français. L'application est conçue pour rester en mode utilisateur : elle ne tourne jamais en root.

## Fonctions décrites par le projet

- consultation des paquets orphelins et vues de vérification pour les paquets inutilisés ou explicitement installés ;
- nettoyage du cache pacman, avec plusieurs modes de conservation ;
- nettoyage des journaux systemd ;
- nettoyage de certains caches utilisateur, navigateurs et dossiers de développement ;
- estimation de l'espace récupérable et récapitulatif des opérations ;
- exécution des tâches bloquantes en arrière-plan pour garder l'interface réactive.

Les opérations nécessitant les droits administrateur passent par un helper dédié, lancé avec Polkit. Le helper accepte une liste limitée d'actions et valide strictement les paramètres ; il ne doit jamais recevoir de chemin ou de commande arbitraire.

## Architecture

Le projet sépare l'interface GTK de la logique métier : backend.py ne dépend pas de GTK et reste testable sans session graphique. Les réglages sont stockés dans ~/.config/vidange/settings.json.

## Installation

Le paquet Arch compilé sera ajouté manuellement à ce dossier. Le document technique CLAUDE.md décrit l'architecture, les contraintes de sécurité, la construction et les vérifications à effectuer.

## Précautions

Le nettoyage est une opération destructive. Vérifie les catégories et les estimations avant de lancer une action. Les étapes privilégiées sont regroupées en un seul appel Polkit, et les noms de paquets sont validés avant d'être transmis à pacman.
