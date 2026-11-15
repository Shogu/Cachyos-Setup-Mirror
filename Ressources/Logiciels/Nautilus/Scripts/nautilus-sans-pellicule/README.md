# Nautilus sans pellicule — supprimer l'effet « filmholes » sur les vignettes vidéo

Script Bash autonome qui supprime l'effet « pellicule / trous de film »
(*filmholes*) que **Nautilus (Fichiers)** superpose sur les vignettes des
vidéos.

- ✅ **Sans sudo**, sans modifier les fichiers système, **sans installation**.
- ✅ **Sans rechargement d'icônes** tant que le script n'est pas exécuté.
- ✅ **Réversible** : tout est annulé avec le mode `restore`.
- ✅ **Sauvegarde** de l'image d'origine conservée dans ce dossier.

---

## 📂 Contenu du dossier

| Élément | Rôle |
|---|---|
| `supprimer-effet-pellicule.sh` | Le script (install / restore / status) |
| `sauvegardes/filmholes.png` | Sauvegarde de l'image d'origine (créé à l'installation) |
| `README.md` | Ce fichier |

> La sauvegarde est créée automatiquement **dans ce dossier**
> (`sauvegardes/filmholes.png`). L'image d'origine dans le système n'est
> **jamais modifiée**.

---

## 🚀 Utilisation

Depuis ce dossier :

```bash
./supprimer-effet-pellicule.sh            # install (défaut)
./supprimer-effet-pellicule.sh install    # équivalent
./supprimer-effet-pellicule.sh restore    # annuler (retour à l'effet d'origine)
./supprimer-effet-pellicule.sh status     # état de la configuration
./supprimer-effet-pellicule.sh help       # aide
```

> ⚠️ Le mode `install` ferme et relance les fenêtres de Nautilus et vide le
> cache des vignettes (`~/.cache/thumbnails`). Cela ne se produit **que si
> toutes les étapes précédentes ont réussi**.

---

## ⚙️ Ce que fait le script (`install`)

1. **Sauvegarde** l'image *filmholes* d'origine (`sauvegardes/filmholes.png`),
   extraite du binaire Nautilus ;
2. **Crée** un PNG entièrement transparent aux dimensions exactes de
   l'original ;
3. **Configure** la variable `G_RESOURCE_OVERLAYS` (idempotent, sans doublons)
   dans :
   - `~/.config/environment.d/60-nautilus-sans-pellicule.conf` (sessions
     modernes systemd / Wayland),
   - `~/.profile` (login shell, secours) ;
4. **Vérifie** que tout est en place, puis seulement :
   - vide le cache des vignettes,
   - relance Nautilus.

L'effet disparaît immédiatement et reste effectif aux sessions suivantes.

### Modes

- **install** : applique la suppression (décrit ci-dessus).
- **restore** : supprime la config, la copie transparente, vide le cache et
  relance Nautilus → l'effet d'origine revient. La sauvegarde est conservée.
- **status** : affiche l'état (PNG transparent, config, sauvegarde).

---

## 🧰 Prérequis

- `bash`
- `python3` (standard sur toute distro de bureau)
- Nautilus installé (`/usr/bin/nautilus`)

Testé sur **CachyOS — GNOME Nautilus 51.1**.

> Note technique : sur les builds récents (la ressource est compilée dans
> l'ELF et l'outil `gresource` est souvent absent), le script extrait le PNG
> embarqué directement du binaire par balayage. Sur les distros où `gresource`
> existe, il est utilisé en priorité.

---

## 🔄 Annuler / désinstaller

```bash
./supprimer-effet-pellicule.sh restore
```

Ensuite, supprimez simplement ce dossier. La configuration ajoutée dans
`~/.config/environment.d/` et `~/.profile` est retirée par `restore`.
