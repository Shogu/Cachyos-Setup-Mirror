from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .domains import normalize_domain_list


LOCAL_API_URL = "http://127.0.0.1:3128"


def _xdg_config_dir() -> Path:
    configured = os.environ.get("XDG_CONFIG_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".config"


class AppConfig:
    """Small, deliberately boring JSON configuration for the frontend."""

    def __init__(self) -> None:
        self.path = _xdg_config_dir() / "jd-adwaita" / "config.json"
        self.data: dict[str, Any] = {
            # Kept for migration from older releases.  The application now
            # has one connection mode and always uses this local endpoint.
            "api_url": LOCAL_API_URL,
            "jar_path": "",
            "java_path": "",
            "download_dir": str(Path.home() / "Downloads"),
            "max_simultaneous_downloads": 3,
            "grabber_filter": "all",
            "grabber_whitelist_enabled": False,
            "grabber_domain_whitelist": [],
            # Links handed to yt-dlp.  The list is the user's: empty out of
            # the box, editable in the settings, stored outside the source.
            "ytdlp_domains": [],
            # Grabber watches the clipboard itself; JDownloader's own observer
            # is disabled to avoid duplicate packages.
            "clipboard_scan_enabled": True,
            # URLs handed over by the browser extension stay silent by
            # default: Grabber only takes the focus on its first launch.
            "focus_on_delivery": False,
            "close_warning_enabled": True,
            "show_export_videos_button": True,
            "moved_video_paths": {},
        }
        self.load()

    def load(self) -> None:
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                stored = json.load(handle)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return
        if isinstance(stored, dict):
            for key in self.data:
                if key in stored:
                    self.data[key] = stored[key]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix="config.", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self.data, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass

    @property
    def api_url(self) -> str:
        return LOCAL_API_URL

    @api_url.setter
    def api_url(self, _value: str) -> None:
        # Do not let an old settings dialog or a hand-edited config switch
        # the frontend away from its embedded local JDownloader instance.
        self.data["api_url"] = LOCAL_API_URL

    @property
    def jar_path(self) -> str:
        return str(self.data["jar_path"]).strip()

    @jar_path.setter
    def jar_path(self, value: str) -> None:
        self.data["jar_path"] = value.strip()

    @property
    def java_path(self) -> str:
        return str(self.data["java_path"]).strip()

    @java_path.setter
    def java_path(self, value: str) -> None:
        self.data["java_path"] = value.strip()

    @property
    def download_dir(self) -> str:
        return str(self.data["download_dir"]).strip() or str(Path.home() / "Downloads")

    @download_dir.setter
    def download_dir(self, value: str) -> None:
        self.data["download_dir"] = value.strip()

    @property
    def max_simultaneous_downloads(self) -> int:
        try:
            value = int(self.data.get("max_simultaneous_downloads", 3))
        except (TypeError, ValueError):
            value = 3
        return max(1, min(20, value))

    @max_simultaneous_downloads.setter
    def max_simultaneous_downloads(self, value: int) -> None:
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            normalized = 3
        self.data["max_simultaneous_downloads"] = max(1, min(20, normalized))

    @property
    def grabber_filter(self) -> str:
        value = str(self.data.get("grabber_filter", "all"))
        return value if value in {"all", "music", "videos", "documents"} else "all"

    @grabber_filter.setter
    def grabber_filter(self, value: str) -> None:
        self.data["grabber_filter"] = value if value in {
            "all",
            "music",
            "videos",
            "documents",
        } else "all"

    @property
    def grabber_whitelist_enabled(self) -> bool:
        return bool(self.data.get("grabber_whitelist_enabled", False))

    @grabber_whitelist_enabled.setter
    def grabber_whitelist_enabled(self, value: bool) -> None:
        self.data["grabber_whitelist_enabled"] = bool(value)

    @property
    def grabber_domain_whitelist(self) -> list[str]:
        value = self.data.get("grabber_domain_whitelist", [])
        if isinstance(value, str):
            values = value.splitlines()
        elif isinstance(value, list):
            values = value
        else:
            values = []
        result: list[str] = []
        seen: set[str] = set()
        for entry in values:
            normalized = str(entry).strip().lower()
            if normalized.startswith("*."):
                normalized = normalized[2:]
            normalized = normalized.lstrip(".").rstrip(".")
            if normalized and normalized not in seen:
                result.append(normalized)
                seen.add(normalized)
        return result

    @grabber_domain_whitelist.setter
    def grabber_domain_whitelist(self, value: Any) -> None:
        if isinstance(value, str):
            values = value.splitlines()
        elif isinstance(value, (list, tuple, set)):
            values = value
        else:
            values = []
        result: list[str] = []
        seen: set[str] = set()
        for entry in values:
            normalized = str(entry).strip().lower()
            if normalized.startswith("*."):
                normalized = normalized[2:]
            normalized = normalized.lstrip(".").rstrip(".")
            if normalized and normalized not in seen:
                result.append(normalized)
                seen.add(normalized)
        self.data["grabber_domain_whitelist"] = result

    @property
    def ytdlp_domains(self) -> list[str]:
        """Sites whose links JDownloader cannot fetch, as entered by the user."""
        return normalize_domain_list(self.data.get("ytdlp_domains", []))

    @ytdlp_domains.setter
    def ytdlp_domains(self, value: Any) -> None:
        self.data["ytdlp_domains"] = normalize_domain_list(value)

    @property
    def close_warning_enabled(self) -> bool:
        return bool(self.data.get("close_warning_enabled", True))

    @close_warning_enabled.setter
    def close_warning_enabled(self, value: bool) -> None:
        self.data["close_warning_enabled"] = bool(value)

    @property
    def show_export_videos_button(self) -> bool:
        return bool(self.data.get("show_export_videos_button", True))

    @show_export_videos_button.setter
    def show_export_videos_button(self, value: bool) -> None:
        self.data["show_export_videos_button"] = bool(value)

    @property
    def clipboard_scan_enabled(self) -> bool:
        return bool(self.data.get("clipboard_scan_enabled", True))

    @clipboard_scan_enabled.setter
    def clipboard_scan_enabled(self, value: bool) -> None:
        self.data["clipboard_scan_enabled"] = bool(value)

    @property
    def focus_on_delivery(self) -> bool:
        return bool(self.data.get("focus_on_delivery", False))

    @focus_on_delivery.setter
    def focus_on_delivery(self, value: bool) -> None:
        self.data["focus_on_delivery"] = bool(value)
