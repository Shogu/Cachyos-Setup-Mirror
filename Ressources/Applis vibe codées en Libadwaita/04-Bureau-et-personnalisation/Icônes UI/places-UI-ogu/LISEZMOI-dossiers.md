# Dossiers Ogu

Mes dossiers, leurs icônes et les dossiers masqués, dans un seul fichier :
**`dossiers-ogu.pyz`**. Rien à installer.

```
python3 dossiers-ogu.pyz
```

## La fenêtre

Une ligne par dossier du plan (chemin depuis ~) : icône **actuelle** et icône **proposée**.
Plus bas, les dossiers **à masquer** (Bureau, Documents, Modèles, Public) : renommés en `.Nom`
comme `.Bureau`, et `~/.config/user-dirs.dirs` est mis à jour pour que GNOME ne les recrée pas.

- **Choisir…** : les icônes en vignettes, un clic pour changer l'icône d'un dossier.
- **Standard** : revenir à l'icône normale de Fichiers.
- **Ajouter un dossier…** / **Retirer la ligne** : modifier le plan.
- **Importer des icônes…** : pour en ajouter une ; renommée `dossier-xxx` au passage.

Menu **Actions** (chaque action demande confirmation) :

| Action | Ce qu'elle fait |
|---|---|
| Appliquer | crée les dossiers manquants, pose les icônes, masque les dossiers cochés (l'état d'avant est mis de côté) |
| Restaurer l'état d'avant | remet tout comme avant le dernier « Appliquer » |
| Exporter | crée un nouveau `dossiers-ogu-DATE.pyz` avec mon plan et mes icônes à jour (imports compris) |
| Relancer Fichiers | pour qu'il relise les icônes |

Les dossiers de Dropbox ne sont pas créés (c'est Dropbox qui le fait) : lancer l'appli une fois
Dropbox synchronisé.

## Les icônes

Seulement celles que j'utilise (16), renommées `dossier-xxx.svg` et recopiées dans
`~/.local/share/dossiers-ogu/icones` : c'est là que pointent les icônes des dossiers.
Les noms d'origine sont dans `correspondances.txt` (dans le .pyz).
