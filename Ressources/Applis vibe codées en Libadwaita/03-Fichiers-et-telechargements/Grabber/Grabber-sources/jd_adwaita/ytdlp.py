from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlsplit
from typing import Callable, Iterable

from .domains import domain_matches

# Sites JDownloader cannot fetch on its own; they are handed to yt-dlp, which
# reads the browser's cookies itself.  The list of such sites belongs to the
# user: it comes from the configuration file, is empty out of the box, and is
# therefore absent from the sources shipped in a release.

_SIZE_UNITS = {"B": 1, "KIB": 1024, "MIB": 1024 ** 2, "GIB": 1024 ** 3, "TIB": 1024 ** 4}
_PROGRESS_RE = re.compile(
    r"\[download\]\s+(?P<percent>\d+(?:[.,]\d+)?)%\s+of\s+~?\s*(?P<size>\d+(?:\.\d+)?)\s*(?P<unit>[KMGT]?i?B)",
    re.IGNORECASE,
)
_DESTINATION_RE = re.compile(r"^\[download\]\s+Destination:\s+(?P<path>.+)$")

BROWSER_ENV = "JD_ADWAITA_YTDLP_BROWSER"
PATH_ENV = "JD_ADWAITA_YTDLP_PATH"
DEFAULT_BROWSER = "vivaldi"


def stable_path() -> Path:
    base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "jd-adwaita" / "bin" / "yt-dlp"


def find_ytdlp() -> str | None:
    for candidate in (os.environ.get(PATH_ENV), str(stable_path())):
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    return shutil.which("yt-dlp")


def browser_name() -> str:
    return os.environ.get(BROWSER_ENV) or DEFAULT_BROWSER


def default_log_path() -> Path:
    base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return base / "jd-adwaita" / "ytdlp.log"


def write_note(message: str) -> None:
    """Leave a trace in the yt-dlp log when the action cannot even start."""
    path = default_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(message + "\n", encoding="utf-8")


def handles(url: str, domains: Iterable[str] | None = None) -> bool:
    """True when this link belongs to a site JDownloader cannot download.

    ``domains`` is the user's configured list.  An empty or missing list means
    no handoff at all — never a built-in one, so no site is named in the code.
    """
    host = urlsplit(str(url or "")).hostname
    if not host:
        return False
    return any(domain_matches(host, pattern) for pattern in (domains or ()))


def parse_progress(line: str) -> tuple[int, int] | None:
    """Read the (loaded, total) byte counts out of a yt-dlp progress line."""
    match = _PROGRESS_RE.search(str(line or ""))
    if match is None:
        return None
    total = int(float(match.group("size")) * _SIZE_UNITS.get(match.group("unit").upper(), 1))
    percent = float(match.group("percent").replace(",", "."))
    return int(total * percent / 100), total


def parse_destination(line: str) -> str | None:
    match = _DESTINATION_RE.match(str(line or "").strip())
    return match.group("path").strip() if match else None


def log_directory() -> Path:
    return default_log_path().parent


def job_log_path(url: str) -> Path:
    """One log per link, named after a digest of that link.

    Not after the link's own tail: that would write the identifier of the
    download into a directory listing, which is the place people forget to
    look.  Same link, same name; two different links never collide.
    """
    digest = hashlib.sha256(str(url or "").encode("utf-8")).hexdigest()[:12]
    return default_log_path().with_name(f"ytdlp-{digest}.log")


def build_command(url: str, output_dir: Path, browser: str | None) -> list[str]:
    binary = find_ytdlp()
    if binary is None:
        raise FileNotFoundError("yt-dlp est introuvable.")
    command = [binary]
    if browser:
        command += ["--cookies-from-browser", browser]
    command += [
        "--no-playlist",
        "--newline",
        "--output",
        str(Path(output_dir) / "%(title)s.%(ext)s"),
        url,
    ]
    return command


def download(
    url: str,
    output_dir: Path,
    browser: str | None = None,
    log_path: Path | None = None,
    on_line: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Run the bundled yt-dlp and report its last line; full output goes to a log."""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    command = build_command(url, directory, browser or browser_name())
    destination = Path(log_path) if log_path else default_log_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    last = ""
    with destination.open("w", encoding="utf-8") as log:
        log.write(" ".join(command) + "\n")
        log.flush()
        process = subprocess.Popen(
            command,
            cwd=str(directory),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        if process.stdout is not None:
            for line in process.stdout:
                log.write(line)
                log.flush()
                stripped = line.rstrip("\n")
                if stripped:
                    last = stripped
                    if on_line is not None:
                        on_line(stripped)
        code = process.wait()
    if code == 0:
        return True, last or "Terminé"
    return False, last or f"Échec (code {code})"
