<p align="center">
  <img src="data/icons/io.gitlab.shogu.Carrousel.svg" width="128" alt="Icône de Carrousel">
</p>

<h1 align="center">Carrousel</h1>

<p align="center">Google Photos dans une vraie fenêtre GNOME (GTK4 / libadwaita)</p>

---

Carrousel enveloppe [photos.google.com](https://photos.google.com) dans une application GTK4/libadwaita : barre latérale native, recherche dans la barre d'en-tête, téléchargements vers `~/Images`, session conservée, raccourcis clavier. L'idée vient de [Verso](https://github.com/jakobhviid/verso), le client GNOME d'Immich, adaptée à Google Photos.

> Projet personnel, non affilié à Google. Usage strictement personnel.

## Pourquoi une enveloppe web et pas un client natif ?

Depuis le 31 mars 2025, l'API Google Photos (Library API) ne permet plus à une application tierce de lire toute la photothèque : seuls les médias créés par l'application elle-même restent accessibles, et la Picker API ne sert qu'à sélectionner quelques photos. Un client natif façon Verso (timeline, carte, recherche, personnes) n'est donc plus possible.

Carrousel utilise l'interface web officielle dans une vue WebKitGTK et l'habille d'une interface libadwaita. On garde ainsi toutes les fonctions de Google Photos : timeline, recherche intelligente, albums, partages, souvenirs, dossier verrouillé.

## Fonctionnalités

- **Barre latérale native** : Photos, Explorer, Albums, Partages, Archives, Dossier verrouillé, Corbeille. L'entrée active suit la page affichée, y compris dans un album ou sur une photo.
- **Menu latéral de Google masqué** pour éviter le doublon (option désactivable).
- **Recherche** dans la barre d'en-tête, qui lance la recherche intelligente de Google Photos (sujets, lieux, dates, texte dans les images).
- **Session persistante** : on reste connecté d'un lancement à l'autre. « Se déconnecter… » efface cookies et données du site, après confirmation.
- **Téléchargements** vers `~/Images`, sans jamais écraser un fichier existant (`photo (2).jpg`…), avec un message et un bouton « Ouvrir » à la fin.
- **Envoi de photos** par glisser-déposer sur la fenêtre, ou par le bouton « Importer » de Google Photos, qui ouvre le sélecteur de fichiers GNOME.
- **Liens externes** ouverts dans le navigateur par défaut ; les pages Google (connexion, compte) restent dans Carrousel.
- **Interface adaptative** : la barre latérale se replie sous 640 px de large.
- **Zoom de page** mémorisé, taille et état de la fenêtre mémorisés.
- **Gestes de navigation** au pavé tactile et boutons précédent/suivant de la souris.
- Le processus s'appelle `carrousel` dans le moniteur système.

## Raccourcis clavier

| Action | Raccourci |
|---|---|
| Précédent / Suivant | <kbd>Alt</kbd>+<kbd>←</kbd> / <kbd>Alt</kbd>+<kbd>→</kbd> (ou boutons de la souris) |
| Recharger | <kbd>Ctrl</kbd>+<kbd>R</kbd>, <kbd>F5</kbd> |
| Accueil (Photos) | <kbd>Alt</kbd>+<kbd>Début</kbd> |
| Rechercher | <kbd>Ctrl</kbd>+<kbd>F</kbd>, <kbd>Ctrl</kbd>+<kbd>L</kbd> |
| Afficher / masquer la barre latérale | <kbd>F9</kbd> |
| Zoom avant / arrière / normal | <kbd>Ctrl</kbd>+<kbd>+</kbd> / <kbd>Ctrl</kbd>+<kbd>-</kbd> / <kbd>Ctrl</kbd>+<kbd>0</kbd> |
| Fermer la fenêtre | <kbd>Ctrl</kbd>+<kbd>W</kbd> |
| Quitter | <kbd>Ctrl</kbd>+<kbd>Q</kbd> |

## Installation (Arch Linux / CachyOS)

### Paquet précompilé

Le paquet compilé `carrousel-1.0.2-1-any.pkg.tar.zst` sera déposé manuellement dans ce dossier. Depuis la racine du dépôt :

```fish
sudo pacman -U "Ressources/Applis vibe codées en Libadwaita/01-Multimedia/Carrousel/carrousel-1.0.2-1-any.pkg.tar.zst"
```

### Depuis les sources

```sh
git clone https://gitlab.com/shogu/carrousel.git
cd carrousel
makepkg -si
```

### Dépendances

| Paquet | Rôle |
|---|---|
| `python` | langage de l'application |
| `python-gobject` | liaisons GObject (PyGObject) |
| `gtk4` | boîte à outils graphique |
| `libadwaita` | composants GNOME (≥ 1.5) |
| `webkitgtk-6.0` | moteur web |

Les hooks pacman de `glib2`, `gtk-update-icon-cache` et `desktop-file-utils` compilent le schéma GSettings et mettent à jour les caches d'icônes et de menus à l'installation.

## Utilisation

1. Lancer **Carrousel** depuis la vue des activités.
2. Se connecter à son compte Google dans la fenêtre (une seule fois).
3. Naviguer avec la barre latérale ou chercher dans le champ du haut.

### Dossier verrouillé

Sur le web, le dossier verrouillé n'affiche que les éléments **sauvegardés**. Il faut activer « Sauvegarder le dossier verrouillé » dans l'appli Google Photos du téléphone. Google redemande la connexion (avec la validation en deux étapes) à chaque ouverture.

### Menu ☰ de Carrousel

- **Ouvrir dans le navigateur** : la page actuelle dans le navigateur par défaut.
- **Ouvrir le dossier Images** : le dossier des téléchargements.
- **Masquer le menu de Google** : active ou désactive le masquage du menu latéral de Google (la page se recharge).
- **Zoom avant / arrière / Taille normale**.
- **Se déconnecter…** : efface toutes les données de Google Photos stockées par Carrousel.
- **À propos de Carrousel**.

## Configuration

Réglages GSettings (schéma `io.gitlab.shogu.Carrousel`) :

| Clé | Type | Défaut | Description |
|---|---|---|---|
| `hide-google-menu` | booléen | `true` | masquer le menu latéral de Google Photos |
| `zoom-level` | réel | `1.0` | zoom de la page (0,5 à 2,0) |
| `window-width` | entier | `1200` | largeur de la fenêtre |
| `window-height` | entier | `800` | hauteur de la fenêtre |
| `window-maximized` | booléen | `false` | fenêtre maximisée |

```sh
gsettings set io.gitlab.shogu.Carrousel hide-google-menu false
```

### Fichiers de données

| Emplacement | Contenu |
|---|---|
| `~/.local/share/carrousel/` | cookies (`cookies.sqlite`) et données du site |
| `~/.cache/carrousel/` | cache web |

Supprimer ces deux dossiers revient à une déconnexion complète.

## Dépannage

**Le menu de Google n'est pas masqué**

Google change régulièrement le code de sa page. Lancer Carrousel avec l'inspecteur web :

```sh
CARROUSEL_INSPECTOR=1 carrousel
```

Clic droit sur le menu de Google, puis « Inspecter l'élément ». Le script à ajuster est `src/carrousel/hide_menu.js`.

**Google refuse la connexion (« navigateur non sécurisé »)**

WebKitGTK est normalement accepté. Si ce n'est plus le cas, définir un identifiant de navigateur (user agent) dans `PhotosView` (`src/carrousel/browser.py`).

**Un téléchargement n'apparaît pas**

Vérifier le dossier `~/Images` et l'existence du répertoire XDG des images (`xdg-user-dir PICTURES`).

## Structure du dépôt

```
carrousel/
├── PKGBUILD                      empaquetage Arch
├── carrousel.sh                  lanceur installé dans /usr/bin/carrousel
├── data/
│   ├── io.gitlab.shogu.Carrousel.desktop
│   ├── io.gitlab.shogu.Carrousel.gschema.xml
│   └── icons/                    icône couleur + symbolique
└── src/
    ├── main.py                   point d'entrée (nom du processus, lancement)
    └── carrousel/
        ├── __init__.py           identifiant, nom, version
        ├── application.py        Adw.Application, raccourcis, À propos
        ├── window.py             fenêtre, barre latérale, actions, menu
        ├── browser.py            vue WebKit, règles de navigation, téléchargements
        ├── sections.py           sections de la barre latérale et URL
        └── hide_menu.js          script de masquage du menu de Google
```

Le code est installé dans `/usr/lib/carrousel/` (jamais dans `site-packages`) : une mise à jour de Python ne casse pas l'application.

### Lancer depuis les sources

```sh
glib-compile-schemas data/ --targetdir=/tmp/carrousel-schemas
GSETTINGS_SCHEMA_DIR=/tmp/carrousel-schemas python3 src/main.py
```

## Icône

Le magasin rond d'un projecteur de diapositives, dont une diapo sortie montre un paysage. La symbolique reprend le disque avec les fenêtres des diapos découpées et la diapo sortie.

## Historique

- **1.0.2** : masquage du menu latéral de Google Photos (option), inspecteur web via `CARROUSEL_INSPECTOR=1`.
- **1.0.1** : entrée « Dossier verrouillé » dans la barre latérale.
- **1.0.0** : première version.

## Licence

MIT. Google Photos est une marque de Google LLC ; Carrousel n'est ni affilié à Google ni approuvé par Google.
