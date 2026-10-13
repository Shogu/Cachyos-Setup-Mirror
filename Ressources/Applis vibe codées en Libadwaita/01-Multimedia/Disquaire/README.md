# Disquaire

Éditeur de tags MP3 et FLAC pour GNOME, qui ne garde que l'essentiel.

Disquaire conserve sept éléments : **artiste, titre, album, date, genre, pochette et paroles**. Tout le reste est supprimé à l'enregistrement.

## Fonctions

- Arbre des dossiers à gauche : recherche de dossiers et de morceaux, création, corbeille, glisser-déposer pour déplacer dossiers et morceaux
- Recherche par tags (titre, artiste, album, genre, année) dans le dossier en cours ou dans toute la discothèque
- Modification de plusieurs morceaux à la fois (ronds de sélection)
- Pochette : bouton, glisser-déposer, `folder.jpg` du dossier ou recherche en ligne, réserve de pochettes par genre ; toujours ramenée à 1024 px maximum
- Mise en forme en un clic : tags artiste/titre propres et fichier renommé « Artiste - Titre Feat. Invité »
- Renommer un dossier en « Artiste - Album » depuis le volet de gauche
- Lecture intégrée, ou ouverture dans le lecteur de son choix
- Renommer, déplacer, mettre à la corbeille, annuler
- Conversion FLAC → MP3 320 kb/s, 44,1 kHz (le FLAC part à la corbeille)
- Recherche floue des doublons dans toute la discothèque

## Installation

Paquet prêt :

```sh
sudo pacman -U disquaire-1.5.2-1-any.pkg.tar.zst
```

Ou depuis les sources :

```sh
cd disquaire-1.5.2
makepkg -si
```

## Utilisation

Les fichiers qui ont des tags en trop sont marqués d'un point bleu. Rien n'est modifié sur le disque tant que vous n'enregistrez pas.

En modification groupée, un champ « Valeurs différentes » n'est changé que si vous écrivez dedans. Plusieurs artistes ou genres se séparent par « ; ».

### Rechercher

- **À gauche** (loupe du volet Dossiers) : dossiers et morceaux d'après leur nom, dans toute la discothèque.
- **Au centre** (loupe de la liste, Ctrl+F) : d'après les tags — titre, artiste, album, genre, année — et le nom du fichier. Deux boutons sous le champ : « Dossier en cours » ou « Tous les morceaux ». Dans toute la discothèque, chaque résultat montre son dossier et reste modifiable comme d'habitude (enregistrement, mise en forme, multi-édition…) ; menu ⋮ de l'éditeur → « Aller au dossier du morceau ». Les tags sont gardés en cache (`~/.cache/disquaire/index.json`) : seule la première recherche lit toute la discothèque.

### Mise en forme

Un seul bouton scindé dans l'éditeur, « Mettre en forme » : le bouton agit sur la sélection, la flèche sur tout le dossier (avec aperçu). En une fois :

1. l'artiste et le titre manquants sont repris du nom du fichier (`01 - artiste - titre.mp3`) ;
2. majuscule à chaque mot ; un nom écrit tout en capitales est corrigé (« KID FRANCESCOLI & Julia Minkin » → « Kid Francescoli & Julia Minkin »), sauf les sigles courts comme AC/DC, MGMT ou IAM ; espaces en trop supprimés ; « feat. / ft. / featuring » écrit « Feat. » (seulement s'il y a un invité) ;
3. les tags sont enregistrés ;
4. le fichier est renommé `Artiste - Titre Feat. Invité.mp3`.

L'album n'est jamais modifié. Tout s'annule d'un clic.

### Dossiers

- **Rechercher** (loupe du volet de gauche) : trouve les dossiers et les morceaux (d'après leur nom de fichier) dans toute la discothèque, sans tenir compte des accents ni de la casse. Entrée ouvre le premier résultat ; un morceau s'ouvre dans son dossier, déjà sélectionné.
- **Menu ⋮ ou clic droit sur un dossier** : nouveau dossier, renommer en « Artiste - Album » (nom proposé d'après les tags, modifiable), mettre à la corbeille.
- **Glisser-déposer** : un dossier de l'arborescence sur un autre dossier le déplace ; des morceaux de la liste (la ligne glissée, ou tous les morceaux cochés) glissés sur un dossier y sont déplacés. Ça marche aussi depuis Fichiers. Un déplacement s'annule d'un clic.

### Pochettes

Toute image intégrée est réduite à 1024 px si elle est plus grande (JPEG qualité 95, sans perte visible) ; une image plus petite est gardée telle quelle. Si le dossier contient `folder.jpg`, Disquaire propose de l'intégrer partout. La recherche en ligne (iTunes, Cover Art Archive) ne montre que des images d'au moins 1024 × 1024, affichées au fur et à mesure ; elle s'arrête d'elle-même au bout de 25 secondes. L'image choisie est aussi enregistrée en `folder.jpg`.

### Réserve de pochettes

Pour les morceaux isolés, sans album : des pochettes réutilisables, rangées par genre dans `~/.local/share/disquaire/reserve/`.

- Bouton « images » sous la pochette → la réserve : un clic applique une pochette au morceau ou aux morceaux cochés. Le bouton + ajoute la pochette affichée ou une image du disque (glisser-déposer accepté) ; clic droit pour renommer ou supprimer.
- Nommez chaque pochette d'après un genre (« Jazz », « Reggae »…). Quand un morceau **sans pochette** a ce genre, Disquaire propose « Pochette « Jazz » de la réserve » en un clic (accents et majuscules ignorés ; « Jazz 2 » va aussi avec Jazz).
- Menu principal → « Pochettes manquantes depuis la réserve » : traite tous les morceaux sans pochette de la liste d'un coup.

### Doublons

Menu principal → « Rechercher les doublons… ». La recherche est floue : les morceaux dont l'artiste et le titre se ressemblent (accents, casse, ponctuation, « feat. », « remastered », année… ignorés) et dont la durée est la même à 4 secondes près sont regroupés, même si les noms de fichiers diffèrent. L'exemplaire à garder est le MP3 320 kb/s (sinon le FLAC, sinon le meilleur débit) ; les autres sont cochés pour la corbeille.

### Annuler

Après un enregistrement, une mise en forme, un renommage (fichier ou dossier) ou un déplacement, le bouton « Annuler » de la notification (ou menu principal → « Annuler la dernière opération ») remet les anciens tags et les anciens noms. L'historique dure le temps de la session.

### Ouvrir depuis Fichiers

Clic droit sur un dossier ou un morceau → « Ouvrir avec… » → Disquaire, ou glisser un dossier sur la fenêtre.

| Raccourci | Action |
|---|---|
| Ctrl+S | Enregistrer la sélection |
| Ctrl+Maj+S | Tout enregistrer |
| F2 | Renommer le fichier |
| F5 | Rafraîchir la liste |
| F9 | Afficher / masquer les dossiers |
| Ctrl+F | Rechercher |
| Ctrl+P | Lire / pause |
| Ctrl+A / Échap | Tout cocher / tout décocher |

## Dépendances

python, python-gobject, python-mutagen, gtk4, libadwaita, gstreamer, gst-plugins-base, gst-plugins-good, ffmpeg.

Dépendances facultatives : `gst-libav` pour un décodage MP3 de secours si la lecture intégrée échoue ; `webp-pixbuf-loader` pour les pochettes WebP.

## Licence

GPL-3.0-or-later
