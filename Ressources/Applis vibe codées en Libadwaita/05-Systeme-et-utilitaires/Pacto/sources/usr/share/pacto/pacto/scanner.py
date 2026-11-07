"""Discovery of pacman maintainer files (.pacnew, .pacsave, .pacorig)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

SUFFIXES = (".pacnew", ".pacsave", ".pacorig")

SEARCH_ROOTS = ("/etc", "/boot", "/usr", "/opt", "/srv", "/var")

PRUNED = {
    "/proc",
    "/sys",
    "/dev",
    "/run",
    "/tmp",
    "/var/cache",
    "/var/tmp",
    "/var/lib/docker",
    "/var/lib/containers",
    "/usr/share/doc",
    "/usr/share/man",
    "/usr/share/locale",
    "/usr/lib/modules",
}


@dataclass(frozen=True)
class PacFile:
    """A maintainer file together with the installed file it relates to."""

    path: Path
    target: Path

    @property
    def kind(self) -> str:
        return self.path.suffix.lstrip(".")

    @property
    def target_exists(self) -> bool:
        return self.target.is_file()

    @property
    def mtime(self) -> float:
        try:
            return self.path.stat().st_mtime
        except OSError:
            return 0.0


def scan(roots: tuple[str, ...] = SEARCH_ROOTS) -> list[PacFile]:
    """Walk the given roots and return every maintainer file found, sorted by path."""
    found: list[PacFile] = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            dirnames[:] = [
                d for d in dirnames if os.path.join(dirpath, d) not in PRUNED
            ]
            for name in filenames:
                if name.endswith(SUFFIXES):
                    path = Path(dirpath) / name
                    found.append(PacFile(path=path, target=path.with_suffix("")))
    found.sort(key=lambda f: str(f.path))
    return found
