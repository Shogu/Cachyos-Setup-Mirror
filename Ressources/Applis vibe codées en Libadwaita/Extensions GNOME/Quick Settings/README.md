# Quick Settings

Extension GNOME Shell qui regroupe les personnalisations de la barre supérieure et du panneau **Réglages rapides**. Elle reprend les fonctions de Focus & Boutons et de Battery Time Compact — Ogu.

- **UUID :** `quick-settings@ogu`
- **Compatibilité visée :** GNOME 50 et 51
- **Préférences :** `gnome-extensions prefs quick-settings@ogu`
- **Pages :** Réglages rapides · Barre du haut

Chaque fonction peut être désactivée indépendamment.

## Commandes rapides dans le panneau

Quick Settings regroupe également plusieurs interrupteurs et commandes système :

- **Mise à jour Shelly** : lance le script de mise à jour configuré.
- **Task Manager / Ressources** : ouvre l'application Ressources et donne accès à ses mesures système détaillées.
- **Fermer les applis** : demande confirmation avant de fermer les fenêtres sélectionnées dans les préférences.
- **Dropbox** : contrôle l'état du client, ouvre le dossier synchronisé, donne accès aux derniers fichiers et à leurs liens de partage, et permet de quitter ou relancer le client.
- **Éclairage nocturne** : active ou désactive la lumière nocturne ; le chevron permet de régler la température de couleur.


> **Validation :** les préférences s'ouvrent correctement. Les mesures de Ressources et le dialogue avec Dropbox ont été vérifiés séparément. L'extension n'a pas encore été exécutée dans une session GNOME Shell : le comportement intégré reste donc à confirmer.

## Fermeture automatique

Le panneau se ferme lorsque le pointeur en sort, après un délai réglable de **100 à 2 000 ms** (350 ms par défaut).

Il reste ouvert :
- tant qu'un bouton de la souris est maintenu ;
- pendant la saisie dans un champ, notamment le mot de passe Wi-Fi ;
- si le panneau se rétrécit sous un pointeur immobile.

## Rangée système

- **Capture d'écran :** masquée dans le panneau ; les raccourcis clavier GNOME restent disponibles.
- **Réglages scindé :** clic sur la roue dentée pour ouvrir Paramètres ; chevron pour accéder à Ajustements, Éditeur dconf et Extensions.
- **Power scindé :** clic pour éteindre ; chevron pour Suspendre, Redémarrer, Reconnexion et Verrouiller.
- **Reconnexion :** dans la fenêtre de confirmation GNOME, remplace « Fermer la session » dans le titre et sur le bouton.

## Tuiles et pilules

### Ressources

Affiche un sous-titre synthétique, par exemple `CPU 12 % · RAM 41 % · 52 °C`.

- Clic : ouvre l'application Ressources.
- Chevron : affiche le processeur, la température, la mémoire, le GPU, le disque personnel, le réseau (débits ↓ et ↑), la batterie (puissance et autonomie) et l'application la plus gourmande.
- Les processus sont regroupés sous l'application qui les a lancés.
- La tuile devient bleue lorsque le processeur dépasse 80 %.
- Aucune mesure n'est effectuée lorsque Quick Settings est fermé ; les mesures sont actualisées toutes les 2 secondes lorsque le panneau est ouvert.

### Dropbox

- Bleu lorsque Dropbox fonctionne ; gris lorsqu'il est en pause ou arrêté.
- Le sous-titre indique l'état de Dropbox.
- Clic : ouvre le dossier Dropbox.
- Chevron : affiche les cinq derniers fichiers modifiés (ouvrir un fichier ou copier son lien de partage), les commandes Mettre en pause / Reprendre et l'accès au site web.

**Particularité de Dropbox pour Linux :** il ne propose pas de véritable fonction de pause. « Mettre en pause » quitte donc le client ; « Reprendre » le relance.

### Upgrade

Un clic lance le script de mise à jour configuré, par défaut :

`~/.local/bin/update-shelly.sh`

La tuile est bleue pendant son exécution.

### Fermer les applis

Le premier clic demande confirmation (« Fermer N fenêtres ? »). Le second ferme chaque fenêtre comme si l'on cliquait sur sa croix : les applications peuvent donc demander l'enregistrement des documents non sauvegardés. Les applications à conserver se sélectionnent dans les préférences.

### Éclairage nocturne

Commande scindée : clic pour activer ou désactiver l'éclairage nocturne ; chevron pour régler la température de couleur.

### Charge batterie

Accès direct à la fonction « Préserver la santé de la batterie » des Paramètres, lorsque le matériel prend cette fonction en charge.

### Projecteur

Propose les modes Dupliquer, Étendre, Écran externe seul et Écran intégré seul. La tuile n'apparaît que lorsqu'un deuxième écran est connecté.

## Barre du haut

### Batterie

Affiche l'autonomie et le pourcentage à côté de l'icône, par exemple `9:27 - 56 %`. Le format est configurable : pourcentage puis temps, temps seul ou pourcentage seul.

Dans le panneau Réglages rapides, le bouton batterie peut afficher la puissance instantanée UPower, par exemple `9:27 - 4.2 W`.

- Autonomie indisponible : `…`
- Batterie pleine : `∞`
- Puissance inconnue : seule l'autonomie est affichée.

### Anneau des transferts

Pendant une copie Fret, un téléchargement Grabber ou une synchronisation Dropbox, un anneau aux couleurs de l'accent GNOME affiche la progression en pourcentage.

Un clic ouvre le détail du transfert par application. L'indicateur disparaît à la fin du transfert ou lorsque l'application concernée est fermée.

## Préférences

Ouvrir les préférences depuis GNOME Extensions ou avec :

```bash
gnome-extensions prefs quick-settings@ogu
```

Les deux pages disponibles sont **Réglages rapides** et **Barre du haut**. Les fonctions sont indépendantes et peuvent être désactivées séparément.

## Historique

### Quick Settings 1 — 9 novembre 2026

- Réunit les fonctions auparavant réparties entre Focus & Boutons et Battery Time Compact — Ogu.
- Ajoute les tuiles Ressources et Dropbox.
- Intègre la synchronisation Dropbox à l'anneau des transferts.
- Réorganise le code en modules à responsabilité unique.
- Sépare les préférences en deux pages : Réglages rapides et Barre du haut.
- Dispose de sa propre fermeture automatique et de son propre délai.
