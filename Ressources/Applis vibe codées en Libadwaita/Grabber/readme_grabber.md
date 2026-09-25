Frontend perso libadwaita pour les principales fonctions de jdownloader. Embarque sa propre version de java et jdownloader. Vibe coded.






Grabber
Grabber est une interface GTK4/libadwaita volontairement minimale pour
JDownloader 2. Elle ne cherche pas à reproduire l'interface Java ni ses
milliers de réglages : son objectif est de trouver des liens, choisir les
fichiers utiles, les télécharger et suivre la file.

Version documentée : 0.10.30 (pyproject.toml).

Ce que fait Grabber
Interface et identité GNOME
deux onglets : Téléchargements et Grabber ;

interface GTK4/libadwaita avec boutons d'action et boutons iconiques
compacts ;

boutons iconiques circulaires de taille fixe, notamment démarrer, arrêter,
réglages, confidentialité, connexion et suppression ;

indicateur de connexion sous forme d'icône circulaire libadwaita, bleu quand
JDownloader est connecté, sans mention inutile de « moteur local connecté » ;

application, processus Linux et classe de fenêtre nommés Grabber ;

identifiant d'application com.ogu.Grabber ;

icône Grabber utilisée par l'interface, le processus et le lanceur GNOME ;

mode discret : un écran opaque masque temporairement les téléchargements et
affiche uniquement le nom et l'icône Grabber ; un bouton œil discret restaure
l'interface.

Grabber et recherche de liens
saisie manuelle d'une ou plusieurs URL ;

analyse par le LinkGrabber de JDownloader ;

onglet nommé « Grabber » plutôt que « Liens détectés » ;

filtre persistant par type : tous les fichiers, musique, vidéos ou
documents ;

affichage de la taille du fichier quand JDownloader la connaît ;

affichage du service hôte et de sa favicon ;

favicons placées dans un cadre carré de taille identique pour éviter que la
longueur du domaine ne modifie la mise en page ;

correction spécifique YouTube : un identifiant vidéo ou un hôte CDN
googlevideo.com est présenté comme youtube.com et utilise la favicon
YouTube ;

cases à cocher indépendantes de l'état interne enabled de JDownloader ;

bouton Sélectionner tous les liens qui sélectionne les liens visibles
après application du filtre ;

bouton Ajouter et démarrer qui déplace uniquement les liens choisis dans
la file et force leur démarrage ;

menu clic droit sur un résultat pour ajouter son domaine d'origine à la
whitelist, y compris lorsque le lien réel est servi par un CDN YouTube.

Whitelist des domaines
La whitelist est facultative et peut être activée ou désactivée directement
dans l'onglet Grabber ou depuis les réglages. Les domaines sont conservés dans
la configuration et normalisés sans doublon.

un domaine par ligne ;

youtube.com autorise youtube.com et ses sous-domaines ;

*.youtube.com est accepté comme écriture équivalente à youtube.com ;

youtube.* n'est pas accepté : ce motif serait trop large et ambigu ;

la whitelist filtre les résultats affichés dans Grabber, après l'analyse
réalisée par JDownloader ; elle ne limite pas les requêtes réseau internes
de JDownloader.

Presse-papiers
Grabber dispose d'un surveillant GTK4 du presse-papiers, activé par défaut pour
les nouvelles configurations et désactivable à tout moment.

Lorsqu'une copie contient une ou plusieurs URL HTTP(S), Grabber :

extrait et déduplique les URL ;

les colle dans le champ du Grabber ;

ouvre automatiquement l'onglet Grabber ;

lance automatiquement l'analyse ;

laisse l'utilisateur sélectionner puis ajouter les fichiers à la file.

L'analyse automatique ne démarre donc pas silencieusement un téléchargement.
Le bouton Presse-papiers de l'onglet et l'interrupteur des réglages
contrôlent la même fonction. L'observateur natif du presse-papiers de
JDownloader est désactivé pour éviter les doublons : c'est le frontend GTK qui
gère cette étape.

Téléchargements
lecture de la file JDownloader ;

démarrage automatique de la file existante lors de la connexion initiale ;

