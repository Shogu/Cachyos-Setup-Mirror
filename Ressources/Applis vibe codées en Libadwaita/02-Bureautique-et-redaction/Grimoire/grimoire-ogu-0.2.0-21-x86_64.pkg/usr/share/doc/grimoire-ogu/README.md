# Grimoire 0.2.0

Éditeur Markdown local, Python / GTK 4 / libadwaita / GtkSourceView 5 / WebKitGTK 6.

## Installer sur Arch ou CachyOS

Téléchargez le paquet dans Téléchargements puis exécutez :

```fish
cd ~/Téléchargements
sudo pacman -U ./grimoire-ogu-0.2.0-1-any.pkg.tar.zst
grimoire
```

Pacman installe les dépendances des dépôts si elles sont absentes. Pas de compilation ni de makepkg nécessaire. Le suffixe `any` est normal : le programme est en Python, sans binaire propre à une architecture. Le paquet s'appelle `grimoire-ogu` pour limiter les collisions de nom avec d'autres projets ; l'application et la commande s'appellent Grimoire et `grimoire`.

## Fonctions

### Conformité GNOME / libadwaita — version 0.2.0

L'interface suit les recommandations GNOME actuelles.

- Fenêtre adaptative : `Adw.OverlaySplitView` et un point de rupture à 700 sp replient la barre latérale sur les écrans étroits ; l'ossature repose sur `Adw.ToolbarView`.
- Plus aucune couleur codée en dur : la sélection de la barre latérale, les boutons suggérés et l'aperçu HTML suivent la couleur d'accentuation du système, en clair comme en sombre.
- API modernes : `Adw.AlertDialog`, `Adw.AboutDialog`, `Adw.ShortcutsDialog`, `Gtk.FileDialog`, `Gtk.SearchBar`, `Adw.ToggleGroup` pour Code/Scindé/Rendu et `Adw.WindowTitle` pour le nom et le chemin du document.
- Préférences : `Adw.PreferencesDialog` (Ctrl+,) avec le thème (Système, Clair, Sombre), numéros de ligne, surlignage de la ligne active, grille de fond et police de l’éditeur (police GNOME à chasse fixe, ou police et taille au choix). Les réglages sont stockés dans GSettings (`io.github.shogu.Grimoire`) ; l'ancien `preferences.json` est importé une fois.
- Raccourcis clavier : fenêtre de raccourcis native (Ctrl+?) ; le zoom passe dans le menu principal, la barre d'état ne garde que le statut du document.
- Intégration bureau : metainfo AppStream, icône symbolique, service D-Bus et `DBusActivatable=true`.
- Icône : marque-page retiré et livre recadré pour occuper environ 92 % du canevas 512 × 512, transparence réelle.
- Recherche : toutes les occurrences sont surlignées à la couleur d'accentuation, même quand le focus est dans la barre de recherche.
- Un bouton icône monochrome insère du code en ligne, à gauche du bouton de bloc `fish`.
- La barre latérale est masquée au démarrage ; F9 ou le bouton de la barre supérieure l'affiche.

Il reste à renseigner `<url type="homepage"/>` et `<url type="bugtracker"/>` dans le metainfo lorsque l'adresse publique du projet sera connue.

### Sous-dossiers et taille du texte — version 0.1.7

**Documents** affiche les sous-dossiers en premier, puis les fichiers `.md` et `.markdown`. Cliquez sur un dossier pour y entrer, à autant de niveaux que nécessaire. La flèche vers le haut remonte au parent, jusqu'au dossier épinglé. Le nom et son infobulle indiquent le dossier affiché. Le filtre agit sur les noms du niveau affiché et se vide en changeant de dossier. Le dossier affiché est surveillé pour actualiser sa liste ; F5 permet aussi de la rafraîchir. Au lancement, la navigation repart du dossier épinglé. Parcourir les dossiers conserve le document et ses modifications ; ouvrir un autre document garde la confirmation habituelle d'enregistrement.

