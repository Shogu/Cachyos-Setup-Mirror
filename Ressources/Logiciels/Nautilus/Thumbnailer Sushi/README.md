# Thumbnailer Sushi — aperçus et miniatures GNOME

Ensemble de deux paquets Arch pour **Sushi** et les miniatures de **Nautilus**, ciblant CachyOS, GNOME 51 et Sushi 51.1. Les interfaces et bandeaux sont en français.

## Paquets fournis

- `sushi-thumbnailer-docs-extra-1.7.0-1-any.pkg.tar.zst` — aperçu Sushi des documents, PDF et archives, ainsi que miniatures des documents et fichiers texte/code.
- `nautilus-vignettes-arrondies-sushi-1.0.0-1-x86_64.pkg.tar.zst` — coins arrondis de style Nautilus/Adwaita appliqués aux miniatures dans Nautilus, y compris les photos et les PDF.

Le script `installer.sh` installe le paquet principal et, si présent dans le même dossier, le paquet des coins arrondis. Il arrête proprement Nautilus et son aperçu, installe les paquets, purge automatiquement tous les caches de miniatures (y compris les échecs), puis relance Nautilus s’il était ouvert. **Il n’est donc plus nécessaire de vider manuellement le cache ou de lancer une CLI de nettoyage séparée.**

## Fonctionnalités

### Aperçu avec la barre d’espace

- **Documents** : DOCX, ODT, RTF, Markdown et variantes prises en charge.
- **PDF** : aperçu simplifié pour une lecture rapide, sans chercher à reproduire fidèlement la mise en page complète.
- **Présentations** : PPTX/ODP, présentées sous forme de cartes textuelles par diapositive.
- **Tableurs** : XLSX/ODS, avec une vue GTK par feuille.
- **Archives** : ZIP, TAR et variantes compressées, 7z, RAR et paquets Arch `.pkg.tar.zst`, listés sans extraction.

### Miniatures dans Nautilus

- **Toutes les miniatures GNOME de Nautilus** bénéficient du rayon de coins Nautilus/Adwaita lorsque le paquet optionnel `nautilus-vignettes-arrondies-sushi` est installé, y compris les photos et les PDF.
- **Les fichiers texte et code** disposent d’un aperçu miniature et d’un bandeau indiquant leur nature/type.
- Les documents bureautiques, présentations et tableurs ont des fiches cohérentes avec un bandeau coloré. Les archives conservent leur icône habituelle.

## Installation et mise à jour

1. Place les deux fichiers `.pkg.tar.zst` et `installer.sh` dans le même dossier.
2. Ouvre un terminal dans ce dossier et lance le script **sans sudo** :

   ```bash
   sh ./installer.sh
   ```

Le mot de passe est demandé par `sudo pacman` au moment de l’installation. Pour voir les opérations sans rien modifier :

```bash
sh ./installer.sh -s
```

Options facultatives : `-y` évite la confirmation de pacman ; `-n` ne relance pas Nautilus à la fin. Le paquet des coins arrondis est optionnel pour le script, mais il est nécessaire pour obtenir les coins arrondis sur toutes les miniatures.

Le script refuse de poursuivre si d’anciens paquets concurrents sont encore installés. Il affiche les versions installées à la fin.

## Dépendances et fonctionnement

Le paquet principal dépend de Sushi 51 ou plus récent, WebKitGTK 6, Python, odfpy, openpyxl, libarchive-c, Markdown, PyGObject, Cairo, Pango, Poppler, GDK-Pixbuf et Adwaita Fonts. Les bibliothèques Python `mammoth` et `cobble` sont embarquées dans le paquet.

La conversion est exécutée dans un processus Python séparé, sans shell. L’aperçu HTML applique une CSP restrictive, désactive JavaScript et bloque le chargement de ressources distantes ou locales. Les archives sont lues à partir de leurs en-têtes et ne sont pas extraites.

Le paquet des coins arrondis ajoute une extension Nautilus native et une feuille CSS dédiée ; il dépend du paquet principal.

## Limites

- Le rendu des documents est destiné à la consultation : marges, en-têtes/pieds de page, polices exactes, colonnes et sauts de page peuvent différer.
- Les PDF utilisent un aperçu simplifié.
- Les présentations affichent le texte des diapositives, sans images ni mise en page complète.
- Les tableurs affichent les valeurs, sans couleurs, cellules fusionnées ni graphiques. Les formules XLSX sans valeur calculée enregistrée peuvent rester vides.
- Les formats Office binaires anciens `.doc`, `.xls` et `.ppt` ne sont pas pris en charge.
- Les images Markdown ne sont intégrées que si elles sont locales au dossier du fichier ou à ses sous-dossiers ; les images distantes sont bloquées.
- Les fichiers distants (SMB, MTP, etc.) ne sont pas pris en charge.
- Des limites de taille et de durée empêchent de bloquer Sushi ; les tables et archives volumineuses peuvent être tronquées avec indication.

## Dépannage

Si les aperçus ne se chargent pas, lance Sushi depuis un terminal avec un fichier pour voir les erreurs :

```fish
sushi "/chemin/vers/compte-rendu.docx"
```

Vérifier les fichiers installés :

```fish
pacman -Ql sushi-thumbnailer-docs-extra
pacman -Ql nautilus-vignettes-arrondies-sushi
```

Pour vérifier le type MIME attribué à un document :

```fish
gio info -a standard::content-type fichier.docx
```

Après installation ou mise à jour, le script s’occupe de vider le cache des miniatures. Si le problème persiste, vérifier le type MIME et les erreurs de chargement du plugin. Si WPS Office a remplacé les types MIME standards par des types `application/wps-office.*`, le paquet les reconnaît ; un fichier personnel `~/.local/share/mime/packages/Override.xml` peut néanmoins expliquer un comportement inhabituel.

## Désinstallation

```fish
sudo pacman -Rns nautilus-vignettes-arrondies-sushi sushi-thumbnailer-docs-extra
nautilus -q
```
