Periscope  - appli perso libadwaita type Nautilus pour transfert locaux et ftp, avec contrôle des transferts. Vibe coded. 


![Interface de Periscope](../../screenshots/vibe-coded/periscope.png)

Version du paquet actuellement fourni : `0.1.0-10`.

Installation : 
```fish
sudo pacman -U ./periscope-0.1.0-10-any.pkg.tar.zst && shelly mark ignore periscope --add #empêche Shelly d'essayer de mettre à jour Periscope à partir des sources d'une appli AUR du même nom
```


Désinstallation : 
```fish
sudo pacman -Rns periscope
```

# Periscope

Periscope est un mini gestionnaire de fichiers GTK4/libadwaita inspiré de
Nautilus, avec deux emplacements indépendants. Chaque emplacement accepte un
chemin local ou une URI prise en charge par GVfs, notamment `ftp://`, `sftp://`
et `smb://`.

Le nom final est **Periscope**. Le projet avait d’abord été appelé Torpille ;
le paquet Arch remplace encore explicitement l’ancien paquet `torpille`.

## 1. Fonctions de navigation

- Deux emplacements indépendants et équilibrés à 50/50, sans libellés imposés
  « gauche » et « droit ».
- La séparation centrale n’est pas redimensionnable : les deux panneaux restent
  égaux et aucun séparateur large ne détourne l’attention.
- Bouton unique pour permuter les emplacements.
- Barre de chemin éditable et bouton de sélection de dossier.
- Navigation dans les dossiers, dossier parent et actualisation.
- Chemins locaux et emplacements GVfs distants, dont FTP, SFTP et SMB si les
  backends correspondants sont installés.
- Les icônes d’éléments sont celles fournies par GIO et le thème installé :
  dossiers et types de fichiers gardent leurs icônes colorées réelles.
- Un simple clic sert à cocher une sélection ; un double clic ouvre un fichier
  avec son application par défaut ou entre dans un dossier.

## 2. Sélection et opérations de fichiers

- La case de chaque ligne permet la sélection multiple.
- Le bouton « Tout sélectionner » sélectionne ou désélectionne la liste entière.
- Deux boutons iconographiques standard libadwaita : copie (`edit-copy-symbolic`)
  et déplacement (`edit-cut-symbolic`). Leur infobulle indique respectivement
  **Copier vers** et **Couper vers**. Chaque bouton lance immédiatement
  l’opération vers le répertoire actuellement affiché dans le panneau adjacent.
- Dès qu’une sélection est disponible, ces actions prennent l’apparence bleue
  `suggested-action` de libadwaita ; elles redeviennent neutres et désactivées
  lorsqu’aucun transfert direct n’est possible.
- Raccourcis : `Ctrl+A`, `Ctrl+C`, `Ctrl+X` et `Ctrl+V` hors de la barre de chemin.
- Les raccourcis `Ctrl+C`, `Ctrl+X` et `Ctrl+V` conservent le comportement de
  presse-papiers classique pour les utilisateurs qui le préfèrent ; les boutons
  visibles sont, eux, des actions directes vers le panneau voisin.
- Une ligne cochée devient une cartouche bleue remplie, dans l’esprit des
  contrôles libadwaita ; les panneaux ne reçoivent pas de liseré bleu au focus.
- Clic droit sur une sélection puis « Supprimer les fichiers » : une
  confirmation est demandée et les éléments sont envoyés à la corbeille.
- La suppression reste possible pendant un transfert. Si une source faisant
  partie de la file est supprimée, Periscope la signale comme absente dans le
  transfert et continue avec les autres éléments.

## 3. Affichage des fichiers cachés

Le bouton de la barre d’en-tête utilise une icône de liste, volontairement
distincte de l’œil qui masque l’interface. Il permet d’afficher ou de masquer
les fichiers dont le nom commence par un point. Le réglage est conservé entre
les lancements.

## 4. Derniers emplacements et favoris

Au démarrage, les deux derniers emplacements utilisés sont restaurés lorsqu’ils
sont encore accessibles. Chaque emplacement possède aussi un bouton étoile pour
être ajouté aux favoris. Un bouton étoile toujours visible dans la barre
supérieure ouvre directement la liste des favoris, sans passer par le menu
hamburger ni par un sous-menu. Le clic ouvre l’emplacement dans le panneau actif.
Le menu hamburger reste réservé aux options d’import et aux informations sur
l’application.

L’ancien réglage d’interface « Récents » a été retiré. Une éventuelle clé
`recent_locations` d’une ancienne configuration est nettoyée lors de sa lecture.
La configuration est enregistrée dans :

```text
~/.config/periscope/locations.json
```

Les mots de passe présents dans une URI ne sont pas mémorisés dans ce fichier.

## 5. Transferts locaux et distants