En bas de l'éditeur, **− / curseur / +** règle la taille entre **70 et 200 %**, dans les modes Code, Scindé et Rendu. Cliquez sur le pourcentage pour revenir à 100 %. La préférence est conservée au prochain lancement. Ce réglage change l'affichage seulement, jamais le Markdown enregistré. Le rendu est agrandi dans son ensemble, images comprises.

### Documents, sommaire et icône — version 0.1.5

La section « Dossier épinglé » se nomme désormais **Documents**, avec une icône de dossier symbolique native. **Sommaire** reçoit également une icône symbolique et un chevron de repli natif GTK. Chaque section se replie indépendamment et mémorise son état. Lorsqu'une section est fermée, l'autre récupère l'espace ; lorsque les deux sont fermées, leurs titres restent en haut. Le texte reste visible à côté des icônes pour identifier les deux fonctions.

À partir de la capture du dock fournie par Ogu, les marges transparentes de l'icône du livre ont été réduites : le livre occupe désormais environ 92 % de la hauteur du canevas, au lieu d'environ 71 %. Le PNG installé reste carré, 512 × 512 pixels, avec transparence réelle. La retouche intégrée a reçu pour consigne de conserver le livre et ses symboles en agrandissant son cadrage.

### Dossier épinglé repliable — ajouté en 0.1.4

Cliquez sur le chevron ou le titre **Dossier épinglé** dans la barre latérale pour masquer ou afficher le nom du dossier, le filtre et la liste des fichiers. Le sommaire reste visible et récupère la place libérée. Le contrôle est un `Gtk.Expander` natif, utilisable au clavier, sans dessin de chevron ni style personnalisé. L'état ouvert/fermé est conservé dans les préférences pour le prochain lancement. Le menu permet toujours d'épingler un dossier lorsque la section est fermée ; choisir un nouveau dossier la déplie automatiquement. Replier ne détache pas le dossier et ne modifie pas les documents. Le bouton existant de la barre supérieure continue de masquer toute la barre latérale.

### Retrait de GitLab et blocs neutres — version 0.1.6

À la demande d’Ogu, après échec de la fonction sur sa machine, le bouton GitLab, son moteur et ses tests spécifiques sont supprimés. `git` et `openssh` ne sont plus des dépendances de Grimoire. L'application n'effectue plus de commit ni de push. Les dépôts locaux et leur configuration restent intacts ; les opérations Git se font avec un outil externe. La fonction avait été ajoutée en 0.1.3 : cette décision de retrait remplace sa documentation précédente.

Le menu des blocs de code propose désormais **Sans langage**, en plus de `fish`, `python` et `systemd`. Ce choix affiche trois accents graves sur le bouton et insère un bloc entouré de trois accents graves, sans nom de langage. Le texte sélectionné est placé dans le bloc. Les délimiteurs sont allongés si le texte contient déjà des accents graves pour préserver un Markdown valide. `fish` reste sélectionné au lancement.

### Éditeur

- Ouverture directe et édition des `.md` et `.markdown` depuis Fichiers ou la commande.
- Code, Scindé, Rendu ; coloration de la source et des blocs de code dans le rendu.
- Dossier épinglé persistant, liste filtrable, actualisation des fichiers du dossier.
- Sommaire cliquable ; les titres dans les blocs de code ne sont pas indexés.
- Titres H1 à H6, gras, italique, listes, citations, liens et images locales.
- Bouton de code avec `fish` par défaut, menu `python`, `systemd` et **Sans langage**.
- Recherche/remplacement littérale, insensible à la casse par défaut ; le bouton **Aa** active la casse.
  Entrée et Maj+Entrée parcourent les occurrences ; le compteur indique l’occurrence courante et le total.
