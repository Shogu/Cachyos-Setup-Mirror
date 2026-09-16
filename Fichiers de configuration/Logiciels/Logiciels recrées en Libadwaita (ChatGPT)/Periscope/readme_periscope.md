Periscope  - appli perso libadwaita type Nautilus pour transfert locaux et ftp, avec contrôle des transferts. Vibe coded. 

Installation : 
```fish
sudo pacman -U ./periscope-0.1.0-2-any.pkg.tar.zst && shelly mark ignore periscope --add #empĉhe Shelly d'essayer de mettre à jour Periscope à partir des sources d'une appli AUR du même nom
```


Désinstallation : 
```fish
sudo pacman -Rns periscope
```



# Periscope

Periscope est un mini gestionnaire de fichiers GTK4/libadwaita inspirÃ© de
Nautilus, avec deux emplacements indÃ©pendants. Chaque emplacement accepte un
chemin local ou une URI prise en charge par GVfs, notamment `ftp://`, `sftp://`
et `smb://`.

Le nom final est **Periscope**. Le projet avait dâ€™abord Ã©tÃ© appelÃ© Torpille ;
le paquet Arch remplace encore explicitement lâ€™ancien paquet `torpille`.

## 1. Fonctions de navigation

- Deux emplacements indÃ©pendants, sans libellÃ©s imposÃ©s Â« gauche Â» et Â« droit Â».
- Bouton unique pour permuter les emplacements.
- Barre de chemin Ã©ditable et bouton de sÃ©lection de dossier.
- Navigation dans les dossiers, dossier parent et actualisation.
- Chemins locaux et emplacements GVfs distants, dont FTP, SFTP et SMB si les
  backends correspondants sont installÃ©s.
- Les icÃ´nes dâ€™Ã©lÃ©ments sont celles fournies par GIO et le thÃ¨me installÃ© :
  dossiers et types de fichiers gardent leurs icÃ´nes colorÃ©es rÃ©elles.
- Un simple clic sert Ã  cocher une sÃ©lection ; un double clic ouvre un fichier
  avec son application par dÃ©faut ou entre dans un dossier.

## 2. SÃ©lection et opÃ©rations de fichiers

- La case de chaque ligne permet la sÃ©lection multiple.
- Le bouton Â« Tout sÃ©lectionner Â» sÃ©lectionne ou dÃ©sÃ©lectionne la liste entiÃ¨re.
- Boutons standard libadwaita : Copier, Couper et Coller.
- Raccourcis : `Ctrl+A`, `Ctrl+C`, `Ctrl+X` et `Ctrl+V` hors de la barre de chemin.
- Une ligne cochÃ©e devient une cartouche bleue remplie, dans lâ€™esprit des
  contrÃ´les libadwaita ; les panneaux ne reÃ§oivent pas de liserÃ© bleu au focus.
- Clic droit sur une sÃ©lection puis Â« Supprimer les fichiers Â» : une
  confirmation est demandÃ©e et les Ã©lÃ©ments sont envoyÃ©s Ã  la corbeille.
- La suppression reste possible pendant un transfert. Si une source faisant
  partie de la file est supprimÃ©e, Periscope la signale comme absente dans le
  transfert et continue avec les autres Ã©lÃ©ments.

## 3. Affichage des fichiers cachÃ©s

Le bouton de la barre dâ€™en-tÃªte utilise une icÃ´ne de liste, volontairement
distincte de lâ€™Å“il qui masque lâ€™interface. Il permet dâ€™afficher ou de masquer
les fichiers dont le nom commence par un point. Le rÃ©glage est conservÃ© entre
les lancements.

## 4. Derniers emplacements et favoris

Au dÃ©marrage, les deux derniers emplacements utilisÃ©s sont restaurÃ©s lorsquâ€™ils
sont encore accessibles. Chaque emplacement possÃ¨de aussi un bouton Ã©toile pour
Ãªtre ajoutÃ© aux favoris. Les favoris et les deux derniers chemins sont
disponibles dans le menu principal.

