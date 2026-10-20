# Disquaire

Éditeur de tags MP3 et FLAC pour GNOME, conçu pour ne garder que l’essentiel.

Disquaire conserve sept champs : **artiste, titre, album, année, genre, pochette et paroles**. Les autres tags sont supprimés lors du nettoyage automatique ou à l’enregistrement. La date complète est normalisée à l’année seule : `2014-03-01` devient `2014`.

## Fonctions

- Arborescence des dossiers, recherche de dossiers et de morceaux, création, renommage, corbeille et glisser-déposer.
- Recherche par tags (titre, artiste, album, genre, année) dans le dossier courant ou toute la discothèque.
- Édition groupée avec sélection de plusieurs morceaux.
- Pochettes par bouton, glisser-déposer, `folder.jpg`, recherche en ligne ou réserve réutilisable par genre.
- Mise en forme des tags artiste/titre et renommage en `Artiste - Titre Feat. Invité`.
- Renommage d’un dossier en `Artiste - Album`.
- Recherche de paroles sur [LRCLIB](https://lrclib.net), avec validation avant utilisation et recherche en lot.
- Lecture intégrée ou ouverture dans le lecteur audio choisi.
- Renommage, déplacement, mise à la corbeille et annulation des dernières opérations.
- Conversion FLAC vers MP3 320 kb/s, 44,1 kHz ; le FLAC source est placé dans la corbeille.
- Recherche floue de doublons à l’échelle de la discothèque.

## Installation

### Paquet Arch

Pour la version **1.7.1**, depuis le dossier contenant le paquet :

```sh
sudo pacman -U ./disquaire-1.7.1-1-any.pkg.tar.zst
```

Le dépôt contient actuellement l’ancienne archive **1.5.2**. Ajoutez manuellement le paquet 1.7.1 dans ce dossier lorsqu’il est prêt à être archivé dans GitLab ; ne renommez pas l’ancien paquet en 1.7.1.

### Depuis les sources

Depuis le dossier des sources de la version correspondante :

```sh
cd disquaire-1.7.1
makepkg -si
```

## Utilisation

### Nettoyage automatique

Le nettoyage automatique est **activé par défaut** et peut être désactivé dans **Menu principal → Préférences**. À l’ouverture d’un dossier, Disquaire traite les fichiers un par un en arrière-plan :

- suppression des tags non conservés ;
- normalisation de la date à l’année ;
- réduction des pochettes trop grandes à 1024 px maximum ;
- intégration des paroles d’un fichier `.lrc` portant le même nom.

Ces opérations de nettoyage écrivent directement dans les fichiers sans attendre un enregistrement manuel. Les miniatures sont conservées en cache pour accélérer les ouvertures suivantes. Utilisez **Préférences → Vider** pour vider ce cache.

Les changements de pochette (bouton, réserve, `folder.jpg`), la mise en forme et les valeurs d’année/album récupérées en ligne sont enregistrés directement. Les autres modifications saisies dans les champs restent en attente, signalées par un point bleu, jusqu’à l’enregistrement. Le badge bleu **Paroles** indique que le morceau contient des paroles dans ses tags.

### Filtres et édition groupée

Le filtre (entonnoir de la liste) propose : **sans paroles**, **sans pochette**, **sans année**, **sans genre** et **à enregistrer**. Les filtres se combinent à la recherche.

En édition groupée, un champ **Valeurs différentes** n’est modifié que si vous saisissez une valeur. Plusieurs artistes ou genres peuvent être séparés par un point-virgule (`;`).

### Rechercher

- **Volet Dossiers** : la loupe recherche dossiers et fichiers d’après leur nom dans toute la discothèque. La recherche ignore les accents et la casse ; Entrée ouvre le premier résultat. Un morceau s’ouvre dans son dossier et est sélectionné.
- **Liste des morceaux** : la loupe ou `Ctrl+F` recherche dans les tags titre, artiste, album, genre, année et dans le nom du fichier.
- Les boutons sous le champ choisissent **Dossier en cours** ou **Tous les morceaux**. Les résultats globaux affichent leur dossier et restent éditables. Dans le menu ⋮ de l’éditeur, **Aller au dossier du morceau** permet de le retrouver dans l’arborescence.
- L’index des tags est mis en cache dans `~/.cache/disquaire/index.json` ; seule la première recherche globale relit toute la discothèque.

### Mise en forme

Le bouton scindé **Mettre en forme** agit sur la sélection ; sa flèche permet de traiter tout le dossier après aperçu.

1. Les artistes et titres manquants sont extraits du nom du fichier, par exemple `01 - artiste - titre.mp3`.
2. La casse est normalisée mot par mot. Les noms entièrement en capitales sont corrigés (par exemple `KID FRANCESCOLI & Julia Minkin` devient `Kid Francescoli & Julia Minkin`), sauf les sigles courts comme AC/DC, MGMT ou IAM. Les espaces superflus sont supprimés et `feat.`, `ft.` ou `featuring` deviennent `Feat.` lorsqu’un invité est présent.
3. Les tags sont enregistrés.
4. Le fichier est renommé `Artiste - Titre Feat. Invité.mp3`.

L’album est également mis en forme, mais n’est pas inclus dans le nom du fichier. L’opération peut être annulée via **Menu principal → Annuler**.

### Genres

Le champ Genre suggère les genres déjà présents dans votre liste pendant la frappe ; la flèche affiche la liste complète. Un genre absent peut être saisi librement.

Dans **Menu principal → Genres…** :
- onglet **Liste** : ajouter, renommer ou retirer des genres ;
- onglet **Discothèque** : examiner les genres présents dans les morceaux et remplacer globalement ceux qui ne figurent pas dans la liste.

### Année et album

Les loupes des champs **Année** et **Album** recherchent des éditions sur MusicBrainz et iTunes, avec les plus anciennes en tête. Les boutons **Année**, **Album** et **Les deux** permettent de choisir ce qui sera appliqué. Rien n’est modifié sans clic explicite.

### Dossiers et déplacements

- Le menu ⋮ ou le clic droit sur un dossier permet de créer un dossier, de le renommer en `Artiste - Album` (nom suggéré depuis les tags, modifiable) ou de le mettre à la corbeille.
- Glisser un dossier sur un autre dossier le déplace.
- Glisser un morceau sur un dossier le déplace ; si plusieurs morceaux sont cochés, ils peuvent être déplacés ensemble.
- Le glisser-déposer fonctionne aussi depuis Fichiers. Un déplacement peut être annulé.

### Pochettes

Les images intégrées de plus de 1024 px sont réduites à 1024 px (JPEG qualité 95). Les images plus petites sont conservées telles quelles.

Si le dossier contient `folder.jpg`, Disquaire propose de l’intégrer aux morceaux du dossier. La recherche en ligne utilise iTunes et Cover Art Archive ; elle ne retient que les images d’au moins **1024 × 1024 px**, affiche les résultats au fur et à mesure et s’arrête après 25 secondes. L’image choisie est également enregistrée sous `folder.jpg`.

### Réserve de pochettes

La réserve permet de réutiliser des pochettes pour les morceaux isolés, sans album. Elle se trouve dans `~/.local/share/disquaire/reserve/`.

- Le bouton **images** sous la pochette ouvre la réserve ; un clic applique une pochette au morceau ou aux morceaux cochés.
- Le bouton **+** ajoute la pochette affichée ou une image du disque ; le glisser-déposer est accepté.
- Un clic droit permet de renommer ou supprimer une pochette.
- Nommez les pochettes d’après un genre, par exemple `Jazz` ou `Reggae`. Pour un morceau sans pochette, Disquaire propose la pochette correspondante au genre, sans tenir compte des accents ni de la casse. `Jazz 2` correspond également à Jazz.
- **Menu principal → Pochettes manquantes depuis la réserve** traite en une fois les morceaux sans pochette de la liste.

### Paroles en ligne

Les paroles proviennent de [LRCLIB](https://lrclib.net), service libre et gratuit.

- **Pour un morceau** : utilisez **Chercher en ligne** près du champ Paroles. Le badge **Conforme** signale une correspondance d’artiste, de titre et de durée (écart maximal de 3 secondes). **Utiliser ces paroles** remplit le champ sans les appliquer avant votre validation.
- **Pour un dossier ou toute la discothèque** : le menu principal propose **Paroles : ce dossier et ses sous-dossiers** et **Paroles : toute la discothèque**. Les morceaux sont traités un par un en arrière-plan ; seules les paroles conformes sont écrites automatiquement.
- La barre en bas de la liste affiche la progression et permet de mettre en pause ou d’arrêter. La file reprend au prochain lancement. Un morceau sans résultat n’est pas réessayé tant qu’il n’a pas changé. Comptez environ 1 à 2 secondes par morceau.

### Doublons

Dans **Menu principal → Rechercher les doublons…**, Disquaire regroupe les morceaux dont artiste et titre sont proches, même si leurs noms de fichiers diffèrent. Les accents, la casse, la ponctuation et les termes comme `feat.`, `remastered` ou l’année sont ignorés. La durée doit différer de **4 secondes maximum**.

L’exemplaire conservé est choisi dans cet ordre : MP3 320 kb/s, sinon FLAC, sinon meilleur débit. Les autres exemplaires sont cochés pour la corbeille : vérifiez la sélection avant de confirmer.

### Annuler une opération

Après un enregistrement, une mise en forme, un renommage de fichier ou de dossier, ou un déplacement, utilisez le bouton **Annuler** de la notification ou **Menu principal → Annuler la dernière opération**. Les anciens tags et noms sont restaurés. L’historique ne dure que pendant la session.

### Ouvrir depuis Fichiers

Clic droit sur un dossier ou un morceau → **Ouvrir avec… → Disquaire**, ou glissez un dossier sur la fenêtre.

### Raccourcis clavier

| Raccourci | Action |
|---|---|
| Ctrl+S | Enregistrer la sélection |
| Ctrl+Maj+S | Tout enregistrer |
| F2 | Renommer le fichier |
| F5 | Rafraîchir la liste |
| F9 | Afficher ou masquer les dossiers |
| Ctrl+F | Rechercher |
| Ctrl+P | Lire ou mettre en pause |
| Ctrl+A / Échap | Tout cocher / tout décocher |

## Dépendances

Dépendances principales : `python`, `python-gobject`, `python-mutagen`, `gtk4`, `libadwaita`, `gstreamer`, `gst-plugins-base`, `gst-plugins-good` et `ffmpeg`.

Dépendances facultatives :
- `gst-libav` : décodeur MP3 de secours si la lecture intégrée échoue ;
- `webp-pixbuf-loader` : prise en charge des pochettes WebP.

## Licence

GPL-3.0-or-later
