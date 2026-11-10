# Extension Manager — fork Ogu 0.7.0.ogu1

Extension Manager 0.7.0 d'origine, avec le classement par catégorie de ogu3.

## Nouveautés de la 0.7.0 (en amont)

- Fiche d'extension repensée : infos locales et web dans une seule vue.
- Recherche des extensions installées depuis la vue d'ensemble de GNOME.
- Erreurs d'extension dans une boîte de dialogue dédiée.
- Versions de GNOME prises en charge dans une boîte de dialogue.
- Mode sélection pour gérer plusieurs extensions à la fois.
- Ouverture du dossier d'une extension dans Fichiers.
- Captures animées, filtre des extensions non prises en charge, cache.

## Ajouts du fork

- **7 catégories** : Interface et apparence, Bureau et fenêtres, Barre supérieure
  et réglages rapides, Productivité, Système et énergie, Multimédia, Autres.
- **Classement automatique** : UUID connus, puis mots-clés du nom et de la
  description (« fenêtre » ajouté pour Bureau et fenêtres).
- **Menu ⋮ sur chaque extension** : « Déplacer vers… » une catégorie, ou
  « Catégorie automatique » pour revenir au classement proposé.
- Les choix déjà faits avec ogu3 sont conservés (clé `extension-categories`).
- Extensions intégrées toujours séparées, en bas ; icônes personnalisées.
- Correctif ogu3 reporté dans les sources (avertissement `has no handler with id`).

## Installation

```fish
sudo pacman -U extension-manager-ogu-0.7.0.ogu1-1-x86_64.pkg.tar.zst
```

Fermer l'ancienne fenêtre avant de relancer.

Testé dans un affichage virtuel avec un faux GNOME Shell (liste, menu, mode
sélection). Pas testé dans une vraie session GNOME. Licence GPL-3.0-or-later.
