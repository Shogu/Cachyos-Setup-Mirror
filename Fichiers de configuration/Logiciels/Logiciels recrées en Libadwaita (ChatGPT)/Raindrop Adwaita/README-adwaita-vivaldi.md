# Raindrop.io — extension Chrome/Vivaldi minimale avec icônes Adwaita

Cette variante est volontairement réduite à une seule action : cliquer sur
l’icône de l’extension pour enregistrer la page courante dans Raindrop.io.

Elle vise Chromium et Vivaldi uniquement. Le clic n’ouvre plus de popup, de
web panel ou de panneau latéral.

## Résultat visible

L’icône de la barre d’outils possède deux états :

| État | Ressource Adwaita | Fichier utilisé par Chromium |
| --- | --- | --- |
| Page non enregistrée | actions/bookmark-new-symbolic.svg | src/assets/target/extension/action_chrome.svg puis les PNG action_chrome_16/24/32.png |
| Page enregistrée | emblems/emblem-ok-symbolic.svg | src/assets/target/extension/action_chrome_saved.svg puis les PNG action_chrome_saved_16/24/32.png |

Ce sont deux icônes Adwaita monochromes séparées. Il n’y a plus de composition
« marque-page + badge », plus de badge Chrome et plus de logique de badge.
La couleur est fixée à #f6f5f4 pour rester lisible sur une barre d’outils sombre
de Vivaldi.

Les sources natives utilisées sont :

~~~text
/usr/share/icons/Adwaita/symbolic/actions/bookmark-new-symbolic.svg
/usr/share/icons/Adwaita/symbolic/emblems/emblem-ok-symbolic.svg
~~~

## Fonctionnement du clic

Le service worker src/target/extension/background/action.js reçoit directement
browser.action.onClicked. Il effectue les opérations suivantes :

1. Il récupère l’onglet actif.
2. Il ignore les pages qui ne commencent pas par http:// ou https://.
3. Il charge le cache des liens Raindrop avec
   GET https://api.raindrop.io/v1/raindrops/links.
4. Si l’URL est déjà dans le cache, il conserve l’état enregistré et ne crée
   pas de doublon.
5. Sinon, il vérifie les doublons côté serveur avec
   GET /v1/import/url/exists?url=....
6. Si la page n’existe pas encore, il la crée avec
   POST /v1/raindrop, dans la collection « Unsorted » (collectionId: -1),
   en envoyant aussi le titre de l’onglet.
7. Dès que la réponse de l’API confirme la création, links.add(url) met à
   jour le cache local et browser.action.setIcon() remplace immédiatement
   l’icône normale par l’icône Adwaita de coche.

L’authentification est celle déjà ouverte dans Raindrop.io : les requêtes
utilisent credentials: 'include'. Aucun écran de connexion ou panneau web
n’est ajouté à l’extension.

## Fichiers qui portent le comportement

~~~text
src/target/extension/background/api.js
    Requêtes minimales vers l’API Raindrop : liste, détection de doublon,
    création d’un bookmark.

src/target/extension/background/links.js
    Cache URL → identifiant Raindrop et normalisation des URL.

src/target/extension/background/action.js
    Clic sur l’icône, synchronisation de l’état et changement d’icône par onglet.
    Utilise directement l’API Chrome Manifest V3 : aucun polyfill Firefox/Safari.

src/target/extension/background/index.js
    Démarrage du seul contrôleur de l’action.

src/target/extension/manifest/index.js
    Manifeste Manifest V3 Chrome/Vivaldi et émission des icônes PNG.

build/extension.js
    Entrées limitées à manifest et background, sans application HTML.

build/common.js
    Les plugins HTML et CSS de l’application ne sont pas activés pour le
    build de l’extension.
~~~

## Ce qui a été supprimé du chemin Chrome/Vivaldi

Le paquet compilé ne contient plus :

- les variantes Firefox, Safari, Opera et Edge ;
- les anciennes sources d’icône génériques et les PNG Safari ;
- le popup, le web panel, le side panel et l’écran de bienvenue ;
- les menus de clic droit (contextMenus) ;
- l’omnibox et les raccourcis clavier (commands) ;
- le surlignage, la sélection de texte et l’injection de script dans les pages ;
- les réglages de permissions, de mode d’extension et de hotkeys ;
- la logique de tabs/clipper de l’ancien panneau ;
- les offres payantes, les écrans Pro, l’IA et leurs textes d’interface ;
- le suivi de badge et le message interne utilisé par l’ancien popup pour
  rafraîchir l’icône.

Les anciens modules de fond devenus inutiles ont été retirés de
src/target/extension/background/ : commands.js, contextMenus.js, omnibox.js,
runtime.js, fix-safari-profile-cookies.js et le dossier highlights/.

Les autres sources du dépôt Raindrop.io concernent encore l’application web
principale et ne sont pas importées par le build Chrome minimal. Elles ne sont
donc pas copiées dans le paquet chargé par Vivaldi.

## Pourquoi la coche fonctionne maintenant

L’ancienne version attendait que le popup React recharge les bookmarks et
envoyait ensuite un message au service worker. Cette chaîne ne pouvait pas
fonctionner de façon fiable lorsque le popup était supprimé ou lorsque la
permission optionnelle tabs n’avait pas été activée.

La nouvelle version ne dépend plus d’un popup :

~~~text
clic sur l’action
    → POST /v1/raindrop réussi
    → ajout immédiat de l’URL au cache local
    → browser.action.setIcon({ path: icône cochée })
~~~

