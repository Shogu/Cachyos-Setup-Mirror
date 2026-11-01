# Perceptron

Interface GNOME native pour [OpenCode](https://opencode.ai), réalisée en GTK4/libadwaita et WebKitGTK 6.0.

Perceptron est un wrapper : il démarre `opencode serve`, réalise l’appairage avec `opencode pair` et affiche l’interface web d’OpenCode dans une fenêtre Adwaita. OpenCode doit être installé séparément et accessible dans le `PATH`.

Le paquet **`perceptron-nautilus`** installe également l’extension Nautilus **« Ouvrir dans Perceptron »**. Depuis le menu contextuel d’un dossier, elle ouvre ce dossier dans Perceptron. L’extension est intégrée au paquet et ne demande aucune installation séparée.

## Installation

Le paquet Arch/CachyOS `perceptron-nautilus` sera ajouté manuellement dans ce dossier. Une fois le paquet déposé, l’installer depuis ce dossier :

```fish
set paquets_perceptron (find . -maxdepth 1 -type f -name 'perceptron-nautilus*.pkg.tar.zst')
if test (count $paquets_perceptron) -eq 1
    sudo pacman -U "$paquets_perceptron[1]"
else
    echo 'Conserver un seul paquet perceptron-nautilus*.pkg.tar.zst dans ce dossier.'
end
```

Puis lancer l’application depuis le menu GNOME ou avec :

```fish
opencode-perceptron
```

## Dépendances

OpenCode doit être installé séparément et accessible dans le `PATH`. Les dépendances graphiques et Nautilus sont déclarées par le paquet.

## Désinstallation

```fish
sudo pacman -Rns perceptron-nautilus
```

Licence : MIT.
