# SPDX-License-Identifier: GPL-3.0-or-later
"""Conversion FLAC → MP3 (CBR 320 kb/s, 44,1 kHz) avec ffmpeg.

Le MP3 reçoit uniquement les tags conservés (ceux en cours d'édition, même non
enregistrés), puis le FLAC d'origine est envoyé à la corbeille.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import threading

from . import tags

BITRATE = "320k"
SAMPLE_RATE = "44100"


class ConversionError(Exception):
    pass


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def unique_path(path: str) -> str:
    """Renvoie `path`, ou `nom (2).ext`, `nom (3).ext`… s'il existe déjà."""
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    n = 2
    while os.path.exists(f"{stem} ({n}){ext}"):
        n += 1
    return f"{stem} ({n}){ext}"


class Converter:
    """Une conversion annulable. `progress(fraction)` est appelé depuis le thread."""

    def __init__(self):
        self._proc: subprocess.Popen | None = None
        self._cancelled = threading.Event()

    def cancel(self) -> None:
        self._cancelled.set()
        proc = self._proc
        if proc and proc.poll() is None:
            proc.terminate()

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    def convert(self, src: str, values: tags.TagValues, duration: float,
                progress=None) -> str:
        """Convertit `src` et renvoie le chemin du MP3 créé.

        Le FLAC n'est PAS supprimé ici : c'est à l'appelant de le mettre à la
        corbeille une fois le MP3 validé.
        """
        if not ffmpeg_available():
            raise ConversionError("ffmpeg est introuvable.")
        folder = os.path.dirname(src)
        stem = os.path.splitext(os.path.basename(src))[0]
        tmp = os.path.join(folder, f".{stem}.disquaire-tmp.mp3")
        cmd = [
            "ffmpeg", "-hide_banner", "-nostdin", "-y", "-nostats",
            "-i", src,
            "-map", "0:a:0", "-vn", "-map_metadata", "-1",
            "-c:a", "libmp3lame", "-b:a", BITRATE, "-ar", SAMPLE_RATE,
            "-id3v2_version", "0", "-write_xing", "1",
            "-progress", "pipe:1",
            "-f", "mp3", tmp,
        ]
        try:
            self._proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            stderr_chunks: list[str] = []
            reader = threading.Thread(
                target=lambda: stderr_chunks.append(self._proc.stderr.read()),
                daemon=True,
            )
            reader.start()
            for line in self._proc.stdout:
                if progress and duration > 0 and line.startswith("out_time_us="):
                    try:
                        us = int(line.split("=", 1)[1])
                        progress(min(us / 1_000_000 / duration, 1.0))
                    except ValueError:
                        pass
            code = self._proc.wait()
            reader.join(timeout=2)
            if self.cancelled:
                raise ConversionError("Conversion annulée.")
            if code != 0:
                tail = "".join(stderr_chunks).strip().splitlines()[-3:]
                raise ConversionError("ffmpeg a échoué : " + " ".join(tail))
            tags.write(tmp, values)
            final = unique_path(os.path.join(folder, stem + ".mp3"))
            os.replace(tmp, final)
            if progress:
                progress(1.0)
            return final
        except tags.TagError as exc:
            raise ConversionError(str(exc)) from exc
        finally:
            self._proc = None
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