Le transfert est asynchrone et affiche dans une même barre :

- le pourcentage et une barre de progression ;
- le poids déjà transféré et le poids total à transférer ;
- la vitesse uniquement pendant l’activité réelle ;
- le fichier courant, le nombre de fichiers traités et le nombre restant ;
- les états préparation, activité, pause, choix de doublon, finalisation,
  arrêt et erreur.

Les commandes disponibles sont pause, reprise et arrêt. Il n’y a pas de
notification au démarrage ; une notification est affichée à la fin, avec un
avertissement si une source a disparu ou n’a pas pu être supprimée.

### Déplacement réel

- Local vers local sur le même système de fichiers : `os.replace` réalise un
  renommage atomique, donc le déplacement est quasi instantané même pour un gros
  fichier.
- Copie locale : les primitives du noyau (`copy_file_range` lorsqu’elles sont
  disponibles) sont utilisées avant le fallback GIO.
- FTP, SFTP, SMB ou autre changement de système de fichiers : aucun backend ne
  peut garantir un renommage atomique entre deux serveurs. Periscope réalise
  alors le vrai comportement de déplacement par fichier : copie vers un fichier
  partiel, finalisation, puis suppression immédiate de la source avant de passer
  au fichier suivant.
- Les fichiers partiels cachés portent le suffixe
  `.periscope-partial`. Une copie interrompue peut reprendre la taille déjà
  présente.
- Après un déplacement de dossier, seuls les dossiers source devenus vides
  sont retirés. Un dossier non vide n’est jamais supprimé par ce nettoyage.

## 6. Doublons

Lorsqu’un fichier portant le même nom existe dans la destination, une boîte de
dialogue libadwaita propose :

- **Remplacer** le fichier existant ;
- **Renommer** la nouvelle copie avec un suffixe numéroté ;
- **Annuler** le transfert ;
- **Appliquer à tous les doublons** pour mémoriser le choix dans le transfert
  en cours et éviter de répondre dix fois.

Le choix ne modifie pas les fichiers sources et ne s’applique pas aux prochains
lancements.

## 7. Bouton `Import videos`

Le bouton reprend le comportement du script `transfert_videos.sh`, mais avec le
même moteur de transfert que le reste de l’application. Par défaut, il déplace
les vidéos de `~/Téléchargements` vers `~/Vidéos/.DEV`, récursivement, en
recherchant :

```text
.mp4 .mkv .avi .mov .flv .wmv .mpeg .mpg .webm
```

Son menu permet de configurer :

- chemin source ;
- chemin destination ;
- déplacer ou copier ;
- extensions ;
- recherche récursive ou limitée au dossier ;
- nettoyage des dossiers vides ;
- conservation du dossier `VDH`.

Les réglages sont conservés dans `locations.json`. Le scan et le transfert
utilisent la même progression, la même gestion des doublons et les mêmes états
que Copier/Couper/Coller.

## 8. Mode Œil

Le bouton Œil masque l’interface de navigation et affiche un écran opaque avec
un bouton pour la réafficher. Un transfert en cours continue en arrière-plan ;
ce mode ne suspend ni ne supprime les données.

L’icône d’application finale est circulaire, sobre et bleue, avec un périscope
blanc et des vagues. Elle est inspirée de la référence fournie pour Periscope
et est utilisée par le lanceur, le menu des applications et l’écran opaque.

## 9. Dépendances d’exécution — CachyOS / Arch Linux

Periscope est écrit en Python et ne demande aucun paquet de compilation pour
être exécuté :

```bash
sudo pacman -S --needed python python-gobject gtk4 libadwaita gvfs
```

Pour les partages SMB/CIFS, ajouter si nécessaire :

```bash
sudo pacman -S --needed gvfs-smb
```

Le paquet `gvfs` fournit les accès GIO locaux et les backends distants usuels,
dont FTP et SFTP sur une installation Arch standard. Les backends disponibles
peuvent varier selon la distribution. SFTP est recommandé lorsque le serveur
le permet, car FTP ne chiffre pas les données.

## 10. Installation utilisateur

Le script installe le code dans `~/.local/share/periscope`, le lanceur dans
`~/.local/bin`, le fichier `.desktop` et l’icône dans les répertoires de données
utilisateur. Il vérifie les bindings GTK/libadwaita mais ne lance pas pacman et
n’installe aucun paquet système.

```bash
./install.sh
~/.local/bin/periscope
```

Pour désinstaller uniquement cette installation utilisateur :

```bash
./uninstall.sh
```

Ce script ne supprime ni les dépendances, ni les fichiers personnels, ni le
dossier du projet. Il retire seulement les fichiers installés par
`install.sh`.

## 11. Paquet Arch pilotable avec pacman

La construction nécessite uniquement les outils de build Arch :

