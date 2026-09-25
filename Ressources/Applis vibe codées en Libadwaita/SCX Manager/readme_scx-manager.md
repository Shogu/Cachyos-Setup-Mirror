# SCX Manager — Libadwaita

Réécriture native GTK4/Libadwaita de SCX Manager pour GNOME. L’application
permet de consulter et de piloter `scx_loader`, le service D-Bus qui gère les
planificateurs Linux `sched-ext`.

Cette version conserve un périmètre volontairement simple : elle agit sur
`scx_loader` et ne remplace ni `tuned`, ni `tuned-ppd`, ni la gestion AMD
P-State/EPP.

## État de la version

- Version du projet : `0.1.2`
- Interface : GTK4 + Libadwaita
- Langage : C11
- Construction : Meson + Ninja
- Service utilisé : `org.scx.Loader` sur le bus système
- Installation utilisateur par défaut : `~/.local`

## Fonctions intégrées

### État du scheduler

- Affichage du scheduler `sched-ext` actuellement actif.
- Affichage de son nom lisible et de son identifiant, par exemple
  `Pandemonium (scx_pandemonium)`.
- Badge d’état `Actif`, `Inactif` ou `Indisponible`.
- Affichage du scheduler Linux par défaut lorsque `sched-ext` est arrêté.
- Message explicite lorsque `scx_loader` ne répond pas.
- Icône dédiée dans le cartouche « scheduler actif » :
  `org.cachyos.scx-manager-adwaita-active-symbolic`.
- Mise à jour de l’état après chaque opération réussie.

### Actualisation

Le bouton d’actualisation situé dans la barre de titre relit immédiatement l’état
de `scx_loader`, sans devoir fermer et rouvrir l’application.

La lecture utilise :

~~~text
org.freedesktop.DBus.Properties.GetAll("org.scx.Loader")
~~~

### Sélection du scheduler

- Liste des schedulers fournie par la propriété D-Bus
  `SupportedSchedulers`.
- Liste de secours si cette propriété est absente.
- Sélection automatique du scheduler actif au chargement.
- Sélection du scheduler par défaut si aucun scheduler `sched-ext` n’est actif.
- Effacement des arguments personnalisés lors du changement de scheduler, afin
  de ne pas réutiliser par erreur les flags d’un autre scheduler.

Les descriptions longues propres à chaque scheduler ont été retirées : la ligne
`Scheduler` affiche uniquement le sélecteur.

### Profils disponibles

Les profils correspondent aux modes numériques utilisés par `scx_loader` :

| Mode | Profil | Intention générale |
| ---: | --- | --- |
| `0` | Auto | Arguments par défaut du scheduler |
| `1` | Gaming | Réactivité et charges de jeu |
| `2` | Power Save | Efficacité énergétique |
| `3` | Low Latency | Latence réduite |
| `4` | Server | Débit et charge soutenue |

Les descriptions génériques des profils restent affichées dans la ligne
`Profil`. Elles ne prétendent pas décrire le fonctionnement interne de chaque
scheduler.

### Arguments personnalisés

- Saisie d’une ligne d’arguments personnalisés.
- Prise en charge des espaces protégés par guillemets simples ou doubles.
- Prise en charge de l’échappement avec `\\`.
- Détection des guillemets non fermés et de la barre oblique finale invalide.
- Transmission des arguments sous forme de tableau D-Bus, sans passer par un
  shell.
- Les arguments personnalisés remplacent le profil prédéfini.
- Le champ reste vide quand `scx_loader` ne transmet aucun argument.
- Les chaînes vides renvoyées par D-Bus sont ignorées.
- Les arguments sont réaffichés avec un échappement correct lorsque cela est
  nécessaire.

### Actions

Les boutons disponibles sont :

- `Appliquer` : démarre ou bascule vers le scheduler sélectionné ;
- `Désactiver` : appelle `StopScheduler` ;
- `Restaurer par défaut` : appelle `RestoreDefault` ;
- bouton d’actualisation : relit l’état de `scx_loader`.

L’application choisit automatiquement la méthode D-Bus adaptée :

| Situation | Méthode utilisée |
| --- | --- |
| Nouveau scheduler avec profil | `StartScheduler` |
| Nouveau scheduler avec arguments | `StartSchedulerWithArgs` |
| Bascule avec profil | `SwitchScheduler` |
| Bascule avec arguments | `SwitchSchedulerWithArgs` |
| Désactivation | `StopScheduler` |
| Restauration | `RestoreDefault` |