La permission tabs est maintenant déclarée directement dans le manifeste.
Elle permet de connaître l’URL et l’identifiant de chaque onglet pour appliquer
l’icône correcte après une navigation ou un changement d’onglet.

## Manifeste produit

src/target/extension/manifest/index.js produit un manifeste Manifest V3 avec :

~~~json
{
  "background": { "service_worker": "background.js" },
  "action": { "default_icon": "assets/action_chrome_*.png" },
  "permissions": ["tabs"],
  "host_permissions": ["https://api.raindrop.io/*"]
}
~~~

Il n’y a pas de default_popup, contextMenus, commands, omnibox, side_panel,
optional_permissions ou permission d’accès aux pages web.

## Refaire le changement d’icône après une mise à jour de Raindrop

Après avoir récupéré une nouvelle version du dépôt officiel, réappliquer les
fichiers de comportement listés ci-dessus, puis refaire les icônes PNG.

### 1. Recréer les deux SVG depuis Adwaita

Copier les deux fichiers natifs :

~~~bash
cp /usr/share/icons/Adwaita/symbolic/actions/bookmark-new-symbolic.svg \
   src/assets/target/extension/action_chrome.svg

cp /usr/share/icons/Adwaita/symbolic/emblems/emblem-ok-symbolic.svg \
   src/assets/target/extension/action_chrome_saved.svg
~~~

Les SVG Adwaita installés par défaut utilisent généralement #2e3436, une
couleur sombre adaptée aux interfaces claires. Pour la barre sombre de Vivaldi,
remplacer cette couleur par #f6f5f4 dans les deux fichiers :

~~~bash
sed -i 's/#2e3436/#f6f5f4/g' \
  src/assets/target/extension/action_chrome.svg \
  src/assets/target/extension/action_chrome_saved.svg
~~~

Cette variante utilise volontairement bookmark-new-symbolic pour l’état normal
et emblem-ok-symbolic pour l’état enregistré. Il ne faut pas recréer une icône
composite ni ajouter un badge séparé.

### 2. Régénérer les tailles PNG attendues par Chrome

Inkscape doit être installé :

~~~bash
for size in 16 24 32; do
  inkscape \
    --export-filename="src/assets/target/extension/action_chrome_${size}.png" \
    --export-width="$size" \
    --export-height="$size" \
    src/assets/target/extension/action_chrome.svg

  inkscape \
    --export-filename="src/assets/target/extension/action_chrome_saved_${size}.png" \
    --export-width="$size" \
    --export-height="$size" \
    src/assets/target/extension/action_chrome_saved.svg
done
~~~

Les six fichiers doivent ensuite exister :

~~~text
src/assets/target/extension/action_chrome_16.png
src/assets/target/extension/action_chrome_24.png
src/assets/target/extension/action_chrome_32.png
src/assets/target/extension/action_chrome_saved_16.png
src/assets/target/extension/action_chrome_saved_24.png
src/assets/target/extension/action_chrome_saved_32.png
~~~

### 3. Vérifier les chemins dans le code

Dans src/target/extension/background/action.js, les chemins d’état doivent
rester exactement ceux-ci :

~~~js
const iconPaths = {
    normal: {
        16: 'assets/action_chrome_16.png',
        24: 'assets/action_chrome_24.png',
        32: 'assets/action_chrome_32.png'
    },
    saved: {
        16: 'assets/action_chrome_saved_16.png',
        24: 'assets/action_chrome_saved_24.png',
        32: 'assets/action_chrome_saved_32.png'
    }
}
~~~

Dans src/target/extension/manifest/index.js, les PNG normaux doivent être
déclarés comme icône par défaut et les trois PNG cochés doivent être émis dans
le paquet afin que setIcon() puisse les utiliser.

### 4. Recompiler et installer dans Vivaldi

~~~bash
npm ci
npm run build:extension
~~~

Le dossier à charger dans vivaldi://extensions est :

~~~text
dist/chrome/prod
~~~

Activer le mode développeur, cliquer sur « Charger l’extension non empaquetée »
et sélectionner ce dossier. Retirer l’ancienne copie Raindrop si elle est
encore installée pour éviter deux icônes concurrentes.

## Vérifications rapides

Vérifier le manifeste produit :

~~~bash
node -e "const m=require('./dist/chrome/prod/manifest.json'); console.log(m)"
~~~

Vérifier que le build ne contient pas les anciennes fonctions :

~~~bash
rg -n -i \
  'firefox|safari|contextMenus|omnibox|sidePanel|commands|highlights|pro|ai|popup' \
  dist/chrome/prod/manifest.json dist/chrome/prod/background.js
~~~

Cette dernière commande ne doit rien trouver dans le manifeste ou le service
worker minimal. Les fichiers compilés ne contiennent donc ni interface Pro/IA,
ni menu contextuel, ni logique de popup.

## Test fonctionnel

1. Ouvrir une page web dans Vivaldi avec une session Raindrop.io connectée.
2. Charger l’extension non empaquetée.
3. Cliquer une fois sur l’icône normale.
4. Attendre la réponse de l’API : l’icône devient immédiatement la coche
   Adwaita.
5. Recharger la page ou changer d’onglet : l’icône cochée doit rester affichée
   si le lien existe dans Raindrop.

Si la coche ne s’affiche pas, ouvrir le lien « Service worker » de l’extension
dans vivaldi://extensions et vérifier l’erreur affichée. Les causes utiles à
distinguer sont alors : session Raindrop expirée, requête API bloquée ou page
non HTTP(S). Le code ne dépend plus d’un popup qui pourrait masquer l’erreur.