- Onglets de documents : les ouvertures depuis le gestionnaire de fichiers rejoignent la fenêtre existante.
- Défilement synchronisé entre la source et l’aperçu dans le mode Scindé.
- Assistant d’insertion de tableaux Markdown et Tab/Maj+Tab pour indenter ou désindenter les listes.
- Renommer le fichier avec F2 et modifier le titre H1 via le menu : deux opérations indépendantes.
- Enregistrer, Enregistrer sous et confirmation native libadwaita avant de quitter un document modifié. Aucune autosauvegarde.
- Icône choisie, widgets natifs, modes clair et sombre, sélection bleue dans le panneau latéral.
- Aucun export HTML/PDF, aucune exécution des commandes contenues dans les documents.

## Premier démarrage

1. Menu → Épingler un dossier : choisissez le dossier de vos Markdown permanents.
2. Cliquez sur un document dans la colonne gauche pour l'ouvrir.
3. Menu → Définir comme éditeur Markdown par défaut pour activer l'association. L'installation seule n'impose pas le changement de votre application par défaut.

Équivalent pour l'association depuis le terminal :

```fish
xdg-mime default io.github.shogu.Grimoire.desktop text/markdown
xdg-mime default io.github.shogu.Grimoire.desktop text/x-markdown
```

## Enregistrement et sécurité

L'enregistrement est exclusivement manuel : Ctrl+S ou bouton Enregistrer. Une modification n'écrit ni le document ni un brouillon automatiquement. L'ancienne préférence d'autosauvegarde est ignorée lors de la mise à jour.

Un changement de fichier ou une fermeture demande quoi faire si des modifications restent non enregistrées. Un fichier changé ou supprimé par un autre logiciel n'est pas écrasé : enregistrez une copie sous un nouveau nom, ou rechargez le fichier en abandonnant vos changements. L'application n'effectue pas de fusion automatique.

Les écritures ordinaires remplacent le fichier atomiquement et conservent ses permissions Unix, UTF-8/BOM et fins de ligne CRLF. Cela ne constitue pas un gestionnaire de versions ni une sauvegarde historique. Les ACL et attributs étendus ne sont pas recopiés lors du remplacement. Évitez les documents nécessitant ces métadonnées spécifiques.

Aucun brouillon automatique n’est créé ni récupéré par Grimoire. Les éventuels anciens fichiers `draft-*.json` peuvent être supprimés manuellement de `${XDG_STATE_HOME:-~/.local/state}/grimoire/` si vous n’en avez plus besoin. Pas d'envoi réseau des notes. JavaScript est désactivé ; le HTML est filtré ; les images distantes sont bloquées dans le rendu. Les liens Web/e-mail explicitement cliqués s'ouvrent dans l'application habituelle.

## Limites de cette première version

- Tests de logique et contrôle de l'archive effectués ; fonctionnement confirmé par Ogu sur sa machine. Exécution GTK/GNOME et installation avec Pacman non vérifiées dans l'environnement de construction, faute de dépendances graphiques et d'un hôte Arch.
- Icône 0.1.2 : livre bleu, dièse cerclé d'or, fermoir et marque-page, issus de la nouvelle référence fournie par Ogu. Détourage avec véritable transparence alpha, toile carrée de 512 × 512 pixels et marges adaptées. Aucun damier imprimé. Documents et sommaire sélectionnés : cartouche bleu arrondi, y compris quand le clavier est dans l'éditeur.
- Les images sont référencées, pas copiées : déplacer le document ou l'image peut casser le chemin relatif.
- Les listes de tâches sont insérées en syntaxe Markdown, sans case interactive dans le rendu.
- Ouverture/sauvegarde et génération du rendu sur le thread principal : pas optimisé pour les fichiers de plusieurs dizaines de Mo.

## Historique des demandes et décisions

Ce document sert de mémoire du projet pour une reprise ultérieure. Les décisions les plus récentes remplacent les demandes antérieures contradictoires.

### Intention initiale et nom

Créer un petit éditeur Markdown par défaut, aussi immédiat qu'un bloc-notes, associé à un gestionnaire des notes permanentes dans un dossier épinglé. Interface GNOME/libadwaita native, accent bleu, boutons natifs, sans export HTML ni PDF. La discussion a également évoqué d'autres applications (Bootprint, Packages, etc.) : elles ne font pas partie du périmètre de Grimoire.

