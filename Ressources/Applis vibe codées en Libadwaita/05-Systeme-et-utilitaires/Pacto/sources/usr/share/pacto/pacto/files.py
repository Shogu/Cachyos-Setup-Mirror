"""Reading and modifying maintainer files, elevating with pkexec when needed."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from gi.repository import Gio, GLib

MAX_SIZE = 8 * 1024 * 1024


class ReadError(Exception):
    """A file could not be shown."""

    def __init__(self, message: str, needs_root: bool = False) -> None:
        super().__init__(message)
        self.needs_root = needs_root


def read_lines(path: Path, privileged: bool = False) -> list[str]:
    """Return the lines of a text file, optionally reading it through pkexec."""
    if privileged:
        data = _run_sync(_elevate(["cat", "--", str(path)]))
    else:
        try:
            if path.stat().st_size > MAX_SIZE:
                raise ReadError("This file is too large to be compared.")
            data = path.read_bytes()
        except PermissionError as error:
            raise ReadError(str(error), needs_root=True) from error
        except FileNotFoundError:
            return []
        except OSError as error:
            raise ReadError(str(error)) from error
    if b"\0" in data:
        raise ReadError("This looks like a binary file.")
    return data.decode("utf-8", errors="replace").splitlines()


def apply_new(pacfile: Path, target: Path) -> None:
    """Install the maintainer file over the file currently in use."""
    _privileged(["mv", "--", str(pacfile), str(target)])


def discard_new(pacfile: Path) -> None:
    """Remove the maintainer file and keep the file currently in use."""
    _privileged(["rm", "--", str(pacfile)])


def _privileged(argv: list[str]) -> None:
    _run_sync(_elevate(argv))


def _elevate(argv: list[str]) -> list[str]:
    """Prefix a command with pkexec unless we already run as root."""
    if os.geteuid() == 0:
        return argv
    if shutil.which("pkexec") is None:
        raise ReadError("pkexec is not available on this system.")
    return ["pkexec", *argv]


def _run_sync(argv: list[str]) -> bytes:
    try:
        process = Gio.Subprocess.new(argv, Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE)
        ok, stdout, stderr = process.communicate(None, None)
    except GLib.Error as error:
        raise ReadError(error.message) from error
    if not ok or process.get_exit_status() != 0:
        message = (stderr.get_data() or b"").decode(errors="replace").strip()
        raise ReadError(message or "The command was cancelled.")
    return stdout.get_data() or b""
