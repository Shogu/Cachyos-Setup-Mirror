# Focus & Boutons v25

Extension GNOME Shell maison, UUID `focus-et-boutons@ogu`, ciblant GNOME Shell 50 et 51.

## Fonctions

- Ferme automatiquement **Quick Settings** lorsque le pointeur en sort, après un délai réglable (350 ms par défaut).
- Applique le même comportement au panneau **Calendrier / Notifications**.
- Masque optionnellement le bouton **Capture d’écran** de la rangée système.
- Remplace le bouton Réglages par un **bouton scindé** :
  - clic sur la roue dentée : ouvre **Paramètres GNOME** ;
  - clic sur le chevron : ouvre un menu avec **Ajustements**, **Éditeur dconf** et **Extensions Manager** ;
  - le bouton complet devient **bleu Adwaita uniquement tant que ce menu est ouvert**.
- Renomme optionnellement le profil de puissance en **Énergie**.
- Remplace Power par un **bouton scindé** :
  - clic principal : ouvre le dialogue GNOME **Éteindre** ;
  - clic sur le chevron : **Suspendre**, **Redémarrer**, **Reconnexion** et **Verrouiller la session** ;
  - le bouton complet devient **bleu Adwaita uniquement tant que ce menu est ouvert**.
- Retire le cadenas séparé de la rangée lorsque le bouton Power scindé est actif.
- Peut **masquer la liste des sorties audio** du curseur de volume (le chevron disparaît ; la sortie par défaut reste utilisée).
- Peut afficher la carte des rendez-vous en **couleur d’accent du système** (bleu par défaut), sans modifier le style de la date ni ajouter de bordure d’accent.
- Peut masquer complètement la grande colonne **Aucune notification** lorsque la liste est vide ; elle réapparaît automatiquement dès qu’une notification existe.

## Changements techniques

### v22 — Appel de l’OSD et journalisation

L’extension essaie plusieurs signatures possibles pour appeler l’OSD de GNOME Shell, conserve la première forme qui fonctionne et l’inscrit dans le journal. Au chargement, elle consigne également une fois la définition de la fonction OSD présente dans la session. Cette trace doit aider à identifier la signature réelle si aucune des trois formes essayées ne fonctionne.

En cas d’échec total, une seule erreur est consignée au lieu de répéter le même message en boucle.

### v25 — Liste des rendez-vous adaptative

La liste des rendez-vous prend désormais la hauteur nécessaire à son contenu :

- avec peu de rendez-vous, elle ne réserve plus un grand espace vide et s’arrête à la hauteur des cartes ;
- avec beaucoup de rendez-vous, elle grandit jusqu’à **300 px**, puis devient défilante ;
- le fondu au bord reste fixé à **14 px**.

**État des tests :** la v25 n’a pas pu être testée dans une session GNOME réelle. La nouvelle hauteur adaptative est donc documentée comme un changement à vérifier, pas comme un résultat confirmé.

## Hors périmètre

L’extension ne modifie ni le microphone ni le volume lui-même (seul le sélecteur de sortie peut être masqué). Elle ne change pas la sortie audio par défaut (par exemple JamesDSP).

## Préférences

```fish
gnome-extensions prefs focus-et-boutons@ogu
```

Toutes les options sont appliquées immédiatement.

## Installation

Le ZIP v25 doit être ajouté manuellement au dépôt dans ce dossier. Une fois l’archive présente, depuis le dossier qui la contient :

```fish
gnome-extensions install --force ./Focus-et-Boutons-v25.zip
gnome-extensions enable focus-et-boutons@ogu
```

Sous Wayland, une déconnexion/reconnexion peut être nécessaire après remplacement des fichiers de l’extension.

## Désinstallation

```fish
gnome-extensions uninstall focus-et-boutons@ogu
```
