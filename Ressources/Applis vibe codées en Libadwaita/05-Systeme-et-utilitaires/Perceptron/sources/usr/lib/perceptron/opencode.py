"""Démarrage du service OpenCode et appairage, sans bloquer la boucle GTK."""

import re

from gi.repository import Gio, GLib

from config import find_opencode
from journal import log

TIMEOUT_SECONDS = 25
PAIR_LINK = re.compile(r"http://127\.0\.0\.1:\d+/auth/connect/\S+")


class Command:
    """Processus enfant avec délai maximal.

    Sans capture, on attend la fin du processus et non la fermeture de ses
    sorties : le service lancé par `opencode service start` peut hériter du tube.
    """

    def __init__(self, argv, on_done, capture=False, cwd=None):
        flags = Gio.SubprocessFlags.STDERR_SILENCE
        flags |= Gio.SubprocessFlags.STDOUT_PIPE if capture else Gio.SubprocessFlags.STDOUT_SILENCE
        self._argv = argv
        self._on_done = on_done
        self._capture = capture
        if cwd:
            launcher = Gio.SubprocessLauncher.new(flags)
            launcher.set_cwd(cwd)
            self._process = launcher.spawnv(argv)
        else:
            self._process = Gio.Subprocess.new(argv, flags)
        self._timeout_id = GLib.timeout_add_seconds(TIMEOUT_SECONDS, self._on_timeout)
        if capture:
            self._process.communicate_utf8_async(None, None, self._on_finished)
        else:
            self._process.wait_async(None, self._on_finished)

    def _on_timeout(self):
        self._timeout_id = 0
        log("commande : délai dépassé pour " + " ".join(self._argv))
        self._process.force_exit()
        return GLib.SOURCE_REMOVE

    def _on_finished(self, process, result):
        if self._timeout_id:
            GLib.Source.remove(self._timeout_id)
            self._timeout_id = 0
        output = ""
        try:
            if self._capture:
                output = process.communicate_utf8_finish(result)[1] or ""
            else:
                process.wait_finish(result)
                log("commande : %s → code %d" % (" ".join(self._argv[1:]), process.get_exit_status()))
        except GLib.Error as error:
            log("commande : %s : %s" % (" ".join(self._argv), error.message))
        self._on_done(output)


def connect(on_ready, start_dir=None):
    """Démarre le service en arrière-plan puis demande un lien d'appairage.

    on_ready(uri) reçoit le lien d'appairage, "" s'il n'a pas pu être obtenu,
    ou None si `opencode` est introuvable.

    start_dir : dossier projet. OpenCode ne possède qu'UN seul service en
    arrière-plan par utilisateur ; pour travailler dans le dossier demandé
    (comme le fait le TUI lancé depuis ce dossier), on stoppe puis redémarre
    le service avec `start_dir` comme répertoire de travail.
    """
    binary = find_opencode()
    if binary is None:
        log("commande : opencode introuvable (PATH et ~/.opencode/bin)")
        on_ready(None)
        return
    log("commande : " + binary)

    def on_paired(output):
        match = PAIR_LINK.search(output)
        if not match:
            log("appairage : aucun lien dans la sortie de `opencode pair`")
        on_ready(match.group(0) if match else "")

    if start_dir:
        def on_restarted(_output):
            Command([binary, "pair"], on_paired, capture=True, cwd=start_dir)

        def on_stopped(_output):
            log("service : redémarrage dans " + start_dir)
            Command([binary, "service", "start"], on_restarted, cwd=start_dir)

        Command([binary, "service", "stop"], on_stopped)
        return

    def on_started(_output):
        Command([binary, "pair"], on_paired, capture=True)

    Command([binary, "service", "start"], on_started)
