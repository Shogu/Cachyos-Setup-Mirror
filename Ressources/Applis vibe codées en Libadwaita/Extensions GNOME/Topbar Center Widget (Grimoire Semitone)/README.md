# Topbar Center Widget 1.7

Extension GNOME Shell compatible avec **GNOME 50 et 51**. Elle gère **tout le contenu du menu de l’horloge**, au centre de la barre supérieure.

> **État de validation :** la version 1.7 n’a pas encore été testée en session GNOME Shell. La documentation décrit les fonctionnalités annoncées, sans prétendre à une validation en conditions réelles.

> **Sources :** ce dépôt ne contient pas les sources brutes du widget ; seul `topbar-center-widgetogu.shell-extension.zip` porte le code. Pour l'extraire : `unzip <zip> -d <cible>` ; c'est le `notesFolder.js` de l'archive qui contient la limite des 80 caractères et la resynchronisation du `# H1` référencées plus bas.

## Lecteur

Le lecteur (Semitone, navigateur, lecteurs vidéo compatibles MPRIS…) est placé au-dessus des notes.

## Lecteur

Le lecteur (Semitone, navigateur, lecteurs vidéo compatibles MPRIS…) est placé au-dessus des notes.

- Pochette arrondie et réglable ; titre et artiste à droite, le titre utilisant toute la largeur disponible.
- Barre de progression cliquable pour rechercher une position dans le morceau. Elle utilise l’identifiant du morceau lorsqu’il est disponible et conserve un fonctionnement de secours pour les lecteurs qui n’en fournissent pas.
- Boutons Aléatoire et Répéter centrés sous la barre de progression.
- Un seul lecteur affiché à la fois, lecteurs ignorés et défilement du titre uniquement lorsqu’il dépasse, avec retour plus rapide.
- Menu contextuel ⋯ affiché uniquement si au moins une action est disponible : **Ouvrir dans Disquaire** pour un fichier local compatible lorsque Disquaire est installé ; **Afficher dans Fichiers** si le chemin local est exposé ; **Copier « Titre – Artiste »**.
- **Titre suivant : …** sous l’artiste lorsque le lecteur peut fournir le prochain morceau.
- Le bouton `^` est masqué.

### Intégration Semitone

La version mise à jour de Semitone expose les informations nécessaires à une intégration plus complète :

1. **Emplacement du fichier** : active les actions « Ouvrir dans Disquaire » et « Afficher dans Fichiers » pour les fichiers locaux.
2. **Identifiant du morceau** : permet de cibler précisément le morceau lors d’un clic sur la barre de progression.
3. **Signal de changement de lecture aléatoire** : le bouton reflète l’état réel. Lorsque l’aléatoire est désactivé, Semitone revient à l’ordre de tri antérieur, plutôt qu’à un tri par titre.
4. **Titre suivant** : affiche « Titre suivant : … ». Avec « Tout répéter », après le dernier morceau, le premier est annoncé comme morceau suivant.

Les bibliothèques utilisées par le programme ont été vérifiées comme identiques à celles de l’ancien paquet, et l’interface intégrée au programme est identique octet pour octet. Cela ne remplace pas un test de lecture en session GNOME.

## Notes

Les notes proviennent des dossiers épinglés dans Grimoire. Les cartes proposent **Copier** et le menu **⋮** en bas à droite ; le titre dispose de toute la largeur.

Une seule catégorie est affichée à la fois : **Épinglées**, **Aujourd'hui**, **Hier**, **Cette semaine**, **Ce mois-ci** ou **Plus ancien**. Le filtre **Toutes** affiche la date sur chaque note.

Pour renommer une catégorie, faire un clic droit sur sa puce, saisir le nouveau nom puis appuyer sur Entrée. Échap annule. Le renommage est effectué dans Grimoire, qui renomme le dossier correspondant.

### Titre des notes et bouton **+**

Le titre tapé dans le champ « Nouvelle note » devient le nom du fichier **et** le premier titre `# H1` du document. Depuis la révision du 4 novembre 2026 :

