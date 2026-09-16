Frontend vibe codé libadwaita pour les services systemd.

Installation :
```fish
sudo pacman -U ./systemd-gui-0.3.0-1-any.pkg.tar.zst
```

Désinstallation :
```fish
sudo pacman -Rns systemd-gui
```





systemd

systemd est une application native GTK4/libadwaita pour inspecter et
administrer les services systemd depuis une interface GNOME simple et
standardisée.

L’application est un frontend graphique : elle conserve systemctl et
journalctl comme sources de vérité et ne réimplémente pas le gestionnaire
systemd. Elle ne constitue pas un service systemd supplémentaire et ne
modifie pas le contenu des fichiers d’unités.

Version actuelle : 0.3.0
Dernière mise à jour de ce document : 15 septembre 2026

Origine du projet

Le projet avait d’abord été nommé Factotum, puis a été renommé
systemd, car son rôle est précisément de fournir une interface graphique
aux outils natifs de systemd.

Fonctions

Périmètres disponibles

services du système, via systemctl classique ;

services de l’utilisateur, via systemctl --user ;

changement de périmètre depuis le sélecteur supérieur de la barre latérale ;

actualisation automatique toutes les cinq secondes lorsque aucune action
n’est en cours.

Le terme « Périmètre » a été retiré de l’interface : seul le sélecteur
« Système / Utilisateur » reste visible.

Liste et filtres

La barre latérale propose les catégories suivantes :

Tous les services ;

En cours ;

Arrêtés ;

En échec ;

Masqués ;

Activés ;

Désactivés ;

Introuvables, pour les unités fantômes encore connues de systemd.

Chaque ligne affiche :

le nom de l’unité ;

sa description officielle ;

son état d’exécution ;

son état d’activation ;

une icône symbolique Adwaita adaptée à son état.

La ligne sélectionnée est signalée par :

une fine barre bleue à gauche ;

un fond bleu-gris léger ;

un arrière-plan de sélection compatible avec le thème Adwaita.

Les états sont aussi présentés sous forme de pastilles :

vert : actif ;

gris : arrêté ;

orange : masqué ou introuvable ;

rouge : en échec.

Recherche

La recherche est effectuée en temps réel sur le nom et la description du
service.

Elle fonctionne même si la catégorie sélectionnée est « En cours »,
« Arrêtés », etc. ; une recherche explicite devient globale.

Le nombre de résultats apparaît à droite du champ.

Le bouton « Effacer » apparaît uniquement lorsqu’une recherche est active.

Effacer la recherche rétablit le filtre de catégorie sélectionné.

Vue de détail

Après sélection d’un service, le panneau droit affiche toujours son état
actuel, indépendamment de l’onglet choisi :

état d’exécution (active, inactive, failed, etc.) ;

sous-état (running, dead, listening, etc.) ;

état d’activation (enabled, disabled, static, masked, etc.) ;

source réelle du fichier d’unité, lorsque systemd en fournit une.

Les quatre onglets conservés sont :

Vue d’ensemble

Statut

Fichier d’unité

Journal

L’ancien onglet Propriétés a été supprimé : ses informations faisaient
double emploi avec Vue d’ensemble.

Les icônes de la barre inférieure utilisent des noms symboliques Adwaita
valides avec des replis automatiques. Lorsqu’une icône n’existe pas dans le
thème, elle est masquée ou remplacée par un symbole standard plutôt que par
une image cassée.

Vue d’ensemble

La vue d’ensemble présente :

la description officielle fournie par systemd ;

le preset ;

le PID principal ;

le résultat de la dernière exécution ;

l’utilisateur et le type du service ;

la date de démarrage ;

les drop-ins ;

la documentation déclarée par l’unité ;

l’état général du service ;

un bouton Afficher permettant d’ouvrir directement l’onglet Statut.

Dépendances et relations

Une section Dépendances regroupe les propriétés exposées par
systemctl show, notamment :

Requires et RequiredBy ;

Wants et WantedBy ;

After et Before ;

Conflicts et ConflictedBy ;

PartOf et BindsTo ;

Triggers et TriggeredBy ;

OnFailure ;

ReferencedBy.

Les relations sont affichées avec leur nombre et la liste des unités
concernées. Elles restent consultatives : les fichiers des unités référencées
ne sont jamais supprimés par l’action de nettoyage d’un service.

Actions disponibles

Les actions sont placées dans une barre fixe toujours visible au-dessus des
onglets :

Démarrer → systemctl start ;

Arrêter → systemctl stop ;

Redémarrer → systemctl restart ;

Recharger → systemctl reload ;

Activer maintenant → systemctl enable --now ;

Désactiver maintenant → systemctl disable --now ;

Masquer → systemctl mask ;

Démasquer → systemctl unmask ;

Supprimer complètement → nettoyage contrôlé décrit plus bas.

L’action principale mise en avant suit l’état réel du service :

service arrêté : Démarrer est mis en avant ;

service actif : Arrêter est mis en avant ;

service masqué : Démasquer est mis en avant.

