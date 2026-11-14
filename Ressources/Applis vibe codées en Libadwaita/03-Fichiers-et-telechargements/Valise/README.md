# Valise

Petit collecteur de fichiers GTK4/libadwaita : on y dépose des fichiers au fil de la navigation, puis on les ressort tous ensemble — par glisser-déposer, copier, couper ou en archive ZIP. Complément de Copyous : Copyous retient ce qu'on copie, Valise retient ce qu'on veut emporter ailleurs.

**Usage strictement personnel, non diffusé.**

## Fonctions

- **Ajouter** : glisser-déposer dans la fenêtre, **Ctrl+V** (fichiers copiés dans Fichiers ou choisis dans Copyous) ou bouton **+**. Fichiers et dossiers ; les doublons sont ignorés.
- **Sélection** : un cercle par élément, coché par défaut. Menu : « Tout sélectionner » (**Ctrl+A**) / « Tout désélectionner » (**Ctrl+Maj+A**).
- **Actions sur les éléments cochés** (barre du bas) :
  - Copier (**Ctrl+C**) et Couper (**Ctrl+X**), à coller dans Fichiers — Couper déplace les originaux ;
  - Zipper : nom `valise-AAAA-MM-JJ.zip` proposé, emplacement au choix, archive créée en arrière-plan ;
  - Retirer de la valise (**Suppr**). « Vider la valise » dans le menu.
- **Glisser vers l'extérieur** (site web, pièce jointe, Fichiers…) : glisser une ligne cochée emporte toute la sélection ; une ligne non cochée part seule.
- **Survol** : aperçu (miniature pour les images, premières lignes pour les textes, grande icône sinon) et dossier d'origine.
- **Clic droit** : « Ouvrir le dossier d'origine », « Retirer de la valise ».
- **Mémoire** : Valise garde des **références**, jamais des copies. Le contenu est conservé entre deux lancements (`~/.local/state/valise/items.json`). Un fichier déplacé ou supprimé apparaît grisé, « Introuvable » ; l'état est revérifié à chaque retour sur la fenêtre.
- **Ouvrir avec Valise** : `valise fichier1 fichier2…` ajoute les fichiers à la valise ouverte.

## Toujours au premier plan

Sous Wayland, une application ne peut pas se mettre elle-même au premier plan. L'extension maison « Always on top, always on top » (v31 et plus) s'en charge : Valise figure par défaut dans sa liste « Au premier plan dès l'ouverture » (préférences de l'extension).

## Installation

Dépendances : `python`, `python-gobject`, `gtk4`, `libadwaita`, `gdk-pixbuf2`.

```fish
sudo pacman -U valise-1.0.0-1-any.pkg.tar.zst
```

## Organisation

```
/usr/bin/valise                          lanceur (exec python3 /usr/lib/valise/main.py)
/usr/lib/valise/main.py                  point d'entrée (nom de processus « valise »)
/usr/lib/valise/valise/application.py    Adw.Application, raccourcis, À propos
/usr/lib/valise/valise/window.py         fenêtre, dépôt, presse-papier, actions
/usr/lib/valise/valise/row.py            ligne : sélection, aperçu au survol, glisser, menu
/usr/lib/valise/valise/item.py           élément (référence à un fichier + infos)
/usr/lib/valise/valise/store.py          sauvegarde/chargement de la liste
/usr/lib/valise/valise/transfer.py       contenu copier/couper/glisser, zip
/usr/share/applications/io.gitlab.shogu.Valise.desktop
/usr/share/icons/hicolor/scalable/apps/io.gitlab.shogu.Valise.svg
/usr/share/icons/hicolor/symbolic/apps/io.gitlab.shogu.Valise-symbolic.svg
```

Le code est installé dans `/usr/lib/valise/` (jamais dans `site-packages`), pour survivre aux mises à jour de Python.

## Reconstruire le paquet

```fish
PKGEXT=.pkg.tar.zst makepkg -f
```

## Tests

### Faits hors session GNOME (GTK 4.14, libadwaita 1.5, rendu Broadway)

- Lancement de l'appli depuis le paquet construit, sans erreur dans le journal.
- Fenêtre vide (« Valise vide » avec la symbolique) et liste chargée depuis `items.json` : cercles cochés/décochés, fichier supprimé grisé « Introuvable », compteur « 2 sur 4 ».
- Survol : aperçu d'une image PNG, premières lignes d'un texte, dossier d'origine.
- Création d'un ZIP contenant un dossier et un fichier (arborescence correcte).
- `ruff` : aucune erreur.

### À vérifier en session

1. Glisser des fichiers depuis Fichiers dans Valise, puis de Valise vers Fichiers, un navigateur (zone d'envoi) et un mail.
2. Copier puis coller dans Fichiers ; Couper puis coller → fichiers déplacés, lignes grisées au retour dans Valise.
3. Ctrl+V après un Ctrl+C dans Fichiers, et depuis le picker de Copyous.
4. Miniatures dans la liste pour les images déjà vues dans Fichiers.
5. Ouverture au premier plan avec l'extension Always on top v31+.
