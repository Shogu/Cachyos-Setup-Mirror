# ananicy-cpp-ogu — contournement (workaround), pas une amélioration

> **Ce paquet n’apporte rien de plus qu’ananicy-cpp.** Il sert uniquement à contourner un plantage du paquet CachyOS `ananicy-cpp` 1.2.0 sur cette machine. Il est **plus ancien** que la version officielle. Il faudra le remplacer par le paquet officiel dès qu’une version de celui-ci démarrera sans planter (voir « Retour au paquet officiel »).

## Le problème contourné

Sur cette machine (ASUS Zenbook 14 OLED, CachyOS, noyau 7.3.4-cachyos, ordonnanceur sched_ext `scx_pandemonium`), `ananicy-cpp 1.2.0-1.1` plante au démarrage, juste après « Doing a full scan » :

```text
kernel: ananicy-cpp[46191]: segfault at 10 ip … error 4 in ananicy-cpp[668b6,…]
systemd[1]: ananicy-cpp.service: Main process exited, code=dumped, status=11/SEGV
```

Le processus planté laisse aussi le verrou `/dev/shm/AnanicyCppMutex`. Toutes les relances suivantes échouent alors avec `Ananicy Cpp is already running!`, et le service boucle en `auto-restart`.

**Hypothèses, non prouvées.** Le plantage est un déréférencement de pointeur nul (`segfault at 10`), reproductible, au moment où démarrent la surveillance des processus et le premier scan. Deux nouveautés de la 1.2.0 sont suspectes :

1. **Surveillance des processus par BPF.** Le paquet 1.2.0 est lié à libbpf, alors que ce binaire utilise netlink. Une incompatibilité avec le noyau 7.3, ou une cohabitation difficile avec l’ordonnanceur sched_ext (lui aussi en BPF), est possible.
2. **Nouvelles options `apply_cpuset: true` et `x3d_mode: auto`**, absentes de la 1.1.1. Ce processeur a un seul bloc de cache L3 (16 Mo) et pas de cache X3D : un code qui chercherait un second bloc pourrait tomber sur un pointeur nul.

Aucune trace (backtrace) n’a été obtenue : les vidages mémoire sont désactivés (`systemd-coredump` masqué) et le binaire officiel est sans symboles.

**Résultat du test du 14/11/2026 : la piste 1 (BPF) est confirmée.** Le binaire officiel 1.2.0 (signature CachyOS vérifiée), lancé à la main 30 s, plante dans les deux cas : sans modification (témoin) et avec `apply_cpuset = false`. Juste avant le `SEGV`, il affiche `failed to attach BPF programs`. L’échec d’attachement BPF n’est pas géré, ce qui provoque le pointeur nul. Lockdown est inactif, et BTF (`/sys/kernel/btf/vmlinux`) ainsi que `CONFIG_BPF_SYSCALL` sont présents : la raison exacte du refus d’attachement reste à trouver (noyau 7.3, cohabitation avec sched_ext ?). Pistes : signaler le bug en amont avec ce message, ou compiler la 1.2.0 sans BPF.

**Test proposé à l’origine (fait, voir ci-dessus) :** ajouter `apply_cpuset = false` dans `/etc/ananicy.d/ananicy.conf`, puis relancer le paquet officiel (voir « Retour au paquet officiel »). S’il tient, c’est l’hypothèse 2 : le signaler en amont (gitlab.com/ananicy-cpp/ananicy-cpp/-/issues) et garder le paquet officiel avec ce réglage. Sinon, c’est probablement l’hypothèse 1 : il faudrait compiler la 1.2.0 sans BPF, ce qui donnerait un contournement plus récent que celui-ci.

## Contenu

| Fichier | Origine |
|---|---|
| `/usr/bin/ananicy-cpp` | Binaire **1.1.1.r17.g7fb9ed**, compilé depuis les sources (gitlab.com/ananicy-cpp/ananicy-cpp) le 21/02/2026, sans BPF. Il est identique octet pour octet à celui qui tournait dans `/usr/local/bin`. |
| `/usr/lib/systemd/system/ananicy-cpp.service` | L’unité de la compilation, avec trois retouches : chemins passés en `/usr/bin`, ligne `CPUAccounting=` supprimée (systemd ne la prend plus en charge), en-tête « contournement » ajouté. |
| `/etc/ananicy.d/` | Le dossier seulement. Les règles et `ananicy.conf` viennent de `cachyos-ananicy-rules`, qui ne change pas. |

Champs du paquet : `provides=(ananicy-cpp=1.1.1)`, `conflicts=(ananicy-cpp)`. Le paquet officiel est désinstallé à l’installation de celui-ci.

## Installation

Depuis la racine du dépôt :

```fish
sudo systemctl disable --now ananicy-cpp
sudo pacman -Rdd ananicy-cpp
sudo pacman -U "Ressources/Logiciels/Ananicy-cpp-ogu/ananicy-cpp-ogu-1.1.1.r17.g7fb9ed-1-x86_64.pkg.tar.zst"
sudo rm -f /dev/shm/AnanicyCppMutex
sudo systemctl enable --now ananicy-cpp
```

Si une ancienne installation `make install` existe encore dans `/usr/local` (voir [5.3](../../../docs/05-performance-tuning.md#53--ananicy-cpp--contournement-du-plantage-du-paquet-officiel)), la supprimer : sinon l’unité de `/usr/local` l’emporte sur celle du paquet.

```fish
sudo rm -f /usr/local/bin/ananicy-cpp /usr/local/lib/systemd/system/ananicy-cpp.service
sudo systemctl daemon-reload
```

Vérification :

```fish
systemctl show ananicy-cpp -p FragmentPath -p ActiveState   # /usr/lib/systemd/system/…, active
journalctl -u ananicy-cpp -b | grep 'Worker initialized'     # nombre de règles chargées
```

## Retour au paquet officiel

À tester à chaque nouvelle version d’`ananicy-cpp` dans les dépôts CachyOS (`pacman -Si ananicy-cpp`) :

```fish
sudo systemctl disable --now ananicy-cpp
sudo pacman -S ananicy-cpp          # accepter le remplacement d’ananicy-cpp-ogu
sudo rm -f /dev/shm/AnanicyCppMutex
sudo systemctl enable --now ananicy-cpp
sleep 30; systemctl show ananicy-cpp -p ActiveState -p NRestarts
journalctl -k -b | grep -i 'ananicy.*segfault'
```

Si le service est `active` avec `NRestarts=0` et qu’aucune ligne `segfault` n’apparaît, garder le paquet officiel et supprimer ce dossier. Sinon, réinstaller `ananicy-cpp-ogu` avec les commandes d’installation ci-dessus.

## Statut

- Paquet construit depuis le binaire en service. Le contenu a été inspecté et le binaire comparé (`cmp`) à l’original.
- Ce binaire tourne sans erreur en session réelle depuis le 14/11/2026, d’abord depuis `/usr/local`. L’installation en tant que paquet est vérifiée dans la même session (voir la doc 5.3).
- La cause exacte du plantage de la 1.2.0 n’est pas établie.
