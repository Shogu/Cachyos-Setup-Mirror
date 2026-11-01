from __future__ import annotations

from pathlib import Path


def _disk_usage(path: Path) -> int:
    """Bytes really occupied on disk, as du reports them (not the apparent size)."""
    stat = path.stat()
    blocks = getattr(stat, "st_blocks", None)
    return stat.st_size if blocks is None else blocks * 512


def log_targets(
    runtime_dir: Path,
    frontend_log: Path | None = None,
    ytdlp_dir: Path | None = None,
) -> list[Path]:
    targets: list[Path] = []
    logs_dir = runtime_dir / "logs"
    if logs_dir.is_dir():
        targets.extend(path for path in sorted(logs_dir.rglob("*")) if path.is_file())
    if frontend_log is not None and frontend_log.is_file():
        targets.append(frontend_log)
    if ytdlp_dir is not None and ytdlp_dir.is_dir():
        targets.extend(sorted(ytdlp_dir.glob("ytdlp*.log")))
    return targets


def logs_size(
    runtime_dir: Path,
    frontend_log: Path | None = None,
    ytdlp_dir: Path | None = None,
) -> int:
    total = 0
    for path in log_targets(runtime_dir, frontend_log, ytdlp_dir):
        try:
            total += _disk_usage(path)
        except OSError:
            continue
    return total


def tidy_logs(
    runtime_dir: Path,
    frontend_log: Path | None = None,
    ytdlp_dir: Path | None = None,
) -> tuple[int, int]:
    """Empty the logs and report (files emptied, bytes freed).

    Truncate rather than unlink: JDownloader holds these files open for its whole
    lifetime, so unlinking them would not release anything before a restart.
    """
    emptied = 0
    freed = 0
    for path in log_targets(runtime_dir, frontend_log, ytdlp_dir):
        if path.suffix == ".lck":
            continue
        try:
            before = _disk_usage(path)
            if ytdlp_dir is not None and path.parent == ytdlp_dir:
                # Our own per-link logs are not held open by JDownloader, so they
                # can be removed outright — which also removes the names.
                path.unlink()
            else:
                with path.open("r+b") as handle:
                    handle.truncate(0)
        except OSError:
            continue
        emptied += 1
        freed += before
    return emptied, freed


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("o", "Ko", "Mo", "Go"):
        if value < 1024 or unit == "Go":
            return f"{value:.0f} o" if unit == "o" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} Go"
