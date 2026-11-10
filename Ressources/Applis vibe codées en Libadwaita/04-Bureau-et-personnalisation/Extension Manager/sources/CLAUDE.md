# Extension Manager (fork Ogu)

Fork de https://github.com/mjakeman/extension-manager. Paquet `extension-manager-ogu` **0.7.0.ogu1-1**, x86_64, `provides=extension-manager=0.7.0`, `conflicts=extension-manager`. App id `com.mattjakeman.ExtensionManager` (conservé). Version affichée : `0.7.0-ogu1` (`version_suffix` dans `meson.build`).

## Fonctions ajoutées

- Classement local des extensions installées en **7 catégories** : Interface et apparence, Bureau et fenêtres, Barre supérieure et réglages rapides, Productivité, Système et énergie, Multimédia, Autres.
- Détection automatique (`src/exm-categories.c`) : choix manuel, puis UUID connus, puis mots-clés du nom, de la description et de l'UUID, testés dans l'ordre énergie → multimédia → productivité → apparence → fenêtres → barre. Sinon « Autres ».
- Choix manuel mémorisé dans la clé GSettings `extension-categories` (`a{ss}`, UUID → id). Ids : `appearance`, `windows`, `panel`, `productivity`, `power`, `media`, `other`. Ne jamais les renommer (`multimedia` est accepté comme alias de `media`).
- Menu ⋮ (`category_btn`) sur chaque ligne d'extension utilisateur : « Déplacer vers… », action d'état `row.category`, « Catégorie automatique » = `auto` (supprime le choix).
- Page Installées : `user_prefs_group` ne garde que le titre et le bouton Sélectionner ; une `AdwPreferencesGroup` par catégorie (créée dans `setup_categories`) avec un `GtkCustomFilter`, masquée si vide. Extensions système toujours en dernier.
- Correctif ogu3 reporté en source (`exm-search-row.c`, `signal_id` remis à 0).
- Icônes personnalisées reprises du paquet ogu3 (à remettre dans le paquet après `meson install`).

## Technique

- **C**, GTK4/libadwaita ≥ 1.8, json-glib, libsoup3, libxml2, glycin 2 ; build **Meson + Ninja** (Blueprint).
- Compilé dans un chroot Ubuntu 26.04 (libadwaita 1.9, GTK 4.22) faute d'accès aux miroirs Arch ; le binaire ne demande que GLIBC 2.34 et les mêmes sonames qu'Arch.
- Les extensions maison s'appuient sur ce classement : leur `description` contient volontairement un mot-clé (ex. « énergie » → Système et énergie pour Power Total, « Gestion du bureau et des fenêtres » pour UI Management, d'où le mot-clé « fenêtre » ajouté). Garder cette cohérence si les règles changent.
- Testé sous Xvfb avec un faux service D-Bus `org.gnome.Shell.Extensions` (liste, menu, mode sélection). Pas testé en session GNOME réelle.
- Pour suivre une future version amont : appliquer `0001-Ogu-fork-…patch` sur les nouvelles sources (`git am`).
