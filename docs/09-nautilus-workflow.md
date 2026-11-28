# 9 — Nautilus — workflow

[Accueil](../README.md) · [Précédent](08-gnome-extensions.md) · [Suivant](10-logiciels.md)

> **Dans ce chapitre :** marque-pages, extensions et outils Nautilus, dossiers masqués, icônes personnalisées, modèles de documents et tri des téléchargements.

Les composants Nautilus du dépôt sont centralisés dans [Ressources/Logiciels/Nautilus](../Ressources/Logiciels/Nautilus/README.md) ; ce chapitre décrit leur usage. **Sushi / Thumbnailer Sushi** fait partie de cette centralisation : son dossier *Thumbnailer Sushi* y est regroupé avec sa documentation et ses procédures.

- [9.1 Marque-pages](#91--marque-pages)
- [9.2 Actions complémentaires dans Nautilus](#92--actions-complémentaires-dans-nautilus)
- [9.3 Masquer des dossiers et personnaliser les icônes](#93--masquer-des-dossiers-et-personnaliser-les-icônes)
- [9.4 Modèles de documents](#94--modèles-de-documents)
- [9.5 Trieur automatique de Téléchargements](#95--trieur-automatique-de-téléchargements)
- [9.6 Aperçu et miniatures avec Sushi](#96--aperçu-et-miniatures-avec-sushi)
- [9.7 Supprimer l'effet pellicule des vignettes vidéo](#97--supprimer-leffet-pellicule-des-vignettes-vidéo)

## 9.1 — Marque-pages

Dans Nautilus, créer les marque-pages utiles :

- Le dossier `Dropbox`.
- Le serveur FTP donnant accès au SSD de la télévision Android : `ftp://192.168.31.68:2121`.
- L'accès administrateur au système de fichiers via `admin:///` : saisir cette adresse, ouvrir le système de fichiers puis ajouter un marque-page avec **Ctrl+D**.

## 9.2 — Actions complémentaires dans Nautilus

Les actions de terminal, d'administration, d'installation de paquets, d'ouverture dans OpenCode, de copie des chemins, de personnalisation des icônes de favoris et de recherche de dossiers récents/fréquents sont intégrées par **nautilus-tools-ogu**. Voir [12.1 — Intégrer Ptyxis à Nautilus](12-shell-terminal.md#121--intégrer-ptyxis-à-nautilus-et-aux-outils-cachyos) et le [README de Nautilus-tools](../Ressources/Logiciels/Nautilus/Outils/Nautilus-tools/README.md).

### Dossiers récents et fréquents

À l'ouverture de la recherche Nautilus (loupe, `Ctrl+F` ou frappe directe dans un dossier), **Nautilus-tools 0.8** affiche sous la loupe une liste de raccourcis : les cinq derniers dossiers ouverts et les cinq dossiers les plus visités selon zoxide, sans doublon. La liste se filtre au fil de la saisie et ne détourne pas le clavier : la recherche habituelle reste inchangée.

Un clic ouvre le dossier dans l'onglet courant ; un clic du milieu l'ouvre dans un nouvel onglet. Les dossiers visités sont également ajoutés à zoxide et deviennent accessibles avec `z` dans le terminal. `/tmp`, `/var/tmp`, `~/.cache`, les supports amovibles, `/mnt` et les montages GVfs sont exclus ; changer d'onglet ne compte pas comme une nouvelle visite. Sans zoxide, seuls les récents sont proposés. L'historique est conservé dans `~/.local/state/nautilus-tools-ogu/recent-folders` (50 entrées au maximum). Cette fonction nécessite Nautilus 47 ou plus récent (`slot.open-location`).

### Actions contextuelles Hide et Unhide

Deux petits scripts Python sont conservés dans [Extensions/Actions contextuelles](../Ressources/Logiciels/Nautilus/Extensions/Actions%20contextuelles/) : **Hide** préfixe les noms sélectionnés par un point pour les masquer ; **Unhide** retire ce point. Ils attendent les chemins des éléments en arguments. Leur intégration à une action personnalisée Nautilus dépend de la configuration locale du menu contextuel.


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

Pour **`word.docx`**, ouvrir Dactylo, créer un document vierge et l'enregistrer comme `/home/ogu/.Modèles/word.docx`. Un simple `touch word.docx`, proposé dans le mémo, créerait un fichier vide et non un document Word valide.

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

- `Archives/` : zip, 7z, rar, tar, gz, xz, zst et paquets Arch `.pkg.tar.*` (y compris les doublons renommés en `.pkg (1).tar.zst`).
- `Audio/` : mp3, flac, opus, ogg, m4a, wav…
- `Code/` : md, json, yaml, sh, fish, py, js, conf…
- `Documents/` : pdf, odt, docx, xlsx, pptx, txt et ebooks (epub, mobi, azw3, cbz, cbr…).
- `Pictures/` : jpg, png, webp, avif, svg…
- `ISOs/` : iso, img et fichiers associés.
- `Packages/` : AppImage, deb et rpm.

### Installation

Les blocs suivants utilisent la syntaxe **Bash** (`EOF`, accolades). Depuis Fish, lancer `bash` une fois, exécuter les blocs dans l'ordre, puis revenir à Fish avec `exit`.

```fish
bash
```

Créer les dossiers (sans modifier ceux qui existent déjà) :

```bash
mkdir -p "$HOME/Téléchargements"/{Archives,Audio,Code,Documents,Pictures,ISOs,Packages}
mkdir -p "$HOME/.local/bin" "$HOME/.config/systemd/user"
```

Copier le script conservé dans [`Ressources/Scripts/trieur`](../Ressources/Scripts/trieur)) :


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

### Migration d'une installation existante

Dans Fish, corriger le script installé, déplacer les fichiers déjà rangés dans `Ebooks/` vers `Documents/` sans écraser les doublons, puis supprimer `Ebooks/` une fois vide :

```fish
python3 -c '
from pathlib import Path
import shutil
import subprocess

home = Path.home()
script = home / ".local/bin/trieur"
source = script.read_text()
old = "move_file \"$file\" \"$DOWNLOADS/Ebooks\""
new = "move_file \"$file\" \"$DOWNLOADS/Documents\""
if old in source:
    updated = source.replace(old, new, 1)
    check = subprocess.run(["bash", "-n"], input=updated, text=True, capture_output=True)
    if check.returncode:
        raise SystemExit(check.stderr)
    script.write_text(updated)
elif new not in source:
    raise SystemExit("Règle Ebooks introuvable : script inchangé")

downloads = home / "Téléchargements"
ebooks = downloads / "Ebooks"
documents = downloads / "Documents"
if ebooks.is_dir():
    documents.mkdir(exist_ok=True)
    for item in ebooks.iterdir():
        target = documents / item.name
        number = 2
        while target.exists() or target.is_symlink():
            target = documents / f"{item.stem} ({number}){item.suffix}"
            number += 1
        shutil.move(str(item), str(target))
    ebooks.rmdir()
print("Ebooks fusionné dans Documents.")
'
```

Le service prendra en compte le script modifié au prochain déclenchement.

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

Attribuer manuellement les icônes **Teal** aux dossiers Archives, Audio, Code, Documents, Images, ISOs et Packages.


## 9.6 — Aperçu et miniatures avec Sushi

**Sushi** ouvre un aperçu rapide avec la barre d’espace dans Nautilus. Deux paquets complémentaires sont fournis dans [le dossier Thumbnailer Sushi](../Ressources/Logiciels/Nautilus/Thumbnailer%20Sushi/), avec un script d’installation.

- **Aperçus Sushi** : documents DOCX/ODT/RTF/Markdown, PDF avec rendu simplifié, présentations PPTX/ODP et tableurs XLSX/ODS.
- **Archives** : ZIP, TAR et variantes compressées, 7z, RAR et paquets Arch, listés sans extraction.
- **Miniatures Nautilus** : les fichiers texte et code ont un aperçu avec un bandeau indiquant leur nature ; les documents bureautiques, présentations et tableurs ont des fiches adaptées.
- **Coins arrondis** : le paquet complémentaire applique le rayon Nautilus/Adwaita à toutes les miniatures GNOME dans Nautilus, photos et PDF compris.

Le rendu sert à la consultation rapide, pas à remplacer l’application d’origine : les mises en page complexes, les images de diapositives et la mise en forme des tableurs ne sont pas reproduites. Les formats Office binaires anciens (`.doc`, `.xls`, `.ppt`) ne sont pas pris en charge.

### Installation et mise à jour

Les deux paquets et `installer.sh` sont conservés dans le sous-dossier *Sushi thumbnailer extra* du dossier Thumbnailer Sushi. Depuis ce sous-dossier, lancer le script **sans sudo** :

```bash
sh ./installer.sh
```

L’installeur vérifie les paquets, arrête Nautilus et l’aperçu Sushi, installe les deux paquets disponibles, vide automatiquement tous les caches de miniatures (y compris les échecs), puis relance Nautilus s’il était ouvert. **Aucune commande CLI de purge du cache n’est nécessaire.**

Pour simuler les opérations sans modifier le système :

```bash
sh ./installer.sh -s
```

Le paquet des coins arrondis est optionnel pour le script, mais requis pour appliquer le rayon Nautilus/Adwaita à toutes les miniatures. Les aperçus prennent en charge DOCX, ODT, RTF, Markdown, PDF simplifiés, PPTX/ODP, XLSX/ODS, archives ZIP/TAR/7z/RAR et paquets Arch. Les anciens formats Office binaires (`.doc`, `.xls`, `.ppt`) et les mises en page complexes ne sont pas pris en charge.


## 9.7 — Supprimer l'effet pellicule des vignettes vidéo

Nautilus superpose par défaut une décoration de pellicule (*filmholes*) aux miniatures vidéo. Le script maison **Nautilus sans pellicule** remplace cette ressource graphique par un PNG transparent, sans modifier le binaire Nautilus ni les fichiers système.

Le script est conservé dans [Ressources/Scripts/nautilus-sans-pellicule](../Ressources/Logiciels/Nautilus/Scripts/nautilus-sans-pellicule/) avec son README.

Depuis la racine du dépôt, se placer dans le dossier du script puis lancer :

```bash
cd Ressources/Logiciels/Nautilus/Scripts/nautilus-sans-pellicule
./supprimer-effet-pellicule.sh
```

Le mode par défaut est `install`. Il sauvegarde l'image originale dans `sauvegardes/filmholes.png` à côté du script, génère une image transparente de mêmes dimensions et configure `G_RESOURCE_OVERLAYS` pour les prochaines sessions GNOME. Après validation des étapes de préparation, il vide le cache des miniatures et ferme puis relance Nautilus. Il ne demande pas `sudo` et ne modifie pas les ressources intégrées au paquet Nautilus.

Commandes disponibles :

```bash
./supprimer-effet-pellicule.sh install
./supprimer-effet-pellicule.sh status
./supprimer-effet-pellicule.sh restore
./supprimer-effet-pellicule.sh help
```

Le mode `restore` retire la configuration et le PNG de remplacement, renouvelle le cache et relance Nautilus pour retrouver l'effet natif. La sauvegarde originale est conservée. Le mode `status` affiche l'état du réglage.

**À noter :** l'icône et les miniatures déjà en cache ne sont pas rechargées simplement parce que le script est présent dans le dépôt. La modification n'est appliquée qu'après exécution de `install`. Consulter le README du dossier avant utilisation pour les détails techniques et les prérequis.

---

[Accueil](../README.md) · [Précédent](08-gnome-extensions.md) · [Suivant](10-logiciels.md)
