# Perceptron

Perceptron est une interface de bureau native GTK4/libadwaita pour le serveur
API local d’OpenCode. Il lance `opencode serve` sur `127.0.0.1:49375`, puis
utilise les API natives et SSE; aucun navigateur ni lien d’appairage n’est
nécessaire. L’interface libadwaita propose recherche dans les titres et les
conversations, onglets natifs (clic milieu pour ouvrir un onglet), archivage,
épinglage local, date et agent en cours. La page d’accueil explique les actions
principales; les raccourcis sont listés dans le menu. Le zoom de texte (Ctrl+plus,
Ctrl+moins, Ctrl+0) est appliqué en GTK et respecte le facteur d’échelle GNOME.
Les sous-agents sont masqués par défaut;
les doublons d’identifiant sont fusionnés sans éliminer des sessions distinctes.
La conversation prend en charge les liens, tableaux, code, listes, titres,
citations, italique, texte barré et couleurs (rouge, orange, jaune, vert, bleu,
violet, rose en hexadécimal), avec boutons de mise en forme, copie par réponse
et **sur vos propres messages**, menus contextuels pour copier le texte,
ouvrir/copier un lien et ouvrir un chemin local ou le dossier d’un fichier dans
Fichiers, repères numérotés avec aperçu pour les réponses et bouton « aller en
bas » visible en remontant l’historique. Une **recherche Ctrl+F** surligne les
mots trouvés, cerne la réponse courante et affiche le compteur de résultats.
Les réponses annoncent leur modèle et fournisseur dans l’en-tête (ex.
« OpenCode — DeepSeek V4 Flash — Albert »), vos messages étant estampillés
« Moi ». La zone de saisie est **redimensionnable** (poignée visible au-dessus,
hauteur mémorisée) et affiche un **placeholder** « Écris ton message… » tant
qu’elle est vide. La **barre latérale** est redimensionnable à la souris
(largeur mémorisée). Les dossiers de départ du menu « Ajouter » sont
configurables dans les **Préférences** via un sélecteur de répertoire.
L’indicateur discret « Génération en cours » et le bouton d’interruption suivent
les sessions actives renvoyées par l’API OpenCode.
Les modèles sont classés par fournisseur, avec les noms fournis par OpenCode;
le choix conserve l’identifiant exact du modèle et du fournisseur. Le catalogue
est filtré selon les modèles déclarés dans la configuration OpenCode et l’état
`enabled` renvoyé par l’API. Les modèles
et agents réels sont renvoyés par OpenCode; des boutons natifs
Build/Plan pilotent l’agent effectif quand le serveur les expose. Le sélecteur
permet aussi de choisir les autres agents principaux. Leurs variantes de
raisonnement sont présentées avec des libellés lisibles sans modifier les
identifiants API. Les
messages peuvent être envoyés avec Entrée (Maj+Entrée insère une nouvelle ligne);
une option met une question secondaire en file d’attente. Le bouton d’envoi
attend la fin d’un changement de modèle ou d’agent, sans perdre le brouillon.
La composition accepte des pièces jointes via le sélecteur de fichiers, sans
glisser-déposer; les fichiers générés peuvent
être prévisualisés, ouverts dans Fichiers ou enregistrés sous une copie locale.
Modifier/régénérer le dernier message utilise l’API native de retour de
conversation, avec confirmation avant réécriture; l’envoi conserve le brouillon
et propose une nouvelle tentative en cas d’erreur. Les notifications GNOME
signalent les permissions, formulaires et fins d’exécution.
Les erreurs HTTP OpenCode affichent aussi leur type et leur champ fautif quand
le serveur les fournit, après neutralisation des détails d’authentification.

## Fonctionnalités principales

- **Interface native GTK4/libadwaita**, sans navigateur ni WebKit.
- **Sessions** : liste, recherche par titre et par contenu, épinglage local,
  archivage, renommage, création à partir d’un message (fork), onglets natifs
  (clic milieu = nouvel onglet).
- **Cartouches à thème fixe** : réponses OpenCode en cartouche clair, messages
  « Moi » en cartouche sombre, indépendant du thème système.
- **Marquage Markdown** : titres, listes, citations, code avec bouton copier et
  libellé de langue, tableaux, liens sûrs, et **7 couleurs** (rouge, orange,
  jaune, vert, bleu, violet, rose) en hexadécimal.
- **En-tête de réponse** annonçant le modèle et le fournisseur
  (ex. « OpenCode — DeepSeek V4 Flash — Albert »).
