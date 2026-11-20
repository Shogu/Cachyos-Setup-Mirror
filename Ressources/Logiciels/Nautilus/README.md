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

## Aperçu et miniatures

- **[Thumbnailer Sushi](Thumbnailer%20Sushi/)** — deux paquets Arch : aperçus Sushi des documents (DOCX/ODT/RTF/Markdown), PDF simplifiés, présentations, tableurs et archives, miniatures des documents et fichiers texte/code, et coins arrondis Nautilus/Adwaita sur les vignettes. Un installeur (sous-dossier *Sushi thumbnailer extra*) purge automatiquement le cache des miniatures. README, captures et procédures dans le dossier.

## Scripts

- **[Nautilus sans pellicule](Scripts/nautilus-sans-pellicule/)** — remplace la ressource graphique `filmholes` par une image transparente via `G_RESOURCE_OVERLAYS`. Le script est réversible et conserve la sauvegarde de l'image d'origine dans son propre dossier.

## Composant associé — Sushi / Thumbnailer Sushi

**Thumbnailer Sushi** complète le workflow de Nautilus avec les aperçus rapides à la barre d’espace et des miniatures enrichies (documents, PDF, présentations, tableurs, fichiers texte/code et archives). Le paquet complémentaire applique les coins arrondis de style Nautilus/Adwaita aux miniatures.

- [Dossier Thumbnailer Sushi](../../Applis%20vibe%20codées%20en%20Libadwaita/03-Fichiers-et-telechargements/Thumbnailer%20Sushi/)
- [README et procédure d’installation](../../Applis%20vibe%20codées%20en%20Libadwaita/03-Fichiers-et-telechargements/Thumbnailer%20Sushi/README.md)
- [Chapitre 9.7 — Aperçu et miniatures avec Sushi](../../../docs/09-nautilus-workflow.md#97--aperçu-et-miniatures-avec-sushi)
- [Chapitre 11.31 — Thumbnailer Sushi](../../../docs/11-applications-vibe-coded.md#1131--thumbnailer-sushi)

Sushi reste volontairement dans son dossier d’origine, hors de l’arborescence centralisée ci-dessus. Ses paquets, son installeur et sa documentation ne sont pas déplacés ni modifiés.

## Documentation

- [Chapitre 9 — Nautilus : workflow](../../../docs/09-nautilus-workflow.md)
- [Chapitre 12 — Shell & terminal : intégration Ptyxis](../../../docs/12-shell-terminal.md#121--intégrer-ptyxis-à-nautilus-et-aux-outils-cachyos)
- [Maintenance](../../../docs/14-maintenance.md)
