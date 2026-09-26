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

`Trieur.path` surveille `~/Téléchargements` ; `Trieur.service` attend **2 secondes**, exécute le script, puis s'arrête. Le script ne parcourt que les fichiers à la racine : dossiers extraits, vidéos et formats inconnus restent en place.

- `Archives/` : zip, 7z, rar, tar, gz, xz, zst…
- `Audio/` : mp3, flac, opus, ogg, m4a, wav…
- `Code/` : md, json, yaml, sh, fish, py, js, conf…
- `Documents/` : pdf, odt, docx, xlsx, pptx, txt…
- `Ebooks/` : epub, mobi, azw3, cbz, cbr…
- `Images/` : jpg, png, webp, avif, svg…
- `ISOs/` : iso, img et fichiers associés.
- `Packages/` : AppImage, deb, rpm ; paquets Arch dans `Packages/<pkgname>/`, selon leur fichier `.PKGINFO`. Les doublons renommés par le navigateur (ex. `stethoscope-0.4.0-2-any.pkg (1).tar.zst`) sont reconnus aussi ; un fichier sans métadonnées de paquet valides reste en place.

### Installation

Les blocs suivants utilisent la syntaxe **Bash** (`EOF`, accolades). Depuis Fish, lancer `bash` une fois, exécuter les blocs dans l'ordre, puis revenir à Fish avec `exit`.

```fish
bash
```

Créer les dossiers (sans modifier ceux qui existent déjà) :

```bash
mkdir -p "$HOME/Téléchargements"/{Archives,Audio,Code,Documents,Ebooks,Images,ISOs,Packages}
mkdir -p "$HOME/.local/bin" "$HOME/.config/systemd/user"
```

Créer le script :

```bash
cat > "$HOME/.local/bin/trieur" <<'EOF'
#!/usr/bin/env bash

DOWNLOADS="$HOME/Téléchargements"

move_file() {
    local file="$1"
    local destination="$2"
    local name target base ext n

    name="${file##*/}"
    mkdir -p "$destination"
    target="$destination/$name"

    if [[ -e "$target" ]]; then
        if [[ "$name" == *.* ]]; then
            base="${name%.*}"
            ext=".${name##*.}"
        else
            base="$name"
            ext=""
        fi

        n=2
        while [[ -e "$destination/$base ($n)$ext" ]]; do
            ((n++))
        done
        target="$destination/$base ($n)$ext"
    fi

    mv -- "$file" "$target"
}

move_arch_package() {
    local file="$1"
    local pkgname

    pkgname="$(
        bsdtar -xOf "$file" .PKGINFO 2>/dev/null |
        sed -n 's/^pkgname = //p' |
        head -n 1
    )"

    [[ -n "$pkgname" ]] || return
    move_file "$file" "$DOWNLOADS/Packages/$pkgname"
}

find "$DOWNLOADS" -maxdepth 1 -type f -print0 |
while IFS= read -r -d '' file; do
    name="${file##*/}"
    lower="${name,,}"

    case "$lower" in
        *.part|*.crdownload|*.download|*.partial|*.tmp)
            continue ;;
        *.pkg*.tar.zst|*.pkg*.tar.xz|*.pkg*.tar.gz)
            move_arch_package "$file" ;;
        *.appimage|*.deb|*.rpm)
            move_file "$file" "$DOWNLOADS/Packages" ;;
        *.iso|*.img|*.iso.sig|*.iso.sha256|*.iso.sha512)
            move_file "$file" "$DOWNLOADS/ISOs" ;;
        *.epub|*.mobi|*.azw|*.azw3|*.fb2|*.cbz|*.cbr)
            move_file "$file" "$DOWNLOADS/Ebooks" ;;
        *.pdf|*.odt|*.ods|*.odp|*.doc|*.docx|*.xls|*.xlsx|*.ppt|*.pptx|*.rtf|*.txt|*.csv)
            move_file "$file" "$DOWNLOADS/Documents" ;;
        *.zip|*.7z|*.rar|*.tar|*.tar.gz|*.tgz|*.tar.xz|*.txz|*.tar.bz2|*.tbz2|*.gz|*.bz2|*.xz|*.zst)
            move_file "$file" "$DOWNLOADS/Archives" ;;
        *.md|*.json|*.yaml|*.yml|*.toml|*.sh|*.fish|*.py|*.js|*.ts|*.css|*.html|*.xml|*.ini|*.conf|*.service|*.path|*.desktop)
            move_file "$file" "$DOWNLOADS/Code" ;;
        *.jpg|*.jpeg|*.png|*.webp|*.avif|*.gif|*.svg|*.bmp|*.tif|*.tiff|*.heic)
            move_file "$file" "$DOWNLOADS/Images" ;;
        *.mp3|*.flac|*.opus|*.ogg|*.oga|*.m4a|*.aac|*.wav|*.wma)
            move_file "$file" "$DOWNLOADS/Audio" ;;
        *)
            continue ;;
    esac
done
EOF
chmod +x "$HOME/.local/bin/trieur"
```

Créer les deux unités utilisateur :

```bash
cat > "$HOME/.config/systemd/user/Trieur.service" <<'EOF'
[Unit]
Description=Trieur automatique du dossier Téléchargements

[Service]
Type=oneshot
ExecStartPre=/usr/bin/sleep 2
ExecStart=%h/.local/bin/trieur
EOF

cat > "$HOME/.config/systemd/user/Trieur.path" <<'EOF'
[Unit]
Description=Surveillance du dossier Téléchargements pour Trieur

[Path]
PathChanged=%h/Téléchargements
Unit=Trieur.service

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now Trieur.path
exit
```

### Vérification et gestion

Ces commandes fonctionnent directement dans Fish :

```fish
systemctl --user status Trieur.path
journalctl --user -u Trieur.service
```

État attendu : `Trieur.path` est `active (waiting)`. Pour arrêter puis réactiver Trieur :

```fish
systemctl --user disable --now Trieur.path
systemctl --user enable --now Trieur.path
```

Après modification d'une unité :

```fish
systemctl --user daemon-reload
systemctl --user restart Trieur.path
```

Attribuer manuellement les icônes **Teal** aux dossiers Archives, Audio, Code, Documents, Ebooks, Images, ISOs et Packages.

---

[Accueil](../README.md) · [Précédent](08-gnome-extensions.md) · [Suivant](10-logiciels.md)
