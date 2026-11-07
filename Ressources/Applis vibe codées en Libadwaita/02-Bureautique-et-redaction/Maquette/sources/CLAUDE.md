# CLAUDE.md — Maquette

Application GTK4/libadwaita en Python (PyGObject) qui assemble des PDF.
Cible : CachyOS, GNOME 51. Interface, messages, commentaires et doc **en
français** ; une seule version cible, pas de code défensif multi-versions.

## Architecture

```
maquette/modele.py       données pures : Page, Op, Source, géométrie. Aucun GTK, aucun PyMuPDF.
maquette/moteur.py       le seul fil qui touche PyMuPDF : ouverture, rendu, opérations, écriture.
maquette/conversion.py   images → page PDF (Pillow, repli sur les chargeurs GTK).
maquette/grille.py       grille de miniatures, glisser-déposer, menu contextuel.
maquette/vuepage.py      page en grand (outils Recadrer et Texte) et page d'aperçu du résultat.
maquette/dialogues.py    petits dialogues (mot de passe, images, issues du recadrage, texte).
maquette/preferences.py  AdwPreferencesDialog lié à GSettings.
maquette/reglages.py     accès GSettings + instantané passé au moteur.
maquette/fenetre.py      document courant, historique, actions, enregistrement.
maquette/application.py  AdwApplication, raccourcis, à-propos.
data/                    schéma GSettings, .desktop, metainfo, icônes hicolor.
tests/test_moteur.py     tests du moteur, sans interface.
tests/scenario.py        scénario d'interface sous Xvfb, avec captures.
tests/compat.py          bouchons pour le conteneur de test uniquement (libadwaita 1.5).
```

## Règles à respecter

- **Le moteur possède PyMuPDF.** PyMuPDF n'est pas sûr entre fils sur un même
  document : tout passe par `Moteur.soumettre`, qui exécute dans le fil du
  moteur puis rappelle l'interface via `GLib.idle_add`. L'interface ne touche
  jamais un `pymupdf.Document`.
- **`construire_apercu()` repasse par `construire()` et `imposer()`,** donc
  l'aperçu montre le fichier tel qu'il sera écrit. Le document d'aperçu occupe
  la source réservée `APERCU` (-1), libérée à chaque nouvel aperçu et à la
  fermeture : ne pas lui donner un identifiant issu du compteur des fichiers.
- **`page_unique()` sert à l'aperçu ET à l'enregistrement.** C'est ce qui
  garantit que la grille montre exactement ce qui sera écrit. Ne pas créer un
  second chemin de rendu.
- **Les `Op` sont immuables et hashables.** L'historique n'est qu'une liste de
  tuples de pages, et `cle_contenu()` sert de clé au cache de rendu. Ne pas y
  mettre de champ non hashable.
- **Repères géométriques.** Les `Op` sont exprimées dans l'espace *non tourné*
  de la page intermédiaire (après les opérations précédentes), origine en haut
  à gauche. `vers_non_tourne()` est vérifié contre `Page.derotation_matrix` de
  PyMuPDF par un test : ne pas le modifier sans relancer ce test.
- **`insert_textbox` dessine aussi ce qui déborde** et renvoie un reste
  négatif. Les essais de mise en page ont donc lieu sur une page jetable, puis
  le texte est écrit une seule fois. Dessiner directement laisserait des
  calques de texte coupé superposés.
- **`Gdk.RGBA(red=…, green=…)` ignore ses arguments** et renvoie du noir
  transparent : tout ce qui est peint avec devient invisible. Toujours passer
  par `_rgba()` de `vuepage.py`, qui affecte les champs.
- **Suppression réelle.** `_retirer()` passe par les annotations de caviardage
  (`add_redact_annot` + `apply_redactions`) : le texte est retiré du flux, pas
  recouvert. C'est la raison d'être de l'outil pour les corrigés ; ne pas le
  remplacer par un rectangle blanc.
- **Écriture atomique.** `enregistrer()` écrit dans un fichier temporaire du
  même dossier puis `os.replace()` : l'original n'est remplacé qu'une fois le
  nouveau complet. Les droits du fichier existant sont repris.
- **Icônes.** Les icônes d'actions vivent dans `data/icons/hicolor/scalable/actions`.
  Un dossier plat n'est **pas** un thème valide : `add_search_path` attend le
  dossier qui contient `hicolor/`. Installées sous `/usr/share/icons/hicolor`,
  elles sont trouvées sans rien déclarer.
- **Widgets GTK4/libadwaita natifs seulement.** `Adw.AlertDialog` et
  `Adw.PreferencesDialog`, jamais `Gtk.Dialog` (déprécié).
- **Nettoyage.** Chaque classe libère ce qu'elle crée : `Grille.do_dispose`
  retire sa source de défilement et déparente son menu. Pas de drapeau
  `_destroyed`.
- **Une seule confirmation de fermeture à la fois.** `_sur_fermeture` garde la
  boîte en cours dans `_confirmation` : sans cela, une deuxième demande de
  fermeture refermait la confirmation qu'elle venait de créer. Si un autre
  dialogue est ouvert, il est refermé puis la confirmation est présentée au
  tour de boucle suivant, sinon elle ne s'affiche pas.
- **Lignes de 200 caractères au maximum.** Pas de commentaire qui paraphrase
  le code.

## Choix déjà tranchés

- **PyMuPDF plutôt que pikepdf + Poppler** : seul lui fait d'un bloc le rendu,
  le caviardage réel, l'imposition et la compression. Il pèse environ 60 Mo de
  plus ; l'application n'étant pas distribuée, sa licence AGPL ne gêne pas.
- **Pas d'insertion de ODT/DOCX/RTF.** Une version antérieure passait par le
  convertisseur HTML du paquet `thumbnailer-docx-nautilus-sushi` : la mise en
  page n'était qu'approchée. Abandonné ; l'application demande un export PDF.
- **Pas de modification du texte existant.** Hors de portée, peu fiable.
- **Un seul outil de recadrage** à trois issues (`ROGNER`, `EFFACER`,
  `SUPPRIMER` dans `modele.ISSUES_RECADRAGE`), plutôt que trois outils séparés.

## Construire et tester

```sh
python3 -m pytest -q tests/test_moteur.py           # moteur, sans interface
xvfb-run -a -s "-screen 0 1280x860x24" \
  python3 tests/scenario.py <dossier d'essai> <dossier des captures>
bash build.sh                                       # → maquette-<ver>-any.pkg.tar.zst
```

- Le scénario d'interface vérifie le chargement, le glisser-déposer, le
  recadrage, le texte, l'enregistrement et le livret, et laisse des captures à
  regarder. **Les regarder** : plusieurs défauts (couleurs invisibles, icônes
  absentes) ne se voient que là.
- Le conteneur de test a libadwaita 1.5 et pas de lecteur SVG par défaut.
  `tests/compat.py` comble les manques d'API ; pour des captures fidèles,
  installer le lecteur SVG de gdk-pixbuf, sinon toutes les icônes symboliques
  s'affichent en « image manquante ».
- Sans gestionnaire de fenêtres, `Gtk.Window.close()` n'émet pas
  `close-request` de façon fiable et un dialogue présenté juste après peut se
  refermer seul. Le scénario émet donc `close-request` et vérifie que la
  fermeture est *retenue* ; l'affichage de la confirmation se vérifie à l'œil
  sur un vrai bureau.
- `tests/compat.py` n'est **jamais** installé et ne doit pas être importé par
  l'application.

## À chaque version

Incrémenter `VER`/`REL` dans `build.sh`, la ligne `<release>` du metainfo, et
`VERSION` dans `maquette/__init__.py`.
