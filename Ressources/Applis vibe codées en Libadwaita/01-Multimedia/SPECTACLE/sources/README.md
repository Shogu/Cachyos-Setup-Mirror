# Spectacle

Lecteur YouTube minimaliste, pour écouter et regarder, pour GNOME (GTK4, libadwaita, GStreamer). Les vidéos sont lues en continu, rien n'est enregistré sur le disque. Les téléchargements restent le rôle de Grabber.

## Fonctionnement

1. Saisir des mots-clés (recherche `ytsearch`, 20 résultats) ou coller une adresse YouTube, puis Entrée.
2. yt-dlp (voir plus bas) renvoie le titre, la chaîne, l'adresse directe du flux et les en-têtes HTTP à utiliser. Aucune vidéo n'est téléchargée (`-J`, sans cache).
3. L'adresse est confiée à `playbin` ; les en-têtes de yt-dlp (User-Agent, etc.) sont appliqués à la source HTTP.
4. L'image est rendue par `gtk4paintablesink` (dans `glsinkbin` si OpenGL est disponible) affiché dans un `Gtk.Picture`.

Format demandé : le meilleur flux qui contient à la fois l'audio et la vidéo, en HTTP direct si possible. Avec `playbin`, YouTube ne propose généralement ce type de flux qu'en qualité moyenne (souvent 360p) ; les formats HD sont séparés (vidéo d'un côté, audio de l'autre).

## Moteur JavaScript

YouTube impose désormais un déchiffrement en JavaScript. Spectacle utilise **QuickJS** (`quickjs-ng`, environ 1 Mo, binaire `/usr/bin/qjs`), passé explicitement à yt-dlp (`--no-js-runtimes --js-runtimes quickjs:/usr/bin/qjs`). Deno et Node.js ne sont ni requis ni téléchargés. Si `qjs` est absent, un bandeau le signale et les échecs de déchiffrement affichent un message clair.

## Nouveautés 0.3.0

- **Envoyer à Grabber** (bouton dans la barre de lecture) : transmet la vidéo en cours à Grabber par son protocole `grabber://add?url=…`, le même que CopierURL dans Vivaldi. Spectacle ne télécharge rien lui-même. Si Grabber n'a pas enregistré son protocole, un message l'indique.

- **Rideau** (bouton à droite de la barre du haut) : son seul. Pendant une lecture, l'image est coupée instantanément, sans interruption du son ni rechargement : plus aucune image n'est décodée ni affichée (moins de processeur, de mémoire et de batterie). Une vidéo lancée sous Rideau ne demande que le flux audio à YouTube (moins de réseau aussi) ; lever le Rideau sur cette vidéo charge l'image et reprend seul au même endroit.
- **Pochette locale** : la miniature YouTube (320×180) est mise en cache dans `~/.cache/spectacle-ogu/covers` (60 au plus) et publiée en `file://` ; les extensions de lecteurs comme Topbar Center Widget l'affichent alors avec les coins arrondis de GNOME.
- **Couper le son** : clic sur l'icône du volume (second clic : son rétabli).
- **Favoris** : étoile dans la barre de lecture ; liste « Favoris » dans le panneau latéral (onglets Résultats / Favoris), avec bouton de retrait. Enregistrés dans `~/.local/share/spectacle-ogu/favoris.json`.
- **Lecture continue** (bouton à côté de l'étoile, actif par défaut) : à la fin d'une vidéo, la suivante de la liste d'où elle a été lancée (résultats ou favoris) démarre. Boutons Précédente / Suivante.
- **Lecteur reconnu par GNOME** (MPRIS, nom `org.mpris.MediaPlayer2.spectacle_ogu`) : titre, chaîne, miniature et durée apparaissent dans le lecteur du menu date de GNOME et dans les extensions de lecteurs comme Topbar Center Widget ; lecture, pause, suivante, précédente et déplacement se pilotent de là.
- **Barre du haut** : le champ de recherche est limité en largeur, il reste de la place de part et d'autre pour saisir et déplacer la fenêtre.

## Commandes

| Action | Raccourci |
|---|---|
| Lecture / pause | Espace (hors champ de saisie) ou bouton lecture |
| Plein écran | F11 ou double-clic sur la vidéo |
| Quitter le plein écran | Échap |
| Aller au champ de recherche | Ctrl+L ou Ctrl+F |
| Fermer | Ctrl+W, Ctrl+Q |

## Erreurs gérées

Adresse non valide, vidéo indisponible ou soumise à l'âge, déchiffrement impossible (moteur JS), aucun format lisible, YouTube injoignable, flux inaccessible (erreur HTTP), média illisible ou greffon GStreamer manquant, fin de lecture (écran « Lecture terminée » avec bouton « Revoir »).

## Arborescence

```
spectacle-ogu-0.3.3/
├── spectacle-cmd                    lanceur → /usr/bin/spectacle-ogu
├── spectacle.py                     point d'entrée → /usr/lib/spectacle-ogu/
├── spectacle/
│   ├── main.py                      Adw.Application, raccourcis
│   ├── window.py                    fenêtre : recherche, résultats, lecteur, contrôles
│   ├── player.py                    playbin + gtk4paintablesink, bus GStreamer (EOS, erreurs, buffering)
│   ├── covers.py                    miniatures en cache local pour MPRIS
│   ├── favorites.py                 favoris
│   ├── mpris.py                     interface MPRIS 2 (lecteur visible dans GNOME)
│   ├── extractor.py                 appels asynchrones à yt-dlp (Gio.Subprocess), analyse des erreurs
│   └── ytdlp.py                     téléchargement, vérification et mise à jour de yt-dlp
├── data/
│   ├── io.gitlab.shogu.Spectacle.desktop
│   └── icons/                       icône couleur et symbolique
└── README.md
```

Le nom affiché est « Spectacle » ; paquet et commande s'appellent `spectacle-ogu` pour ne pas entrer en conflit avec l'outil de capture d'écran de KDE (paquet `spectacle`).

## yt-dlp

Rien à installer à part. Au premier usage, Spectacle télécharge le binaire officiel autonome `yt-dlp_linux` (dernière version publiée sur GitHub) dans `~/.local/share/yt-dlp-ogu/yt-dlp`, après avoir vérifié sa somme SHA-256 avec le fichier `SHA2-256SUMS` de la même publication. Si cette copie a plus de 7 jours, elle sert quand même et une mise à jour se fait en arrière-plan ; en cas d'échec, l'ancienne copie reste utilisée. Chihiro utilise la même copie. Le paquet Arch officiel `yt-dlp` n'est pas utilisé : il impose Deno ; ici, le déchiffrement YouTube passe par QuickJS (`quickjs-ng`).

Pour forcer une mise à jour : supprimer `~/.local/share/yt-dlp-ogu/yt-dlp` puis relancer l'application.

## Dépendances

`python`, `python-gobject`, `gtk4`, `libadwaita`, `gstreamer`, `gst-plugins-base` (playbin), `gst-plugins-good` (souphttpsrc, démultiplexeur MP4), `libsoup3` (chargée par souphttpsrc), `gst-plugins-bad` (HLS pour les directs, VA-API), `gst-libav` (décodeurs H.264/AAC), `gst-plugin-gtk4` (gtk4paintablesink), `quickjs-ng`.
