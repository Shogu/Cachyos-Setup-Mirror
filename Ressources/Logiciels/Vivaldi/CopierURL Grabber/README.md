# CopierURL — extension Vivaldi pour Grabber

Extension Chromium Manifest V3, destinée à Vivaldi. Elle remplace Tab Copy / Auto Tab Copy dans ce setup et ajoute un chemin direct vers Grabber.

## Fonctions

- Clic sur l’icône ou raccourci `Alt+Maj+G` : copie l’URL de l’onglet courant.
- `Alt+Maj+H` : copie les URL de tous les onglets de la fenêtre.
- Menus contextuels pour copier l’URL de l’onglet, les URL des onglets sélectionnés, toutes les URL de la fenêtre et les URL HTTP(S) trouvées dans un texte sélectionné.
- Menus **Ouvrir … avec Grabber** pour transmettre l’URL d’un lien, d’un onglet, d’onglets sélectionnés, d’une fenêtre ou d’un média.
- Badge temporaire indiquant le nombre d’URL copiées ou remises au protocole.

Les URL sont filtrées sur HTTP(S), dédupliquées et copiées une par ligne. L’extension ne lit pas le presse-papiers et ne contacte aucun serveur.

## Installation

1. Décompresser l’archive de l’extension, puis **déplacer le dossier extrait vers `~/.config/vivaldi_css/` avant de l’installer**. Créer `~/.config/vivaldi_css/` si nécessaire. Conserver le dossier de l’extension à cet emplacement après l’installation : Vivaldi chargera les fichiers depuis ce chemin.
2. Installer l’association de protocole de Grabber depuis l’emplacement définitif de l’AppImage :

   ```fish
   ./Grabber.AppImage --install-desktop
   ```

   Adapter le nom du fichier si nécessaire. Relancer uniquement si l’AppImage est déplacée ou renommée.
2. Ouvrir `vivaldi://extensions`.
3. Activer le **mode développeur**.
4. Choisir **Charger l’extension non empaquetée** et sélectionner le dossier de l’extension déplacé dans `~/.config/vivaldi_css/` (par exemple `~/.config/vivaldi_css/CopierURL Grabber/`).

Pour copier des URL, aucun autre prérequis n’est nécessaire. Pour **Ouvrir avec Grabber**, Vivaldi peut demander une confirmation avant d’ouvrir le protocole externe. Une politique Chromium peut contrôler cette confirmation, mais elle doit être adaptée à l’ID réel de l’extension et n’est pas fournie dans ce dossier.

## Utilisation

| Action | Résultat |
|---|---|
| Clic sur l’icône | Copie l’URL de l’onglet actif |
| `Alt+Maj+G` | Copie l’URL de l’onglet actif |
| `Alt+Maj+H` | Copie les URL de tous les onglets de la fenêtre |
| Clic droit sur la page ou l’onglet | Copier l’URL de l’onglet ou toutes les URL de la fenêtre ; ouvrir l’onglet ou la fenêtre avec Grabber |
| Clic droit sur des onglets sélectionnés | Copier ou transmettre les URL sélectionnées |
| Clic droit sur un lien | Ouvrir ce lien avec Grabber |
| Clic droit sur une image, vidéo ou audio | Transmettre l’URL du fichier média à Grabber |
| Clic droit sur un texte sélectionné | Copier les URL HTTP(S) trouvées dans la sélection |

Les entrées contextuelles sont filtrées selon l’élément cliqué. Le badge vert indique le nombre d’URL traitées ; le badge rouge `0` signale qu’aucune URL exploitable n’a été trouvée ou que l’opération a échoué.

### Limites du protocole externe

Les commandes **Ouvrir … avec Grabber** transmettent les URL via `grabber://add`. Chromium peut exiger une confirmation d’ouverture de l’application externe. Les URL sont découpées en lots lorsque la taille de l’URI l’exige. L’extension peut confirmer la remise au navigateur, mais ne peut pas vérifier que Grabber a effectivement commencé un téléchargement.

La liste « tous les onglets de la fenêtre » couvre les onglets de la fenêtre entière, pas uniquement un workspace Vivaldi : l’API d’extension ne fournit pas de filtre par workspace.

## Permissions

- `tabs` : lire les URL des onglets.
- `contextMenus` : proposer les commandes du menu contextuel.
- `offscreen` et `clipboardWrite` : écrire dans le presse-papiers depuis un document offscreen.

L’extension n’a pas besoin d’accéder au contenu des pages ni d’effectuer de requêtes réseau.

## Icônes

Les PNG de `icons/` sont les icônes générales de l’extension. Ceux de `icons/symbolic-light/` sont la variante claire utilisée par le bouton de barre d’outils sombre de Vivaldi.

## Maintenance

Le dossier contient les sources nécessaires au chargement manuel de l’extension. Les scripts de génération d’icônes et les tests mentionnés dans le README de développement d’origine n’étaient pas présents dans l’archive fournie ; ils ne sont donc pas référencés comme des commandes exécutables ici.
