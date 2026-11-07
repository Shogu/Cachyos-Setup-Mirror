# SPDX-License-Identifier: GPL-3.0-or-later
"""File d'attente des paroles : recherche en arrière-plan, un morceau à la fois.

- les paroles « conformes » (artiste, titre, durée) sont écrites directement ;
- la file est gardée sur le disque et reprend au lancement suivant ;
- pause, reprise et arrêt à tout moment ;
- un morceau déjà essayé sans succès n'est pas réessayé tant qu'il n'a pas
  changé (fichier modifié).
"""

from __future__ import annotations

import json
import os
import threading

from gi.repository import GLib, GObject

from . import lyrics, tags

_DATA = os.path.join(GLib.get_user_data_dir(), "disquaire")
_STATE = os.path.join(_DATA, "lyrics-queue.json")
_TRIED = os.path.join(GLib.get_user_cache_dir(), "disquaire", "lyrics-tried.json")
PAUSE_BETWEEN = 1.0     # secondes entre deux requêtes (service gratuit : on le ménage)


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def _save(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path + ".tmp", "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)
        os.replace(path + ".tmp", path)
    except OSError:
        pass


def _mtime(path):
    try:
        return os.stat(path).st_mtime_ns
    except OSError:
        return None


class LyricsQueue(GObject.Object):
    __gtype_name__ = "DisquaireLyricsQueue"
    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        # paroles écrites dans le fichier
        "saved": (GObject.SignalFlags.RUN_FIRST, None, (str, str)),
        # paroles trouvées pour un morceau en cours de modification (non écrites)
        "found-unsaved": (GObject.SignalFlags.RUN_FIRST, None, (str, str)),
        "error": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "finished": (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
    }

    def __init__(self):
        super().__init__()
        st = _load(_STATE, {})
        self.pending: list[str] = st.get("pending", [])
        self.total = st.get("total", len(self.pending))
        self.done = st.get("done", 0)
        self.found = st.get("found", 0)
        self.not_found = st.get("not_found", 0)
        self.paused = st.get("paused", False)
        self.current = ""
        self._tried: dict[str, int] = _load(_TRIED, {})
        self._lock = threading.Lock()
        self.protected: set[str] = set()   # morceaux modifiés à la main : pas d'écriture
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        if not self.pending:
            self.total = self.done = self.found = self.not_found = 0

    # --- état -------------------------------------------------------------
    @property
    def active(self) -> bool:
        return bool(self.pending)

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _persist(self):
        with self._lock:
            data = {"pending": list(self.pending), "total": self.total, "done": self.done,
                    "found": self.found, "not_found": self.not_found,
                    "paused": self.paused}
            tried = dict(self._tried)
        _save(_STATE, data)
        _save(_TRIED, tried)

    def _notify(self):
        GLib.idle_add(lambda: (self.emit("changed"), False)[1])

    # --- commandes --------------------------------------------------------
    def enqueue(self, paths) -> int:
        with self._lock:
            known = set(self.pending)
            new = [p for p in paths if p not in known
                   and self._tried.get(p) != _mtime(p)]
            if not self.pending:
                self.total = self.done = self.found = self.not_found = 0
            self.pending.extend(new)
            self.total += len(new)
        self.paused = False
        self._persist()
        self.start()
        self.emit("changed")
        return len(new)

    def start(self):
        if self.paused or not self.pending or self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def pause(self):
        self.paused = True
        self._stop.set()
        self._persist()
        self.emit("changed")

    def resume(self):
        self.paused = False
        self._persist()
        self.start()
        self.emit("changed")

    def cancel(self):
        self._stop.set()
        with self._lock:
            self.pending.clear()
            self.total = self.done = self.found = self.not_found = 0
        self.paused = False
        self._persist()
        self.emit("changed")

    def shutdown(self):
        self._stop.set()
        self._persist()

    # --- travail ----------------------------------------------------------
    def _run(self):
        failures = 0
        since_save = 0
        while not self._stop.is_set():
            with self._lock:
                if not self.pending:
                    break
                path = self.pending[0]
            self.current = os.path.basename(path)
            self._notify()
            result = self._process(path)
            if result == "network":
                failures += 1
                if failures >= 3:
                    self.paused = True
                    self._persist()
                    GLib.idle_add(lambda: (self.emit(
                        "error", "Le service de paroles ne répond pas : file mise en pause."),
                        self.emit("changed"), False)[2])
                    return
                self._stop.wait(5)
                continue
            failures = 0
            with self._lock:
                if self.pending and self.pending[0] == path:
                    self.pending.pop(0)
                self.done += 1
                if result == "found":
                    self.found += 1
                elif result == "notfound":
                    self.not_found += 1
            since_save += 1
            if since_save >= 10:
                self._persist()
                since_save = 0
            self._notify()
            if result in ("found", "notfound"):
                self._stop.wait(PAUSE_BETWEEN)
        self.current = ""
        self._persist()
        self._notify()
        if not self._stop.is_set() and self.total:
            GLib.idle_add(lambda: (self.emit(
                "finished", self.found, self.not_found), False)[1])

    def _process(self, path: str) -> str:
        if not os.path.exists(path):
            return "skip"
        try:
            report = tags.read(path)
        except tags.TagError:
            return "skip"
        v = report.values
        if v.lyrics.strip():
            return "skip"
        from .textfmt import tags_from_filename
        filename_artist, filename_title = tags_from_filename(
            os.path.splitext(os.path.basename(path))[0])
        artist = v.artist.strip() or filename_artist
        title = v.title.strip() or filename_title
        if not title.strip():
            return "skip"
        try:
            cand = lyrics.best(artist, title, v.album, report.info.length)
        except lyrics.LyricsError:
            return "network"
        if cand is None:
            with self._lock:
                self._tried[path] = _mtime(path)
            return "notfound"
        with self._lock:
            protected = path in self.protected
        if protected:
            GLib.idle_add(lambda: (self.emit("found-unsaved", path, cand.text), False)[1])
            return "found"
        v.lyrics = cand.text
        try:
            tags.write(path, v)   # écrit aussi les tags nettoyés
        except tags.TagError as exc:
            message = (f"Paroles trouvées, mais impossibles à enregistrer dans "
                       f"« {os.path.basename(path)} » : {exc}")
            GLib.idle_add(lambda: (self.emit("error", message), False)[1])
            return "write-error"
        GLib.idle_add(lambda: (self.emit("saved", path, cand.text), False)[1])
        return "found"
