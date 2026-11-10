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
- vidange/taches.py : in_background(func, done, *args).
- vidange/lignes.py : rangee(classe, **props) crée une Adw.ActionRow/ExpanderRow en texte brut (use_markup=False réglé avant le texte).
- vidange/bilan_page.py : page « Bilan après une mise à jour » (options, applis à lancer, dossiers d'AppImage, résultats).
- vidange/bilan/ : bilan sans Gtk (Gio seulement, pour D-Bus et les .desktop), utilisable en CLI par `vidange --bilan`.
  - commun.py : niveaux OK/INFO/A_CORRIGER/CASSE, Constat, Element, réglages ~/.config/vidange/bilan.json, état ~/.local/state/vidange/bilan.json.
  - paquets.py : inventaire pacman -Qm/-Qlm/-Qi, ldd, fichiers sous /usr/lib/python3.X, appel de sources.py.
  - sources.py : syntaxe Python (compile + SyntaxWarning) et API GTK/libadwaita dépréciées.
  - lancement.py : lancement de quelques secondes dans une session de processus à part (killpg), relevé des messages ; AppImage.
  - extensions.py : org.gnome.Shell.Extensions (ListExtensions, ShellVersion), journal du Shell, shell-version.
  - rapport.py : faire_bilan(), versions suivies, element_python(), texte du rapport, bilan_conseille().
  - cli.py : `vidange --bilan [--sans-lancement] [--delai S]`, code 0/1/2.
- helper/vidange-helper : helper privilégié, Python -I, entrée JSON sur stdin.
- helper/vidange-bilan-hook + data/vidange-bilan.hook : hook pacman PostTransaction ; retient les versions dans /var/lib/vidange/versions.json, écrit /var/lib/vidange/bilan-conseille.json quand une branche change, notifie les sessions graphiques (runuser + gdbus).
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
- Les textes provenant de pacman sont affichés en texte brut avec rangee() : passé au constructeur, use_markup=False arrive trop tard.
- Le bilan ne lance jamais une appli déjà ouverte (NameHasOwner sur son identifiant) et n'a besoin d'aucun droit root.
- Gtk.StyleContext.add_provider_for_display() n'est pas déprécié : sources.py ne le signale pas.
- Le hook ne notifie que pour un changement de branche (gnome-shell et nautilus : 1re composante ; les autres : deux premières).

## Construire et vérifier

~~~fish
python3 -m py_compile vidange/*.py vidange/bilan/*.py helper/vidange-helper helper/vidange-bilan-hook data/vidange
python3 -m pyflakes vidange/ helper/vidange-helper
makepkg -si
~~~

Pour une nouvelle version, mettre à jour pkgver dans PKGBUILD et VERSION dans main.py.

## Icône

Bidon d'huile rouge à remplir ; huile et jauge ambre, formes simples, volume indiqué par une épaisseur sombre en bas. La version symbolique 16 px reprend le dessin en monochrome.