Noms explorés : Balise, puis Samizdat ; trois pistes d'icônes demandées pour Samizdat, Fanzine et Grimoire. Choix final : **Grimoire**. Les premières recherches autour de Balise visaient une balise plutôt qu'un phare, intégrée dans une forme rectangulaire.

### Cahier des charges retenu

- Édition dès l'ouverture, association aux fichiers Markdown, ouverture depuis le gestionnaire de fichiers.
- Modes Code, Scindé et Rendu ; coloration Markdown ; recherche et remplacement.
- Barre d'insertion : titres, gras, italique, listes, liens, images, citations.
- Blocs de code : un bouton et un menu de langues, `fish` sélectionné par défaut, `python` et `systemd` disponibles ; cette solution répond à l'alternative initiale de trois boutons distincts.
- Sommaire latéral cliquable et dossier épinglé persistant pour les documents permanents.
- Modification du titre Markdown et possibilité de renommer le fichier.
- Livraison d'un paquet Arch natif directement installable avec `pacman -U`, sans compilation pour l'utilisateur.
- L'autosauvegarde faisait partie de la demande initiale, puis a été **explicitement retirée**. Ne pas la réintroduire sans nouvelle demande.

### Corrections de la version 0.1.1

- Suppression de l'autosauvegarde, de son menu et des nouveaux brouillons automatiques ; l'ancienne préférence est ignorée.
- Dialogue natif libadwaita avec Enregistrer / Ne pas enregistrer / Annuler avant d'abandonner un document modifié, notamment en changeant de document ou en fermant la fenêtre.
- Protection du renommage par le même dialogue ; aucune sauvegarde implicite des modifications à cette occasion.
- Une annulation restaure la sélection du document réellement ouvert ; cliquer sur le document déjà ouvert ne le recharge pas.
- Une décision de ne pas enregistrer abandonne réellement les modifications, sans les considérer à tort comme sauvegardées.
- Sélection bleue arrondie des lignes de documents et de sommaire, maintenue lorsque le focus retourne dans l'éditeur ; sommaire reconstruit avec sélection du titre proche du curseur.
- Les lignes sont des widgets Gtk.ListBox natifs. La couleur bleue et l'arrondi sont appliqués par CSS : il ne s'agit pas d'un composant libadwaita distinct nommé « cartouche ».

### Évolution de l'icône et version 0.1.2

La première icône Grimoire a été simplifiée : étoile remplacée par un dièse, couverture unie sans lignage, bleu approfondi, tranche plus sombre et fermeture travaillée. Après un problème de fond, une variante remplissant tout le rectangle avait été demandée. La dernière consigne revient à une icône plus petite avec transparence, basée sur la nouvelle image jointe : livre bleu avec dièse dans un cercle doré et fermoir à serrure. **Cette dernière référence remplace les précédentes.**

Le JPEG de référence contient un damier dessiné, sans canal alpha. Le détourage a été effectué avec l'outil de retouche intégré, en demandant de conserver le livre, de retirer tout le damier et de produire un PNG transparent centré avec des marges. L'asset intégré est `data/icon.png`, redimensionné à 512 × 512 pour le thème hicolor. La 0.1.2 ne modifie pas les fonctions de l'éditeur par rapport à la 0.1.1.

Le paquet 0.1.1 transmis avait une taille de zéro octet : problème de livraison constaté, pas un paquet installable. La nouvelle archive doit être reconstruite et contrôlée (taille non nulle, décompression Zstandard et contenu du tar) avant livraison. Ne jamais réutiliser le fichier vide.

## Informations pour poursuivre le développement