Les actions incompatibles avec une unité masquée sont désactivées dans
l’interface. La décision finale reste toujours celle de systemd et de
systemctl.

Les opérations sensibles — arrêt, masquage, désactivation et suppression —
affichent une confirmation avant exécution.

Statut et fichier d’unité

L’onglet Statut affiche la sortie de :

systemctl status --no-pager --full --lines=80 SERVICE.service

L’onglet Fichier d’unité affiche le contenu obtenu par :

systemctl cat --no-pager SERVICE.service

Le bouton Afficher de Vue d’ensemble ouvre réellement l’onglet Statut.
Les panneaux affichent un message de chargement explicite, puis une erreur
lisible si la commande échoue.

Coloration syntaxique

Les sorties sont affichées avec une coloration légère, sans dépendance
supplémentaire :

sections [Unit], [Service] et [Install] colorées ;

directives d’unité mises en évidence ;

valeurs booléennes et valeurs courantes colorées ;

commentaires grisés et italiques ;

lignes d’erreur en rouge ;

avertissements en orange/jaune ;

états actifs ou réussis en vert.

Journal

L’onglet Journal utilise :

journalctl --unit SERVICE.service --no-pager --output=short-iso --lines=20

Seules les vingt dernières entrées sont demandées.

Si le journal système n’est pas lisible par la session graphique, l’application
tente une lecture privilégiée ponctuelle via Polkit et les chemins système
protégés /usr/bin/pkexec et /usr/bin/journalctl. Si Polkit, l’agent
d’authentification ou les permissions ne permettent pas la lecture, l’erreur
est affichée dans le panneau au lieu de laisser une vue vide.

Le bouton Actualiser le journal ne recharge que le journal. Le bouton
global de la barre latérale actualise la liste des services ; ces deux actions
ont donc des rôles différents.

Suppression complète et unités fantômes

Le bouton Supprimer complètement ne correspond pas à une désinstallation
de paquet. Il nettoie uniquement les entrées locales appartenant au service
sélectionné.

Avant suppression, l’application :

lit un plan détaillé avec systemctl show ;

affiche les fichiers locaux trouvés et les chemins protégés ;

indique les services qui référencent l’unité ;

demande une confirmation destructive ;

exige la saisie exacte du nom du service.

Lors de l’exécution, elle peut :

arrêter le service ;

le désactiver ;

le désmasquer si nécessaire ;

supprimer ses fichiers locaux et ses drop-ins ;

exécuter systemctl daemon-reload ;

exécuter systemctl reset-failed.

Une unité fantôme sans fichier local est traitée sans tentative de suppression
d’un chemin inexistant. Le rechargement et la réinitialisation de systemd sont
néanmoins effectués.

Les éléments suivants sont volontairement protégés :

/usr/lib/systemd/system ;

/lib/systemd/system ;

/run/systemd/system ;

les fichiers fournis par les paquets ;

les fichiers des autres services ;

les journaux systemd.

Pour le périmètre utilisateur, le nettoyage est limité à :

~/.config/systemd/user ;

~/.local/share/systemd/user.

Architecture technique

Source de vérité

L’application n’invente pas l’état d’un service. Elle interroge directement
systemd grâce aux commandes natives suivantes :

systemctl list-unit-files et systemctl list-units pour la liste ;

systemctl show pour les propriétés et les relations ;

systemctl status pour l’état détaillé ;

systemctl cat pour le fichier d’unité ;

journalctl pour le journal ;

les commandes d’action natives pour les modifications d’état.

Les commandes sont lancées par subprocess.run avec une liste d’arguments,
sans shell intermédiaire. Les noms d’unités sont validés avant exécution.

Fichiers du projet

systemd/
├── systemd.py                    # application GTK4/libadwaita
├── systemd-file-helper.py        # nettoyage local strictement limité
├── bin/systemd-gui               # lanceur technique
├── data/org.gnome.Systemd.desktop # entrée de menu GNOME
├── data/org.gnome.Systemd.svg    # icône de l’application
├── data/org.gnome.Systemd.appdata.xml
├── install.sh
├── uninstall.sh
├── run.sh
├── PKGBUILD
├── README.md
└── LICENSE

Le helper de suppression système est exécuté par Polkit uniquement depuis
/usr/lib/systemd-gui/systemd-file-helper, après installation root-owned. Il
ne parcourt jamais les répertoires de fichiers d’unités fournis par les
paquets.

Installation sur CachyOS / Arch

Dépendances d’exécution

sudo pacman -S --needed python python-gobject gtk4 libadwaita systemd polkit

Ces paquets sont les dépendances runtime. L’application ne nécessite ni Rust,
ni Meson, ni Ninja, ni compilateur.

Lancer depuis les sources

cd systemd
./run.sh

Installer avec le script

cd systemd
sudo ./install.sh

install.sh :

vérifie python3, systemctl, journalctl, pkexec et install ;

vérifie la présence de GTK4/libadwaita via PyGObject ;

n’installe aucun paquet ;

copie l’application, le helper, le lanceur, l’icône et le fichier desktop ;

installe uninstall.sh dans /usr/lib/systemd-gui/.

Pour une installation utilisateur :

