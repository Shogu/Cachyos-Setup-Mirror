# Mail — mail-postcard

**Mail (`mail-postcard`)** est le client de messagerie retenu pour ce setup, compilé avec **Claude** depuis les sources de [Postcard](https://github.com/gxanshu/postcard). Il ne s’agit pas d’une application créée de zéro par vibe coding : la base upstream est conservée, avec quelques ajouts : **recherche et affichage des pièces jointes**, **contraste entre les panneaux** et **francisation complète**.

## Paquet et installation

Le paquet Arch compilé avec Claude est à ajouter manuellement dans ce dossier. Sa version exacte n’est pas précisée ici.

Depuis le dossier contenant le paquet, installer le fichier correspondant puis lancer Mail :

```fish
set paquets_mail (find . -maxdepth 1 -type f -name 'mail-postcard*.pkg.tar.zst')
if test (count $paquets_mail) -eq 1
    sudo pacman -U "$paquets_mail[1]"
else
    printf '%s\n' 'Conserver un seul paquet Mail dans ce dossier avant installation.'
end
```

Après une installation réussie :

```fish
mail-postcard
```

Voir [10.1.4 — Messagerie : Mail](../../../docs/10-logiciels.md#1014--messagerie--mail).
