# Iconostase

Iconostase rassemble en une seule appli GNOME (GTK4 / libadwaita, Python) tout ce qui touche à l'habillage du bureau :
les icônes des applications, en couleur **et** en symbolique, les lanceurs du menu et les icônes des dossiers.

Application adaptée à GNOME 50/51 et enrichie avec les outils maison `icones-ogu` et `dossiers-ogu`.
Usage strictement personnel.

## Installation

```sh
sudo pacman -U iconostase-<version>-1-any.pkg.tar.zst
```

Dépendances : `python`, `python-gobject`, `gtk4`, `libadwaita`, `gdk-pixbuf2`, `librsvg`.
Le code est installé dans `/usr/lib/iconostase/`, avec un lanceur minimal `/usr/bin/iconostase`.

## Ce que fait l'appli

### Onglet Applications

Toute l'édition des lanceurs `.desktop` : nom, commentaire, commande, répertoire de travail,
actions, mots-clés, catégories, terminal, visibilité, GPU dédié…

La partie **Apparence** gère les deux icônes d'une appli :

- **Icône couleur** : choisie dans le thème (recherche) ou depuis un fichier SVG/PNG.
- **Icône symbolique** : aperçu en clair et en sombre, choix d'un SVG.

Une icône choisie depuis un fichier est installée dans `~/.local/share/icons/hicolor/` sous le nom du lanceur,
et le lanceur reçoit `Icon=nom` (sans chemin). C'est indispensable : GNOME ne trouve la version symbolique
d'une icône que par son nom (`nom-symbolic`). Un lanceur qui désigne son icône par un chemin affiche un bouton
**Convertir** qui fait cette opération d'un clic.

Si une appli livre des PNG en tailles fixes, Iconostase pose aussi des PNG de ton icône dans ces tailles :
sinon GNOME préférerait ceux du paquet.

Les badges de la liste signalent les lanceurs à revoir :

| Badge | Signification |
|---|---|
| triangle orange | icône désignée par un chemin, ou introuvable |
| petite icône grise | pas de version symbolique |

### Onglet Dossiers

- **Mes dossiers** : le bouton **+** ajoute un dossier (créé tout de suite s'il n'existe pas, sous-dossiers compris)
  ou reprend un dossier existant, puis propose une icône. Le menu ⋮ de chaque dossier permet de revenir à
  l'icône d'origine, de cocher « Recréer s'il manque » ou de retirer le dossier de la liste (sans jamais le supprimer).
- **Dossiers masqués** : les dossiers spéciaux (Bureau, Documents, Modèles…) peuvent être renommés avec un point
  devant ; `~/.config/user-dirs.dirs` est mis à jour pour que les applis continuent de les trouver.
- **Tout réappliquer** : recrée les dossiers manquants, remet leurs icônes et masque les dossiers prévus.

Les icônes passent par l'attribut `metadata::custom-icon` de GVfs, celui que lit Fichiers.

### Menu principal

| Entrée | Rôle |
|---|---|
| Exporter des icônes à redessiner… | ZIP des icônes cochées (celles à revoir le sont d'office), renommées avec l'identifiant du lanceur, plus un `inventaire.tsv` |
| Importer des icônes redessinées… | Reprend un ZIP de `nom.svg` / `nom-symbolic.svg` : installe les icônes et corrige `Icon=` des lanceurs concernés |
| Lanceurs orphelins… | Lanceurs dont la commande n'existe plus : masquer, ou supprimer pour les lanceurs faits main |
| Annuler la dernière modification | Revient en arrière, jusqu'aux 20 derniers changements |
| Exporter la sauvegarde… / Importer une sauvegarde… | Archive complète pour une réinstallation |

Le menu ⋮ d'un lanceur propose aussi **Exporter l'icône…** pour une seule appli.

Un point sur le bouton de menu rappelle que des modifications n'ont pas encore été exportées.

## Circuit de refonte d'icônes

1. **Exporter des icônes à redessiner…** : on récupère `icones-a-redessiner-AAAA-MM-JJ.zip`.
2. On redessine les icônes en gardant les noms de fichiers (`com.ogu.Grabber.svg`, `com.ogu.Grabber-symbolic.svg`…).
3. **Importer des icônes redessinées…** avec le ZIP retourné : tout est installé et les lanceurs sont corrigés.
   Une fausse manipulation s'annule depuis le message qui s'affiche ou depuis le menu.

### Kit d'icônes des dossiers Dropbox

Le sous-dossier [Backup icones](Backup%20icones/) conserve deux éléments complémentaires : la sauvegarde complète Iconostase à restaurer dans l'application et le kit autonome `icones-dossiers-kit_dropbox.zip`. Le kit contient les SVG de dossiers et le script `icones-dossiers-kit_dropbox.sh` (également livré seul à côté de l'archive de sauvegarde).

