#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Ré-injecte les deux correctifs locaux dans le window.py de Showtime.

Correctifs injectés (tous ADDITIFS ou substitutions ciblées, ancrés sur le
fichier d'origine) :
  A. Chargement automatique des sous-titres externes :
        à l'ouverture d'une vidéo, cherche <video>.fr.srt puis <video>.srt
        et la branche via self.play.props.suburi  (méthode _try_auto_subtitles)
  B. Comportement clavier :
        sauts ←/→ = 1% (min 5 s), ↑/↓ = 5% (min 30 s),
        Maj+←/→ = 10 s (ajustement fin), Supr = corbeille,
        volume déplacé sur Ctrl+↑/↓.

Sur une MAJ de Showtime, le paquet réécrit window.py et efface les correctifs.
Ce script les ré-applique proprement, SANS régresser le fichier entier :
il part de la version NEUVE du paquet (extraite de /var/cache/pacman/pkg,
sinon du fichier installé) et y applique des transformations vérifiées.

Idempotent : déjà tout appliqué -> ne fait rien.  Chaque transformation a un
ancrage ; si un ancrage manque (version trop différente), il s'arrête proprement
au lieu d'écrire un fichier incohérent.

Usage (racine, pkexec affichera la demande d'autorisation graphique) :
    pkexec python3 patch_showtime.py
"""

import pathlib
import shutil
import subprocess
import sys

TARGET = "/usr/lib/python3.14/site-packages/showtime/widgets/window.py"
BACKUP = TARGET + ".pre-ogu.bak"


# --------------------------------------------------------------------------- #
# Textes exacts des blocs à injecter (alignés sur showtime 50.1.1-1)
# --------------------------------------------------------------------------- #
SRT_METHOD = """    def _try_auto_subtitles(self, uri: str) -> None:
        \"\"\"Auto-load a sidecar subtitle file matching the video basename.\"\"\"
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

"""

KB_METHODS = """    def _seek_by(self, seconds: float) -> None:
        pos = self.play.props.position + seconds * Gst.SECOND
        if (dur := self.play.props.duration) > 0:
            pos = min(pos, dur - Gst.SECOND)
        self.play.seek(max(0, int(pos)))

    def _seek_by_percent(self, percent: float, min_secs: float) -> None:
        \"\"\"Saut en % de la durée, avec un saut minimal pour les vidéos courtes.\"\"\"
        dur_secs = max(self.play.props.duration, 0) / Gst.SECOND
        step = max(dur_secs * abs(percent) / 100, min_secs)
        self._seek_by(step if percent > 0 else -step)

    def _delete_current_video(self, *_args) -> None:
        \"\"\"Déplace la vidéo en cours de lecture vers la corbeille (SUPPR).\"\"\"
        if not (gfile := self._playing_gfile):
            return

        if not gfile.is_native():
            self.toast_overlay.add_toast(
                Adw.Toast.new(
                    "Seuls les fichiers locaux peuvent être déplacés vers la corbeille"
                )
            )
            return

        dialog = Adw.AlertDialog.new(
            "Déplacer vers la corbeille ?",
            None,
        )
        dialog.props.body = "« {} » sera déplacé dans la corbeille.".format(
            gfile.get_basename() or gfile.get_uri()
        )
        dialog.add_response("cancel", "Annuler")
        dialog.add_response("trash", "Déplacer vers la corbeille")
        dialog.set_response_appearance("trash", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.props.default_response = "cancel"
        dialog.props.close_response = "cancel"

        def on_response(_dialog, response: str) -> None:
            if response != "trash":
                return

            try:
                gfile.trash(None)
            except GLib.Error as error:
                logger.error("Could not move video to trash: %s", error.message)
                self.toast_overlay.add_toast(
                    Adw.Toast.new(
                        "Impossible de déplacer le fichier vers la corbeille"
                    )
                )
                return

            self.close()

        dialog.connect("response", on_response)
        dialog.present(self)

"""

KB_ACTIONS = """        # Sauts en % de la durée (avec minimum en secondes) :
        # ←/→ = 1 % (min 5 s), ↑/↓ = 5 % (min 30 s)
        for name, pct, min_secs, keys in (
            ("backwards", -1, 5, ("Left",)),
            ("forwards", 1, 5, ("Right",)),
            ("backwards-long", -5, 30, ("Down",)),
            ("forwards-long", 5, 30, ("Up",)),
        ):
            self._create_action(
                name,
                lambda *_, p=pct, m=min_secs: self._seek_by_percent(p, m),
                keys,
            )

        # Maj+←/→ = saut fixe de 10 s pour l'ajustement fin
        for name, secs, keys in (
            ("backwards-short", -10, ("<shift>Left",)),
            ("forwards-short", 10, ("<shift>Right",)),
        ):
            self._create_action(
                name,
                lambda *_, s=secs: self._seek_by(s),
                keys,
            )
"""

DELETE_FILE_ACTION = """        self._create_action(
            "delete-file",
            lambda *_: self._delete_current_video(),
            ("Delete",),
        ).props.enabled = False

"""


# --------------------------------------------------------------------------- #
# Transformations ordonnées (old -> new). old doit exister UNE fois au départ.
# --------------------------------------------------------------------------- #
PATCHES = [
    (
        "import os",
        "import json\n",
        "import json\nimport os\n",
    ),
    (
        "sous-titres auto : appel dans play_video",
        "        self.play.props.uri = uri\n        self.pause()\n",
        "        self.play.props.uri = uri\n"
        "        self._try_auto_subtitles(uri)\n"
        "        self.pause()\n",
    ),
    (
        "sous-titres auto : méthode",
        "    def teardown_playback(self) -> None:\n",
        SRT_METHOD + "    def teardown_playback(self) -> None:\n",
    ),
    (
        "clavier : méthodes _seek_by / _seek_by_percent / _delete_current_video",
        "    def _create_actions(self) -> None:\n",
        KB_METHODS + "    def _create_actions(self) -> None:\n",
    ),
    (
        "clavier : volume Ctrl+↑ / Ctrl+↓",
        '            ("Up",),\n',
        '            ("<primary>Up", "plus", "KP_Add"),\n',
    ),
    (
        "clavier : volume Ctrl+↓ (moins)",
        '            ("Down",),\n',
        '            ("<primary>Down", "minus", "KP_Subtract"),\n',
    ),
    (
        "clavier : remplacer backwards/forwards par sauts en %",
        '        self._create_action(\n'
        '            "backwards",\n'
        '            lambda *_: self.play.seek(max(0, self.play.props.position - 1e10)),\n'
        '            ("Left",),\n'
        '        )\n'
        '\n'
        '        self._create_action(\n'
        '            "forwards",\n'
        '            lambda *_: self.play.seek(self.play.props.position + 1e10),\n'
        '            ("Right",),\n'
        '        )\n',
        KB_ACTIONS,
    ),
    (
        "clavier : action delete-file (Supr)",
        '        ).props.enabled = False\n'
        '\n'
        '        self._create_action(\n'
        '            "open-video",\n',
        '        ).props.enabled = False\n'
        '\n'
        + DELETE_FILE_ACTION +
        '        self._create_action(\n'
        '            "open-video",\n'
        ,
    ),
    (
        "clavier : activer delete-file dans play_video",
        '        if action := lookup_action(self, "show-in-files"):\n'
        '            action.props.enabled = True\n'
        '\n'
        '    def unpause(self) -> None:\n',
        '        if action := lookup_action(self, "show-in-files"):\n'
        '            action.props.enabled = True\n'
        '\n'
        '        if action := lookup_action(self, "delete-file"):\n'
        '            action.props.enabled = True\n'
        '\n'
        '    def unpause(self) -> None:\n',
    ),
]


def pristine_from_pkg() -> str | None:
    """Reconstruit le window.py NEUF du paquet showtime depuis le cache pacman."""
    try:
        out = subprocess.run(
            ["pacman", "-Ql", "showtime"],
            capture_output=True, text=True,
        ).stdout
        pkg_path = None
        for line in out.splitlines():
            if line.endswith(".pkg.tar.zst"):
                pkg_path = line.split()[-1]
                break
        if not pkg_path:
            import glob as _g
            cands = _g.glob("/var/cache/pacman/pkg/showtime-*.pkg.tar.zst")
            pkg_path = cands[0] if cands else None
        if not pkg_path or not pathlib.Path(pkg_path).exists():
            return None
        data = subprocess.run(
            ["tar", "--zstd", "-xOf", pkg_path,
             "usr/lib/python3.14/site-packages/showtime/widgets/window.py"],
            capture_output=True,
        )
        if data.returncode != 0 or not data.stdout:
            return None
        return data.stdout.decode("utf-8")
    except Exception:
        return None


def is_fully_patched(text: str) -> bool:
    return (
        "def _try_auto_subtitles" in text
        and "def _seek_by_percent" in text
        and '"delete-file"' in text
    )


def main() -> int:
    target = pathlib.Path(TARGET)
    if not target.exists():
        print("Cible introuvable :", TARGET)
        return 1

    current = target.read_text()
    if is_fully_patched(current):
        print("Déjà tout appliqué (clavier + SRT) : rien à faire.")
        return 0

    # Base : version NEUVE du paquet si disponible (fiabilité sur maj), sinon
    # le fichier installé (on applique alors les ancrages directement dessus).
    base = pristine_from_pkg() or current
    if not is_fully_patched(current):
        # On conserve l'original une seule fois AVANT tout patch.
        if not pathlib.Path(BACKUP).exists():
            shutil.copyfile(target, BACKUP)
            print("Sauvegarde de l'original ->", BACKUP)

    text = base
    for name, old, new in PATCHES:
        if name == "import os" and "import os\n" in text:
            continue
        if new in text:
            continue  # déjà appliqué (idempotent)
        if text.count(old) != 1:
            print(
                f"ÉCHEC ancrage [{name}] : {text.count(old)} occurrence(s) de "
                "l'ancrage attendu. Version trop différente ? Aucun fichier "
                "écrit. Vérifie puis actualise ce script."
            )
            return 1
        text = text.replace(old, new, 1)
        print(f"  + {name}")

    target.write_text(text)
    print("Corrections injectées. Taille :", len(current), "->", len(text), "octets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
