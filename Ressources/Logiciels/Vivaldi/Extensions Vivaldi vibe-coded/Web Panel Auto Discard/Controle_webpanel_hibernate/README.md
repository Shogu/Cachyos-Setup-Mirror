# Contrôle Web Panel Hibernate

Script de contrôle complémentaire au mod **Web Panel Auto-Discard**. Il affiche en direct l'état de chaque web panel de Vivaldi : panneau affiché, masqué avec compte à rebours avant déchargement, exclu du déchargement ou déjà déchargé.

Le script `vivaldi-webpanel-status.py` sera placé manuellement dans ce dossier.

## Utilisation

Depuis ce dossier :

```bash
python3 vivaldi-webpanel-status.py
```

Effectue un relevé ponctuel de l'état des panneaux.

Pour actualiser l'affichage toutes les cinq secondes :

```bash
python3 vivaldi-webpanel-status.py --watch
```

Interrompre le mode continu avec **Ctrl+C**.

### Exemple d'affichage

```text
Délai de déchargement : 2 min 00 s   ·   exclus : claude.ai

  app.raindrop.io      ● affiché
  web.whatsapp.com     ◐ caché depuis 1 min 10 s → déchargement dans ~49 s
  claude.ai            ◌ caché, exclu (jamais déchargé)
  open.spotify.com     ○ déchargé ✔
```

## Prérequis

- Le mod **vivaldi-webpanel-auto-discard** doit être installé.
- Python 3 ; aucune dépendance Python supplémentaire.
- Vivaldi doit être lancé avec l'option `--remote-debugging-port=9222`.

Si Vivaldi n'est pas lancé avec ce port de débogage, le script propose de le fermer puis de le relancer avec cette option. La session peut être restaurée si Vivaldi est configuré pour rouvrir la dernière session.

> **Avertissement de sécurité :** tant que le port de débogage est ouvert, tout programme local peut piloter Vivaldi. Une fois le contrôle terminé, fermer Vivaldi puis le relancer normalement, sans `--remote-debugging-port=9222`.

## Vérification sans le script

Le gestionnaire de tâches intégré de Vivaldi (**Maj+Échap**) permet une vérification sommaire : un panneau déchargé disparaît de la liste ou n'y consomme presque plus de mémoire. Il ne fournit toutefois pas le détail des états et du compte à rebours affichés par le script.

## Emplacement

Ce dossier est réservé au script de suivi :

```text
Controle_webpanel_hibernate/
├── README.md
└── vivaldi-webpanel-status.py   # à ajouter manuellement
```

Le script n'est pas fourni ni créé par cette documentation : déposer ici le fichier `vivaldi-webpanel-status.py`.
