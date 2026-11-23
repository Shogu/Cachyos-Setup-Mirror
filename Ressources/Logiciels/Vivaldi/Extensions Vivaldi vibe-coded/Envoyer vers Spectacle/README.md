# Extension Vivaldi — Envoyer vers Spectacle

Extension Vivaldi : ouvre une vidéo YouTube dans **Spectacle**, à la même position.

## Utilisation

- **Sur YouTube** : bouton **« Spectacle »** sous la vidéo (à côté de J'aime, Partager…). La vidéo se met en pause dans le navigateur.
- **Partout** : clic droit sur un lien YouTube, puis **« Ouvrir dans Spectacle »**. Liens reconnus : `youtube.com/watch`, `youtu.be/`, `youtube.com/shorts/`, `music.youtube.com`, playlists `list=`.

Au clic, Spectacle démarre (ou reçoit l'URL dans sa fenêtre déjà ouverte, même en arrière-plan) et reprend **à la même position** (`spectacle://open?url=…&t=…`). Le Rideau reste dans l'état où il était.

## Installation

1. `vivaldi://extensions`, activer le **mode développeur**.
2. **Charger l'extension non empaquetée** et choisir le dossier extrait (le laisser en place).
3. Au premier envoi, cocher **« toujours autoriser »** pour `spectacle://`.

L'archive [vivaldi-send-to-spectacle-1.0.0.zip](vivaldi-send-to-spectacle-1.0.0.zip) est conservée dans ce dossier. Décompresser l'archive, puis charger le dossier extrait.

Nécessite **Spectacle 0.6.1** ou plus récent (gestion des liens `spectacle://`).

## Détails

- Manifest V3 ; permission minimale `contextMenus`, script de contenu injecté uniquement sur `*://*.youtube.com/*`.
- Pas d'icône dans la barre d'outils : l'extension n'en a pas besoin.

Voir aussi [13.9 — Envoyer vers Spectacle](../../../../docs/13-vivaldi.md#139--envoyer-vers-spectacle--extension-vivaldi-pour-spectacle).
