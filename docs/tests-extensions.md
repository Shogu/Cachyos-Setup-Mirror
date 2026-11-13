# Tests des extensions — 12–13 novembre 2026

Quatre extensions mises à jour : **Quick Settings v12**, **Widget Topbar 2.3**, **Copyous v16** et **Power Total 0.3.0**. Aucune n’a encore été testée dans une session GNOME réelle : toutes les cases restent à vérifier.

## Installation

~~~sh
gnome-extensions install --force ./quick-settings_ogu-v12.zip
gnome-extensions install --force ./widget-topbar_ogu-2.3.zip
gnome-extensions install --force ./copyous-multiclipboard_shogu-v16.zip
gnome-extensions install --force ./Power_Total-0.3.0.zip
journalctl -f -o cat /usr/bin/gnome-shell
~~~

Sous Wayland, se déconnecter puis se reconnecter après installation.

## 1. Quick Settings — v6 → v12

- [ ] Tout fermer : titre complet, sous-titre avec nombre de fenêtres recalculé à chaque ouverture, exclusions respectées ; premier clic confirmation, second fermeture.
- [ ] Clavier : icône clavier éclairé au lieu du soleil ; réglage dans Libellés, icônes et son.
- [ ] Style sombre utilise le libellé natif GNOME ; Mise à jour remplace Upgrade ; Énergie remplace Powersave.
- [ ] La tuile Charge batterie a disparu.
- [ ] Menu Énergie : Limiter la charge à 80 % suit le réglage GNOME Préserver la santé de la batterie dans les deux sens, si le matériel le permet. Si absent, examiner /sys/class/power_supply/BAT*/charge_control_end_threshold.
- [ ] Clé USB : insertion affiche une tuile bleue, nom, espace libre, icône topbar et bulle prête ; clic éjecte, avertit et masque la tuile. Tester les volumes occupés et plusieurs clés. Menu : Ouvrir, Ouvrir dans Fret, Éjecter.
- [ ] Minuteur : durées 5, 10, 15, 30 min, 1 h et durée personnalisée ; relance la dernière durée après reconnexion ; pause/reprise/arrêt ; décompte dans tuile et barre du haut ; préférence d’affichage sans interrompre le minuteur ; son et notification à la fin.
- [ ] Ressources : libellés blancs, valeurs secondaires ; barre Réseau relative au débit maximal observé depuis la connexion ; santé de batterie en pourcentage avec barre.
- [ ] Batterie : autonomie et pourcentage en barre supérieure ; autonomie et watts dans la pilule Quick Settings.
- [ ] Bulles OSD : Verr. Maj, Verr. Num, branchement/débranchement, limite de charge, changement de mode énergétique hors Quick Settings ; chaque bulle peut être coupée et aucun doublon ne doit apparaître.
- [ ] Ordre des tuiles : extensions tierces classées Autre extension ; Clavier, Clé USB et Minuteur classables ; nouvelle extension reclassée à son arrivée.
- [ ] Préférences : changer une option ne recrée que son module ; les autres modules et minuteurs restent actifs.
- [ ] Thème clair facultatif : tester prefer-light puis default ; textes secondaires lisibles.

## 2. Widget Topbar — 2.0 → 2.3

- [ ] Cartes des notes : même gris que lecteur, notifications et Aujourd’hui ; survol et clic identiques.
- [ ] Dates, aperçus, À venir, morceau suivant et sections : taille des heures de rendez-vous natives (9 pt).
- [ ] Notifications : en-tête gras, gris secondaire, cloche comprise.
- [ ] Thème clair facultatif : cartes blanches avec liseré.

## 3. Copyous — v15 → v16

- [ ] Le sélecteur ne montre plus la ligne d’aide « Entrée coller · Espace sélectionner · Échap fermer » ni son séparateur.
- [ ] Le pied (compteur, Annuler, Coller) n’apparaît que lorsqu’au moins un élément est coché.

## 4. Power Total — 0.1.2 → 0.3.0

- [ ] État actuel actualisé en direct : secteur/batterie, mode actif, origine du choix et santé de la batterie (+ cycles si connus).
- [ ] Tableau Secteur et batterie : mode, luminosité, thème et clavier rétroéclairé ; interrupteur à gauche et valeurs secteur/batterie grisées lorsque coupées.
- [ ] Groupes Modes d’énergie (mémorisation, batterie faible, modes disponibles) et Options (chargeur insuffisant, animations, erreurs).
- [ ] La page Applications n’existe plus.
- [ ] Branchement/débranchement applique les réglages du tableau.
- [ ] Choisir un autre mode dans Quick Settings fait passer Choisi par à Choix manuel.
- [ ] En mode Économie, les animations GNOME sont coupées puis restaurées à la sortie ; un réglage manuel préexistant reste respecté.
- [ ] Désactiver Power Total pendant le mode Économie restaure les animations.
- [ ] Auto Power Profile : modes secteur/batterie, notifications, mémorisation du choix manuel et protection chargeur faible repris ; profils par application et relancement lap-detected retirés.
- [ ] Power Switching Manager : thème, luminosité et clavier secteur/batterie repris.

## Résultat des tests

Ne cocher une case qu’après vérification en session GNOME réelle. Ajouter les anomalies observées, la version GNOME Shell et les extraits pertinents du journal.