Lâ€™ancien rÃ©glage dâ€™interface Â« RÃ©cents Â» a Ã©tÃ© retirÃ©. Une Ã©ventuelle clÃ©
`recent_locations` dâ€™une ancienne configuration est nettoyÃ©e lors de sa lecture.
La configuration est enregistrÃ©e dans :

```text
~/.config/periscope/locations.json
```

Les mots de passe prÃ©sents dans une URI ne sont pas mÃ©morisÃ©s dans ce fichier.

## 5. Transferts locaux et distants

Le transfert est asynchrone et affiche dans une mÃªme barre :

- le pourcentage et une barre de progression ;
- le poids dÃ©jÃ  transfÃ©rÃ© et le poids total Ã  transfÃ©rer ;
- la vitesse uniquement pendant lâ€™activitÃ© rÃ©elle ;
- le fichier courant, le nombre de fichiers traitÃ©s et le nombre restant ;
- les Ã©tats prÃ©paration, activitÃ©, pause, choix de doublon, finalisation,
  arrÃªt et erreur.

Les commandes disponibles sont pause, reprise et arrÃªt. Il nâ€™y a pas de
notification au dÃ©marrage ; une notification est affichÃ©e Ã  la fin, avec un
avertissement si une source a disparu ou nâ€™a pas pu Ãªtre supprimÃ©e.

### DÃ©placement rÃ©el

- Local vers local sur le mÃªme systÃ¨me de fichiers : `os.replace` rÃ©alise un
  renommage atomique, donc le dÃ©placement est quasi instantanÃ© mÃªme pour un gros
  fichier.
- Copie locale : les primitives du noyau (`copy_file_range` lorsquâ€™elles sont
  disponibles) sont utilisÃ©es avant le fallback GIO.
- FTP, SFTP, SMB ou autre changement de systÃ¨me de fichiers : aucun backend ne
  peut garantir un renommage atomique entre deux serveurs. Periscope rÃ©alise
  alors le vrai comportement de dÃ©placement par fichier : copie vers un fichier
  partiel, finalisation, puis suppression immÃ©diate de la source avant de passer
  au fichier suivant.
- Les fichiers partiels cachÃ©s portent le suffixe
  `.periscope-partial`. Une copie interrompue peut reprendre la taille dÃ©jÃ 
  prÃ©sente.
- AprÃ¨s un dÃ©placement de dossier, seuls les dossiers source devenus vides
  sont retirÃ©s. Un dossier non vide nâ€™est jamais supprimÃ© par ce nettoyage.

## 6. Doublons

Lorsquâ€™un fichier portant le mÃªme nom existe dans la destination, une boÃ®te de
dialogue libadwaita propose :

- **Remplacer** le fichier existant ;
- **Renommer** la nouvelle copie avec un suffixe numÃ©rotÃ© ;
- **Annuler** le transfert ;
- **Appliquer Ã  tous les doublons** pour mÃ©moriser le choix dans le transfert
  en cours et Ã©viter de rÃ©pondre dix fois.

Le choix ne modifie pas les fichiers sources et ne sâ€™applique pas aux prochains
lancements.

## 7. Bouton `Import videos`

Le bouton reprend le comportement du script `transfert_videos.sh`, mais avec le
mÃªme moteur de transfert que le reste de lâ€™application. Par dÃ©faut, il dÃ©place
les vidÃ©os de `~/TÃ©lÃ©chargements` vers `~/VidÃ©os/.DEV`, rÃ©cursivement, en
recherchant :

```text
.mp4 .mkv .avi .mov .flv .wmv .mpeg .mpg .webm
```

Son menu permet de configurer :

- chemin source ;
- chemin destination ;
- dÃ©placer ou copier ;
- extensions ;
- recherche rÃ©cursive ou limitÃ©e au dossier ;
- nettoyage des dossiers vides ;
- conservation du dossier `VDH`.

