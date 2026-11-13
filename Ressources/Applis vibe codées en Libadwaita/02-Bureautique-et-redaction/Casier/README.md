# Casier

**Casier 1.3.0** est une application GTK4/libadwaita en Python pour récupérer, identifier, corriger et archiver les devoirs remis par les élèves.

Les élèves déposent leurs fichiers depuis un lien Dropbox File Request, sans compte Dropbox. Casier rapproche les fichiers des élèves, affiche les rendus, retards et copies manquantes, puis associe chaque copie à une note et une appréciation.

## Livrables

- casier-1.3.0-1-any.pkg.tar.zst — paquet Arch.
- casier-1.3.0-sources.tar.gz — sources Python, tests, métadonnées desktop et ressources.

## Installation

Depuis ce dossier :

~~~fish
sudo pacman -U ./casier-1.3.0-1-any.pkg.tar.zst
~~~

Dépendances automatiques : python-gobject, python-cairo, python-qrcode, gtk4, libadwaita, poppler-glib, libsoup3 et libsecret. Facultatifs : gst-plugins-good pour l’aperçu vidéo/audio et libheif pour les photos HEIC.

## Première connexion à Dropbox

Dans **Préférences → Dropbox → Connecter** :

1. Depuis la console Dropbox, créer une application **Scoped access → Full Dropbox**.
2. Accorder les permissions account_info.read, files.metadata.read, files.content.read, files.content.write, file_requests.read, file_requests.write, sharing.read et sharing.write.
3. Copier l’App key dans Casier.
4. Ouvrir la page d’autorisation, accepter, puis coller le code affiché.

L’accès est conservé dans le trousseau GNOME. Après l’ajout de permissions, déconnecter puis reconnecter Casier.

## Utilisation

1. Créer une classe et importer les élèves (un NOM Prénom par ligne ou un CSV Nom;Prénom).
2. Créer un devoir : titre, barème, date limite, consignes et éventuellement document de consignes. Casier crée la demande de fichiers Dropbox.
3. Partager le lien ou projeter le QR code.
4. Suivre les rendus : synchronisation toutes les deux minutes tant que la page du devoir est ouverte ; statuts **Rendu**, **En retard** et **Manquant**. Les fichiers non reconnus peuvent être attribués manuellement.
5. Corriger la copie (PDF, image, vidéo ou texte extrait d’un Word/ODT) avec note et appréciation. Ctrl+Page suivante / Ctrl+Page précédente change d’élève.
6. Fermer les dépôts à l’échéance.
7. Depuis le menu du devoir : renommer les fichiers (NOM_Prénom_Devoir), exporter les notes en CSV ou archiver le devoir.

Un dossier local (par exemple un dossier Dropbox synchronisé sur le PC) peut remplacer la demande de fichiers.

## Données et sauvegardes

| Donnée | Emplacement |
|---|---|
| Base | ~/.local/share/casier/casier.db |
| Sauvegardes automatiques (30 derniers jours) | ~/.local/share/casier/sauvegardes/ |
| Copies récupérées | ~/.local/share/casier/depots/ |
| Archives | ~/Documents/Casier/ (modifiable dans les Préférences) |
| Dossiers Dropbox | Casier/<année>/<classe>/<devoir> et Casier/<année>/<classe>/Consignes/ |

Le menu principal propose **Sauvegarder la base…** et **Restaurer une sauvegarde…**.

## Nettoyage

La suppression d’un devoir ou d’une classe peut également supprimer le lien, les copies et les consignes correspondants dans Dropbox. **Préférences → Dropbox → Nettoyer une année** supprime Casier/<année> côté Dropbox ; les notes et copies déjà récupérées localement restent dans Casier. Les fichiers supprimés dans Dropbox restent récupérables 30 jours dans « Fichiers supprimés ».

## Licence

GPL-3.0-or-later.
