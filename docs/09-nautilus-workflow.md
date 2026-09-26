# 9 — Nautilus — workflow

[Accueil](../README.md) · [Précédent](08-gnome-extensions.md) · [Suivant](10-logiciels.md)

> **Dans ce chapitre :** marque-pages, scripts et extensions Nautilus, dossiers masqués, icônes personnalisées, modèles de documents et tri des téléchargements.

- [9.1 Marque-pages](#91--marque-pages)
- [9.2 Scripts Nautilus et extensions (copy-path, admin)](#92--scripts-nautilus-et-extensions-copy-path-admin)
- [9.3 Masquer des dossiers et personnaliser les icônes](#93--masquer-des-dossiers-et-personnaliser-les-icônes)
- [9.4 Modèles de documents](#94--modèles-de-documents)
- [9.5 Trieur automatique de Téléchargements](#95--trieur-automatique-de-téléchargements)

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

## 9.5 — Trieur automatique de Téléchargements

`Trieur.path` surveille `~/Téléchargements`. Après un changement, `Trieur.service` attend **2 secondes**, lance `~/.local/bin/trieur` pour classer les fichiers, puis s'arrête. Les vidéos et les formats inconnus restent à la racine.

- `Archives/` : zip, 7z, rar, tar, gz, xz, zst…
- `Audio/` : mp3, flac, opus, ogg, m4a, wav…
- `Code/` : md, json, yaml, sh, fish, py, js, conf…
- `Documents/` : pdf, odt, docx, xlsx, pptx, txt…
- `Ebooks/` : epub, mobi, azw3, cbz, cbr…
- `Images/` : jpg, png, webp, avif, svg…
- `ISOs/` : iso, img, signatures et sommes de contrôle des ISO.
- `Packages/` : AppImage, deb, rpm ; les paquets Arch sont rangés dans `Packages/<pkgname>/` d'après leur fichier `.PKGINFO`.

Les deux unités se trouvent dans `~/.config/systemd/user/`. Vérifier la surveillance et consulter le journal :

```fish
systemctl --user status Trieur.path
journalctl --user -u Trieur.service
```

L'état attendu de `Trieur.path` est `active (waiting)`. Pour désactiver ou réactiver la surveillance :

```fish
systemctl --user disable --now Trieur.path
systemctl --user enable --now Trieur.path
```

Après modification d'une unité :

```fish
systemctl --user daemon-reload
systemctl --user restart Trieur.path
```

Attribuer manuellement les icônes de dossiers **Teal** aux huit dossiers créés : Archives, Audio, Code, Documents, Ebooks, Images, ISOs et Packages.

---

[Accueil](../README.md) · [Précédent](08-gnome-extensions.md) · [Suivant](10-logiciels.md)
