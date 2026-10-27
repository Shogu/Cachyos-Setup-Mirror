# Focus & Boutons v38

Extension GNOME Shell pour **GNOME Shell 50 et 51**. Elle s’occupe des **réglages rapides** et du **comportement des menus**.

## Ce qu’elle fait

- Ferme Quick Settings et le menu de l’horloge quand le pointeur en sort (350 ms par défaut).
- Boutons scindés **Réglages** (Paramètres · Ajustements, dconf, Extensions) et **Power** (Éteindre · Suspendre, Redémarrer, Reconnexion, Verrouiller).
- Pilule **Updates** (paquet `upgrade-check` requis) : nombre de mises à jour, liste, ⟳ pour vérifier, clic pour lancer le script.
- Capture d’écran masquée, libellé « Énergie », sorties audio masquées, affichage du volume à l’écran et fenêtre « Reconnexion ».

## Changements

### v38

- Les rendez-vous du calendrier et l’icône animée du lecteur sont transférés dans **Topbar Center Widget**.
- Un menu ne se ferme plus automatiquement pendant la saisie dans l’un de ses champs (titre d’une note, mot de passe Wi-Fi, etc.).

### v37

- La pilule s’appelle **Updates**.
- Le bouton ⟳ apparaît dans l’en-tête de sa liste.
- Le menu reste ouvert pendant la vérification, puis 3 secondes supplémentaires.

### v36

- Intervalle de vérification réglable (12 h par défaut).
- Un résultat périmé est revérifié au démarrage.

### v32 à v35

- Ajout de la pilule **Updates**, de l’icône animée du lecteur et d’une attente de 30 secondes après une mise à jour.

## Installation

Depuis le dossier contenant l’archive :

```sh
gnome-extensions install --force Focus-et-Boutons-v38.zip
```

Puis se déconnecter et se reconnecter à la session GNOME.
