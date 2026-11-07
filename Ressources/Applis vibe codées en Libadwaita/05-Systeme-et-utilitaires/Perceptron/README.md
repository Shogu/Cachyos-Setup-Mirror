# Perceptron — interface GNOME pour OpenCode

**Perceptron** est une interface GTK4/libadwaita pour [OpenCode](https://opencode.ai). L’application démarre `opencode serve`, effectue l’appairage avec `opencode pair`, puis affiche l’interface web d’OpenCode dans une vue **WebKitGTK 6.0**. OpenCode doit être installé séparément et accessible dans le `PATH` : Perceptron fournit une fenêtre GNOME native, tandis que les modèles, les conversations et les sessions restent gérés par OpenCode.

## Dépendances

Dépendances système :

- `python`
- `python-gobject`
- `gtk4`
- `libadwaita`
- `webkitgtk-6.0`

Le binaire `opencode` est indispensable, mais s’installe séparément.

## Installation et lancement

Le paquet Arch compilé est fourni séparément du dépôt de sources. Depuis le dossier contenant le paquet :

```fish
set paquets_perceptron (find . -maxdepth 1 -type f -name 'perceptron*.pkg.tar.zst')
if test (count $paquets_perceptron) -eq 1
    sudo pacman -U "$paquets_perceptron[1]"
else
    echo 'Conserver un seul paquet perceptron*.pkg.tar.zst dans ce dossier.'
end
```

Lancer ensuite Perceptron depuis la grille d’applications GNOME. Vérifier au préalable qu’OpenCode est disponible :

```fish
opencode --version
```

Pour désinstaller :

```fish
sudo pacman -Rns perceptron
```

## Extension compagnon Vivaldi

L’extension compagnon permet d’envoyer l’URL de l’onglet courant ou une sélection de texte vers **une nouvelle session dédiée dans Perceptron**. Les fichiers et la notice d’installation sont regroupés dans [Ressources/Logiciels/Vivaldi/Perceptron](../../../Logiciels/Vivaldi/Perceptron/README.md).

## Dépannage : génération automatique du titre des sessions

Si OpenCode ne génère plus automatiquement de titre pour les nouvelles sessions, vérifier la configuration dans `~/.config/opencode/opencode.jsonc`. Une ancienne configuration peut encore employer le bloc singulier `agent` ou le champ historique `prompt`, alors que la configuration actuelle attend le bloc `agents` et son entrée `title`.

La configuration du titre doit donc être placée dans `agents.title` (et non dans un ancien bloc `agent`). Le modèle peut être explicitement défini dans cette configuration ; la variable `OPENCODE_TITLE_MODEL` avait également été utilisée pour sélectionner `albert/gpt-oss-120b`.

Cette correction concerne les **nouvelles sessions** : les titres des sessions déjà créées ne sont pas recalculés. Elles peuvent être renommées manuellement avec `Ctrl+R`. Avant toute modification du fichier JSONC, en conserver une copie de sauvegarde et vérifier la syntaxe de la configuration.

## Ressources

L’archive de la variante WebKit est conservée dans ce dossier. Les notes de version et les évolutions du projet sont suivies dans le dépôt de sources.
