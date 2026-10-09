# Extension Manager (fork Ogu)

Fork de https://github.com/mjakeman/extension-manager. Paquet `extension-manager-ogu` **0.6.5.ogu2-1**, x86_64, `provides=extension-manager=0.6.5`, `conflicts=extension-manager`. App id `com.mattjakeman.ExtensionManager` (conservé).

## Fonctions ajoutées

- Classement local des extensions installées en **7 catégories** : Interface et apparence, Bureau et fenêtres, Barre supérieure et réglages rapides, Productivité, Système et énergie, Multimédia, Autres.
- Détection automatique : UUID connus, puis mots-clés du nom/de la description. Choix manuel prioritaire et mémorisé ; « Catégorie automatique » pour revenir.
- Extensions système séparées ; icône personnalisée.
- ogu2 repart de l'app originelle pour garder **Parcourir** et sa recherche ; pas de filtre N+1/N−1.

## Technique

- **C**, GTK4/libadwaita ≥ 1.8, json-glib, libsoup3, libxml2, glycin ; build upstream **Meson + Ninja** (Blueprint). Sources non présentes ici.
- Les extensions maison s'appuient sur ce classement : leur `description` contient volontairement un mot-clé (ex. « énergie » → Système et énergie pour Power Total, « Gestion du bureau et des fenêtres » pour UI Management). Garder cette cohérence si les règles changent.
- Pas testé en session GNOME réelle lors de l'intégration.
