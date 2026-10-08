# Samizdat

Samizdat est un traitement de texte simple pour GNOME, écrit en Rust avec GTK 4
et libadwaita. Il ouvre, modifie et enregistre des documents Word (DOCX),
OpenDocument (ODT) et Markdown, et les exporte en PDF.

L'objectif n'est pas de remplacer LibreOffice ou OnlyOffice : c'est un éditeur
léger, rapide à lancer, intégré au bureau GNOME, pour écrire et retoucher des
documents courants.

## D'où vient-il ?

Samizdat repose sur **letters-core**, le moteur de documents du projet
[gtk-office-suite](https://github.com/tuna-os/gtk-office-suite) (GPL-3.0). Ce
moteur fournit le modèle de document et la lecture et l'écriture des formats.
Samizdat y ajoute sa propre interface.

## Ce qu'il sait faire

- **Formats :** il ouvre le DOCX, l'ODT, le Markdown, le texte brut et le HTML,
  enregistre dans ces mêmes formats et exporte en PDF.
- **Mise en forme du texte :** police, taille, couleur, surlignage, gras,
  italique, souligné et barré.
- **Paragraphes :** styles (corps de texte, titres, citation), alignements,
  listes à puces et numérotées sur plusieurs niveaux, retraits, espacement et
  interligne.
- **Tableaux :** insertion, ajout et suppression de lignes et de colonnes.
- **Images :** insertion, redimensionnement à la souris par une poignée au coin,
  taille précise et recadrage.
- **Mise en page :** format du papier, orientation, marges, en-tête et pied de
  page.
- **Navigation :** plan du document dans un panneau latéral, rechercher et
  remplacer.
- **Confort :** annuler et rétablir, glisser-déposer d'un fichier, alerte avant
  de fermer un document non enregistré.

L'interface n'utilise que les composants natifs de GNOME (barre de titre,
dialogues, panneau latéral, notifications, sélecteurs de police et de
couleur…), et suit le thème clair ou sombre du système. La page reste blanche,
comme une feuille de papier.

## Ce qui a été ajouté par rapport au projet d'origine

- **Une nouvelle interface**, plus simple, construite autour de l'éditeur de
  texte de GTK.
- **Les commandes** de police, de couleur, de retraits, de recherche, de
  tableaux, de mise en page, d'images et de plan, toutes branchées sur le
  modèle de letters-core : chaque action s'annule d'un seul Ctrl+Z.
- **La frappe passe par le modèle de document :** le texte tapé reprend le style
  voulu, et le curseur reste au bon endroit après un saut de paragraphe.
- **Des corrections dans letters-core :**
  - à la lecture d'un DOCX, les tableaux restaient en fin de document ; ils
    sont remis à leur place ;
  - chaque enregistrement ajoutait des paragraphes vides autour des images et
    après les tableaux ; le document reste maintenant identique d'un
    enregistrement à l'autre ;
  - les images restent dans leur paragraphe, ce qui conserve leur alignement.

## Limites connues

- Les tableaux s'affichent sous forme de grille de texte dans l'éditeur. Ce
  sont de vrais tableaux dans le DOCX, l'ODT et le PDF.
- Pendant la saisie, le texte défile en continu, sans séparation en pages.
  L'export PDF, lui, est paginé.
- Les commentaires et le suivi des modifications ne sont pas proposés.

## Compiler et installer

Sur Arch Linux, avec le PKGBUILD fourni :

    makepkg -si

À la main :

    cargo build --release
    xvfb-run cargo test -p samizdat    # les tests GTK ont besoin d'un affichage

Le `[patch.crates-io]` du `Cargo.toml` (fork épinglé d'`oxml-layout`) est
nécessaire à la compilation.

## Licence

GPL-3.0-or-later, comme letters-core.
