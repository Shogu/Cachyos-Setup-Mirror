# Dactylo — documentation et développement

Traitement de texte GNOME en Rust, GTK4/libadwaita, basé sur `letters-core` de [gtk-office-suite](https://github.com/tuna-os/gtk-office-suite) (GPL-3.0). La documentation utilisateur de référence est le [README Dactylo](README.md).

## État documenté

Le README couvre la base fonctionnelle de la version 0.8.0 et les nouveautés signalées pour les versions 0.8.1 à 0.11.0 : aperçu paginé en direct, OCR Tesseract en français, règle graduée, commandes de paragraphe remaniées, correction orthographique globale, mode concentration amélioré, interface plus compacte et corrections d’enregistrement/copie.

Le dépôt contient le README, ce fichier, les modèles DOCX sous `Modeles/` et un ancien paquet binaire Samizdat (`samizdat-0.11.3-1-x86_64.pkg.tar.zst`). Le code source n’est pas présent ici. Le paquet n’a pas été reconstruit sous le nom Dactylo : ne pas le présenter comme une release Dactylo. Ajouter le nouveau paquet après reconstruction réelle.

## Architecture et compilation

- Rust, GTK4/libadwaita (`gtk4-rs` / `libadwaita-rs`), éditeur basé sur `GtkTextView`.
- Moteur documentaire : `letters-core` de gtk-office-suite, avec correctifs locaux décrits dans l’historique de l’application.
- Toute commande doit passer par le modèle de document et pouvoir être annulée en un seul `Ctrl+Z` lorsque la fonctionnalité est conçue comme une opération atomique.
- Compilation Arch : `makepkg -si` ; compilation Cargo : `cargo build --release` ; tests : `xvfb-run cargo test -p samizdat`. Le `[patch.crates-io]` de `Cargo.toml` (fork épinglé d’`oxml-layout`) est indispensable. Les tests GTK ont besoin d’un affichage.
- Le paquet doit déclarer `tesseract` et `tesseract-data-fra` comme dépendances runtime pour que l’OCR français fonctionne après installation.

## Principes à préserver

- Garder une interface native GNOME, sobre, en GTK4/libadwaita.
- Préserver le texte sélectionné lors des changements de police, taille et couleur.
- L’OCR doit rester non bloquant, nettoyer les césures et respecter les listes, puis insérer le résultat comme une seule opération annulable.
- L’aperçu ne doit pas ralentir la frappe : temporiser le rendu après la dernière touche et ne dessiner que les pages visibles.
- Maintenir la cohérence du modèle de document, des exports DOCX/ODT/PDF et de l’annulation/rétablissement.
- Ne pas présenter la page de l’éditeur comme une maquette exacte de la pagination PDF ; c’est l’aperçu paginé qui fait foi.

## Limites documentées

- OCR prévu pour le texte imprimé ; écriture manuscrite non prise en charge et colonnes multiples complexes moins fiables.
- Dans l’éditeur, les tableaux sont représentés en grille de texte ; les exports contiennent de vrais tableaux.
- Les images et cartouches restent dans le fil du texte ; pas de placement flottant libre.
- Pas de commentaires ni de suivi des modifications.

## Licence

GPL-3.0-or-later.
