# Showtime — correctifs locaux du lecteur GNOME

Ce dossier conserve les **correctifs locaux** du lecteur vidéo GNOME **Showtime** (GTK4 / libadwaita, écrit en Python). Ils ne modifient ni la version du paquet ni son comportement de base de façon destructrice :

- un correctif **comportement clavier** (sauts proportionnels + suppression du fichier en cours) ;
- un correctif **chargement automatique des sous-titres externes** (SRT).

Contenu du dossier :

| Fichier | Rôle |
| --- | --- |
| `window.py` | Fichier `window.py` **complet corrigé** (clavier + SRT), aligné sur la **version actuellement installée**. C’est la référence pour un `mv` / `cp` de réinstallation. |
| `patch_showtime.py` | Script de **ré-injection des deux correctifs** (sous-titres + clavier) — additif, idempotent, basé sur la version neuve du paquet. |
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
pkexec cp "Ressources/Logiciels/Players/Showtime/window.py" (pacman -Ql showtime | string match -r '\S+/widgets/window\.py$')
```

Cette commande remplace le `window.py` installé par le paquet par la version corrigée courante (clavier **+** SRT).

---

## 4. Mise à jour — REPRODUIRE le correctif après une maj de Showtime

Après `sudo pacman -Syu`, le paquet **réécrit** `window.py` et **efface les deux correctifs**.

> ⚠️ **Ne jamais poser l’ancien `window.py` entier** sur le nouveau : le fichier de ce dossier reflète la version installée aujourd’hui ; une maj fait évoluer l’API / les connecteurs / les actions. Régresser tout le fichier casse le lancement de Showtime. **Ré-injecter uniquement les correctifs** sur le `window.py` neuf.

### 4.1 Ré-injection automatique des DEUX correctifs (script unique)

Un **seul script** ré-applique tout (sous-titres **+** clavier) :

```fish
pkexec python3 "Ressources/Logiciels/Players/Showtime/patch_showtime.py"
```

Il fonctionne en **transformations ciblées ancrées** sur le fichier d’origine :
- il prend pour base la **version NEUVE du paquet** (extraite de `/var/cache/pacman/pkg/showtime-*.pkg.tar.zst` s’il y est, sinon le fichier installé), donc il n’utilise jamais un ancien `window.py` écrasé ;
- pour chacune des 9 transformations, il vérifie que l’**ancrage** existe **une seule fois** ; sinon il **s’arrête proprement** (version trop différente) sans rien écrire ;
- il ignore chaque transformation déjà présente (**idempotent**) — relançable sans risque ;
- il **sauvegarde l’original** `window.py` → `window.py.pre-ogu.bak` (une seule fois) avant la première application ;
- le résultat obtenu est **strictement identique** au `window.py` corrigé de référence (vérifiable par `diff`, cf. §6).

`pkexec` ouvre le dialogue d’autorisation graphique (pas de mot de passe à taper dans le terminal de l’agent).

### 4.2 Si le script refuse (ancrage absent)

Cela signifie que la nouvelle version de Showtime a déplacé/renommé l’un des points d’ancrage (`self.play.props.uri = uri`, `def teardown_playback`, `def _create_actions`, `backwards`/`forwards`, volume…). Dans ce cas :
1. regarde **quel ancrage échoue** (le script l’indique) ;
2. ouvre le `window.py` neuf pour localiser le point équivalent et **recaler la transformation concernée** dans `patch_showtime.py` ;
3. teste le script sur une copie (`cp`), vérifie avec `diff` + `python3 -m py_compile`, puis applique ;
4. **actualise ce dossier** (voir §6) pour qu’il reste aligné.

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
- **Sauvegarde locale** : `patch_showtime.py` conserve l’original sous `window.py.pre-ogu.bak` à côté du fichier système — il n’a pas vocation à être versionné.
- **Ne pas commiter** le `__pycache__`.
