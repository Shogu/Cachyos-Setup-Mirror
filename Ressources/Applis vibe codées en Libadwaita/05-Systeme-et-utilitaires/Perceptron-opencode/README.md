# Perceptron

Interface GNOME native pour [OpenCode](https://opencode.ai), réalisée en GTK4/libadwaita et WebKitGTK 6.0.

Perceptron est un wrapper : il démarre `opencode serve`, réalise l’appairage avec `opencode pair` et affiche l’interface web d’OpenCode dans une fenêtre Adwaita. OpenCode doit être installé séparément et accessible dans le `PATH`.

## Installation

Le paquet Arch/CachyOS est fourni dans ce dossier :

```fish
sudo pacman -U ./perceptron-1.0.0-1-any.pkg.tar.zst
```

Le dossier contient aussi `perceptron-1.0.0-sources.tar.gz` (archive des sources de cette version, à titre de référence).

Puis lancer l’application depuis le menu GNOME ou avec :

```fish
perceptron
```

## Dépendances

`python`, `python-gobject`, `gtk4`, `libadwaita`, `webkitgtk-6.0` et **OpenCode** (à installer séparément).

## Reconstruction

Depuis le dossier des sources : `makepkg -si` ou `./build.sh` (voir la documentation du projet).

## Désinstallation

```fish
sudo pacman -Rns perceptron
```

## Fix : nommage des sessions OpenCode (agent `title`)

**Problème** : les sessions restent titrées « session » (nom par défaut) au lieu
d'être nommées d'après le premier message. Cause : la config OpenCode
(`~/.config/opencode/opencode.jsonc`) contenait un bloc invalide en V2 —
clé `agent` au singulier + champ `prompt` (vestige V1) → **ignoré** par OpenCode.
La génération auto du titre échouait donc en silence.

**Correctif** : le bloc valide V2 `agents.title` (avec `model` épinglé et un
prompt `system` qui reprend les **4 à 7 premiers mots** du premier message).

Script de correction (sûr, idempotent, avec sauvegarde `.bak.<date>` avant écriture) :

```fish
# depuis ce dossier (copie référencée dans le repo)
python3 fix-opencode-titre/fix-opencode-titre-sessions.py

# ou, en dépannage, la copie archivée
python3 ~/Téléchargements/Archives/fix-opencode-titre-sessions.py
```

Le modèle de titre peut être surchargé :
`OPENCODE_TITLE_MODEL=albert/gpt-oss-120b python3 fix-opencode-titre-sessions.py`

**Effet** : s'applique aux **nouvelles** sessions ; les anciennes gardent leur nom
(re-nommage manuel avec `Ctrl+R`). Vérification : lancer une nouvelle session —
le titre doit apparaître après le premier message.

Licence : MIT.