```bash
sudo pacman -S --needed base-devel
./build-pkg.sh
```

La version actuellement produite est :

```bash
sudo pacman -U ./periscope-0.1.0-10-any.pkg.tar.zst
```

Le paquet installe le programme dans `/usr/lib/periscope`, le lanceur dans
`/usr/bin/periscope`, l’icône, le fichier `.desktop` et ce README dans la
documentation système. Ses dépendances d’exécution sont déclarées dans le
`PKGBUILD` : `python`, `python-gobject`, `gtk4`, `libadwaita` et `gvfs`.

Pour retirer l’installation paquetée :

```bash
sudo pacman -R periscope
```

### Collision avec l’AUR

Un autre paquet AUR nommé `periscope` existe déjà pour un client Nintendo
Switch. Le nom du paquet local est donc identique, même si les applications
n’ont pas le même contenu. Avec un helper AUR, il faut refuser ou ignorer la
mise à jour de cet autre paquet avant d’utiliser le paquet local. Avec pacman,
une mise à jour explicite du dépôt ne remplace pas l’installation locale sans
action de l’utilisateur ; l’installation du fichier local se fait avec
`pacman -U`.

## 12. Fichiers du projet

- `periscope.py` : application GTK4/libadwaita et moteur de transfert ;
- `bin/periscope` : lanceur adapté à l’installation utilisateur ou système ;
- `data/io.github.periscope.Periscope.desktop` : entrée du menu ;
- `data/io.github.periscope.Periscope.png` : icône finale ;
- `install.sh` / `uninstall.sh` : installation et désinstallation utilisateur ;
- `PKGBUILD` / `build-pkg.sh` : paquet Arch ;
- `check.sh` : vérifications de syntaxe, scripts, icône et fonctions clés.

## 13. Historique des demandes intégrées

1. Création d’un gestionnaire libadwaita à deux emplacements, avec choix des
   chemins et support FTP/GVfs.
2. Ajout de la sélection multiple, Tout sélectionner, Copier, Couper, Coller,
   inversion des emplacements et contrôles pause/arrêt/reprise.
3. Ajout du pourcentage, de la barre de progression, de la vitesse, du fichier
   courant et des fichiers restants.
4. Création des scripts d’installation et de désinstallation, puis indication
   séparée des dépendances d’exécution et des paquets de construction.
5. Renommage final de Torpille en Periscope, avec migration déclarée dans le
   paquet Arch et prise en compte de la collision AUR.
6. Suppression des mentions gauche/droit, suppression du réglage Récents et
   mémorisation des deux derniers emplacements.
7. Ajout des favoris persistants et du toggle des fichiers cachés, avec une
   icône de liste distincte de l’œil de confidentialité.
8. Remplacement de l’encadrement bleu des panneaux par une cartouche bleue
   uniquement sur les lignes dont la case est cochée.
9. Remplacement des icônes noir et blanc par les icônes colorées de GIO et du
   thème courant.
10. Correction des erreurs de transfert FTP et local, de l’appel GIO de lecture,
    des propriétés CSS GTK invalides et de la suppression par clic droit.
11. Accélération des copies locales et déplacement atomique sur le même SSD.
12. Ajout de `Import videos`, de sa configuration persistante et du mode Œil.
13. Suppression des notifications au démarrage ; la vitesse est figée à « — »
    dès que le transfert n’est plus actif.
14. Déplacement par fichier avec suppression immédiate de la source pour les
    transferts distants ou inter-systèmes de fichiers.
15. Rafraîchissement des panneaux après arrivée, déplacement, suppression ou
    disparition d’un fichier.
16. Suppression autorisée pendant un transfert et signalement des sources
    absentes dans la barre de transfert et la notification finale.
17. Ajout du poids transféré/total et d’une interface de résolution des
    doublons avec remplacement, renommage, annulation et choix pour tous.
18. Passage à l’ouverture par double clic uniquement.
19. Abandon des onglets ou sessions latéraux au profit des favoris persistants.
20. Suppression de la poignée centrale redimensionnable et passage à deux
    panneaux toujours équilibrés.
21. Remplacement des boutons visibles Copier/Coller par **Copier vers** et
    **Couper vers**, qui transfèrent directement vers le panneau adjacent.
22. Accès direct aux favoris par un bouton étoile visible, sans sous-menu du
    hamburger ; actions de transfert réduites à des icônes, avec infobulles et
    état bleu lorsqu’elles sont disponibles.

## Maintenance

Après une modification de `periscope.py`, lancer :

```bash
./check.sh
```

Puis reconstruire le paquet si nécessaire :

```bash
./build-pkg.sh
```

Lors d’une nouvelle version, mettre à jour ensemble `pkgrel` dans `PKGBUILD`,
le nom du paquet documenté ci-dessus et les sommes SHA-256 générées par
`makepkg`.