cd systemd
PREFIX="$HOME/.local" ./install.sh

Désinstaller une installation par script

sudo ./uninstall.sh

Après une installation système, le script est également disponible ici :

sudo /usr/lib/systemd-gui/uninstall.sh

Pour une installation utilisateur, employer le même préfixe :

PREFIX="$HOME/.local" ./uninstall.sh

La désinstallation retire uniquement les fichiers de l’application. Elle ne
modifie aucun service systemd ni aucun fichier d’unité.

Installer le paquet Pacman

sudo pacman -U ./systemd-gui-0.3.0-1-any.pkg.tar.zst

Désinstallation d’une installation Pacman :

sudo pacman -R systemd-gui

Ne pas utiliser uninstall.sh après une installation par Pacman, afin de ne
pas désynchroniser la base de données des paquets.

Le nom affiché dans GNOME est systemd. Le lanceur technique est
systemd-gui, pour éviter tout conflit avec les commandes du paquet systemd.
Il n’est pas nécessaire de lancer l’application avec sudo.

Installation Debian / Ubuntu

sudo apt install python3 python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 systemd policykit-1

Le script d’installation ne gère pas les paquets automatiquement : il vérifie
les dépendances et indique celles qui manquent.

Compilation du paquet Arch

Pour utiliser makepkg, installer uniquement les outils de build nécessaires :

sudo pacman -S --needed base-devel
cd systemd
makepkg -si

Le paquet est any, car l’application est écrite en Python. Les dépendances
runtime restent celles listées plus haut.

Historique des demandes et corrections

Version

Évolutions principales

0.1.0

Première interface native pour lister et inspecter les services.

0.1.1

Actions GUI visibles, panneaux de détail fiables et icônes compatibles avec les thèmes.

0.2.0

Correction des icônes et du chargement des panneaux ; état permanent du service ; ajout de la suppression complète et des unités fantômes.

0.2.1

Correction du callback de sélection ; rechargement réel des détails ; réactivation correcte des boutons après une suppression.

0.2.2–0.2.3

Suppression de l’onglet Propriétés redondant ; lecture du journal système avec repli Polkit ; recherche dynamique ; action principale adaptée à l’état du service.

0.2.4

Suppression du bouton Actualiser redondant dans le panneau droit ; recherche indépendante de la catégorie ; journal limité à vingt entrées ; retrait du libellé « Périmètre ».

0.3.0

Dépendances dans Vue d’ensemble ; coloration syntaxique ; barre bleue de sélection ; fond bleu-gris ; pastilles d’état ; compteur de résultats ; bouton Effacer.

Les problèmes traités au cours du projet ont notamment été :

icônes inférieures cassées ou absentes ;

absence de boutons d’action réellement fonctionnels ;

panneaux droits vides après sélection ;

état courant non affiché en permanence ;

bouton « Consulter l’état détaillé — Afficher » inopérant ;

journal bloqué par No journal files were opened due to insufficient permissions ;

recherche qui ne réagissait pas à la saisie ;

recherche limitée par erreur au filtre « Tous les services » ;

suppression d’unités fantômes incomplète ;

boutons restant désactivés après une suppression ;

doublon de bouton Actualiser ;

onglet Propriétés redondant ;

absence de dépendances visibles ;

absence de feedback de chargement ou d’erreur.

Vérifications avant publication

Après une modification du code :

cd systemd
python3 -B -m py_compile systemd.py systemd-file-helper.py
bash -n PKGBUILD
sh -n install.sh uninstall.sh run.sh bin/systemd-gui

Vérifier également que :

les quatre onglets sont toujours overview, status, unit et journal ;

aucune référence à properties_text ou à un cinquième onglet n’a été ajoutée ;

le journal utilise bien --lines=20 ;

les actions continuent de passer par systemctl ;

le helper de suppression ne dépasse pas ses répertoires autorisés ;

les erreurs sont affichées dans l’interface et non avalées silencieusement.

Maintenir ce README à jour

À chaque nouvelle version :

mettre à jour APP_VERSION dans systemd.py ;

mettre à jour pkgver dans PKGBUILD ;

ajouter une entrée de version dans data/org.gnome.Systemd.appdata.xml ;

ajouter la fonction ou la correction dans la section correspondante ;

compléter l’historique des versions ;

mettre à jour les noms des paquets dans les commandes d’installation ;

exécuter les vérifications ci-dessus ;

reconstruire l’archive source et le paquet Pacman.

Le README doit documenter les comportements effectivement présents dans le
code, et non les idées encore prévues.

Limites connues

La liste vise actuellement les unités *.service.

Les timers, sockets, mounts et autres types d’unités ne sont pas encore
affichés comme objets administrables séparés.

L’application ne propose pas d’éditeur de fichiers d’unités.

La suppression complète ne désinstalle pas un paquet Arch et ne supprime
jamais les journaux.

Les actions dépendent des permissions systemd et de l’agent Polkit de la
session graphique.

Comme toute interface graphique, l’état affiché peut évoluer entre deux
rafraîchissements ; systemd reste l’autorité finale.

