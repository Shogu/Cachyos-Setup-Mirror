# Maquette

**Maquette** assemble et prépare des documents PDF. C'est une application
GTK4/libadwaita en Python (PyGObject), en français, pour CachyOS et GNOME.
Identifiant : `io.gitlab.shogu.Maquette`.

La grille de miniatures montre **toujours le document final** tel qu'il sera
enregistré : ordre des pages, rotations, recadrages, texte ajouté. Rien n'est
écrit sur le disque avant « Enregistrer sous… ».

## Ce que fait l'application

- **Assembler** : ouvrir plusieurs PDF et images d'un coup, par le bouton
  « Insérer » ou en les déposant sur la fenêtre. Une fine bande de couleur sous
  chaque miniature rappelle de quel fichier vient la page.
- **Choisir le dossier d'enregistrement** : dans les préférences, « Dossier
  proposé » accepte le dossier du premier fichier, le dernier dossier utilisé,
  ou **toujours le même** — ton dossier de cours, choisi une fois pour toutes.
- **Réordonner** par glisser-déposer, y compris plusieurs pages à la fois. En
  glissant près d'un bord, la grille défile toute seule.
- **Pivoter**, **supprimer**, **extraire** la sélection vers un nouveau fichier.
- **Insérer une page blanche**, au format de la page voisine ou à un format fixe.
- **Insérer des images** (PNG, JPG, WebP, GIF, TIFF, AVIF, HEIC, SVG…) : une
  image par page A4, orientation choisie d'après le format de l'image, marges
  réglables ou pleine page.
- **Recadrer** (`Ctrl+R`) : tu traces une zone sur la page en grand, puis tu
  choisis ce qu'elle devient. Voir ci-dessous.
- **Écrire sur une page** (`Ctrl+T`) : un bloc de texte posé où tu veux, avec
  son corps et sa couleur. Le cadre s'agrandit vers le bas avant que le corps
  soit réduit, pour qu'aucun mot ne disparaisse.
- **Annuler et rétablir** (`Ctrl+Z`, `Ctrl+Maj+Z`) sur toutes les opérations.
- **Aperçu du résultat** (`Ctrl+P`) : le document final, page par page, tel qu'il
  sera écrit — imposition comprise. Rien n'est enregistré.
- **Enregistrer sous…** : le bouton bleu enregistre dans la disposition réglée
  dans les préférences ; sa partie déroulante propose l'aperçu et les trois
  dispositions, pour n'en choisir une que cette fois-ci.

### Le recadrage et ses trois issues

Un seul outil, une seule zone à tracer, puis trois réponses possibles :

| Issue | Effet |
|---|---|
| **Garder cette zone** | La page est réduite à la zone tracée ; tout le reste est retiré du fichier. |
| **Vider cette zone** | La zone est vidée et devient blanche ; la page garde son format. |
| **Retirer cette zone et réduire la page** | La bande est retirée et la suite de la page remonte pour combler le vide. |

Dans les trois cas le contenu est **réellement supprimé du fichier**, pas
seulement masqué : un corrigé dont on retire les réponses ne les laisse pas
récupérables par un copier-coller.

### Brochures et livrets

La partie déroulante du bouton d'enregistrement, et le réglage « Disposition
des pages », placent deux pages par face dans l'ordre d'impression recto
verso, pour plier et agrafer au centre :

- **Brochure A5 sur A4** : deux A5 par feuille A4 paysage ;
- **Livret A4 sur A3** : deux A4 par feuille A3 paysage.

Le nombre de pages est complété par des blanches jusqu'au multiple de quatre.
L'aperçu (`Ctrl+P`) montre les feuilles telles qu'elles sortiront de
l'imprimante, ce qui évite d'imprimer pour vérifier.

L'extraction d'une sélection reste toujours en assemblage fidèle.

## Ce que l'application ne fait pas

- **Elle ne modifie pas un texte déjà présent dans un PDF.** Les polices y sont
  souvent incomplètes et le résultat casserait la mise en page. Il faut
  reprendre le document source.
- **Elle n'insère pas de ODT, DOCX ou RTF.** Sans LibreOffice, aucune
  conversion ne respecte la mise en page d'origine. Exporte le document en PDF
  depuis son éditeur, puis dépose le PDF ici. L'application le dit clairement
  si tu déposes un tel fichier.

## Installation

Le paquet est déjà compilé :

```sh
sudo pacman -U maquette-1.0.0-1-any.pkg.tar.zst
```

pacman compile le schéma GSettings et rafraîchit le cache d'icônes par ses
propres hooks ; il n'y a rien à lancer après.

**Dépendances**, toutes dans les dépôts officiels : `python`, `python-gobject`,
`python-cairo`, `gtk4`, `libadwaita`, `python-pymupdf`, `python-pillow`,
`hicolor-icon-theme`.

L'application apparaît dans « Ouvrir avec » pour les PDF et les images, sans
devenir l'application par défaut.

## Lancer depuis les sources

```sh
cd src && python3 -m maquette
```

Les icônes sont alors lues dans `data/icons`.

## Raccourcis

| Raccourci | Action |
|---|---|
| `Ctrl+O` | Insérer des fichiers |
| `Ctrl+B` | Insérer une page blanche |
| `Ctrl+S` | Enregistrer sous |
| `Ctrl+P` | Aperçu du résultat |
| `Ctrl+E` | Extraire la sélection |
| `Ctrl+Z` / `Ctrl+Maj+Z` | Annuler / rétablir |
| `Ctrl+R` | Recadrer |
| `Ctrl+T` | Écrire sur la page |
| `Ctrl+←` / `Ctrl+→` | Pivoter |
| `Ctrl+A` | Tout sélectionner |
| `Suppr` | Supprimer les pages choisies |
| `Ctrl` + molette | Agrandir ou réduire les miniatures |
| `Entrée`, double-clic | Afficher la page en grand |
| `Échap` | Revenir à la grille |

## Licence

AGPL-3.0-or-later, imposée par PyMuPDF.
