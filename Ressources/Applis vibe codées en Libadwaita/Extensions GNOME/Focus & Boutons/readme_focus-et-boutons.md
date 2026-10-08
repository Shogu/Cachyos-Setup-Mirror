# Focus & Boutons v14

Extension GNOME Shell ciblant GNOME 50 et 51.

## Fonctions

- Ferme automatiquement **Quick Settings** quand le pointeur en sort, après un délai réglable (350 ms par défaut).
- Applique le même comportement au panneau **Calendrier / Notifications**.
- Masque optionnellement le bouton **Capture d’écran** de la rangée système.
- Remplace le bouton Réglages par un **bouton scindé** :
  - clic sur la roue dentée : ouvre **Paramètres GNOME** ;
  - clic sur le chevron : ouvre un menu avec **Ajustements**, **Éditeur dconf** et **Extensions Manager** ;
  - le bouton complet devient **bleu Adwaita uniquement tant que ce menu est ouvert**.
- Renomme optionnellement le profil de puissance en **Énergie**.
- Remplace Power par un **bouton scindé** :
  - clic principal : ouvre le dialogue GNOME **Éteindre** ;
  - clic sur le chevron : **Suspendre**, **Redémarrer**, **Redémarrer la session**, **Verrouiller la session** ;
  - le bouton complet devient **bleu Adwaita uniquement tant que ce menu est ouvert**.
- Retire le cadenas séparé de la rangée lorsque le bouton Power scindé est actif.
- Peut **masquer la liste des sorties audio** du curseur de volume (le chevron disparaît ; la sortie par défaut reste utilisée).
- Peut afficher la carte des rendez-vous en **couleur d’accent du système** (bleu par défaut), sans modifier le style de la date ni ajouter de bordure d’accent.
- Peut masquer complètement la grande colonne **Aucune notification** lorsque la liste est vide ; elle réapparaît automatiquement dès qu’une notification existe.

## Hors périmètre

L’extension ne modifie ni le microphone ni le volume lui-même (seul le sélecteur de sortie peut être masqué). Elle ne change pas la sortie audio par défaut (par exemple JamesDSP).

## Préférences

```fish
gnome-extensions prefs focus-et-boutons@ogu
```

Toutes les options sont appliquées immédiatement.

## Installation

**Le dépôt contient encore le ZIP v12. Le ZIP v14 décrit ici reste à ajouter ; ne pas renommer le paquet v12 en v14.** Après récupération de la v14, depuis le dossier qui contient l’archive :

```fish
gnome-extensions install --force ./Focus-et-Boutons-v14.zip
gnome-extensions enable focus-et-boutons@ogu
```

Sous Wayland, une déconnexion/reconnexion peut être nécessaire après remplacement des fichiers de l’extension.
