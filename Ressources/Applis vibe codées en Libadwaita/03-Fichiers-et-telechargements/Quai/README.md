# Quai

Un petit serveur FTP pour Android TV, compagnon de Fret : il permet de
copier des fichiers entre l'ordinateur et la TV, depuis le second panneau de Fret.

Usage strictement personnel, sur le réseau local.

## Ce qu'il fait

- Un serveur FTP protégé par mot de passe, sur le port 2121 par défaut.
- Le mot de passe est tiré au hasard au premier lancement ; il se voit et se change dans Quai.
  N'importe quel nom d'utilisateur est accepté, seul le mot de passe compte.
- Lecture et écriture (envoi, téléchargement, reprise, création, renommage, suppression).
- Stockage interne de la TV, ou un disque externe branché (un bouton par disque).
- Fait pour la télécommande : aucun sélecteur de dossier, tout se règle d'un bouton OK.
- Aucune dépendance : tout est écrit à la main, sans bibliothèque externe.

## Deux tuiles dans la liste des applis

| Tuile | Rôle |
| --- | --- |
| **Quai** | Les réglages : démarrer ou arrêter, adresse, mot de passe, port, disque, démarrage avec la TV. |
| **Quai ON/OFF** | Un interrupteur sans écran : un appui démarre le serveur et affiche son adresse, un second l'arrête. |

Le serveur tourne en service au premier plan, avec une notification qui rappelle son adresse
(`ftp://192.168.1.x:2121`) et un bouton « Arrêter ».

## Utilisation avec Fret

1. Sur la TV, ouvre **Quai ON/OFF** (ou **Quai** → Démarrer). Note l'adresse affichée.
2. Dans Fret, dans le panneau de ton choix, tape <kbd>Ctrl</kbd>+<kbd>L</kbd> et saisis
   `ftp://192.168.1.x:2121`.
3. Donne n'importe quel nom d'utilisateur et le mot de passe de Quai.
4. Glisse, copie ou déplace comme entre deux dossiers locaux.

Pour connaître l'adresse de la TV : elle est dans la notification de Quai, dans l'écran
de Quai, ou dans le message de **Quai ON/OFF**. Une adresse fixe réservée dans la box évite
de la rechercher à chaque fois.

## Démarrage automatique

Quai essaie de se lancer tout seul (démarrage de la TV, disque branché, surveillance chaque
minute), mais **les TV TCL bloquent souvent le démarrage des applis installées à la main** :
ça marche parfois, pas toujours. La ligne « Dernier démarrage automatique » dans Quai dit
quand et pourquoi le serveur s'est lancé seul. Si rien ne démarre, **Quai ON/OFF** le fait en un appui.

Un arrêt volontaire (interrupteur, bouton des réglages ou de la notification) n'est pas
défait : le serveur ne repart seul qu'après un nouveau démarrage de ta part.

Quand TCL monte son disque externe longtemps après le démarrage, Quai relance son serveur pour
qu'il voie le disque.

## Sécurité

Le FTP envoie le mot de passe et les fichiers **en clair**. C'est sans importance sur ton
réseau domestique, mais n'ouvre jamais le port sur Internet (pas de redirection de port sur
la box). Arrête le serveur quand tu ne t'en sers pas.

## Installer

Copie `Quai-x.y.apk` sur la TV (clé USB, ou un gestionnaire de fichiers de la TV), ouvre-le et autorise
l'installation depuis cette source. Les mises à jour se font par-dessus, sans perdre les réglages.

Android TV 6 ou plus (API 23).

## Compiler

Les sources se construisent sans Gradle, avec les paquets Ubuntu `android-sdk-platform-23`,
`aapt`, `dalvik-exchange`, `zipalign` et `apksigner`, plus un JDK :

```sh
keytool -genkeypair -keystore quai.keystore -alias quai -keyalg RSA -keysize 2048 -validity 36500
export QUAI_KS_PASS=…   # le mot de passe de ce trousseau
./build.sh              # produit Quai-<version>.apk
```

Le trousseau de signature (`quai.keystore`) est à toi : ne le publie pas. Un
`.gitignore` utile : `*.keystore`, `*.apk`, `*.idsig`, `build/`.

## Organisation du code

| Fichier | Rôle |
| --- | --- |
| `FtpServer`, `FtpSession` | Le serveur et le dialogue FTP (PASV/EPSV, REST, MLSD…) |
| `Storage`, `FileStorage`, `SafStorage` | Accès aux fichiers : direct ou via l'accès au disque d'Android |
| `FtpService` | Service au premier plan, notification, verrous de veille pendant un transfert |
| `MainActivity` | Les réglages, pensés pour la télécommande |
| `ToggleActivity` | L'interrupteur sans écran |
| `BootReceiver`, `Watchdog` | Les démarrages automatiques |
| `Volumes`, `Settings`, `Paths` | Disques branchés, préférences, chemins FTP |