boutons globaux démarrer/arrêter la file ;

choix du nombre maximal de téléchargements simultanés : 1, 2, 3, 4, 5, 8,
10, 15 ou 20 ;

nom du fichier, service hôte, favicon, état, quantité transférée, taille
totale, vitesse, pourcentage et ETA ;

ETA calculé à partir du débit réellement observé par le frontend afin de
mieux fonctionner lorsque la valeur fournie par JDownloader est imprécise ;

ETA masqué lorsqu'il n'y a pas assez de données fiables ;

remplacement de la barre de progression par la mention bleue TERMINÉ
lorsque le fichier est fini ;

double-clic sur un téléchargement pour ouvrir son dossier dans Nautilus ;

clic droit sur un téléchargement pour :

réinitialiser le téléchargement, supprimer ses données et le reprendre
depuis zéro ;

ouvrir le fichier avec l'application par défaut adaptée à son type ;

bouton de corbeille pour supprimer définitivement le fichier exact choisi,
ses fichiers temporaires .part/.part.e2e, son entrée JDownloader et son
dossier parent uniquement s'il est vide et sûr à supprimer ;

confirmation courte avant une suppression définitive ;

bouton Supprimer les téléchargements terminés qui retire seulement les
entrées terminées de la liste JDownloader, sans toucher aux fichiers du
disque ;

traitement par identifiant de lien, et non par nom de fichier, afin qu'un
fichier portant le même nom qu'un autre ne soit pas supprimé ou sélectionné
par erreur ;

dialogue de doublon avec Renommer, Annuler et Remplacer.

Fonctionnement technique
Un seul mode de connexion
Grabber utilise uniquement l'instance locale de JDownloader qu'il lance et
possède. Il ne propose plus de second mode, de remoteAPI, d'adoption
heuristique d'une instance externe ou de compte My.JDownloader.

La communication utilise l'API locale historique de JDownloader sur :

http://127.0.0.1:3128
Cette API est appelée « deprecated » par JDownloader, mais c'est l'interface
locale non authentifiée utilisée ici. Elle ne doit pas être exposée sur le
réseau.

Moteur headless et cycle de vie
Le frontend lance JDownloader sans interface graphique Java :

java -Djava.awt.headless=true -jar JDownloader.jar -norestart
À la fermeture, Grabber arrête d'abord l'interface pour que la fenêtre
disparaisse immédiatement, puis conserve l'application vivante pendant le
nettoyage de JDownloader dans un thread dédié. Cela évite la fenêtre grisée et
la latence visible qui existaient auparavant, tout en évitant de laisser une
JVM orpheline.

Le projet ne fournit ni service systemd ni démon séparé : le processus Java
est attaché au cycle de vie de Grabber. Le chemin de données JDownloader n'est
pas supprimé à la fermeture.

Données persistantes
La configuration du frontend est enregistrée dans :

~/.config/jd-adwaita/config.json
Elle contient notamment le dossier de téléchargement, le filtre du Grabber,
la whitelist, l'état du surveillant presse-papiers et le nombre de
téléchargements simultanés.

Les données mutables de JDownloader sont conservées dans :

~/.local/share/jd-adwaita/jdownloader
Elles restent donc disponibles après un déplacement ou une suppression de
l'AppImage. Pour repartir de zéro, il faut supprimer ce dossier manuellement
après avoir fermé Grabber.

AppImage
L'AppImage embarque :

un JRE Temurin OpenJDK 17 ;

JDownloader headless et son runtime initialisé ;

le frontend Python Grabber et son icône.

Elle choisit explicitement le Java situé dans son propre bundle : Java et
JDownloader installés sur le système ne sont donc pas utilisés par l'AppImage.
En revanche, l'interface libadwaita reste dépendante de l'environnement Linux
hôte : GTK4, libadwaita, Python 3 et PyGObject doivent être disponibles.

L'AppImage est en lecture seule. Au premier lancement, elle copie le runtime
JDownloader dans ~/.local/share/jd-adwaita/jdownloader afin que la
configuration et le bouton de mise à jour natif puissent fonctionner.

Lancement :

