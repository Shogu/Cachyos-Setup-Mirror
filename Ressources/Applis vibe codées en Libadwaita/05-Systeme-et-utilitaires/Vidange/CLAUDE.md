# CLAUDE.md — Vidange

Application GTK4/libadwaita en Python (PyGObject) de nettoyage système pour CachyOS / GNOME 51. ID : io.gitlab.shogu.Vidange. Interface et messages en français.

## Contraintes

- GTK4/libadwaita uniquement, widgets Adw natifs ; jamais de Qt.
- L'application ne tourne jamais en root. Les opérations privilégiées passent par helper/vidange-helper, installé dans /usr/lib/vidange/, lancé par pkexec avec l'action Polkit io.gitlab.shogu.Vidange.helper.
- Exécuter les commandes avec subprocess.run([...]) ou Popen([...]), sans shell.
- Pas d'analyse ni de prévisualisation des gros fichiers.
- Livrable : paquet Arch avec PKGBUILD et paquet compilé pour pacman -U.

## Architecture

- vidange/main.py : Adw.Application, actions app.about et app.quit.
- vidange/window.py : fenêtre, listes de paquets orphelins et récapitulatif.
- vidange/backend.py : estimations, recherches pacman, nettoyages utilisateur et appel du helper ; ne doit pas importer gi.
- helper/vidange-helper : helper privilégié, Python -I, entrée JSON sur stdin.
- data/ : lanceur, fichier desktop, politique Polkit et icônes.
- Réglages dans ~/.config/vidange/settings.json, sans schéma GSettings.

Tout travail bloquant doit passer par in_background(func, done, *args), puis revenir dans GTK avec GLib.idle_add. Les catégories sont orphans, pacman, aur, journal, home, dev et browsers. Les vues unneeded et explicit sont des vues de vérification et ne font pas partie de « Tout nettoyer ».

## Protocole du helper

Entrée : liste JSON d'au plus 10 étapes sur stdin. Sortie : une ligne JSON par étape, contenant id, ok et message.

| Action | Champs | Commande |
|---|---|---|
| remove | packages | pacman -Rns --noconfirm -- … |
| asdeps | packages | pacman -D --asdeps -- … |
| pacman-cache | mode : keep2, keep2-uninstalled, all | paccache -rk2 / -ruk0 / pacman -Scc |
| journal | size_mb (16 à 100000) | journalctl --vacuum-size=NM |

Les noms de paquets sont validés strictement, au plus 2000 noms. PATH=/usr/bin et LC_ALL=C. Toute nouvelle action privilégiée doit être documentée et valider ses paramètres. Ne jamais accepter de chemin ni de commande arbitraire.

## Pièges connus

- pacman -Scc --noconfirm répond « non » et ne vide rien : le helper envoie y puis y sur stdin.
- shelly purify standard --aur-cache vide tout ~/.cache/Shelly, y compris PKGBUILD, sources et historique git ; le nettoyage direct du dossier a le même effet.
- L'estimation keep2-uninstalled combine -k2, -uk0 et -uk2 pour éviter le double comptage.
- pacman -Qi est analysé avec LC_ALL=C.
- pacman -Qtdq renvoie 1 lorsqu'il n'y a rien ; ce n'est pas une erreur.
- profile-cleaner libère peu d'espace estimable ; le récapitulatif mesure avant/après.
- Adw.Spinner demande libadwaita ≥ 1.6.
- Les textes provenant de pacman sont affichés avec use_markup=False.

## Construire et vérifier

~~~fish
python3 -m py_compile vidange/*.py helper/vidange-helper data/vidange
python3 -m pyflakes vidange/ helper/vidange-helper
makepkg -si
~~~

Pour une nouvelle version, mettre à jour pkgver dans PKGBUILD et VERSION dans main.py.

## Icône

Bidon d'huile rouge à remplir ; huile et jauge ambre, formes simples, volume indiqué par une épaisseur sombre en bas. La version symbolique 16 px reprend le dessin en monochrome.
