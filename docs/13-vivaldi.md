# 13 — Vivaldi

[Accueil](../README.md) · [Précédent](12-shell-terminal.md) · [Suivant](14-maintenance.md)

> **Dans ce chapitre :** synchronisation, thème, panneau latéral et extensions du navigateur Vivaldi.

- [13.1 Synchronisation, cache et réglages internes](#131--synchronisation-cache-et-réglages-internes)
- [13.2 Appliquer le thème et les modifications CSS](#132--appliquer-le-thème-et-les-modifications-css)
- [13.3 Configurer le panneau latéral et la recherche Google](#133--configurer-le-panneau-latéral-et-la-recherche-google)
- [13.4 Personnaliser les icônes des extensions](#134--personnaliser-les-icônes-des-extensions)
- [13.5 Installer les extensions et associer les liens magnet](#135--installer-les-extensions-et-associer-les-liens-magnet)
- [13.6 CopierURL — extension Vivaldi pour Grabber](#136--copierurl--extension-vivaldi-pour-grabber)

## 13.1 — Synchronisation, cache et réglages internes

Commencer par synchroniser les réglages avec le compte Vivaldi, puis utiliser `chrome://settings/system`.

### Lanceur : processus et cache

Ajouter au lanceur les arguments du mémo :

```text
--process-per-site --disk-cache-dir=/run/user/1000/vivaldi-cache
```

Le chemin est personnel : vérifier l'UID avec `id -u` avant d'utiliser `1000`.

### Options expérimentales

Dans `vivaldi://flags`, rechercher et activer les options suivantes **si elles existent dans la version installée** :

- Smooth Scrolling.
- Experimental QUIC.
- GPU rasterization.
- Zero-copy rasterizer.
- Parallel downloading.
- `http-cache-custom-backend`.
- `memory-purge-on-freeze-limit`.
- Split View.

Désactiver **Touch UI Layout** si l'option est disponible. Ces choix sont ceux du mémo, pas des gains de performance mesurés pour chaque version.

### Préchargement et lecture automatique

Ouvrir les réglages système internes, indiqués dans le mémo comme `vivaldi:settings/system` (adresse à essayer : `vivaldi://settings/system`). Régler le préchargement et décocher les options qui le désactivent dans uBlock Origin et LocalCDN si l'objectif est de l'autoriser.

Pour bloquer la lecture automatique YouTube, le parcours indiqué est **Vivaldi → Paramètres → Confidentialité → Permissions des sites → Lecture automatique → Bloquer**.

## 13.2 — Appliquer le thème et les modifications CSS

Appliquer le thème personnalisé disponible dans le dépôt.

Pour les modifications CSS de l'interface :

1. Ouvrir `vivaldi://experiments/`.
2. Activer **Allow for using CSS modifications** si l'option est proposée.
3. Redémarrer Vivaldi.
4. Dans **Paramètres → Apparence → Modifications UI personnalisées**, sélectionner le dossier contenant les fichiers CSS du dépôt.

## 13.3 — Configurer le panneau latéral et la recherche Google

Ajouter Perplexity et [WhatsApp Web](https://web.whatsapp.com/) au panneau latéral. Le mémo conserve [ce retour sur WhatsApp en panneau Web](https://www.reddit.com/r/vivaldibrowser/comments/1m93s3b/does_anyone_know_how_to_open_whatsapp_as_webpanel/).

Ajouter également Raindrop, Discord et Gmail, ainsi que les accès à la traduction, aux commandes rapides d'extension et aux sessions.

### Moteur de recherche Google « noAI »

Créer un moteur de recherche Google noAI en éditant les lignes suivantes :

```
Alias:
n

URL:
https://www.google.com/search?q=%s&udm=14

URL des suggestions:
https://www.google.com/complete/search?client=chrome&q=%s

URL de recherche inversée d'image:
{google:baseSearchByImageURL}upload

Paramètres POST de recherche d'image:
encoded_image={google:imageThumbnail},image_url={google:imageURL},sbisrc={google:imageSearchSource},original_width={google:imageOriginalWidth},original_height={google:imageOriginalHeight},processed_image_dimensions={google:processedImageDimensions}
```

## 13.4 — Personnaliser les icônes des extensions

Le script [fix-vivaldi-extension-icons.sh](../Ressources/Logiciels/Vivaldi/fix-vivaldi-extension-icons.sh) personnalise les icônes de **Raindrop** (nuage Adwaita blanc) et **uBlock Origin classique** (cadre continu quand le filtrage est actif, pointillé et « u » atténué quand il est désactivé). **CopierURL** embarque directement ses propres icônes : le script ne la modifie pas.

### Installation et exécution

1. Vérifier que Vivaldi, Raindrop et uBlock Origin classique sont installés dans le profil par défaut.
2. Installer la conversion SVG si nécessaire : `sudo pacman -S librsvg`
3. Depuis la racine du dépôt, rendre le script exécutable, vérifier sa syntaxe, puis le lancer :

   `chmod +x Ressources/Logiciels/Vivaldi/fix-vivaldi-extension-icons.sh`

   `bash -n Ressources/Logiciels/Vivaldi/fix-vivaldi-extension-icons.sh`

   `bash Ressources/Logiciels/Vivaldi/fix-vivaldi-extension-icons.sh`

4. Redémarrer Vivaldi.

Le script s'arrête si une dépendance, une icône Adwaita ou un fichier cible attendu est absent. Il ne crée pas de sauvegarde des originaux. Une mise à jour de Vivaldi ou d'une extension peut restaurer les icônes d'origine : relancer alors le script.

**Badge uBlock :** le nombre de publicités bloquées est géré séparément de l'image de l'icône et devrait rester disponible. Si l'extension redéfinit dynamiquement son icône, elle peut toutefois remplacer l'image personnalisée.

## 13.5 — Installer les extensions et associer les liens magnet

Les extensions sont regroupées ci-dessous par usage.

### Confidentialité & blocage

- [ublock Origin](https://chromewebstore.google.com/detail/ublock-origin/cjpalhdlnbpafiamejdnhcphjbkeiagm)

- [Rehistoria Auto Delete](https://chromewebstore.google.com/detail/rehistoria-auto-delete-hi/dheibmdojjjhiahbdmcnmbepnaiilloe)

### Téléchargement


### Productivité

- **CopierURL — Grabber** : extension locale documentée en [13.6](#136--copierurl--extension-vivaldi-pour-grabber), qui remplace Tab Copy/Auto Tab Copy pour la copie d’URL et ajoute l’envoi vers Grabber.
- [Raindrop](https://chromewebstore.google.com/detail/raindropio/ldgfbffkinooeloadekpmfoklnobpien?pli=1)

### Apparence

- [Stylus](https://chromewebstore.google.com/detail/stylus/clngdbkpkpeebahjckkjfobafhncgmne?hl=fr) pour la couleur de surlignage et insérer :

```
::selection {
    color: white !important;
    background-color: #3584e4 !important;
}
```

### Liens magnet

Associer les liens magnet à Fragments :

```fish
gio mime x-scheme-handler/magnet de.haeckerfelix.Fragments.desktop
```

## 13.6 — CopierURL — extension Vivaldi pour Grabber

**CopierURL** remplace Tab Copy et Auto Tab Copy dans ce setup. L’archive et les icônes sont conservées dans `Ressources/Logiciels/Vivaldi/CopierURL Grabber/`.

Fonctions principales :

- clic sur l’icône ou `Alt` + `Maj` + `G` : copier l’URL de l’onglet actif ;
- `Alt` + `Maj` + `H` : copier les URL de tous les onglets de la fenêtre ;
- menus contextuels pour copier l’URL de l’onglet, les URL des onglets sélectionnés, toutes les URL de la fenêtre et les URL HTTP(S) trouvées dans un texte sélectionné ;
- commandes **Ouvrir … avec Grabber** pour transmettre les URL de liens, onglets, fenêtres, onglets sélectionnés ou médias.

Les URL copiées sont écrites une par ligne dans le presse-papiers. L’envoi à Grabber utilise le protocole `grabber://add` et peut déclencher une confirmation du navigateur pour ouvrir l’application externe.

### Installation

1. **Décompresser l’archive de l’extension CopierURL Grabber**, puis déplacer le dossier extrait vers `~/.config/vivaldi_css/` (créer ce dossier parent s’il n’existe pas). L’extension doit rester dans ce dossier définitif : Vivaldi chargera les fichiers directement depuis celui-ci.
2. Depuis l’emplacement définitif de l’AppImage Grabber, exécuter une fois :

   ```fish
   ./Grabber.AppImage --install-desktop
   ```

   Adapter le nom si l’AppImage porte un autre nom. Refaire cette étape uniquement si son chemin change.
3. Ouvrir `vivaldi://extensions`, activer le **mode développeur**, puis choisir **Charger l’extension non empaquetée**.
4. Sélectionner le dossier extrait que tu as déplacé dans `~/.config/vivaldi_css/` (par exemple `~/.config/vivaldi_css/CopierURL Grabber/`).

L’extension utilise les raccourcis et menus contextuels listés ci-dessus. L’envoi vers Grabber passe par le protocole `grabber://add` et peut nécessiter l’autorisation du navigateur pour ouvrir l’application externe.
---

---

[Accueil](../README.md) · [Précédent](12-shell-terminal.md) · [Suivant](14-maintenance.md)