- **Réinitialiser la conversation** : sur chaque message « Moi » (sauf le
  dernier), un bouton « Réinitialiser ici » ramène la session à ce point via
  l’API de revert native d’OpenCode.
- **Zone de saisie redimensionnable** (poignée visible, hauteur mémorisée) avec
  placeholder « Écris ton message… ».
- **Barre latérale redimensionnable** (poignée visible, largeur mémorisée).
- **Recherche Ctrl+F** avec surlignage des mots trouvés, cerclage de la réponse
  courante et compteur de résultats.
- **Mémoire** : édition des instructions globales d’OpenCode (systemPrompt)
  avec sauvegarde automatique.
- **Bouton « Ajouter »** par catégorie avec dossiers de départ configurables
  dans les Préférences via un sélecteur de répertoire.
- **Copie fiable** via `wl-copy` sous Wayland (repli GTK/X11).
- Curseur stable dans la TUI OpenCode (`cursor.style = "line"`).
- **Terminal en appui** : tiroir en bas (`Ctrl+@` ou bouton de l’en-tête) avec un
  vrai shell `bash` via PTY pour lancer `ls`, `pacman -U`, etc. Codes ANSI
  neutralisés, interruption Ctrl+C, effacement.

## Installation

### Depuis le paquet Arch

Le paquet `perceptron-1.5.2-1-any.pkg.tar.zst` s’installe directement avec
Pacman sans compilation :

```sh
sudo pacman -U perceptron-1.5.2-1-any.pkg.tar.zst
```

Il installe l’exécutable `perceptron`, les fichiers GTK/libadwaita sous
`/usr/lib/perceptron/`, le fichier `.desktop` et les icônes.

### Depuis les sources

```sh
python3 src/main.py
```

## Dépendances


- Python 3, PyGObject, GTK 4 et libadwaita
- libsoup 3
- OpenCode installé et accessible dans le `PATH` ou dans `~/.opencode/bin`

WebKitGTK n’est plus utilisé ni requis. Le mot de passe du serveur local est généré
par Perceptron et conservé dans
`~/.local/share/perceptron/server-password` (mode 0600). Pour réutiliser un mot
de passe HTTP existant, définissez `OPENCODE_SERVER_PASSWORD` et éventuellement
`OPENCODE_SERVER_USERNAME` (par défaut `opencode`) dans l’environnement de
l’application.

## Lancer depuis les sources

```sh
python3 src/main.py
```

## Tester et construire

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
./build.sh
```

La recherche et l’affichage chargent maintenant toutes les pages de messages
disponibles pour chaque session. Les dimensions de fenêtre sont sauvegardées
sans écraser les préférences locales d’affichage, de zoom et d’épinglage.
Une session devenue introuvable sur le serveur est signalée comme telle
(distinctement d’un historique vide) ; le brouillon et les pièces jointes sont
conservés pour créer une session de remplacement et, sur confirmation, renvoyer
le message.

`build.sh` crée dans le dossier du projet le paquet Arch
`perceptron-1.5.2-1-any.pkg.tar.zst` et une archive `-sources.tar.gz`.
Le paquet est assemblé localement à partir des sources présentes, sans cloner
un dépôt et sans installer de dépendances de développement. Il nécessite
`bsdtar` et `zstd` (disponibles sur Arch Linux).

## Données locales

Les dimensions de la fenêtre, le journal et les cookies sont stockés sous
`~/.local/share/perceptron/`. Le service OpenCode reste actif lorsque seule
l’interface est fermée, sauf choix contraire dans la boîte de fermeture.

## Limites d’intégration OpenCode

L’épinglage est une préférence locale à Perceptron. Le serveur v2.2.5 expose
la liste et la sélection d’agents, mais pas leur renommage depuis le client.
La recherche de contenu parcourt les pages de sessions récentes renvoyées par
l’API et leurs messages, et peut prendre du temps sur un historique volumineux.
Les actions d’outils ne sont pas exécutées par Perceptron : leurs confirmations
et permissions doivent être configurées côté OpenCode; les notifications
d’autorisation ne remplacent pas cette protection.
Les sessions sont horodatées selon le format milliseconde renvoyé par OpenCode.
En cas d’erreur API de chargement, l’erreur est affichée dans la barre latérale
avec une action de nouvelle tentative plutôt que de présenter une liste vide.
Les cartes de conversation distinguent visuellement les messages utilisateur et
assistant; les commandes de mise en forme utilisent des icônes Adwaita présentes
dans le thème, avec boutons colorés textuels pour les couleurs.
