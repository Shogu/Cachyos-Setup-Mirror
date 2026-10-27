# Radar

Recherche de fichiers avec aperçu, en GTK4 et libadwaita. Un seul fichier Python, installé dans /usr/bin/radar, sans dépendance Qt.

## Fonctionnalités

- Recherche floue en mémoire (classement façon fzf, moteur maison), indexation unique du système de fichiers.
- Filtres par type, date et emplacement ; fichiers cachés affichables.
- Aperçus :
  - images ;
  - première page des PDF avec pdftoppm ;
  - texte et tableaux DOCX/ODT, lus depuis le XML sans exécuter le document ;
  - **texte des ODS/XLSX** : nom de chaque feuille et premières lignes, cellules séparées par « | », valeurs affichées, jamais les formules ;
  - **contenu des archives** : zip, tar (gz/bz2/xz/zst), 7z, rar et paquets .pkg.tar.zst, listés par bsdtar sans extraction, jusqu'à 1000 entrées ;
  - audio et vidéo ;
  - texte et code avec coloration syntaxique via GtkSourceView ;
  - les autres types affichent « Aperçu indisponible ».
- Bouton « Ouvrir avec… » affichant l'application par défaut pour le fichier sélectionné, par exemple Papers.
- Suppression d'un fichier depuis la liste (clic droit).

## Nouveautés de la version 1.6.0

1. **Aperçu ODS/XLSX.** Les noms et l'ordre des feuilles sont récupérés depuis les métadonnées du classeur. Seules les valeurs sont lues, jamais les formules ; les cellules booléennes s'affichent « VRAI »/« FAUX ».
2. **Contenu des archives.** Détection par suffixe, lecture dans un thread et affichage du nombre de fichiers et de la taille totale décompressée. Une archive chiffrée ou illisible affiche une erreur claire, sans contenu partiel.
3. **Bouton « Ouvrir avec… ».**
4. **Correctif ODT.** L'extraction du texte des documents ODT a été corrigée.

Aucune nouvelle dépendance : libarchive/bsdtar est déjà requis par pacman sur Arch.

## Installation

Le paquet compilé **radar-1.6.0-1-any.pkg.tar.zst est à ajouter manuellement au dépôt**. Une fois placé dans ce dossier :

~~~sh
sudo pacman -U ./radar-1.6.0-1-any.pkg.tar.zst
~~~

La même commande permet de mettre à jour une version précédente.

## Dépendances

- Obligatoires : python, python-gobject, gtk4, libadwaita.
- Optionnelles : gtksourceview5 (coloration), gst-plugins-gtk4 (audio/vidéo), poppler (aperçu PDF), libarchive (contenu des archives ; déjà requis par pacman sur Arch).

## Tests rapportés

Les tests de cette version ont été réalisés hors session GNOME, dans un conteneur isolé avec Xvfb et GTK4/libadwaita. Ils comprennent des fichiers ODS/XLSX validés par conversion LibreOffice, des archives zip/tar/7z et un paquet Arch, des documents DOCX/ODT, ainsi que des tests de non-régression pour les images, PDF et texte/code. Le paquet a été vérifié avec zstd -t et le script avec python -m py_compile.

**Non testé en session GNOME réelle :** rendu sous GNOME 51/Wayland et bouton « Ouvrir avec… » avec de vraies associations d'applications.

## Limites connues

- ODS/XLSX : valeurs affichées telles qu'enregistrées, sans reformattage des dates ou devises ; les formules ne sont pas recalculées, seule la valeur mise en cache est lue.
- Archives chiffrées ou tronquées : message d'erreur, aucun contenu affiché.
- Le libellé « Ouvrir avec… » dépend des associations d'applications du système ; sans association, le bouton reste « Ouvrir ».