chmod +x grabber-0.10.30-x86_64.AppImage
./grabber-0.10.30-x86_64.AppImage
Le fichier peut être déplacé : il n'y a pas de chemin enregistré dans le
runtime et aucun nouveau fichier .desktop n'est généré automatiquement.

Lancement depuis les sources
Sur Arch/CachyOS, installer les dépendances graphiques et Java :

sudo pacman -S --needed gtk4 libadwaita python python-gobject jre-openjdk
Puis :

cd jd-adwaita
./scripts/run.sh
Dans une installation source, Java peut être fourni par le PATH ou indiqué
dans les réglages, et JDownloader.jar peut être sélectionné manuellement.

Installation utilisateur sans AppImage
Le script installe le frontend et l'icône dans le profil utilisateur :

cd jd-adwaita
./scripts/install-user.sh
La commande installée est :

grabber
Le script n'écrit pas de fichier .desktop. Il installe seulement le code,
la commande et l'icône, puis indique qu'un lanceur GNOME peut être créé
manuellement.

Créer manuellement un lanceur GNOME
Exemple de fichier ~/.local/share/applications/grabber.desktop :

[Desktop Entry]
Name=Grabber
Comment=Interface libadwaita minimale pour JDownloader
Exec=/chemin/absolu/vers/grabber-0.10.30-x86_64.AppImage
Icon=com.ogu.Grabber
Terminal=false
Type=Application
Categories=Network;FileTransfer;GTK;
StartupNotify=true
StartupWMClass=Grabber
X-GNOME-Application-ID=com.ogu.Grabber
Si l'icône n'est pas installée dans le thème utilisateur, remplacer Icon=
par le chemin absolu vers com.ogu.Grabber.svg. Le chemin de Exec= peut
ensuite être modifié librement lorsque l'AppImage est déplacée.

Construction de l'AppImage
Le script de construction télécharge le JRE Temurin depuis Adoptium et
JDownloader depuis l'installeur officiel, puis produit une AppImage autonome
pour Java et JDownloader.

Dépendances de construction principales : curl, tar, python3, find,
sed, stat, setsid, file, grep, mktemp et les utilitaires système
usuels. appimagetool est téléchargé dans le répertoire de travail s'il n'est
pas déjà disponible.

cd jd-adwaita
./scripts/build-appimage.sh
Le résultat est placé dans dist/ sous la forme :

dist/grabber-VERSION-x86_64.AppImage
Le fichier .desktop copié dans l'AppImage sert uniquement de métadonnée et
ne déclenche aucune installation automatique sur le système.

Vérification et sécurité du bundle
La construction récupère JDownloader depuis https://installer.jdownloader.org
et le JRE depuis Adoptium. Le script ne télécharge pas de binaire Java ou
JDownloader depuis un miroir personnel. Pour une vérification de confiance,
conserver le SHA-256 de l'AppImage distribuée et vérifier séparément le JAR
JDownloader avec la signature publiée par JDownloader lorsque celle-ci est
disponible.

L'AppImage ne rend pas les URL téléchargées anonymes et ne contourne pas les
captchas ou les règles des hébergeurs. La whitelist est un filtre d'affichage,
pas une mesure de sécurité réseau.

Mise à jour de JDownloader
Le bouton de mise à jour des réglages appelle l'outil de mise à jour natif de
JDownloader. Il arrête puis relance le moteur. La vérification distingue une
absence de mise à jour d'une erreur réelle et ne transforme plus une opération
réussie en faux échec après un délai arbitraire.

Options volontairement retirées ou non prises en charge
Ces choix sont intentionnels et doivent rester explicites lors des futures
évolutions :

pause et reprise ciblées par clic droit : retirées car trop instables dans
les versions précédentes ;

fonction spéciale Doodstream de déconnexion/reconnexion : retirée ;

action contextuelle « Retirer de la file uniquement » : retirée car elle
doublonnait avec le retrait des téléchargements terminés et se comportait
mal ;

gestion des comptes/hébergeurs : non intégrée ;

second mode de connexion, remoteAPI et My.JDownloader : non intégrés ;

