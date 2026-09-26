# 9 — Nautilus — workflow

[Accueil](../README.md) · [Précédent](08-gnome-extensions.md) · [Suivant](10-logiciels.md)

> **Dans ce chapitre :** marque-pages, scripts et extensions Nautilus, dossiers masqués, icônes personnalisées et modèles de documents.

- [9.1 Marque-pages](#91--marque-pages)
- [9.2 Scripts Nautilus et extensions (copy-path, admin)](#92--scripts-nautilus-et-extensions-copy-path-admin)
- [9.3 Masquer des dossiers et personnaliser les icônes](#93--masquer-des-dossiers-et-personnaliser-les-icônes)
- [9.4 Modèles de documents](#94--modèles-de-documents)

## 9.1 — Marque-pages

Dans Nautilus, créer les marque-pages utiles :

- Le dossier `Dropbox`.
- Le serveur FTP donnant accès au SSD de la télévision Android : `ftp://192.168.31.68:2121`.
- L'accès administrateur au système de fichiers via `admin:///` : saisir cette adresse, ouvrir le système de fichiers puis ajouter un marque-page avec **Ctrl+D**.

## 9.2 — Scripts Nautilus et extensions (copy-path, admin)


Ajouter les extensions de copie du chemin et d'accès administrateur :

```fish
sudo pacman -Syu nautilus-python
shelly aur install nautilus-copy-path nautilus-admin

```

Éditer les fichiers de configuration et d'extension :

```fish
sudoedit /usr/share/nautilus-python/extensions/nautilus-copy-path/nautilus_copy_path.py
sudoedit /usr/share/nautilus-python/extensions/nautilus-copy-path/config.json
sudoedit /usr/share/nautilus-python/extensions/nautilus-admin.py
```

Dans la configuration de copie de chemin, passer **URI** et **Content** à `false`. Dans l'extension administrateur, traduire **Open as admin**.

Ces modifications touchent des fichiers de paquets et peuvent être remplacées lors d'une mise à jour. Fermer puis rouvrir Nautilus après l'édition :

```fish
nautilus -q
nautilus
```

Pour l'intégration du terminal Ptyxis dans Nautilus (clic droit → ouvrir un terminal), voir [Shell & terminal](12-shell-terminal.md#121--intégrer-ptyxis-à-nautilus-et-aux-outils-cachyos).

## 9.3 — Masquer des dossiers et personnaliser les icônes

Dans Nautilus :

- Masquer les dossiers Modèles et Bureau si souhaité.
- Masquer les fichiers du fond d'écran et de l'image utilisateur sans les déplacer hors des chemins configurés.
- Augmenter la taille des icônes de dossiers.

Personnaliser les icônes **Places** des dossiers suivants à partir des icônes du dossier **Icons & background** du dépôt : `Dropbox`, MP3, Root, Domestique et Lycée (dans Dropbox), Nicotine, Téléchargements, `usr`, `root`, Extensions, Icons, ainsi que des extensions GNOME et des autres dossiers souhaités.

## 9.4 — Modèles de documents

Utiliser un dossier caché **`.Modèles`** pour le menu de création de fichiers de Nautilus.

Renommer l'ancien dossier s'il existe et si la destination n'existe pas encore, puis créer le dossier caché :

```fish
if test -d "$HOME/Modèles"; and not test -e "$HOME/.Modèles"
    mv -- "$HOME/Modèles" "$HOME/.Modèles"
end
mkdir -p "$HOME/.Modèles"
```

Si les deux dossiers existaient déjà, déplacer manuellement les modèles à conserver dans `.Modèles`.

Créer le modèle texte :

```fish
touch "$HOME/.Modèles/notepad.txt"
```

Pour **`word.docx`**, ouvrir OnlyOffice, créer un document vierge et l'enregistrer comme `/home/ogu/.Modèles/word.docx`. Un simple `touch word.docx`, proposé dans le mémo, créerait un fichier vide et non un document Word valide.

Faire pointer XDG vers ce dossier :

```fish
mkdir -p "$HOME/.config"
touch "$HOME/.config/user-dirs.dirs"
sed -i '/^XDG_TEMPLATES_DIR=/d' "$HOME/.config/user-dirs.dirs"
printf '%s\n' 'XDG_TEMPLATES_DIR="$HOME/.Modèles"' >> "$HOME/.config/user-dirs.dirs"
xdg-user-dirs-update
nautilus -q
```

Rouvrir Nautilus et vérifier la présence des deux modèles dans le menu de création de documents.

---

[Accueil](../README.md) · [Précédent](08-gnome-extensions.md) · [Suivant](10-logiciels.md)
