# Samizdat 0.11.0

Traitement de texte GNOME léger, écrit en Rust avec GTK4/libadwaita et basé sur **letters-core**, le moteur de documents de [gtk-office-suite](https://github.com/tuna-os/gtk-office-suite) (GPL-3.0). Samizdat vise les cours, sujets et documents élèves, avec une interface native GNOME plutôt qu’une suite bureautique complète. Ce README regroupe les fonctions de la version 0.8.0 et les ajouts des versions 0.8.1 à 0.11.0.

## Formats

- DOCX, ODT, Markdown, texte brut et HTML : ouverture, modification et enregistrement.
- PDF : ouverture en lecture seule, zoom, recherche, sélection/copier du texte et OCR ; export PDF depuis les documents éditables.

## Édition et typographie

- Police, taille, couleur, surlignage en six couleurs, gras, italique, souligné et barré.
- Typographie française automatique : espaces insécables, guillemets français, apostrophe typographique et points de suspension.
- Styles de paragraphes (corps de texte, titres 1 à 4), alignements, interligne, retraits et listes à puces/numérotées multiniveaux.
- Menu de style représenté par une icône ¶ : l’infobulle indique le style sous le curseur et le menu coche le style courant. Raccourcis Ctrl+1 à Ctrl+3 pour les titres.
- Bouton de retrait unique : ajoute ou retire le retrait ; dans une liste, passe au sous-niveau ou revient au premier niveau. Tab et Maj+Tab conservent la navigation par niveau.
- Boutons séparés pour aligner à gauche et centrer ; la flèche du bouton Centrer donne accès à l’alignement à droite, au justifié, à l’interligne et à la numérotation des lignes.
- Numérotation des lignes de textes de français : repère toutes les cinq lignes, avec redémarrage à 1 pour chaque texte ; export pris en charge en PDF, DOCX et ODT.
- Six styles de cartouches (Définition, Problématique, À retenir, Extrait, Document, Sujet), personnalisation des coins, du trait et du fond ; sortie par Entrée sur ligne vide ou Maj+Entrée.
- Formes : flèches, carré, rectangle, cercle et étoile, avec six couleurs ou contour transparent.
- Tableaux avec ajout/suppression de lignes et colonnes ; les styles de cellules sont conservés.
- Frises chronologiques avec échelle en années et dates sous forme d’années, périodes, dates avant notre ère ou jour/mois. Double-clic pour les modifier ; les données restent enregistrées dans le texte alternatif de l’image.
- Liens hypertexte avec Ctrl+K.

## Images

- Insertion depuis un fichier, collage d’images et de captures (Ctrl+V), glisser-déposer depuis le gestionnaire de fichiers ou une page web.
- Redimensionnement par poignée, recadrage, rotation, miroir, luminosité, contraste, coins arrondis, cadre fin et légendes « Document 1, 2… ».
- Texte alternatif conservé dans le DOCX ; option pour placer chaque image seule sur sa ligne.
- Fenêtre Image accessible par double-clic dans le texte ou l’aperçu : recadrage, retouches, légende et texte de l’image.

## Texte d’une image (OCR)

La reconnaissance optique de caractères utilise **Tesseract en français**. Elle permet de récupérer du texte imprimé depuis une capture d’écran, une image ou un PDF scanné.

- **Coller une image (Ctrl+V)** : l’image est collée comme d’habitude et une notification propose « Coller le texte à la place ». Cliquer remplace l’image par son texte inséré au curseur ; sinon, la notification disparaît après quelques secondes. Le choix se fait à chaque collage. Si le document a changé entre-temps, l’image est conservée et le texte est ajouté au curseur.
- **Bouton OCR** dans la barre d’outils : « Insérer le texte d’une image ou d’un PDF scanné ». Le fichier sélectionné est traité et le texte est inséré au curseur ; toutes les pages d’un PDF sont traitées avec une indication de progression.
- **Image déjà dans le document** : dans la fenêtre Image, la rubrique « Texte de l’image → Extraire » ajoute le texte reconnu sous l’image, aligné à gauche.
- **Onglet PDF** : le bouton « Texte (OCR) » permet de copier le texte de la page courante ou de tout le document dans le presse-papiers, puisque le PDF est en lecture seule.
- **Nettoyage du résultat** : lignes recollées en paragraphes, césures de fin de ligne supprimées, puces/numéros/tirets de dialogue préservés et typographie française appliquée (espaces insécables, guillemets français, apostrophe ’, points de suspension).
- **Traitement en arrière-plan** : l’interface reste réactive. Compter environ 1 à 3 secondes par page ; les petites captures sont agrandies et placées sur fond blanc avant reconnaissance.
- **Annulation** : tout le texte inséré par une opération OCR est retiré par un seul Ctrl+Z.
- **Limites** : le moteur reconnaît le texte imprimé, pas l’écriture manuscrite. Les documents complexes en plusieurs colonnes sont moins bien reconnus.

Les dépendances `tesseract` et `tesseract-data-fra` sont installées automatiquement par pacman avec le paquet Samizdat.

## Orthographe

- Correcteur orthographique français Hunspell, suggestions au clic droit et dictionnaire personnel.
- « Corriger tout le document » applique, après confirmation, la première suggestion du dictionnaire à chaque mot souligné. Les noms propres commençant par une majuscule en milieu de phrase sont ignorés ; les mots sans suggestion restent soulignés. Un seul Ctrl+Z annule toutes les corrections de l’opération.

## Mise en page, plan et sommaire

- Format papier, orientation, marges, en-têtes et pieds de page à trois zones sur deux lignes, numéros de page et colonnes équilibrées de une à trois.
- Plan des titres (F9), navigation par clic et sommaire automatique avec numéros de page.
- Règle graduée optionnelle (Ctrl+R ou bouton de la barre du bas), masquée par défaut avec état mémorisé. Graduation en centimètres tous les 0,25 cm ; le triangle bleu indique le retrait du paragraphe et peut être déplacé par pas de 0,25 cm. Des clics sur les graduations posent/retirent des lignes repères verticales bleues.
- La page de l’éditeur n’est pas une maquette exacte de la page imprimée : le texte se réadapte à la largeur de la fenêtre. Pour contrôler le résultat paginé, utiliser l’aperçu.

## Aperçu en direct

Le panneau d’aperçu s’affiche à droite du texte et représente les pages comme elles apparaîtront dans le PDF.

- **Afficher/masquer** : F12, bouton Aperçu de la barre du bas ou croix du panneau.
- **Actualisation pendant la frappe** : les pages se redessinent environ une demi-seconde après la dernière touche ; seules les pages visibles sont dessinées.
- **Suivi du curseur** : la ligne en cours est repérée en bleu et l’aperçu suit automatiquement la page où l’on écrit. Le panneau affiche le numéro de page courant.
- **Clic sur une page** : place le curseur à l’endroit correspondant dans le texte. **Double-clic** : ouvre l’outil de l’élément (image, frise, tableau ou cartouche).
- **Largeur ajustable** par glissement de la séparation ; la largeur est mémorisée. Les pages se redimensionnent avec le panneau.
- Dans une fenêtre étroite, l’aperçu passe au-dessus du texte. Il est masqué en mode concentration et dans un onglet PDF.
- Le bouton Aperçu est scindé : clic pour l’aperçu en direct, flèche pour « Aperçu en grand », l’ancienne fenêtre d’aperçu.

## Modèles et documents pédagogiques

Quatre modèles DOCX sont fournis :
1. **Cours** ;
2. **Page de garde de séquence**, avec cartouches Problématique et Document ;
3. **Bac blanc Français** ;
4. **Bac blanc Histoire-Géographie**, avec page de garde, tableau des parties, dossiers documentaires, questions, annexes NOM/Prénom, frise à compléter, cadre d’anonymat et pied de page à trois zones.

Il est possible d’enregistrer un document comme modèle, d’importer un modèle et de choisir le modèle de démarrage dans les préférences. Dossier par défaut : `~/.local/share/samizdat/modeles`.

Les quatre modèles préétablis sont regroupés dans l’archive `Modèles de cours en docx (Samizdat).tar.xz`, disponible sous `Ressources/Applis vibe codées en Libadwaita/02-Bureautique-et-redaction/Samizdat/Modeles/` :
- `Cours.docx`
- `Page de garde de séquence.docx`
- `Bac blanc Français.docx`
- `Bac blanc Histoire-Géographie.docx`

### Télécharger et importer les modèles

1. Télécharger le dépôt GitLab (ou récupérer uniquement l’archive ci-dessus).
2. Extraire l’archive `.tar.xz` pour obtenir les quatre fichiers DOCX.
3. Dans Samizdat, ouvrir les préférences avec `Ctrl+,`, lancer l’importation d’un modèle et sélectionner les fichiers DOCX extraits.
4. Choisir ensuite le modèle souhaité dans les préférences comme modèle de démarrage, si besoin.

Le téléchargement de l’archive ne les importe pas automatiquement dans l’application.

## Aménagements et exports

Le bouton **Aménagements**, masquable, produit un PDF séparé « Nom (aménagé).pdf » sans modifier l’original. Réglages : Luciole ou OpenDyslexic (incluses), taille 16 ou 20 pt, interligne augmenté, alignement à gauche, une ligne sur deux teintée et contraste renforcé. Les derniers réglages sont mémorisés.

- Enregistrer : enregistrement direct, Enregistrer sous, Enregistrer comme modèle.
- Exporter : PDF, DOCX + PDF, livret de séquence ou copie vers une clé USB.
- Livret de séquence : rassemble les documents d’un dossier dans l’ordre naturel, évite de reprendre un PDF doublon d’un DOCX, permet de réordonner/ajouter/retirer des documents et produit couverture, sommaire et numérotation continue ; version aménagée possible.
- Les opérations de sauvegarde et de copie expliquent désormais la cause probable des erreurs (support en lecture seule, dossier appartenant à root, espace insuffisant). La copie vers une clé USB fabrique d’abord les fichiers sur l’ordinateur, puis les recopie tels quels, ce qui évite les problèmes de droits sur les supports FAT, exFAT et NTFS.

## Onglets, concentration et sécurité

- Nouvel onglet/fenêtre, aperçu des onglets, détachement d’un onglet vers une fenêtre.
- Alt+1…9 pour choisir un onglet ; Ctrl+Page précédente/suivante pour naviguer entre onglets.
- **Mode concentration** : F11 pour entrer, Échap pour sortir, plein écran et barres masquées. L’écran est entièrement blanc, en thème clair comme sombre, sans fond gris ni bord de page. Une demi-hauteur d’écran vide au-dessus et au-dessous permet de centrer le texte dès la première ligne ; la ligne en cours reste centrée si l’option « Ligne centrée » est activée. On peut entrer dans ce mode pendant la frappe, y compris dans un cartouche ou un titre, sans déplacer le curseur.
- Annuler/rétablir sans limite, documents récents, glisser-déposer d’un fichier pour l’ouvrir.
- Sauvegarde de secours automatique toutes les deux minutes avec récupération après plantage ; confirmation avant de fermer un document non enregistré.
- Dossier de documents par défaut : `~/Dropbox/LYCEE/CLASSES`. Le premier Titre 1 peut servir de nom de fichier proposé ; option d’enregistrement automatique d’un PDF à côté du document.

## Préférences et interface

Les préférences (`Ctrl+,`) règlent la police/taille, le modèle de démarrage, le titre utilisé comme nom de fichier, la vérification orthographique à l’ouverture, le collage d’images web, les légendes, le dossier des documents, la copie PDF, les boutons masquables, le Plan au démarrage, l’aperçu à droite au démarrage, le zoom et le centrage en mode concentration. Le bouton OCR fait partie des boutons masquables.

- Infobulles explicites pour les boutons d’insertion de cartouche, de frise chronologique et d’OCR.
- Annuler/Rétablir sont placés à gauche de la barre d’outils ; les commandes de mise en forme restent centrées.
- La barre d’outils est plus compacte (environ 1120 px au lieu de 1370 px). Les groupes se replient sous environ 1180 px ; les boutons d’insertion rejoignent alors le menu « + ».
- La phrase d’essai du choix de police est le début du *Manifeste du parti communiste* : « Un spectre hante l’Europe… ».

## Raccourcis clavier

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
| F12 | Afficher/masquer l’aperçu en direct |
| Ctrl+R | Afficher/masquer la règle |
| Ctrl+, | Préférences |

## Corrections et limites connues

- La sélection de texte est conservée lors du changement de police, de taille ou de couleur.
- Cliquer dans la page après la barre d’outils ne provoque plus de remontée intempestive en haut ni de sélection accidentelle ; le défilement suit le curseur pendant la frappe et avec les flèches.
- Les tableaux apparaissent sous forme de grille de texte dans l’éditeur ; ce sont de vrais tableaux dans les exports DOCX, ODT et PDF.
- La saisie défile en continu sans séparation en pages ; le PDF exporté est paginé.
- Les images et cartouches restent dans le fil du texte, sans placement flottant libre.
- Dans Word, les coins des cartouches sont carrés ; la numérotation des lignes repart à chaque page et ne s’applique pas aux lignes des tableaux.
- Dans un cartouche justifié, une ligne terminée par un retour à la ligne peut être étirée ; les modèles utilisent l’alignement à gauche.
- Les commentaires et le suivi des modifications ne sont pas proposés.

## Compiler et installer

Les dépendances OCR sont déclarées par le paquet et installées automatiquement par pacman : `tesseract` et `tesseract-data-fra`.

Depuis le dossier contenant l’archive compilée, installer le paquet Samizdat avec pacman. Le nom exact dépend de la version de construction ajoutée au dépôt :

```fish
sudo pacman -U ./samizdat-*.pkg.tar.zst
```

Vérifier qu’un seul paquet Samizdat correspond au motif avant d’exécuter la commande.

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