Les rÃ©glages sont conservÃ©s dans `locations.json`. Le scan et le transfert
utilisent la mÃªme progression, la mÃªme gestion des doublons et les mÃªmes Ã©tats
que Copier/Couper/Coller.

## 8. Mode Å’il

Le bouton Å’il masque lâ€™interface de navigation et affiche un Ã©cran opaque avec
un bouton pour la rÃ©afficher. Un transfert en cours continue en arriÃ¨re-plan ;
ce mode ne suspend ni ne supprime les donnÃ©es.

Lâ€™icÃ´ne dâ€™application finale est circulaire, sobre et bleue, avec un pÃ©riscope
blanc et des vagues. Elle est inspirÃ©e de la rÃ©fÃ©rence fournie pour Periscope
et est utilisÃ©e par le lanceur, le menu des applications et lâ€™Ã©cran opaque.

## 9. DÃ©pendances dâ€™exÃ©cution â€” CachyOS / Arch Linux

Periscope est Ã©crit en Python et ne demande aucun paquet de compilation pour
Ãªtre exÃ©cutÃ© :

```bash
sudo pacman -S --needed python python-gobject gtk4 libadwaita gvfs
```

Pour les partages SMB/CIFS, ajouter si nÃ©cessaire :

```bash
sudo pacman -S --needed gvfs-smb
```

Le paquet `gvfs` fournit les accÃ¨s GIO locaux et les backends distants usuels,
dont FTP et SFTP sur une installation Arch standard. Les backends disponibles
peuvent varier selon la distribution. SFTP est recommandÃ© lorsque le serveur
le permet, car FTP ne chiffre pas les donnÃ©es.

## 10. Installation utilisateur

Le script installe le code dans `~/.local/share/periscope`, le lanceur dans
`~/.local/bin`, le fichier `.desktop` et lâ€™icÃ´ne dans les rÃ©pertoires de donnÃ©es
utilisateur. Il vÃ©rifie les bindings GTK/libadwaita mais ne lance pas pacman et
nâ€™installe aucun paquet systÃ¨me.

```bash
./install.sh
~/.local/bin/periscope
```

Pour dÃ©sinstaller uniquement cette installation utilisateur :

```bash
./uninstall.sh
```

Ce script ne supprime ni les dÃ©pendances, ni les fichiers personnels, ni le
dossier du projet. Il retire seulement les fichiers installÃ©s par
`install.sh`.

## 11. Paquet Arch pilotable avec pacman

La construction nÃ©cessite uniquement les outils de build Arch :

```bash
sudo pacman -S --needed base-devel
./build-pkg.sh
```

La version actuellement produite est :

```bash
sudo pacman -U ./periscope-0.1.0-4-any.pkg.tar.zst
```

Le paquet installe le programme dans `/usr/lib/periscope`, le lanceur dans
`/usr/bin/periscope`, lâ€™icÃ´ne, le fichier `.desktop` et ce README dans la
documentation systÃ¨me. Ses dÃ©pendances dâ€™exÃ©cution sont dÃ©clarÃ©es dans le
`PKGBUILD` : `python`, `python-gobject`, `gtk4`, `libadwaita` et `gvfs`.

Pour retirer lâ€™installation paquetÃ©e :

```bash
sudo pacman -R periscope
```

### Collision avec lâ€™AUR

Un autre paquet AUR nommÃ© `periscope` existe dÃ©jÃ  pour un client Nintendo
Switch. Le nom du paquet local est donc identique, mÃªme si les applications
nâ€™ont pas le mÃªme contenu. Avec un helper AUR, il faut refuser ou ignorer la
mise Ã  jour de cet autre paquet avant dâ€™utiliser le paquet local. Avec pacman,
une mise Ã  jour explicite du dÃ©pÃ´t ne remplace pas lâ€™installation locale sans
action de lâ€™utilisateur ; lâ€™installation du fichier local se fait avec
`pacman -U`.

