# Icônes Ogu

Mes icônes maison pour GNOME — couleur **et** symboliques — dans un seul fichier :
**`icones-ogu.pyz`**. Rien à installer.

## Lancer

```
python3 icones-ogu.pyz
```

(Il lui faut Python et GTK4, présents d'office sur CachyOS GNOME ;
sinon : `sudo pacman -S python-gobject gtk4`.)

## La fenêtre

Une ligne par appli installée : son icône **actuelle** et l'icône **proposée**, en couleur et
en symbolique. Celles déjà en place sont décochées.

Menu **Actions** (chaque action demande confirmation) :

| Action | Ce qu'elle fait |
|---|---|
| Appliquer | met les icônes cochées en place (l'état d'avant est mis de côté) |
| Restaurer | remet les icônes comme avant le dernier « Appliquer » |
| Remettre mes lanceurs faits main | Upgrade, etc. — seulement ceux qui manquent |
| Exporter | crée un nouveau `icones-ogu-DATE.pyz` qui contient aussi mes imports |
| Recharger la session | déconnexion, pour que GNOME affiche les nouvelles icônes |

**Modifier / importer** : boutons *Couleur…* et *Symbolique…* sur chaque ligne (le fichier
est renommé tout seul). Case *Afficher toutes les applis installées* pour en habiller une
nouvelle. *Oublier l'import* revient à l'icône d'origine.

## Jour de réinstallation

1. Installer mes applis.
2. `python3 icones-ogu.pyz` → **Actions › Remettre mes lanceurs faits main**
3. **Actions › Appliquer**
4. **Actions › Recharger la session**

## Après avoir importé de nouvelles icônes

**Actions › Exporter**, puis remplacer `icones-ogu.pyz` de ce dépôt par le fichier créé
(en le renommant `icones-ogu.pyz`).

**Limite :** cet outil gère les icônes des applications, pas les icônes PLACES des dossiers personnels.
