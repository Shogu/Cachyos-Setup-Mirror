# 14 — Maintenance

[Accueil](../README.md) · [Précédent](13-vivaldi.md) · [Suivant](archives.md)

> **Dans ce chapitre :** tâches ponctuelles de maintenance, vérifications après mise à jour et dépannage réseau. Les réglages permanents sont documentés dans leur rubrique dédiée.

- [14.1 Retirer Cachy-update](#141--retirer-cachy-update)
- [14.2 Dépannage iwd](#142--dépannage-iwd)

## 14.1 — Retirer Cachy-update

Shelly est l'outil de mise à jour retenu pour ce setup. Pour supprimer Cachy-update, lancer :

```fish
sudo pacman -Rns cachy-update
```

Lire attentivement la liste des paquets proposés par Pacman avant de confirmer. Cette commande retire Cachy-update et les dépendances devenues inutiles ; elle ne désinstalle pas Paru.

La configuration de Shelly et son lanceur sont documentés dans [Shell & terminal](12-shell-terminal.md#123--shelly-et-le-lanceur-de-mise-à-jour). Le hook de protection de `/boot` est documenté dans [Boot & kernel](03-boot-kernel.md#37--protéger-les-transactions-noyau-si-boot-nest-pas-monté).

## 14.2 — Dépannage iwd

Symptôme : connexion qui échoue avec `state change: config → failed (reason 'no-secrets')`.

Log associé : `GDBus.Error:net.connman.iwd.Failed: Operation failed`.

Ou côté nmcli : « Des secrets étaient requis, mais aucun n'a été fourni ».

1. **Lister les profils et repérer les doublons :**

   ```fish
   nmcli connection show
   ```

   NetworkManager peut créer un nouveau profil dupliqué (`Xiaomi_03F1_5 1`, `Xiaomi_03F1_5 2`, etc.) à chaque reconnexion via l'interface graphique quand un profil du même nom existe déjà. Ces doublons n'ont souvent pas de mot de passe correctement enregistré.

2. **Supprimer les profils liés au SSID concerné.** Adapter la liste selon ce que renvoie `nmcli connection show` :

   ```fish
   nmcli connection delete Xiaomi_03F1_5 "Xiaomi_03F1_5 1" "Xiaomi_03F1_5 2"
   ```

3. **Vérifier que le réseau est visible :**

   ```fish
   nmcli device wifi rescan
   nmcli device wifi list
   ```

4. **Recréer le profil proprement, mot de passe fourni en CLI :**

   ```fish
   nmcli device wifi connect Xiaomi_03F1_5 password "MOT_DE_PASSE"
   ```

   Si un profil `Xiaomi_03F1_5` existe encore, même s'il n'apparaît pas dans la liste des réseaux, nmcli peut tenter de le réactiver tel quel et ignorer le mot de passe fourni. Supprimer d'abord les profils existants.

5. **Si l'erreur persiste, vérifier le stockage propre à iwd.** Il est distinct des fichiers NetworkManager :

   ```fish
   sudo ls -la /var/lib/iwd/
   ```

   Si une entrée `Xiaomi_03F1_5.psk` corrompue ou obsolète existe, la supprimer puis recréer la connexion :

   ```fish
   sudo rm "/var/lib/iwd/Xiaomi_03F1_5.psk"
   sudo systemctl restart iwd NetworkManager
   nmcli device wifi connect Xiaomi_03F1_5 password "MOT_DE_PASSE"
   ```

6. **Reconnecter le profil**, depuis GNOME si le dialogue le propose, ou en CLI :

   ```fish
   nmcli connection up Xiaomi_03F1_5
   ```

   Préférer `connection up` à une reconnexion via l'interface graphique pour éviter que NetworkManager ne crée un doublon.

---

[Accueil](../README.md) · [Précédent](13-vivaldi.md) · [Suivant](archives.md)