surveillance native du presse-papiers de JDownloader : désactivée pour
laisser le frontend GTK gérer le collage et l'analyse sans doublon ;

notification GNOME séparée lors d'une détection presse-papiers : non
intégrée dans l'état actuel ; le résultat apparaît directement dans Grabber ;

création automatique d'un fichier .desktop : supprimée ;

création d'un service systemd : jamais nécessaire ;

création automatique de sous-dossiers music, videos et documents :
supprimée ;

réglages avancés de JDownloader (captchas, règles de nommage, limites de
débit, proxies et réglages d'hébergeurs) : laissés à JDownloader natif.

Les fonctions réinitialiser depuis zéro et ouvrir le fichier restent,
elles, disponibles dans le menu clic droit des téléchargements.

Corrections importantes apportées
Le projet a notamment corrigé les problèmes suivants rencontrés pendant son
développement :

construction de l'interface avec l'API correcte de Adw.ViewSwitcher ;

lancement forcé des liens sélectionnés afin qu'ils démarrent réellement
après l'ajout ;

conservation de la sélection du Grabber pendant les rafraîchissements ;

traitement par identifiant pour éviter les suppressions et sélections de
tous les fichiers portant le même nom ;

suppression des fichiers finaux et temporaires exacts, y compris pendant un
téléchargement, avant retrait de l'entrée JDownloader ;

suppression limitée au dossier parent vide et jamais au dossier de
téléchargement lui-même ;

dialogue de doublon avec les trois choix demandés ;

normalisation des hôtes YouTube et de leurs CDN dans Grabber et dans la
whitelist ;

fallback favicon YouTube lorsque le CDN ou le réseau ne fournit pas
directement l'icône ;

taille fixe des favicons et des boutons iconiques ;

état terminé bleu avec disparition de la barre de progression ;

calcul d'ETA basé sur plusieurs mesures de débit ;

ouverture du dossier uniquement au double-clic et ouverture du fichier via
l'application par défaut au clic droit ;

menu contextuel conservé assez longtemps malgré les rafraîchissements ;

démarrage automatique de la file existante ;

fermeture visuelle immédiate et arrêt différé propre de Java/JDownloader ;

démarrage sans écran opaque ou noir parasite ;

identification du processus et de la fenêtre sous le nom Grabber ;

comportement explicite de la mise à jour lorsqu'aucune mise à jour n'est
disponible ;

persistance du filtre de type, de la whitelist, du surveillant presse-papiers
et des préférences de téléchargements.

Organisation du code
Le gros fichier initial a été découpé pour rendre les corrections localisées :

Module	Responsabilité
jd_adwaita/app.py	fenêtre, orchestration et rafraîchissement
jd_adwaita/ui.py	construction GTK/libadwaita, CSS et mode discret
jd_adwaita/settings.py	fenêtre des réglages et mise à jour
jd_adwaita/api.py	client de l'API locale JDownloader
jd_adwaita/process.py	lancement, possession et arrêt de Java/JDownloader
jd_adwaita/clipboard.py	observation GTK4 du presse-papiers
jd_adwaita/clipboard_utils.py	extraction et déduplication des URL
jd_adwaita/domains.py	normalisation et comparaison des domaines
jd_adwaita/formatting.py	hôtes, catégories, tailles, états et ETA
jd_adwaita/favicons.py	récupération des favicons et fallback YouTube
tests/	tests unitaires de l'API, de la configuration et du formatage
Vérifications
Depuis la racine du projet :

python3 -m compileall -q jd_adwaita tests
PYTHONPATH=. python3 -m unittest discover -s tests
Un test graphique réel nécessite une session GTK4/libadwaita. La compilation
et les tests unitaires ne remplacent donc pas une vérification manuelle de
l'AppImage sur une session GNOME.

Tenir ce document à jour
Pour chaque évolution :

mettre à jour la version dans pyproject.toml ;

actualiser la liste des fonctions réellement présentes ;

déplacer toute fonction supprimée dans « Options volontairement retirées » ;

ajouter la correction importante dans la section correspondante ;

relancer la compilation et les tests avant de construire une nouvelle
AppImage.