Les opérations sont asynchrones. Pendant une opération, les contrôles concernés
sont désactivés et un message temporaire confirme le succès ou signale l’erreur.

## Cas particulier de Pandemonium

### Comportement des flags

`scx_pandemonium` peut fonctionner avec ses paramètres internes sans recevoir
d’argument. Lorsque `CurrentSchedulerArgs` vaut `[]`, l’application affiche donc
un champ de flags vide et le texte :

~~~text
Paramètres d'origine du scheduler · aucun argument transmis
~~~

Cela signifie « aucun flag transmis au processus », et non « le scheduler ne
fonctionne pas ».

### Correction de l’affichage du profil

`scx_loader` expose séparément :

- `SchedulerMode` : mode actuellement mémorisé par le service ;
- `DefaultMode` : mode par défaut configuré ;
- `CurrentSchedulerArgs` : arguments effectivement transmis.

Pour Pandemonium, plusieurs profils peuvent produire une liste d’arguments vide.
La version `0.1.2` applique donc la règle d’affichage suivante lorsque le
scheduler actif est aussi le scheduler par défaut et qu’aucun argument n’est
transmis : l’interface utilise `DefaultMode` comme profil effectif affiché.

Cette règle est une interprétation de présentation dans l’application. Elle ne
modifie pas `SchedulerMode`, ne modifie pas la configuration de `scx_loader` et
ne relance pas le scheduler. Une interrogation D-Bus peut donc continuer à
retourner `SchedulerMode = 2` alors que l’interface affiche le mode par défaut.

Limite connue : avec un scheduler dont plusieurs profils n’envoient aucun
argument, l’application ne peut pas distinguer uniquement avec `[]` un choix
volontaire de `Power Save` d’un fonctionnement avec les paramètres natifs du
scheduler. Le champ « aucun argument transmis » est donc l’information la plus
fiable sur la ligne de commande réellement utilisée.

## Architecture technique

- `AdwApplication` et `AdwApplicationWindow` pour l’application GNOME.
- `AdwHeaderBar` avec bouton d’actualisation.
- `AdwToolbarView`, `AdwClamp` et zone défilante pour une interface adaptée aux
  petites et grandes fenêtres.
- `AdwPreferencesGroup`, `AdwActionRow` et `AdwEntryRow` pour la configuration.
- `AdwToastOverlay` pour les confirmations et les erreurs.
- CSS Libadwaita léger pour le cartouche d’état et les badges colorés.
- Thème clair ou sombre fourni automatiquement par GNOME.
- Une seule fenêtre est présentée lorsque l’application est relancée alors
  qu’elle est déjà ouverte.

## Corrections réalisées

### Compatibilité GTK4/Libadwaita récentes

- Suppression de l’appel inexistant `gtk_editable_set_placeholder_text()`.
- Utilisation de `GTK_APPLICATION(...)` avec le constructeur de fenêtre
  Libadwaita qui attend un `GtkApplication`.
- Utilisation de `adw_application_window_set_content()` au lieu de
  `gtk_window_set_child()` pour éviter l’arrêt brutal de l’application.
- Utilisation de `gtk_css_provider_load_from_string()`.

### Interface et état

- Remplacement de l’icône cassée du cartouche actif par une icône SVG installée
  avec l’application.
- Suppression des descriptions peu utiles des schedulers.
- Ajout du bouton d’actualisation sans redémarrage de l’application.
- Nettoyage des arguments vides renvoyés par D-Bus.
- Effacement des flags lorsqu’aucun argument réel n’est transmis.
- Protection contre la réutilisation des flags d’un scheduler précédent.
- Indication explicite des paramètres natifs de Pandemonium.

## Demandes non intégrées dans `0.1.2`

Les idées suivantes ont été évoquées, mais ne font pas partie du code actuel :

- lecture et affichage de l’EPP AMD ;
- bouton EPP sous la ligne `Profil` ;
- synchronisation directe avec `tuned` ou `tuned-ppd` ;
- notification automatique lorsqu’un autre programme change le scheduler ;
- écoute en temps réel du signal D-Bus `PropertiesChanged` ;
- descriptions spécifiques des flags de chaque scheduler ;
- paquet binaire `.pkg.tar.zst` précompilé prêt à télécharger.

L’application affiche seulement l’état lu auprès de `scx_loader`. Elle ne modifie
pas l’EPP et ne prend pas la place de la synchronisation déjà assurée par
`tuned`, `tuned-ppd` ou la configuration système.

## Tableau de suivi des demandes

