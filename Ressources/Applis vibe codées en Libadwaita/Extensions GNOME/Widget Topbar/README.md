# Widget Topbar

**Version documentée : 2.3** (widget-topbar@ogu), compatibilité visée GNOME 50/51.

Extension GNOME Shell qui enrichit le **menu de l'horloge**, au centre de la barre supérieure. Elle rassemble le lecteur multimédia, les notes de Grimoire, les notifications et le calendrier.

- **UUID :** `widget-topbar@ogu`
- **Version :** 1.8
- **Compatibilité visée :** GNOME 50 et 51
- **Préférences :** `gnome-extensions prefs widget-topbar@ogu`
- **Pages :** Lecteur · Notes · Calendrier

> **Validation :** les préférences s'ouvrent correctement. L'extension n'a pas encore été exécutée dans une session GNOME Shell : le comportement intégré reste à confirmer.

## Fermeture automatique

Le menu de l'horloge se ferme lorsque le pointeur en sort. Son délai est indépendant de celui de Quick Settings et se règle dans la page **Calendrier**, groupe **Menu de l'horloge**.

## Lecteur

Le lecteur multimédia apparaît au-dessus des notes. Il prend en charge Semitone, les navigateurs et les lecteurs vidéo compatibles MPRIS.

- Pochette aux coins arrondis, de taille réglable ; titre et artiste à droite. Le titre dispose de toute la largeur disponible.
- Barre de progression cliquable pour se déplacer dans le morceau, que le lecteur fournisse ou non un identifiant de piste.
- Boutons Aléatoire et Répéter centrés sous la barre.
- Un seul lecteur est affiché à la fois ; les lecteurs indésirables peuvent être ignorés dans les préférences.
- Le titre ne défile que s'il dépasse la largeur disponible, avec un retour rapide.
- Le menu **⋯**, lorsqu'une action est disponible, propose :
  - **Ouvrir dans Disquaire** pour un fichier local lorsque Disquaire est installé ;
  - **Afficher dans Fichiers** ;
  - **Copier « Titre – Artiste »**.
- Lorsque le lecteur fournit cette information, le titre suivant apparaît sous l'artiste.
- Une icône animée identifie le lecteur actif à gauche des icônes système, pendant la lecture comme pendant la pause.

### Intégration Semitone

Avec Semitone, le widget peut exploiter des informations supplémentaires :

- emplacement du fichier pour l'ouvrir dans Disquaire ou l'afficher dans Fichiers ;
- identifiant du morceau pour une progression précise ;
- état réel de la lecture aléatoire ;
- titre du morceau suivant.

Avec **Tout répéter**, le premier morceau de la liste est annoncé après le dernier.

## Notes

Les notes sont fournies par **Grimoire** à partir de ses dossiers épinglés.

- Un dossier épinglé contenant des sous-dossiers fournit une catégorie pour chaque sous-dossier.
- Chaque carte propose les boutons **Copier** et **⋮** en bas à droite.
- Le titre dispose de toute la largeur de la carte.
- La liste se met à jour automatiquement lorsqu'une note est ajoutée, supprimée ou modifiée pendant que le menu reste ouvert.

### Replier les notes

Le bouton **Replier les notes**, dans l'en-tête, réduit la colonne à son seul titre. Le lecteur et les notifications peuvent alors récupérer l'espace libéré.

### Catégories

Une seule catégorie est affichée à la fois :

- **Épinglées**
- **Aujourd'hui**
- **Hier**
- **Cette semaine**
- **Ce mois-ci**
- **Plus ancien**

Avec **Toutes**, la date de chaque note reste affichée.

Pour renommer une catégorie, faire un clic droit sur sa puce, saisir le nouveau nom puis appuyer sur Entrée. Échap annule l'édition. Le dossier correspondant est renommé dans Grimoire.

### Création et renommage des notes

Le titre saisi dans **Nouvelle note** devient à la fois le nom du fichier et le titre Markdown `# H1`. Il est limité à **80 caractères**.

Lorsqu'une note est renommée, son `# H1` est actualisé s'il correspondait à l'ancien nom. Un titre rédigé manuellement dans le contenu n'est jamais écrasé.

**Raccourci clavier :** `Super+Alt+N`.

## Notifications

Les notifications sont repliées sous les notes. L'interrupteur **Ne pas déranger** reste accessible.

La ligne **Notifications** est alignée à gauche. Elle peut être masquée dans les préférences grâce à l'option **Rangée Notifications**.

## Calendrier

Les rendez-vous sont présentés séparément pour chaque agenda :

- point de couleur associé à l'agenda et cartouche aplati ;
- rendez-vous passés atténués ;
- indication **en cours** pour les événements commencés.

### Temps restant

Le widget affiche une indication adaptée, par exemple :

- « dans 25 min » ;
- « en cours · reste 40 min » ;
- « encore 7 jours » ;
- « demain ».

Une fine barre de 2 px matérialise la progression des rendez-vous longs en cours.

### Section À venir

Sous la grille du calendrier, la section **À venir** affiche le reste de la semaine. Le dimanche, elle présente la semaine suivante.

Le bouton **+** permet de créer un rendez-vous sans ouvrir l'application Agenda. La date qui figurait sous le calendrier a été supprimée : la liste occupe désormais la hauteur nécessaire à son contenu.

## Préférences

Ouvrir les préférences depuis GNOME Extensions ou avec :

```bash
gnome-extensions prefs widget-topbar@ogu
```

Les trois pages disponibles sont **Lecteur**, **Notes** et **Calendrier**.

## Dépendances et intégrations

- **Grimoire 0.3.0-3** pour les notes, les dossiers épinglés et la création de notes.
- **Semitone** pour les informations multimédias enrichies ; les autres lecteurs compatibles MPRIS restent pris en charge.
- **Disquaire** est nécessaire uniquement pour l'action « Ouvrir dans Disquaire ».

## Évolutions 2.3 — 12–13 novembre 2026

- Harmonise le gris des cartes de notes avec le lecteur, les notifications et « Aujourd’hui ».
- Uniformise les tailles des dates, aperçus, sections et morceaux suivants sur la typographie des rendez-vous GNOME (9 pt).
- Aligne le titre Notifications et sa cloche sur les autres en-têtes.
- Améliore le rendu des cartes en thème clair du Shell.

Les vérifications restent à effectuer en session GNOME réelle ; voir le [plan de tests](../../../../../../docs/tests-extensions.md).

## Historique

### Widget Topbar 1.8 — 9 novembre 2026

- Nouveau nom de Topbar Center Widget.
- Réunit les évolutions des versions 1.7 et 1.7.2.
- Déplace la fermeture automatique du menu de l'horloge dans cette extension, avec un délai indépendant.
- Intègre les notes, le lecteur, les notifications et le calendrier dans le menu de l'horloge.
- Suit le nouveau nom du widget dans Grimoire 0.3.0-3.

### Topbar Center Widget 1.7.2

- Ajoute le repli de la colonne des notes et la section À venir.
- Ajoute les catégories issues des sous-dossiers.
- Actualise la liste pendant que le menu est ouvert.
- Rend la rangée Notifications facultative.
- Limite les titres de notes à 80 caractères et resynchronise le `# H1` lors d'un renommage, sans écraser un titre écrit manuellement.

### Topbar Center Widget 1.7

- Ajoute les boutons **Copier** et **⋮** dans chaque carte de note.
- Affiche une seule catégorie à la fois.
- Permet de renommer une catégorie par clic droit.
- Aligne à gauche la ligne Notifications.
