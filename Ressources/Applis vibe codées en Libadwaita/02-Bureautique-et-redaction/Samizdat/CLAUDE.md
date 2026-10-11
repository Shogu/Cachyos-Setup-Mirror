# Samizdat

Traitement de texte léger pour GNOME : ouvre/édite/enregistre **DOCX, ODT, Markdown**, texte brut et HTML, export **PDF**. Mise en forme, styles de paragraphe, listes, tableaux, images (redimensionnement, recadrage), mise en page, plan, rechercher/remplacer, annuler/rétablir.

## Technique

- **Rust**, GTK4/libadwaita (gtk4-rs / libadwaita-rs), éditeur basé sur `GtkTextView`. Moteur de document : **letters-core** de https://github.com/tuna-os/gtk-office-suite (GPL-3.0), avec corrections maison (position des tableaux DOCX, paragraphes vides ajoutés à chaque enregistrement, images dans leur paragraphe).
- Toute commande passe par le modèle letters-core et doit s'annuler en **un seul Ctrl+Z**.
- Build : `cargo build --release` ; tests : `xvfb-run cargo test -p samizdat` (besoin d'un affichage). Le `[patch.crates-io]` de `Cargo.toml` (fork épinglé d'`oxml-layout`) est indispensable. Paquet : `makepkg -si`.
- Licence GPL-3.0-or-later.

## État

- Seul `README.md` est présent : ni sources ni paquet. Le paquet est à ajouter par Ogu ; nom et version encore inconnus (`docs/11` §11.25 à compléter à son arrivée).
- Limites connues : tableaux affichés en grille de texte dans l'éditeur, pas de pagination à l'écran, pas de commentaires ni de suivi des modifications.