Pour l'utiliser après avoir restauré la sauvegarde Iconostase :

1. Décompresser `icones-dossiers-kit_dropbox.zip` dans le même dossier que le script, afin d'obtenir le sous-dossier `icones/`.
2. Fermer Iconostase.
3. Depuis ce dossier, lancer `bash ./icones-dossiers-kit_dropbox.sh`.

Le script copie les SVG dans `~/.local/share/iconostase/dossiers/`, pose les icônes sur les dossiers Dropbox prévus (séances, séquences, cartes, matières, classes et dossiers administratifs), puis attribue automatiquement une icône aux sous-dossiers reconnus sous `Dropbox/LYCEE` et `Dropbox/Dropboxable`. Il actualise aussi `dossiers.json` pour qu'Iconostase reprenne ces icônes dans ses prochaines sauvegardes.

Le script cible une arborescence précise sous `~/Dropbox` : les dossiers absents sont signalés et ignorés, à l'exception des répertoires annuels `Dropboxable` qu'il crée. Il préserve les icônes personnalisées qui ne proviennent pas de ce kit. Il peut être relancé. Fichiers peut nécessiter un redémarrage de Nautilus pour rafraîchir l'affichage.

## Sauvegarde

L'archive `iconostase-AAAA-MM-JJ.tar.gz` contient :

```
manifeste.json   version, date, nombres, dossiers masqués
icones/          icônes des applis (nom.svg, nom-symbolic.svg, PNG)
lanceurs/        les .desktop de ~/.local/share/applications
dossiers/        icônes des dossiers
dossiers.json    dossiers, icônes, « recréer s'il manque », dossiers masqués
```

À l'import, un résumé s'affiche avant de restaurer. Les dossiers Dropbox gardent « Recréer s'il manque » désactivé
pour ne pas devancer le client Dropbox ; ils sont signalés « laissés tels quels » tant qu'ils n'existent pas.

## Où sont les données

| Emplacement | Contenu |
|---|---|
| `~/.local/share/icons/hicolor/` | icônes installées (thème utilisateur) |
| `~/.local/share/applications/` | lanceurs modifiés ou faits main |
| `~/.local/share/iconostase/icones/` | collection des icônes sources |
| `~/.local/share/iconostase/dossiers/`, `dossiers.json` | icônes et plan des dossiers |
| `~/.local/share/iconostase/historique/` | instantanés pour « Annuler » |
| `~/.local/share/iconostase/config.json` | réglages de la fenêtre |

## Développement

```
main.py                    point d'entrée (gettext, nom du processus)
iconostase/
  application.py           fenêtre, menus, export/import, annulation
  base_application.py      Adw.Application, chemins, thème d'icônes
  settings_page.py         page d'édition d'un lanceur
  desktop_entry.py         lecture/écriture des .desktop
  icon_store.py            pose des icônes couleur et symbolique
  icon_batch.py            export/import d'icônes en lot
  history.py               instantanés et annulation
  folder_icons.py          icônes, création et masquage des dossiers
  folders_page.py          onglet Dossiers
  backup.py                sauvegarde complète
  orphans_dialog.py, icons_export_dialog.py
  core/                    échappement Exec=, évènements, config, surveillance de fichiers
  widgets/                 lignes, liste, navigateur d'icônes, menus
fr.po                      traduction française (compilée en locale/fr/LC_MESSAGES/iconostase.mo)
build_pkg.sh               construit le paquet pacman sans makepkg
convertir_pyz.py           convertit les anciens exports icones-ogu et dossiers-ogu en sauvegarde
```

Après une modification de `fr.po` :

```sh
msgfmt -o locale/fr/LC_MESSAGES/iconostase.mo fr.po
```

Code écrit selon les règles GNOME (EGO / gjs.guide) : une seule version cible, pas de vérifications défensives,
pas d'appels shell évitables (seul `gtk-update-icon-cache` reste, faute d'API).

## Licence

GPL-3.0-or-later (mentions de copyright d'origine : © 2022 Free Software Foundation).
