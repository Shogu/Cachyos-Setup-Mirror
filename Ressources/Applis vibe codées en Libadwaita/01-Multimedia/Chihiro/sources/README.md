# Chihiro

Petite fenêtre GTK4 sans décoration (260×225 au lancement, à glisser dans un coin) : une vidéo locale muette de Chihiro en plein cadre, en boucle sans coupure, avec le direct audio de Lofi Girl en bande son.

## Gestes (aucun contrôle visible)

| Geste | Effet |
|---|---|
| Clic droit | pause / reprise (vidéo et son) |
| Glisser | déplacer la fenêtre |
| Double-clic | vidéo suivante (deux vidéos en plan rapproché : le train, aux proportions exactes de la fenêtre, et Zeniba) ; la fenêtre ne s'agrandit jamais |
| Glisser le coin inférieur droit | redimensionner |
| Échap, Ctrl+W, Ctrl+Q | fermer |

L'image remplit la fenêtre ; le recadrage suit un point d'intérêt par vidéo pour garder Chihiro visible dans une fenêtre étroite. Au premier plan : fonction native GNOME (menu de fenêtre Alt+Espace, ou ton extension « Always on top »).

## Extension Réglages rapides

« Chihiro Quick Settings Launch Toggle » (`chihiro-quicksettings-launch-toggle@ogu`), installée par le paquet. Une tuile on/off avec l'icône Susuwatari (chargée depuis le dossier de l'extension par `Gio.FileIcon`) :

- activée : lance Chihiro ;
- désactivée : ferme Chihiro par son action D-Bus `quit` ;
- l'état suit la présence de l'application sur le bus de session (`Gio.bus_watch_name`), même quand Chihiro est ouvert ou fermé autrement.

Activation : se déconnecter puis se reconnecter, puis `gnome-extensions enable chihiro-quicksettings-launch-toggle@ogu`.

## Technique

- Vidéo : `playbin` (vidéo seule) + `gtk4paintablesink` ; boucle sans coupure par `about-to-finish`.
- Son : `playbin` (audio seul) sur l'adresse du direct résolue par yt-dlp, téléchargé au premier lancement dans `~/.local/share/yt-dlp-ogu/` (binaire officiel, somme SHA-256 vérifiée), mis à jour automatiquement chaque semaine et partagé avec Spectacle ; déchiffrement par QuickJS, pas de Deno. En pause, le flux est coupé ; à la reprise, il repart au direct. Sans réseau, la vidéo continue sans son.
- Indépendante de Spectacle : seule la copie de yt-dlp dans le dossier personnel est partagée.

## Arborescence

```
chihiro-0.6.1/
├── chihiro-cmd            lanceur → /usr/bin/chihiro
├── chihiro.py             point d'entrée → /usr/lib/chihiro/
├── chihiro/
│   ├── main.py            fenêtre, gestes
│   ├── player.py          vidéo locale en boucle
│   ├── radio.py           direct audio Lofi Girl
│   ├── ytdlp.py           téléchargement et mise à jour de yt-dlp
│   └── cover.py           remplissage avec recadrage sur point d'intérêt
├── data/media/*.mp4       → /usr/share/chihiro/media/
├── data/fr.ogu.Chihiro.desktop
├── icons/                 icône couleur et symbolique (dessins de l'utilisatrice)
└── extension/             extension Réglages rapides (metadata.json, extension.js, icons/)
```
