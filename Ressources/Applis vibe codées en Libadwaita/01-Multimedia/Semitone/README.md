# Semitone

**Semitone** est un lecteur musical GTK4/libadwaita écrit en Vala. C’est un fork de [Gapless](https://gitlab.com/Lalaggi/semitone/-/tree/main), dans la lignée de G4Music. Le fork a été compilé avec **Claude** pour le setup CachyOS et remplace le paquet `gapless`.

## Fonctions

- Lecture audio sans blanc entre les morceaux (*gapless*) via GStreamer.
- Paroles synchronisées au format LRC, avec 13 fournisseurs annoncés par le projet.
- Égaliseur à six bandes.
- Prise en charge de ReplayGain.
- Gestion des playlists.
- Intégration MPRIS pour le contrôle depuis GNOME et les commandes multimédias.

## Installation du paquet compilé

Le paquet Arch sera ajouté manuellement dans ce dossier. Une fois le fichier `semitone-*.pkg.tar.zst` copié ici, ouvrir un terminal dans ce dossier et exécuter :

```fish
set paquets_semitone (find . -maxdepth 1 -type f -name 'semitone*.pkg.tar.zst')
if test (count $paquets_semitone) -eq 1
    sudo pacman -U "$paquets_semitone[1]"
else
    printf '%s\\n' 'Conserver un seul paquet Semitone dans ce dossier avant installation.'
end
```

Le nom et la version exacts du paquet seront précisés lorsqu’il aura été ajouté. Le paquet n’est pas encore inclus dans le dépôt.

## Projet source

- [Semitone — dépôt GitLab](https://gitlab.com/Lalaggi/semitone/-/tree/main)

Semitone est distribué comme fork du projet source ; consulter le dépôt pour les informations à jour sur le code, les dépendances, la licence et la compilation.