- `src/grimoire.py` : application GTK, fenêtres, actions, dialogues, panneaux, aperçu et styles.
- `src/core.py` : documents, lecture/écriture, titres, rendu Markdown et filtrage HTML.
- `data/` : lanceur, fichier desktop et icône ; identifiant d'application `io.github.shogu.Grimoire`.
- `tests/test_core.py` : tests du moteur ; `tests/test_manual_save.py` : tests des chemins de sauvegarde manuelle avec doubles pour les dialogues, sans session graphique.
- `build.py` : assembleur du paquet Python, métadonnées `.PKGINFO` et `.MTREE`, vérification des octets de chaque fichier embarqué.
- `PKGBUILD` : alternative de construction conventionnelle Arch ; `LICENSE` : licence MIT du code.
- Dépendances : Python, PyGObject, GTK4, libadwaita ≥ 1.2, GtkSourceView 5, WebKitGTK 6, python-markdown, Pygments et Bleach.
- Le README est aussi installé dans `/usr/share/doc/grimoire-ogu/README.md`.

Garder les versions de l'application, de `build.py`, du `PKGBUILD` et de ce document cohérentes. Préserver les protections contre les conflits de fichiers et les dialogues d'abandon des changements. Pour toute évolution, vérifier sur GNOME les trois issues du dialogue, les ouvertures externes, le renommage, le dossier épinglé, le sommaire et l'apparence de l'icône en clair et en sombre. Les tests automatisés ne remplacent pas ces vérifications graphiques.

Les onglets, la récursivité des dossiers, la synchronisation du défilement et les optimisations pour gros fichiers sont des pistes possibles, pas des fonctions promises ou déjà présentes. Ne pas ajouter d'export HTML/PDF : il a été explicitement exclu.

## Diagnostic de lancement

```fish
grimoire 2>&1 | tee ~/grimoire.log
```

## Sources et tests

Les sources sont dans `src/`, les tests dans `tests/`, et les ressources dans `data/`.

Après installation des dépendances du paquet :

```fish
python -m unittest discover -s tests -v
python src/grimoire.py
```

Le paquet livré a été assemblé avec `build.py` (programme Python sans compilation native). Pour une reconstruction conventionnelle sur Arch :

```fish
sudo pacman -S --needed base-devel
makepkg -s
```

## Désinstaller

```fish
sudo pacman -R grimoire-ogu
```

Les documents utilisateur ne sont pas supprimés par cette désinstallation. Les éventuels anciens brouillons historiques présents dans le dossier d’état ne sont pas gérés par l’application.

## Références techniques

- https://archlinux.org/packages/extra/x86_64/webkitgtk-6.0/
- https://archlinux.org/packages/extra/x86_64/gtksourceview5/
- https://archlinux.org/packages/extra/any/python-markdown/
- https://gnome.pages.gitlab.gnome.org/gtksourceview/gtksourceview5/class.Buffer.html

## Métadonnées de distribution

Le dépôt extrait ne contient ni URL publique de projet ni gestionnaire d'incidents
identifiable. Les champs `homepage` et `bugtracker` restent donc volontairement
absents du fichier AppStream plutôt que de publier une adresse inventée. Aucune
capture d'écran AppStream n'est fournie : seules les icônes d'application sont
présentes, et elles ne constituent pas une capture visuelle utilisable.


### Simplification 0.2.0-14

- Suppression de l’entrée **Modifier le titre principal…** et de toute sa logique dédiée.
- Suppression de **Récupérer un brouillon…**, du lecteur de brouillons historiques et de toute la logique `recovery_write`.
- L’enregistrement reste strictement manuel.


## Révision 0.2.0-18

- Police de l'éditeur : interrupteur « Utiliser la police du système » (police à chasse fixe de GNOME, lue dans `org.gnome.desktop.interface`) ou sélecteur de police et de taille. Le réglage « Taille du texte » des préférences est retiré ; le zoom (70 à 200 %, Ctrl+ / Ctrl− / Ctrl+0) reste et s'applique à l'éditeur et à l'aperçu.
- Aperçu : police d'interface GNOME (`font-name`) pour le texte, police à chasse fixe GNOME pour le code, au lieu de la résolution fontconfig (DejaVu sur certaines installations).