## 12. Fichiers du projet

- `periscope.py` : application GTK4/libadwaita et moteur de transfert ;
- `bin/periscope` : lanceur adaptÃ© Ã  lâ€™installation utilisateur ou systÃ¨me ;
- `data/io.github.periscope.Periscope.desktop` : entrÃ©e du menu ;
- `data/io.github.periscope.Periscope.png` : icÃ´ne finale ;
- `install.sh` / `uninstall.sh` : installation et dÃ©sinstallation utilisateur ;
- `PKGBUILD` / `build-pkg.sh` : paquet Arch ;
- `check.sh` : vÃ©rifications de syntaxe, scripts, icÃ´ne et fonctions clÃ©s.

## 13. Historique des demandes intÃ©grÃ©es

1. CrÃ©ation dâ€™un gestionnaire libadwaita Ã  deux emplacements, avec choix des
   chemins et support FTP/GVfs.
2. Ajout de la sÃ©lection multiple, Tout sÃ©lectionner, Copier, Couper, Coller,
   inversion des emplacements et contrÃ´les pause/arrÃªt/reprise.
3. Ajout du pourcentage, de la barre de progression, de la vitesse, du fichier
   courant et des fichiers restants.
4. CrÃ©ation des scripts dâ€™installation et de dÃ©sinstallation, puis indication
   sÃ©parÃ©e des dÃ©pendances dâ€™exÃ©cution et des paquets de construction.
5. Renommage final de Torpille en Periscope, avec migration dÃ©clarÃ©e dans le
   paquet Arch et prise en compte de la collision AUR.
6. Suppression des mentions gauche/droit, suppression du rÃ©glage RÃ©cents et
   mÃ©morisation des deux derniers emplacements.
7. Ajout des favoris persistants et du toggle des fichiers cachÃ©s, avec une
   icÃ´ne de liste distincte de lâ€™Å“il de confidentialitÃ©.
8. Remplacement de lâ€™encadrement bleu des panneaux par une cartouche bleue
   uniquement sur les lignes dont la case est cochÃ©e.
9. Remplacement des icÃ´nes noir et blanc par les icÃ´nes colorÃ©es de GIO et du
   thÃ¨me courant.
10. Correction des erreurs de transfert FTP et local, de lâ€™appel GIO de lecture,
    des propriÃ©tÃ©s CSS GTK invalides et de la suppression par clic droit.
11. AccÃ©lÃ©ration des copies locales et dÃ©placement atomique sur le mÃªme SSD.
12. Ajout de `Import videos`, de sa configuration persistante et du mode Å’il.
13. Suppression des notifications au dÃ©marrage ; la vitesse est figÃ©e Ã  Â« â€” Â»
    dÃ¨s que le transfert nâ€™est plus actif.
14. DÃ©placement par fichier avec suppression immÃ©diate de la source pour les
    transferts distants ou inter-systÃ¨mes de fichiers.
15. RafraÃ®chissement des panneaux aprÃ¨s arrivÃ©e, dÃ©placement, suppression ou
    disparition dâ€™un fichier.
16. Suppression autorisÃ©e pendant un transfert et signalement des sources
    absentes dans la barre de transfert et la notification finale.
17. Ajout du poids transfÃ©rÃ©/total et dâ€™une interface de rÃ©solution des
    doublons avec remplacement, renommage, annulation et choix pour tous.
18. Passage Ã  lâ€™ouverture par double clic uniquement.

## Maintenance

AprÃ¨s une modification de `periscope.py`, lancer :

```bash
./check.sh
```

Puis reconstruire le paquet si nÃ©cessaire :

```bash
./build-pkg.sh
```

Lors dâ€™une nouvelle version, mettre Ã  jour ensemble `pkgrel` dans `PKGBUILD`,
le nom du paquet documentÃ© ci-dessus et les sommes SHA-256 gÃ©nÃ©rÃ©es par
`makepkg`.