- Le titre est tronqué à **80 caractères** pour produire un nom de fichier raisonnable ; le `# H1` du document est égal à ce nom tronqué.
- Renommer une note met à jour le `# H1` quand celui-ci correspond exactement à l'ancien nom de fichier ; un titre écrit à la main dans le document n'est jamais écrasé.
- Renommer une note vers un nom différent qui tronque au même nom des 80 caractères est silencieusement ignoré (pas d'erreur « le fichier existe déjà »).

Raccourci : `Super+Alt+N`.

La ligne **Notifications** est alignée à gauche.

## Notifications

Les notifications sont repliées sous les notes. L’interrupteur **Ne pas déranger** reste accessible.

## Calendrier

Les rendez-vous sont présentés séparément par agenda, avec point de couleur et cartouche aplati. Les événements passés sont atténués et les événements en cours sont indiqués.

- Temps restant dans la ligne grise : « dans 25 min », « en cours · reste 40 min » ou « encore 7 jours ».
- Les événements futurs affichent une indication relative comme « demain » ou « dans 3 jours ».
- Les événements longs en cours peuvent afficher une fine barre de progression de 2 px indiquant le temps écoulé.
- Le bouton **+** permet de créer un rendez-vous sans ouvrir Agenda.
- La date située en bas du menu est supprimée.
- La liste prend la hauteur correspondant à son contenu.

## Barre du haut

L’icône animée du lecteur est placée tout à gauche des icônes système.

## Préférences

Trois pages : **Lecteur**, **Notes** et **Calendrier**.

```sh
gnome-extensions prefs topbar-center-widget@ogu
```

## Changements

### 1.7

- Boutons **Copier** et **⋮** dans chaque carte de note, en bas à droite ; le titre utilise toute la largeur.
- Une seule catégorie de notes affichée à la fois ; le filtre **Toutes** conserve la date sur chaque note.
- Renommage d’une catégorie par clic droit sur sa puce ; Grimoire renomme le dossier correspondant.
- Ligne **Notifications** alignée à gauche.

### Révision du 4 novembre 2026

- Titre des notes tronqué à **80 caractères** à la création (bouton **+**) pour garder un nom de fichier raisonnable ; le `# H1` suit ce nom tronqué.
- Renommer une note resynchronise le `# H1` du document quand il correspond à l'ancien nom ; un titre écrit à la main n'est jamais écrasé.
- Renommer une note vers un nom différent mais tronqué au même nom des 80 caractères est ignoré au lieu de lever une erreur.

### 1.6.6 (4 novembre 2026)

- Titre des notes tronqué à **80 caractères** à la création (bouton **+**) pour garder un nom de fichier raisonnable ; le `# H1` du document suit ce nom tronqué.
- Renommer une note resynchronise le `# H1` du document quand il correspond à l'ancien nom ; un titre écrit à la main n'est jamais écrasé.
- Renommer une note vers un nom différent mais tronqué au même nom des 80 caractères est ignoré au lieu de lever une erreur.
- Masquage du bouton `^`.
- Barre de progression compatible aussi avec les lecteurs sans identifiant de morceau.
- Défilement du titre uniquement si nécessaire, avec retour plus rapide.
- Libellé « Titre suivant : … ».
- Actions contextuelles sur les fichiers locaux, selon les informations exposées par le lecteur et la présence de Disquaire.

### 1.1

- Affichage distinct des rendez-vous par agenda, hauteur de liste ajustée au contenu et icône animée du lecteur.

### 1.0

- Barre de progression, pochette arrondie avec rayon de 18 px, Aléatoire/Répéter, affichage d’un seul lecteur, titre défilant et lecteurs ignorés.

## Installation

```sh
gnome-extensions install --force topbar-center-widget@ogu.shell-extension.zip
```

Puis se déconnecter et se reconnecter à la session GNOME, puis activer l’extension :

```sh
gnome-extensions enable topbar-center-widget@ogu
```
