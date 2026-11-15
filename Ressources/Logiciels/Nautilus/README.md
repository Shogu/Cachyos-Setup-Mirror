# Nautilus — ressources et personnalisations

Ce répertoire rassemble les composants du dépôt qui étendent ou personnalisent **GNOME Files (Nautilus)**. Les fichiers sont classés par fonction.

## Extensions et actions

### Extensions Python

- **[Nautilus Bookmark Icons](Extensions/Nautilus%20Bookmark%20Icons/)** — personnalisation des icônes des favoris dans la barre latérale. Le dossier contient le paquet Arch, le README et les notes techniques.
- **[Ouvrir dans OpenCode](Extensions/Opencode/)** — ajoute une entrée au menu contextuel pour ouvrir une session OpenCode dans le dossier visé.

### Actions contextuelles

- **[Hide](Extensions/Actions%20contextuelles/Hide)** — renomme les éléments sélectionnés en ajoutant un point initial pour les masquer.
- **[Unhide](Extensions/Actions%20contextuelles/Unhide)** — retire le point initial pour rendre visibles les éléments sélectionnés.

## Outils

- **[Nautilus-tools-ogu](Outils/Nautilus-tools/)** — intégration de Ptyxis : terminal dans le dossier, ouverture en root, terminal intégré, installation de paquets et copie de chemins.

## Scripts

- **[Nautilus sans pellicule](Scripts/nautilus-sans-pellicule/)** — remplace la ressource graphique `filmholes` par une image transparente via `G_RESOURCE_OVERLAYS`. Le script est réversible et conserve la sauvegarde de l'image d'origine dans son propre dossier.

## Documentation

- [Chapitre 9 — Nautilus : workflow](../../../docs/09-nautilus-workflow.md)
- [Chapitre 12 — Shell & terminal : intégration Ptyxis](../../../docs/12-shell-terminal.md#121--intégrer-ptyxis-à-nautilus-et-aux-outils-cachyos)
- [Maintenance](../../../docs/14-maintenance.md)

## Périmètre

Les composants **Sushi / Thumbnailer Sushi ne sont pas déplacés ni modifiés** : ils restent dans leur emplacement actuel, avec leur documentation et leurs procédures.
