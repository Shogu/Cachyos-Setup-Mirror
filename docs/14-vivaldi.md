# 14 — Vivaldi

[Accueil](../README.md) · [Précédent](13-shell-terminal.md) · [Suivant](15-maintenance.md)

> **Dans ce chapitre :** synchronisation, thème, panneau latéral et extensions du navigateur Vivaldi.

- [14.1 Synchronisation, cache et réglages internes](#141--synchronisation-cache-et-réglages-internes)
- [14.2 Appliquer le thème et les modifications CSS](#142--appliquer-le-thème-et-les-modifications-css)
- [14.3 Configurer le panneau latéral et la recherche Google](#143--configurer-le-panneau-latéral-et-la-recherche-google)
- [14.4 Installer les extensions et associer les liens magnet](#144--installer-les-extensions-et-associer-les-liens-magnet)

## 14.1 — Synchronisation, cache et réglages internes

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

## 14.2 — Appliquer le thème et les modifications CSS

Appliquer le thème personnalisé disponible dans le dépôt.

Pour les modifications CSS de l'interface :

1. Ouvrir `vivaldi://experiments/`.
2. Activer **Allow for using CSS modifications** si l'option est proposée.
3. Redémarrer Vivaldi.
4. Dans **Paramètres → Apparence → Modifications UI personnalisées**, sélectionner le dossier contenant les fichiers CSS du dépôt.

## 14.3 — Configurer le panneau latéral et la recherche Google

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

## 14.4 — Installer les extensions et associer les liens magnet

Les extensions sont regroupées ci-dessous par usage.

### Confidentialité & blocage

- [ublock Origin](https://chromewebstore.google.com/detail/ublock-origin/cjpalhdlnbpafiamejdnhcphjbkeiagm)

- [Rehistoria Auto Delete](https://chromewebstore.google.com/detail/rehistoria-auto-delete-hi/dheibmdojjjhiahbdmcnmbepnaiilloe)

### Téléchargement

- [Video Download Helper](https://chromewebstore.google.com/detail/video-downloadhelper/lmjnegcaeklhafolokijcfjliaokphfk) et réglages mkv + dossier téléchargements VDH, repris par Périscope (application maison) pour le tri des vidéos téléchargées

### Productivité

- [Tab Copy](https://chromewebstore.google.com/detail/tab-copy/micdllihgoppmejpecmkilggmaagfdmb)
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

---

[Accueil](../README.md) · [Précédent](13-shell-terminal.md) · [Suivant](15-maintenance.md)
