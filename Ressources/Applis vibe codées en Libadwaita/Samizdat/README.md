# Samizdat 0.8.0

Traitement de texte GNOME léger, écrit en Rust avec GTK4/libadwaita et basé sur **letters-core**, le moteur de documents de [gtk-office-suite](https://github.com/tuna-os/gtk-office-suite) (GPL-3.0). Samizdat vise les cours, sujets et documents élèves, avec une interface native GNOME plutôt qu’une suite bureautique complète.

## Formats

- DOCX, ODT, Markdown, texte brut et HTML : ouverture, modification et enregistrement.
- PDF : ouverture en lecture seule, zoom, recherche et sélection/copier du texte ; export PDF depuis les documents éditables.

## Édition et typographie

- Police, taille, couleur, surlignage en six couleurs, gras, italique, souligné et barré.
- Typographie française toujours active : espaces insécables avant « ; : ! ? », guillemets français et apostrophe typographique.
- Styles de paragraphes (corps de texte, titres 1 à 4), alignements, interligne, retraits et listes à puces/numérotées multiniveaux.
- Numérotation des lignes de textes de français : repère toutes les cinq lignes, avec redémarrage à 1 pour chaque texte ; export pris en charge en PDF, DOCX et ODT.
- Six styles de cartouches (Définition, Problématique, À retenir, Extrait, Document, Sujet), personnalisation des coins, du trait et du fond ; sortie par Entrée sur ligne vide ou Maj+Entrée.
- Formes : flèches, carré, rectangle, cercle et étoile, avec six couleurs ou contour transparent.
- Tableaux avec ajout/suppression de lignes et colonnes ; les styles de cellules sont conservés.
- Frises chronologiques avec aperçu en direct, échelle en années et dates sous forme d’années, périodes, dates avant notre ère ou jour/mois. Double-clic pour les modifier ; les données restent enregistrées dans le texte alternatif de l’image.
- Liens hypertexte avec Ctrl+K.

## Images, orthographe et mise en page

- Insertion depuis un fichier, collage d’images et de captures (Ctrl+V), glisser-déposer depuis le gestionnaire de fichiers ou une page web.
- Redimensionnement par poignée, recadrage, rotation, miroir, luminosité, contraste, coins arrondis, cadre fin et légendes « Document 1, 2… ».
- Texte alternatif conservé dans le DOCX ; option pour placer chaque image seule sur sa ligne.
- Correcteur orthographique français Hunspell, suggestions au clic droit et dictionnaire personnel.
- Format papier, orientation, marges, en-têtes et pieds de page à trois zones sur deux lignes, numéros de page et colonnes équilibrées de une à trois.
- Plan des titres (F9), navigation par clic, sommaire automatique avec numéros de page.
- Aperçu paginé, recherche/remplacement (Ctrl+F / Ctrl+H) et zoom (Ctrl+plus, Ctrl+moins, Ctrl+0).

## Modèles et documents pédagogiques

Quatre modèles DOCX sont fournis :
1. **Cours** ;
2. **Page de garde de séquence**, avec cartouches Problématique et Document ;
3. **Bac blanc Français** ;
4. **Bac blanc Histoire-Géographie**, avec page de garde, tableau des parties, dossiers documentaires, questions, annexes NOM/Prénom, frise à compléter, cadre d’anonymat et pied de page à trois zones.

Il est possible d’enregistrer un document comme modèle, d’importer un modèle et de choisir le modèle de démarrage dans les préférences. Dossier par défaut : `~/.local/share/samizdat/modeles`.

Les modèles joints à la version 0.8.0 sont à placer dans `Ressources/Applis vibe codées en Libadwaita/Samizdat/Modeles/` du dépôt :
- `Cours.docx`
- `Page de garde de séquence.docx`
- `Bac blanc Français.docx`
- `Bac blanc Histoire-Géographie.docx`

## Aménagements et exports

Le bouton **Aménagements**, masquable, produit un PDF séparé « Nom (aménagé).pdf » sans modifier l’original. Réglages : Luciole ou OpenDyslexic (incluses), taille 16 ou 20 pt, interligne augmenté, alignement à gauche, une ligne sur deux teintée et contraste renforcé. Les derniers réglages sont mémorisés.

- Enregistrer : enregistrement direct, Enregistrer sous, Enregistrer comme modèle.
- Exporter : PDF, DOCX + PDF, livret de séquence ou copie vers une clé USB.
- Livret de séquence : rassemble les documents d’un dossier dans l’ordre naturel, évite de reprendre un PDF doublon d’un DOCX, permet de réordonner/ajouter/retirer des documents et produit couverture, sommaire et numérotation continue ; version aménagée possible.

## Onglets, concentration et sécurité

- Nouvel onglet/fenêtre, aperçu des onglets, détachement d’un onglet vers une fenêtre.
- Alt+1…9 pour choisir un onglet ; Ctrl+Page précédente/suivante pour naviguer entre onglets.
- Mode concentration : F11 pour entrer, Échap pour sortir, plein écran et barres masquées ; option de centrage de la ligne en cours.
- Annuler/rétablir sans limite, documents récents, glisser-déposer d’un fichier pour l’ouvrir.
- Sauvegarde de secours automatique toutes les deux minutes avec récupération après plantage ; confirmation avant de fermer un document non enregistré.
- Dossier de documents par défaut : `~/Dropbox/LYCEE/CLASSES`. Le premier Titre 1 peut servir de nom de fichier proposé ; option d’enregistrement automatique d’un PDF à côté du document.

## Préférences et raccourcis

Les préférences (Ctrl+,) règlent la police/taille, le modèle de démarrage, le titre utilisé comme nom de fichier, la vérification orthographique à l’ouverture, le collage d’images web, les légendes, le dossier des documents, la copie PDF, les boutons masquables, le Plan au démarrage, le zoom et le centrage en mode concentration.

| Raccourci | Action |
|---|---|
| Ctrl+N / Ctrl+T | Nouveau document / onglet |
| Ctrl+Maj+N | Nouvelle fenêtre |
| Ctrl+O | Ouvrir |
| Ctrl+S / Ctrl+Maj+S | Enregistrer / Enregistrer sous |
| Ctrl+E | Exporter en PDF |
| Ctrl+W / Ctrl+Maj+W / Ctrl+Q | Fermer onglet / fenêtre / quitter |
| Ctrl+Z / Ctrl+Maj+Z ou Ctrl+Y | Annuler / rétablir |
| Ctrl+B / Ctrl+I / Ctrl+U | Gras / italique / souligné |
| Ctrl+1 / Ctrl+2 / Ctrl+3 | Titre 1 / 2 / 3 |
| Ctrl+K | Insérer un lien |
| Ctrl+F / Ctrl+H | Rechercher / remplacer |
| Ctrl+plus / moins / 0 | Zoom avant / arrière / 100 % |
| Tab / Maj+Tab | Niveau de liste suivant / précédent |
| Maj+Entrée | Sortir d’un cartouche |
| Alt+1…9 | Aller à l’onglet 1 à 9 |
| Ctrl+PgPréc / Ctrl+PgSuiv | Onglet précédent / suivant |
| F9 | Afficher/masquer le Plan |
| F11 / Échap | Mode concentration |
| Ctrl+, | Préférences |

## Interface et limites connues

- Thème clair/sombre du système, icônes symboliques et sélection bleu Adwaita.
- Barre d’outils qui se replie par groupes lorsque la fenêtre est étroite.
- Polices Luciole et OpenDyslexic installées avec le paquet.
- Dans l’éditeur, les tableaux apparaissent sous forme de grille de texte ; ce sont de vrais tableaux dans les exports DOCX, ODT et PDF.
- La saisie défile en continu sans séparation en pages ; le PDF exporté est paginé.
- Les images et cartouches restent dans le fil du texte, sans placement flottant libre.
- Dans Word, les coins des cartouches sont carrés ; la numérotation des lignes repart à chaque page et ne s’applique pas aux lignes des tableaux.
- Dans un cartouche justifié, une ligne terminée par un retour à la ligne peut être étirée ; les modèles utilisent l’alignement à gauche.
- Les commentaires et le suivi des modifications ne sont pas proposés.

## Compiler et installer

Avec le paquet Arch fourni, installer celui-ci avec pacman :

```fish
sudo pacman -U ./samizdat-0.8.0-1-x86_64.pkg.tar.zst
```

Pour compiler depuis les sources sur Arch :

```sh
makepkg -si
# ou, depuis les sources :
cargo build --release
xvfb-run cargo test -p samizdat
```

Le `[patch.crates-io]` du `Cargo.toml` (fork épinglé d’`oxml-layout`) est nécessaire à la compilation. Les tests GTK nécessitent un affichage.

## Licence

GPL-3.0-or-later, comme letters-core.