| Demande ou correction | État |
| --- | --- |
| Réécriture GTK4/Libadwaita | Intégrée |
| Lecture de l’état via `scx_loader` | Intégrée |
| Liste des schedulers | Intégrée |
| Profils Auto, Gaming, Power Save, Low Latency et Server | Intégrés |
| Arguments personnalisés | Intégrés |
| Appliquer, désactiver et restaurer par défaut | Intégrés |
| Bouton d’actualisation | Intégré |
| Suppression des descriptions de scheduler | Intégrée |
| Correction de l’icône du scheduler actif | Intégrée |
| Champ vide en l’absence de flags | Intégrée |
| Gestion du cas Pandemonium sans argument | Intégrée avec limite documentée |
| Hiérarchie typographique rapprochée du style GNOME natif | Intégrée |
| Indication EPP | Non intégrée |
| Notification lors d’un changement externe du scheduler | Non intégrée |
| Paquet Arch source avec `PKGBUILD` | Intégré |
| Paquet binaire précompilé pour `pacman -U` | Non fourni |

## Dépendances

### Exécution

~~~text
gtk4
libadwaita
scx-tools
scx-scheds
~~~

`scx-tools` et `scx-scheds` fournissent le service et les schedulers SCX. Le
noyau doit également prendre en charge `sched-ext` et un agent Polkit doit être
disponible pour les opérations privilégiées.

### Construction

~~~text
base-devel
meson
ninja
pkgconf
~~~

Installation complète sur CachyOS ou Arch Linux :

~~~bash
sudo pacman -S --needed base-devel meson ninja pkgconf gtk4 libadwaita scx-tools scx-scheds
~~~

`meson`, `ninja`, `pkgconf` et `base-devel` sont nécessaires à la construction.
`gtk4`, `libadwaita`, `scx-tools` et `scx-scheds` doivent rester installés pour
l’utilisation normale.

## Compilation et installation utilisateur

Compilation seule :

~~~bash
./build.sh
~~~

Le binaire est alors disponible dans `build/scx-manager-adwaita`.

Installation par défaut dans `~/.local` :

~~~bash
./install.sh
~~~

Le script installe :

- `~/.local/bin/scx-manager-adwaita` ;
- le lanceur `.desktop` ;
- l’icône principale ;
- l’icône du scheduler actif.

Pour choisir un autre préfixe :

~~~bash
PREFIX=/usr/local ./install.sh
~~~

Pour empêcher le script de tenter d’installer automatiquement les outils de
construction :

~~~bash
SKIP_BUILD_DEPS=1 ./install.sh
~~~

## Paquet Arch avec `PKGBUILD`

Le projet contient un `PKGBUILD` et une archive source locale. Ils permettent de
construire un paquet Arch adapté à la machine cible :

~~~bash
makepkg -s
~~~

Puis installer le paquet généré :

~~~bash
sudo pacman -U ./scx-manager-adwaita-0.1.2-1-x86_64.pkg.tar.zst
~~~

Le paquet installe le binaire dans `/usr/bin`, le lanceur GNOME et les deux
icônes.

`makepkg` est nécessaire pour compiler le binaire depuis les sources. Le fichier
`.pkg.tar.zst` n’est pas inclus dans l’archive source actuelle.

## Désinstallation

### Installation via le paquet Arch

~~~bash
sudo pacman -R scx-manager-adwaita
~~~

Cette commande ne supprime pas `gtk4`, `libadwaita`, `scx-tools` ou `scx-scheds`.

### Installation utilisateur avec `install.sh`

~~~bash
./uninstall.sh
~~~

Le script ne supprime pas les paquets système ni les outils de compilation.

Après vérification qu’ils ne servent à aucun autre projet, les outils de
construction peuvent être retirés séparément :

~~~bash
sudo pacman -Rns meson ninja pkgconf
~~~

`base-devel` est un groupe général souvent utile pour les paquets AUR ; il ne
doit pas être supprimé sans vérifier les autres usages du système.

## Diagnostic rapide

Vérifier directement l’état publié par `scx_loader` :

~~~bash
gdbus call --system --dest org.scx.Loader --object-path /org/scx/Loader --method org.freedesktop.DBus.Properties.GetAll org.scx.Loader
~~~

Les propriétés les plus utiles sont `CurrentScheduler`, `DefaultScheduler`,
`SchedulerMode`, `DefaultMode`, `CurrentSchedulerArgs` et
`SupportedSchedulers`.

Si `scx_loader` est indisponible :

~~~bash
systemctl status scx_loader.service
systemctl restart scx_loader.service
~~~

## Licence

GPL-3.0-or-later.
