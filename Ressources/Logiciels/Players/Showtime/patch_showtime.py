import pathlib, shutil

"""Correctif local Showtime : chargement automatique des sous-titres externes.

Le fichier installé (/usr/lib/python3.14/site-packages/showtime/widgets/window.py)
est modifie de facon PUREMENT ADDITIVE (aucun bloc existant remplace) :
  1. ajoute  `import os`
  2. ajoute  l'appel  `self._try_auto_subtitles(uri)`  juste apres
             `self.play.props.uri = uri`  dans  play_video()
  3. ajoute  la methode  `_try_auto_subtitles()`  (cherche `<video>.fr.srt` puis
             `<video>.srt` a cote de la video et la branche via `suburi`).

Le patch est IDEMPOTENT (deja applique -> ne fait rien) et SANS DANGER pour une
maj : chaque insertion a un ancrage controle ; si un ancrage n'est pas trouve,
le script s'arrete proprement au lieu d'ecrire un fichier incoherent.

Usage (en root, via pkexec demandera l'autorisation graphique) :
    pkexec python3 patch_showtime.py
"""

TARGET = "/usr/lib/python3.14/site-packages/showtime/widgets/window.py"
BACKUP = TARGET + ".pre-srt.bak"

p = pathlib.Path(TARGET)
if not p.exists():
    print("Cible introuvable:", TARGET)
    raise SystemExit(1)

s = p.read_text()

if "def _try_auto_subtitles" in s:
    print("Deja patche : rien a faire.")
    raise SystemExit(0)

# sauvegarde unique du fichier d'origine
if not pathlib.Path(BACKUP).exists():
    shutil.copyfile(TARGET, BACKUP)
    print("Sauvegarde de l'original ->", BACKUP)

orig = s

# 1) import os
if "import os\n" not in s:
    assert "import json\n" in s, "ancrage 'import json' introuvable"
    s = s.replace("import json\n", "import json\nimport os\n", 1)

# 2) appel auto sous-titres apres l'assignation uri
old_call = "        self.play.props.uri = uri\n"
assert old_call in s, "ancrage 'self.play.props.uri = uri' introuvable : version differente, verifie avant d'ecrire"
s = s.replace(old_call, old_call + "        self._try_auto_subtitles(uri)\n", 1)

# 3) methode (additive, passee avant teardown_playback)
method = '''    def _try_auto_subtitles(self, uri: str) -> None:
        """Auto-load a sidecar subtitle file matching the video basename."""
        try:
            vpath = Gio.File.new_for_uri(uri).get_path()
            if not vpath:
                return
            base = vpath.rsplit(".", 1)[0] if "." in vpath else vpath
            for suffix in (".fr.srt", ".srt"):
                cand = base + suffix
                if os.path.exists(cand):
                    self.play.props.suburi = Gio.File.new_for_path(cand).get_uri()
                    logger.debug("Auto subtitle loaded: %s", cand)
                    break
        except Exception:
            return

'''
anchor = "    def teardown_playback(self) -> None:\n"
assert anchor in s, "ancrage 'def teardown_playback' introuvable"
s = s.replace(anchor, method + anchor, 1)

p.write_text(s)
print("PATCH APPLIQUE.", len(orig), "->", len(s), "octets")
