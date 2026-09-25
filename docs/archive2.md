ARCHIVES


Configurer Paru pour nettoyer les dépendances de compilation et les fichiers de construction :

```fish
mkdir -p ~/.config/paru
cp /etc/paru.conf ~/.config/paru/paru.conf
gnome-text-editor ~/.config/paru/paru.conf
```

Dans la section `[options]`, activer les réglages suivants :

```ini
[options]
PgpFetch
Devel
Provides
DevelSuffixes = -git -cvs -svn -bzr -darcs -always -hg -fossil
AurOnly
BottomUp
RemoveMake
SudoLoop
#UseAsk
#SaveChanges
CombinedUpgrade
CleanAfter
UpgradeMenu
#NewsOnUpgrade
#SkipReview
```




Autre piste du mémo : utiliser LAVD en mode automatique avec `--autopower` pour son adaptation énergétique. Vérifier que le scheduler et le plugin installés acceptent cette combinaison.



## 10.2 — Outils optionnels

Installer [PacHub](https://github.com/mrks1469/PacHub) OU régler `pacseek` pour inclure paru à la place de yay si besoin, et `EnableAutoSuggest=true` + `ColorScheme=Endeavour OS` : soit avec Ctrl+S dans Pacseek, soit en éditant le json :

```fish
gnome-text-editor ~/.config/pacseek/config.json
```


**Ciné** à Celluloid. Pour Ciné, créer puis éditer :

```fish
mkdir -p ~/.config/cine
gnome-text-editor ~/.config/cine/input.conf
```

```text
# Flèches horizontales : 60 secondes ; verticales : 5 minutes.
RIGHT seek 60
LEFT seek -60
UP seek 300
DOWN seek -300
```

Pour les options du moteur vidéo, le mémo indique `vo=gpu-next` et `gpu-api=vulkan` dans **Paramètres → Divers → Options supplémentaires**. Adapter leur syntaxe au champ proposé par l'application : options de configuration MPV et arguments de ligne de commande ne se saisissent pas nécessairement de la même manière.

Activer les options **focus** et **toujours afficher les boutons de titre**. Installer les scripts Lua **Visualizer** et **Delete File** pour l'usage musical ; leurs URL ne sont pas précisées dans le README source.


Extensions Vivaldi

- [LocalCDN](https://chromewebstore.google.com/detail/localcdn/njdfdhgcmkocbgbhcioffdbicglldapd)
- [Better Scroll To Bottom](https://chromewebstore.google.com/detail/better-scroll-to-topbotto/ifdjdmipgndncbeopapghbohjdiieibl?hl=es)


Extensions GNOMES :
- [Custom Command Toggle](https://extensions.gnome.org/extension/7012/custom-command-toggle/)

- [Battery Monitor](https://extensions.gnome.org/extension/8348/battery-monitor/)
- [Media Controls](https://extensions.gnome.org/extension/4470/media-controls/)
- [Quick Settings Audio Device](https://extensions.gnome.org/extension/5964/quick-settings-audio-devices-hider/) pour masquer les périphériques audio inutiles. L'exemple JamesDSP du mémo est sans objet depuis sa désinstallation.
- [Night Light Slider](https://extensions.gnome.org/extension/6781/night-light-slider-updated/)
- [AppIndicator Quick Setting](https://github.com/VaZark/appindicator-quicksetting) : indicateurs d'applications dans les réglages rapides.
- [Appindicator](https://extensions.gnome.org/extension/615/appindicator-support/)
- [Slider percentages](https://extensions.gnome.org/extension/10125/slider-percentages/)

- [Windows Rounded Corners](https://extensions.gnome.org/extension/7048/rounded-window-corners-reborn/)
- [Lilypad Topbar Organizer](https://extensions.gnome.org/extension/7266/lilypad/)