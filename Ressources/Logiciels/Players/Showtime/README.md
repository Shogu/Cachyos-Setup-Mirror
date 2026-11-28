# Showtime — correctifs locaux du lecteur GNOME

Ce dossier conserve les **correctifs locaux** du lecteur vidéo GNOME **Showtime** (GTK4 / libadwaita, écrit en Python). Ils ne modifient ni la version du paquet ni son comportement de base de façon destructrice :

- un correctif **comportement clavier** (sauts proportionnels + suppression du fichier en cours) ;
- un correctif **chargement automatique des sous-titres externes** (SRT).

Contenu du dossier :

| Fichier | Rôle |
| --- | --- |
| `window.py` | Fichier `window.py` **complet corrigé** (clavier + SRT), aligné sur la **version actuellement installée**. C’est la référence pour un `mv` / `cp` de réinstallation. |
| `patch_showtime.py` | Script de **ré-injection** de la partie sous-titres (additif, idempotent) — utilisé après une mise à jour de Showtime. |
| `README.md` | Ce mode d’emploi. |

---

## 1. Correctif — comportement clavier

- **← / →** : saut d’environ **1 %** de la durée totale de la vidéo (minimum 5 s).
- **↑ / ↓** : saut d’environ **5 %** de la durée totale de la vidéo (minimum 30 s).
- **Maj + ← / →** : saut fixe de **10 s** pour l’ajustement fin.
- **Supr** : déplace la vidéo en cours vers la **corbeille** (après confirmation).
- **Volume** : déplacé sur `Ctrl + ↑ / ↓` (les flèches ↑/↓ servent aux sauts de 5 %).

Les sauts sont calculés par proportion de la durée du média (avec un minimum en secondes), pour s’adapter aux vidéos courtes comme aux longues.

**Supr** ne fonctionne que sur les **fichiers locaux** : ouvre un dialogue « Déplacer vers la corbeille ? » ; le fichier part à la corbeille (récupérable) et Showtime se ferme. Un fichier distant (réseau) affiche « uniquement les fichiers locaux ».

---

## 2. Correctif — sous-titres automatiques (SRT)

Par défaut, Showtime **n’affiche pas** les fichiers `.srt` externes dans son menu : il faut passer par le bouton **« Ajouter un fichier de sous-titres… »** → le sous-titre ne redevient visible qu’à la lecture.

Le correctif fait que, **à l’ouverture d’une vidéo**, Showtime cherche à côté d’elle un fichier de sous-titres nommé exactement :

1. `video.fr.srt` (prioritaire) — c’est ce que produisent par exemple des sous-titres français générés à côté des vidéos ;
2. `video.srt` (repli, mode « sidecar » classique).

dès qu’il en trouve un, il le **charge automatiquement**, sans passer par le menu ni le bouton. La détection suit le nom / chemin de la vidéo réellement ouverte (symlink résolu).

Mécanique : dans `play_video()`, la méthode `_try_auto_subtitles(uri)` branche le fichier trouvé via `self.play.props.suburi` — exactement le même mécanisme interne que « Ajouter un fichier de sous-titres », donc aucune autre modification que le chargement.

---

## 3. Installation — from scratch / fresh reinstall

Le plus simple est de poser le fichier **complet corrigé** :

```fish
sudo cp "Ressources/Logiciels/Players/Showtime/window.py" (pacman -Ql showtime | string match -r '\S+/widgets/window\.py$')
```

Cette commande remplace le `window.py` installé par le paquet par la version corrigée courante (clavier **+** SRT).

---

## 4. Mise à jour — REPRODUIRE le correctif après une maj de Showtime

Après `sudo pacman -Syu`, le paquet **réécrit** `window.py` et **efface les deux correctifs**.

> ⚠️ **Ne jamais poser l’ancien `window.py` entier** sur le nouveau : le fichier de ce dossier reflète la version installée aujourd’hui ; une maj fait évoluer l’API / les connecteurs / les actions. Régresser tout le fichier casse le lancement de Showtime. **Ré-injecter uniquement les correctifs** sur le `window.py` neuf.

### 4.1 Partie sous-titres (sûre, ré-applicable par script)

Cette partie est **purement additive** (ajout d’un `import` + d’un appel + d’une méthode, aucun code existant remplacé). Elle se ré-applique donc proprement sur n’importe quelle version récente, via le script :

```fish
pkexec python3 "Ressources/Logiciels/Players/Showtime/patch_showtime.py"
```

Le script (`pkexec` ouvre le dialogue d’autorisation graphique) :
- **ne fait rien** s’il est déjà appliqué (idempotent) ;
- **sauvegarde l’original** `window.py` → `window.py.pre-srt.bak` (une seule fois) avant la première application ;
- vérifie chaque **ancrage** (`import json`, `self.play.props.uri = uri`, `def teardown_playback`) ; si un ancrage n’est pas trouvé (version trop différente), il **s’arrête proprement** au lieu d’écrire un fichier incohérent ;
- n’écrit que si tous les ancrages sont présents.

### 4.2 Partie clavier

Le correctif clavier remplace des actions existantes (`backwards` / `forwards`, raccourcis volume, ajout de `Supr`), donc il ne s’auto-ré-injecte pas par script. Le ré-appliquer manuellement sur le `window.py` neuf, en réinsérant :

- les méthodes `_seek_by()` et `_seek_by_percent()` (sauts par % + saut minimal) et `_delete_current_video()` (corbeille avec confirmation), dans la classe `Window`, juste avant `_create_actions()` ;
- dans `_create_actions()` : les actions proportionnelles (remplacement de `backwards`/`forwards`) et l’action `delete-file` + le raccourci `Supr` ;
- dans `play_video()` : l’activation de `delete-file`.

Si le script 4.1 s’arrête sur un ancrage absent (version trop récente) ou si le clavier diffère, **mets-toi à jour** : rapproche-toi du `window.py` neuf, ré-injecte les blocs par-dessus, teste, puis **actualise ce dossier** (voir §6) pour qu’il reste aligné.

---

## 5. Vérification

```fish
grep -n "_try_auto_subtitles"     /usr/lib/python3.14/site-packages/showtime/widgets/window.py
grep -n "_seek_by_percent\|_delete_current_video" /usr/lib/python3.14/site-packages/showtime/widgets/window.py
```

- la 1ʳᵉ retrouve le **chargement automatique des sous-titres** ;
- la 2ᵉ retrouve le **correctif clavier**.

Si le chemin diffère, retrouve le chemin fourni par le paquet :

```fish
pacman -Ql showtime | string match -r '\S+/widgets/window\.py$'
```

---

## 6. Maintenance / mise au propre de ce dossier

- **Trace de la version** : `window.py` doit rester **identique à celui installé + corrigé**. Après une maj, une fois les correctifs ré-appliqués et testés, rafraîchis-le :
  ```fish
  cp "Ressources/Logiciels/Players/Showtime/window.py" (pacman -Ql showtime | string match -r '\S+/widgets/window\.py$')  # sens inverse ci-dessous
  ```
  Attention au sens : on copie le fichier **installé neuf + correctifs** vers le dépôt :
  ```fish
  cp (pacman -Ql showtime | string match -r '\S+/widgets/window\.py$') "Ressources/Logiciels/Players/Showtime/window.py"
  ```
- **Sauvegarde locale** : `patch_showtime.py` conserve l’original sous `window.py.pre-srt.bak` à côté du fichier système — il n’a pas vocation à être versionné.
- **Ne pas commiter** le `__pycache__`.
