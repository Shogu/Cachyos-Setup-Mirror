# K — Vivaldi

[Accueil](README.md) · [Précédent](J-gnome.md) · [Suivant](L-maintenance.md)

- [Synchronisation, cache et réglages internes](#reglages)
- [Appliquer le thème et les modifications CSS](#theme)
- [Configurer le panneau latéral et la recherche Google](#panneau-recherche)
- [Installer les extensions et associer les liens magnet](#extensions)

<a id="reglages"></a>

## K1 — Synchronisation, cache et réglages internes

Commencer par synchroniser les réglages avec le compte Vivaldi.

### Lanceur : processus et cache

Ajouter au lanceur les arguments du mémo :

```text
--process-per-site --disk-cache-dir=/run/user/1000/vivaldi-cache
```

Le chemin est personnel : vérifier l’UID avec `id -u` avant d’utiliser `1000`. Le cache placé dans `/run/user/1000` est temporaire ; ce réglage ne déplace pas tout le profil du navigateur en RAM.

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

Désactiver **Touch UI Layout** si l’option est disponible. Ces choix sont ceux du mémo, pas des gains de performance mesurés pour chaque version.

### Préchargement et lecture automatique

Ouvrir les réglages système internes, indiqués dans le mémo comme `vivaldi:settings/system` (adresse à essayer : `vivaldi://settings/system`). Régler le préchargement et décocher les options qui le désactivent dans uBlock Origin et LocalCDN si l’objectif est de l’autoriser.

Pour bloquer la lecture automatique YouTube, le parcours indiqué est **Vivaldi → Paramètres → Confidentialité → Permissions des sites → Lecture automatique → Bloquer**.

<a id="theme"></a>

## K2 — Appliquer le thème et les modifications CSS

Appliquer le thème personnalisé disponible dans le dépôt.

Pour les modifications CSS de l’interface :

1. Ouvrir `vivaldi://experiments/`.
2. Activer **Allow for using CSS modifications** si l’option est proposée.
3. Redémarrer Vivaldi.
4. Dans **Paramètres → Apparence → Modifications UI personnalisées**, sélectionner le dossier contenant les fichiers CSS du dépôt.

<a id="panneau-recherche"></a>

## K3 — Configurer le panneau latéral et la recherche Google

Ajouter Perplexity et [WhatsApp Web](https://web.whatsapp.com/) au panneau latéral. Le mémo conserve [ce retour sur WhatsApp en panneau Web](https://www.reddit.com/r/vivaldibrowser/comments/1m93s3b/does_anyone_know_how_to_open_whatsapp_as_webpanel/).

Ajouter également Raindrop, Discord et Gmail, ainsi que les accès à la traduction, aux commandes rapides d’extension et aux sessions.

### Moteur de recherche Google « noAI »
Créer un moteur de recherche Google noAI en éditant les lignes suivantes :
```
Alias:
n

URL:
https://www.google.com/search?q=%s&udm=14

URL des suggestions:
https://www.google.com/complete/search?client=chrome&q=%s

URL de recherche inversée d’image:
{google:baseSearchByImageURL}upload

Paramètres POST de recherche d’image:
encoded_image={google:imageThumbnail},image_url={google:imageURL},sbisrc={google:imageSearchSource},original_width={google:imageOriginalWidth},original_height={google:imageOriginalHeight},processed_image_dimensions={google:processedImageDimensions}
```

<a id="extensions"></a>

## K4 — Installer les extensions et associer les liens magnet

- [Better Scroll To Bottom](https://chromewebstore.google.com/detail/better-scroll-to-topbotto/ifdjdmipgndncbeopapghbohjdiieibl?hl=es)
- [Video Download Helper](https://chromewebstore.google.com/detail/video-downloadhelper/lmjnegcaeklhafolokijcfjliaokphfk) et réglages mkv + dossier téléchargements VDH pour correspondre au script `transfert`
- [Tab Copy](https://chromewebstore.google.com/detail/tab-copy/micdllihgoppmejpecmkilggmaagfdmb)
- [LocalCDN](https://chromewebstore.google.com/detail/localcdn/njdfdhgcmkocbgbhcioffdbicglldapd)
- [Rehistoria Auto Delete](https://chromewebstore.google.com/detail/rehistoria-auto-delete-hi/dheibmdojjjhiahbdmcnmbepnaiilloe)
- [ublock Origin](https://chromewebstore.google.com/detail/ublock-origin/cjpalhdlnbpafiamejdnhcphjbkeiagm)
- [Raindrop](https://chromewebstore.google.com/detail/raindropio/ldgfbffkinooeloadekpmfoklnobpien?pli=1)
- [Stylus](https://chromewebstore.google.com/detail/stylus/clngdbkpkpeebahjckkjfobafhncgmne?hl=fr) pour la couleur de surlignage et insérer:
```
::selection {
    color: white !important;
    background-color: #3584e4 !important;
}
```
Associer les liens magnet à Fragments :

```fish
gio mime x-scheme-handler/magnet de.haeckerfelix.Fragments.desktop
```

[Accueil](README.md) · [Précédent](J-gnome.md) · [Suivant](L-maintenance.md)
