# thumbnailer-docx-nautilus-sushi

Paquet Arch `arch=any` qui complète **Sushi** (aperçu Nautilus avec la barre d’espace) et le générateur de miniatures de GNOME. Cible documentée : **CachyOS, GNOME 51 et Sushi 51.1**. Interface, messages et documentation en français.

**Version documentée : 1.6.0-1.** Le paquet compilé sera ajouté manuellement dans ce dossier ; aucun binaire n’est inclus pour le moment.

## Fonctions

- **Aperçu Sushi des documents** : DOCX, ODT, RTF, Markdown et variantes/modèles pris en charge. Les documents sont convertis en HTML et affichés dans WebKit.
- **Présentations** : PPTX, ODP et variantes ; une carte textuelle par diapositive.
- **Tableurs** : XLSX et ODS et variantes ; tableau GTK natif, avec une vue par feuille.
- **Archives** : ZIP, TAR (dont gzip, xz, zstd et bz2), 7z, RAR et paquets Arch `.pkg.tar.zst`, présentés en arborescence sans extraction.
- **Miniatures Nautilus** : documents, présentations, tableurs, texte brut et code. Les archives n’ont volontairement pas de miniature spécifique.

Les miniatures utilisent un bandeau coloré et une fiche adaptée à la famille de fichiers. Les miniatures intégrées par LibreOffice sont ignorées afin de conserver un style uniforme.

## Installation

Depuis la racine du dépôt, après avoir ajouté le paquet Arch à ce dossier :

```fish
set paquets (find "Ressources/Applis vibe codées en Libadwaita/03-Fichiers-et-telechargements/Thumbnailer Sushi" -maxdepth 1 -type f -name 'thumbnailer-docx-nautilus-sushi-*-any.pkg.tar.zst')
if test (count $paquets) -eq 1
    sudo pacman -U "$paquets[1]"
else
    echo 'Conserver un seul paquet thumbnailer-docx-nautilus-sushi dans ce dossier avant installation.'
end
```

Puis relancer Sushi et Nautilus et supprimer le cache des miniatures :

```fish
pkill -f NautilusPreviewer
nautilus -q
rm -rf ~/.cache/thumbnails/*
```

Les deux processus seront relancés au prochain usage. Le nettoyage du cache force GNOME à recréer les miniatures et à retenter celles dont l’échec avait été mémorisé.

## Dépendances et fonctionnement

Dépendances des dépôts officiels indiquées par le projet : `webkitgtk-6.0`, `python-odfpy`, `python-openpyxl`, `python-libarchive-c` et `python-markdown`. Les miniatures s’appuient aussi sur `python-gobject`, `python-cairo` et Pango. Les bibliothèques Python `mammoth` et `cobble` sont embarquées dans le paquet sous `/usr/lib/thumbnailer-docx-nautilus-sushi/vendor/`.

Le paquet installe deux plugins Sushi dans `/usr/lib/sushi/plugins-1/`, les outils Python partagés sous `/usr/lib/thumbnailer-docx-nautilus-sushi/` et le fichier de déclaration du thumbnailer sous `/usr/local/share/thumbnailers/`. Ce dernier emplacement est intentionnel : GNOME sélectionne le premier thumbnailer trouvé pour un type MIME, et ce chemin permet de passer avant le thumbnailer générique de `libgsf`.

La conversion est exécutée dans un processus Python séparé, sans shell. L’aperçu des documents HTML applique une CSP restrictive, désactive JavaScript et bloque le chargement de ressources distantes ou locales. Les archives sont listées à partir de leurs en-têtes et ne sont pas extraites.

## Limites

- Rendu documentaire de consultation : les marges, en-têtes/pieds de page, polices exactes, colonnes et sauts de page ne sont pas fidèles.
- Les présentations affichent le texte des diapositives, sans images ni mise en page.
- Les tableurs affichent les valeurs, sans couleurs, cellules fusionnées ni graphiques. Les formules XLSX sans valeur calculée enregistrée peuvent rester vides.
- Les formats binaires Office 97–2003 `.doc`, `.xls`, `.ppt` sont volontairement exclus.
- Les images Markdown ne sont intégrées que si elles sont locales au dossier du fichier ou à ses sous-dossiers ; les images distantes sont bloquées.
- Les fichiers distants (SMB, MTP, etc.) ne sont pas pris en charge.
- Des limites de taille et de durée empêchent de bloquer Sushi ; les tables et archives volumineuses peuvent être tronquées avec indication.

## Dépannage

Si les aperçus ne se chargent pas, lancer Sushi depuis un terminal avec un fichier pour voir les erreurs :

```fish
sushi "/chemin/vers/compte-rendu.docx"
```

Si le message `failed to load renderer` apparaît, un plugin n’a pas été chargé. Vérifier les fichiers installés :

```fish
pacman -Ql thumbnailer-docx-nautilus-sushi
```

Pour vérifier le type MIME attribué à un document :

```fish
gio info -a standard::content-type fichier.docx
```

Après un échec de miniature, vider le cache avec `rm -rf ~/.cache/thumbnails/*`. Si WPS Office a remplacé les types MIME standards par des types `application/wps-office.*`, le paquet les reconnaît ; un fichier personnel `~/.local/share/mime/packages/Override.xml` peut néanmoins expliquer un comportement inhabituel.

Le générateur peut être testé indépendamment de Nautilus :

```fish
python3 /usr/lib/thumbnailer-docx-nautilus-sushi/vignette.py -s 256 fichier.docx /tmp/v.png
xdg-open /tmp/v.png
```

## État des tests

Les tests hors session décrits par le projet couvrent la conversion des documents, l’affichage WebKit, le blocage des ressources externes, la lecture XLSX/ODS, les archives, les limites et la génération de miniatures via la vraie fabrique GNOME dans un bac à sable. Le fonctionnement des plugins dans la session Sushi 51.1 reste à vérifier. Des miniatures DOCX dans Nautilus 51 ont été observées en session réelle le 13/10/2026 après correction d’un remplacement MIME laissé par WPS Office.

La documentation technique complète, les maquettes retenues et les résultats détaillés sont dans les fichiers de développement du projet source ; les informations de maintenance essentielles sont résumées ici.

## Désinstallation

```fish
sudo pacman -Rs thumbnailer-docx-nautilus-sushi
pkill -f NautilusPreviewer
nautilus -q
```
