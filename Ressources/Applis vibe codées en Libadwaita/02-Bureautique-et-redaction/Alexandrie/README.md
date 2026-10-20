<p align="center">Visionneuse simple de Wikipédia en français pour GNOME, en GTK 4 et libadwaita.</p>

Alexandrie sert à lire des articles d'histoire, de géographie et de littérature pour préparer des cours. On y garde des extraits dans un panier, puis on les colle dans un traitement de texte ou on les exporte en fiche PDF.

## Fonctionnalités

- Lecture épurée en onglets, avec sommaire latéral, aperçu des liens au survol, recherche dans l'article et historique.
- Dates clés tirées de Wikidata (vie, œuvres, événements, fonctions), carte OpenStreetMap et lieux cités ouvrables dans GNOME Cartes.
- Panier d'extraits (passages, images, dates, consignes, glossaire), documents numérotés, à copier ou à exporter en PDF.
- Favoris classés par tags libres.
- Quatre sources : Encyclopédie (Wikipédia), Vikidia (8–13 ans), Textes (Wikisource) et Images (Commons) ; Wiktionnaire au double-clic et rubrique « Voir aussi ».

## Installation (Arch, CachyOS)

Depuis le dossier des sources :

```sh
makepkg -si
```

Ou, avec le paquet déjà construit :

```sh
sudo pacman -U ./alexandrie-*.pkg.tar.*
```

Vérifier qu'un seul paquet Alexandrie correspond au motif avant de lancer la commande.

## Essai sans installer

Depuis le dossier des sources :

```sh
./run.sh
```

## Documentation

Le guide complet fourni avec les sources, `docs/GUIDE.md`, détaille les fonctionnalités, les raccourcis, les préférences et l'emplacement des données. Le code source et ce guide ne sont pas encore présents dans ce dossier du dépôt de configuration ; ce README récapitule les informations disponibles.

## Paquet dans ce dépôt

Le sous-dossier est créé pour accueillir la documentation et le paquet compilé. Le paquet Alexandrie sera ajouté manuellement lorsqu'il sera disponible ; aucun fichier de paquet n'est prétendu présent pour le moment.

## Licence

GPL-3.0-or-later. Les contenus affichés viennent des projets Wikimedia (CC BY-SA 4.0 ; chaque image a sa propre licence).
