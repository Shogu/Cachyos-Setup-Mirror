# Grabber

Frontend GTK4/libadwaita minimal pour **JDownloader 2** : trouver des liens (LinkGrabber), choisir les fichiers, télécharger, suivre la file. Livré en **AppImage** (`Grabber.AppImage`), pas en paquet pacman.

`readme_grabber.md` est la spécification complète (fonctions, options volontairement retirées, corrections). La consulter avant toute modification ; la section « Options volontairement retirées » liste ce qu'il ne faut **pas** réintroduire (pause/reprise ciblées, mode Doodstream, remoteAPI/My.JDownloader, .desktop automatique, service systemd, sous-dossiers auto…).

## Technique

- **Python / PyGObject**, package `jd_adwaita/` (app, ui, settings, api, process, clipboard, clipboard_utils, domains, formatting, favicons) + `tests/`. Version dans `pyproject.toml` (documentée : 0.10.30). App id `com.ogu.Grabber`, classe de fenêtre `Grabber`.
- Pilote une JVM JDownloader headless lancée et possédée par l'app (`java -Djava.awt.headless=true -jar JDownloader.jar -norestart`) via l'API locale **http://127.0.0.1:3128** (non authentifiée, ne jamais l'exposer).
- AppImage : embarque JRE Temurin 17 + JDownloader + frontend ; GTK4/libadwaita/Python/PyGObject viennent de l'hôte. Build : `./scripts/build-appimage.sh` → `dist/grabber-VERSION-x86_64.AppImage`.
- Données : `~/.config/jd-adwaita/config.json`, `~/.local/share/jd-adwaita/jdownloader`.
- `--install-desktop` installe explicitement lanceur + icône ; le démarrage normal n'en crée pas.

## Vérifications

```fish
python3 -m compileall -q jd_adwaita tests
PYTHONPATH=. python3 -m unittest discover -s tests
```

Les sources ne sont pas dans ce dossier ; le frontend se lit en extrayant l'AppImage (`./Grabber.AppImage --appimage-extract` dans un dossier temporaire). Toute opération par identifiant de lien, jamais par nom de fichier.
