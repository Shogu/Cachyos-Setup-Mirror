#!/usr/bin/env python3
"""A small native GTK4/libadwaita front-end for systemctl.

The application deliberately keeps systemd as its source of truth.  It does
not edit unit contents; its optional complete-cleanup action removes only the
selected unit's local entries through a narrowly scoped helper.  Commands are
never run through a shell.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import gettext
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Pango


APP_ID = "io.github.systemd_gui.SystemdGui"
APP_NAME = "Services systemd"
APP_VERSION = "0.4.0"
VALID_UNIT = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9:_.@%\-]*\."
    r"(service|timer|socket|mount|automount|target|path|device|swap|slice|scope)$"
)
UNIT_TYPES = (
    "service",
    "timer",
    "socket",
    "mount",
    "target",
    "path",
    "device",
    "swap",
    "slice",
    "scope",
)
_ = gettext.gettext

APP_CSS = """
.systemd-service-row {
  border-radius: 8px;
}

.systemd-service-row:selected {
  background-color: color-mix(in srgb, var(--accent-bg-color) 14%, transparent);
}

.systemd-selection-accent {
  background-color: transparent;
  border-radius: 999px;
}

.systemd-service-row:selected .systemd-selection-accent {
  background-color: var(--accent-color);
}

.systemd-service-row .systemd-row-title {
  font-weight: 500;
}
"""

# Names provided by the standard Adwaita icon theme.
ICON_ACTIVE = "emblem-ok-symbolic"
ICON_FAILED = "dialog-error-symbolic"
ICON_NOT_FOUND = "dialog-warning-symbolic"
ICON_STOPPED = "media-playback-stop-symbolic"
ICON_MASKED = "changes-prevent-symbolic"
ICON_UNMASKED = "changes-allow-symbolic"


ICON_FALLBACKS: dict[str, tuple[str, ...]] = {
    ICON_ACTIVE: (ICON_ACTIVE, "emblem-default-symbolic", "dialog-information-symbolic"),
    ICON_FAILED: (ICON_FAILED, "dialog-warning-symbolic", "dialog-information-symbolic"),
    ICON_NOT_FOUND: (ICON_NOT_FOUND, "dialog-error-symbolic", "dialog-information-symbolic"),
    ICON_STOPPED: (ICON_STOPPED, "process-stop-symbolic", "dialog-information-symbolic"),
    ICON_MASKED: (ICON_MASKED, "object-locked-symbolic", "system-lock-screen-symbolic"),
    ICON_UNMASKED: (ICON_UNMASKED, "object-unlocked-symbolic", "emblem-ok-symbolic"),
    "media-playback-start-symbolic": (
        "media-playback-start-symbolic",
        "emblem-ok-symbolic",
        "system-run-symbolic",
    ),
    "system-run-symbolic": (
        "system-run-symbolic",
        "emblem-ok-symbolic",
        "media-playback-start-symbolic",
    ),
    "process-stop-symbolic": (
        "process-stop-symbolic",
        "media-playback-stop-symbolic",
        "dialog-warning-symbolic",
    ),
    "view-conceal-symbolic": (
        "view-conceal-symbolic",
        "eye-not-looking-symbolic",
        "pan-up-symbolic",
        "go-up-symbolic",
    ),
    "view-reveal-symbolic": (
        "view-reveal-symbolic",
        "eye-open-negative-symbolic",
        "pan-down-symbolic",
        "go-down-symbolic",
    ),
    "view-refresh-symbolic": ("view-refresh-symbolic", "emblem-synchronizing-symbolic"),
    "open-menu-symbolic": ("open-menu-symbolic", "view-more-symbolic"),
    "document-open-symbolic": (
        "document-open-symbolic",
        "document-properties-symbolic",
        "text-x-generic-symbolic",
    ),
    "document-properties-symbolic": (
        "document-properties-symbolic",
        "document-open-symbolic",
        "text-x-generic-symbolic",
    ),
    "utilities-terminal-symbolic": (
        "utilities-terminal-symbolic",
        "terminal-symbolic",
        "application-x-executable-symbolic",
    ),
    "dialog-information-symbolic": (
        "dialog-information-symbolic",
        "help-about-symbolic",
        "emblem-default-symbolic",
    ),
    "view-list-symbolic": (
        "view-list-symbolic",
        "view-app-grid-symbolic",
        "view-grid-symbolic",
    ),
    "user-trash-symbolic": (
        "user-trash-symbolic",
        "edit-delete-symbolic",
        "user-trash-full-symbolic",
    ),
    "edit-clear-symbolic": (
        "edit-clear-symbolic",
        "window-close-symbolic",
        "process-stop-symbolic",
    ),
}


def available_icon_name(*names: str) -> Optional[str]:
    """Return the first icon available in the active theme.

    A missing symbolic icon must never turn into GTK's broken-image glyph.
    Themes are allowed to provide only a subset of symbolic names, so every
    icon used by the application has a small, standard fallback chain.
    """

    candidates: list[str] = []
    for name in names:
        candidates.extend(ICON_FALLBACKS.get(name, (name,)))

    display = Gdk.Display.get_default()
    if display is None:
        return candidates[0] if candidates else None

    theme = Gtk.IconTheme.get_for_display(display)
    for name in candidates:
        if theme.has_icon(name):
            return name
    return None


def themed_icon(*names: str, pixel_size: int = 18) -> Gtk.Image:
    """Create an image without ever displaying a broken icon placeholder."""

    name = available_icon_name(*names)
    if name is None:
        image = Gtk.Image()
        image.set_pixel_size(pixel_size)
        image.set_visible(False)
        return image
    image = Gtk.Image.new_from_icon_name(name)
    image.set_pixel_size(pixel_size)
    return image


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass
class Service:
    name: str
    unit_type: str = "service"
    unit_file_state: str = "unknown"
    preset: str = ""
    load_state: str = "not-loaded"
    active_state: str = "inactive"
    sub_state: str = "dead"
    description: str = ""

    @property
    def is_active(self) -> bool:
        return self.active_state in {"active", "reloading"}

    @property
    def is_failed(self) -> bool:
        return self.active_state == "failed"

    @property
    def is_masked(self) -> bool:
        return self.unit_file_state in {"masked", "masked-runtime"}

    @property
    def is_not_found(self) -> bool:
        return self.load_state == "not-found"

    @property
    def is_not_loaded(self) -> bool:
        return self.load_state in {"unknown", "not-loaded"}

    @property
    def is_enabled(self) -> bool:
        return self.unit_file_state in {"enabled", "enabled-runtime"}

    @property
    def is_disabled(self) -> bool:
        return self.unit_file_state == "disabled"

    @property
    def has_runtime_state(self) -> bool:
        """True when systemd actually returned a runtime unit state.

        ``list-unit-files`` is an inventory of installed unit files; it is not
        evidence that a unit is loaded by the manager.  In particular, an
        installed socket/timer/service that is absent from ``list-units`` must
        not be presented as a stopped runtime unit.
        """
        return self.load_state not in {"unknown", "not-loaded"}

    @property
    def is_stopped(self) -> bool:
        return (
            self.has_runtime_state
            and self.active_state == "inactive"
            and not self.is_failed
            and not self.is_not_found
        )

    @property
    def state_text(self) -> str:
        if self.is_masked:
            return "Masqué"
        if self.is_not_found:
            return "Introuvable"
        if self.is_not_loaded:
            return "Non chargé"
        if self.is_failed:
            return "En échec"
        if self.is_active:
            if self.sub_state and self.sub_state not in {"running", "listening"}:
                return f"Actif · {_fr(SUB_STATE_FR, self.sub_state)}"
            return "Actif"
        if self.active_state in {"activating", "deactivating"}:
            return "Transition en cours"
        return "Arrêté"

    @property
    def state_icon(self) -> str:
        if self.is_not_found:
            return ICON_NOT_FOUND
        if self.is_not_loaded:
            return ICON_NOT_FOUND
        if self.is_failed:
            return ICON_FAILED
        if self.is_masked:
            return ICON_MASKED
        if self.is_active:
            return ICON_ACTIVE
        return ICON_STOPPED


ACTIVE_STATE_FR = {
    "active": "actif",
    "inactive": "inactif",
    "failed": "en échec",
    "activating": "activation",
    "deactivating": "arrêt en cours",
    "reloading": "rechargement",
    "maintenance": "maintenance",
}
SUB_STATE_FR = {
    "running": "en cours",
    "dead": "arrêté",
    "exited": "terminé",
    "failed": "échec",
    "listening": "à l’écoute",
    "waiting": "en attente",
    "mounted": "monté",
    "mounting": "montage",
    "unmounting": "démontage",
    "plugged": "branché",
    "active": "actif",
    "start": "démarrage",
    "start-pre": "pré-démarrage",
    "start-post": "post-démarrage",
    "stop": "arrêt",
    "stop-sigterm": "arrêt (SIGTERM)",
    "stop-sigkill": "arrêt (SIGKILL)",
    "stop-post": "post-arrêt",
    "reload": "rechargement",
    "auto-restart": "redémarrage automatique",
    "condition": "condition non remplie",
    "elapsed": "écoulé",
    "abandoned": "abandonné",
    "final-sigterm": "fin (SIGTERM)",
    "final-sigkill": "fin (SIGKILL)",
}
LOAD_STATE_FR = {
    "loaded": "chargé",
    "not-found": "introuvable",
    "masked": "masqué",
    "error": "erreur",
    "stub": "ébauche",
    "bad-setting": "réglage invalide",
    "merged": "fusionné",
}
UNIT_FILE_STATE_FR = {
    "enabled": "activé",
    "enabled-runtime": "activé (temporaire)",
    "disabled": "désactivé",
    "static": "statique",
    "indirect": "indirect",
    "generated": "généré",
    "transient": "transitoire",
    "alias": "alias",
    "linked": "lié",
    "linked-runtime": "lié (temporaire)",
    "masked": "masqué",
    "masked-runtime": "masqué (temporaire)",
    "bad": "invalide",
    "unknown": "inconnu",
}


def _fr(table: dict[str, str], value: str) -> str:
    """Display-only translation of a systemd state; unknown values pass through."""
    return table.get(value, value)


def _state_icon_css_class(service: Service) -> str:
    """Return the Adwaita colour class used for the compact state icon."""
    if service.is_failed:
        return "error"
    if service.is_masked or service.is_not_found:
        return "warning"
    if service.is_active:
        return "success"
    return "dimmed"


ROW_ICON_CLASSES = ("success", "warning", "error", "dimmed")

# Resizable sidebar.
SIDEBAR_DEFAULT_WIDTH = 340
SIDEBAR_MIN_WIDTH = 240
SIDEBAR_GRAB_PX = 6
SIDEBAR_MAX_FRACTION = 0.6
COLLAPSE_BREAKPOINT = "max-width: 560sp"


@dataclass
class RemovalItem:
    path: str
    kind: str
    removable: bool
    exists: bool = True
    reason: str = ""


@dataclass
class RemovalPlan:
    name: str
    scope: str
    load_state: str
    active_state: str
    unit_file_state: str
    items: list[RemovalItem]
    references: list[str]

    @property
    def existing_items(self) -> list[RemovalItem]:
        return [item for item in self.items if item.exists]

    @property
    def removable_items(self) -> list[RemovalItem]:
        return [item for item in self.existing_items if item.removable]

    @property
    def is_ghost(self) -> bool:
        return self.load_state == "not-found" and not self.existing_items


@dataclass
class RemovalResult:
    removed: list[str]
    warnings: list[str]


class SystemctlError(RuntimeError):
    pass


class Systemctl:
    """Small, shell-free wrapper around systemctl and journalctl."""

    def __init__(self, user: bool = False):
        self.user = user

    @property
    def scope_name(self) -> str:
        return "Utilisateur" if self.user else "Système"

    def _systemctl_args(self, args: list[str]) -> list[str]:
        return (["--user"] if self.user else []) + args

    def _journalctl_args(self, args: list[str]) -> list[str]:
        return (["--user"] if self.user else []) + args

    @staticmethod
    def _environment() -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "LC_ALL": "C",
                "LANG": "C",
                "SYSTEMD_COLORS": "0",
                "SYSTEMD_PAGER": "cat",
                "SYSTEMD_LESS": "FRX",
            }
        )
        return env

    def run(self, args: list[str], timeout: int = 30) -> CommandResult:
        command = ["systemctl", *self._systemctl_args(args)]
        return self._run_program(command, timeout)

    def run_journal(self, args: list[str], timeout: int = 40) -> CommandResult:
        command = ["journalctl", *self._journalctl_args(args)]
        return self._run_program(command, timeout)

    def _run_program(self, command: list[str], timeout: int) -> CommandResult:
        try:
            completed = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=self._environment(),
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            raise SystemctlError(f"La commande {command[0]} est introuvable.") from exc
        except subprocess.TimeoutExpired as exc:
            raise SystemctlError(f"{command[0]} n’a pas répondu dans le délai prévu.") from exc

        return CommandResult(completed.returncode, completed.stdout, completed.stderr)

    @staticmethod
    def _require_success(result: CommandResult, context: str) -> str:
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            if not detail:
                detail = f"code de sortie {result.returncode}"
            raise SystemctlError(f"{context} : {detail}")
        return result.stdout

    @staticmethod
    def _validate_unit(name: str) -> None:
        if not VALID_UNIT.fullmatch(name):
            raise SystemctlError("Nom d’unité refusé par mesure de sécurité.")

    def list_services(self) -> list[Service]:
        unit_files = self._require_success(
            self.run(
                [
                    "list-unit-files",
                    "--no-legend",
                    "--no-pager",
                ]
            ),
            "Impossible de lire les fichiers d’unités",
        )
        loaded_units = self._require_success(
            self.run(
                [
                    "list-units",
                    "--all",
                    "--no-legend",
                    "--no-pager",
                    "--plain",
                    "--full",
                ]
            ),
            "Impossible de lire les unités chargées",
        )

        services: dict[str, Service] = {}

        for line in unit_files.splitlines():
            columns = line.split()
            if len(columns) < 2:
                continue
            name = columns[0]
            if not VALID_UNIT.fullmatch(name):
                continue
            services[name] = Service(
                name=name,
                unit_type=name.rsplit(".", 1)[1],
                unit_file_state=columns[1],
                preset=columns[2] if len(columns) > 2 else "",
            )

        for line in loaded_units.splitlines():
            columns = line.split(maxsplit=4)
            if len(columns) < 4:
                continue
            name = columns[0]
            if not VALID_UNIT.fullmatch(name):
                continue
            service = services.setdefault(
                name, Service(name=name, unit_type=name.rsplit(".", 1)[1])
            )
            service.load_state = columns[1]
            service.active_state = columns[2]
            service.sub_state = columns[3]
            service.description = columns[4].strip() if len(columns) > 4 else ""

        return sorted(services.values(), key=lambda item: item.name.casefold())

    def get_details(self, name: str) -> dict[str, str]:
        self._validate_unit(name)
        properties = [
            "Id",
            "Names",
            "Description",
            "Documentation",
            "LoadState",
            "ActiveState",
            "SubState",
            "UnitFileState",
            "UnitFilePreset",
            "FragmentPath",
            "DropInPaths",
            "MainPID",
            "ExecMainPID",
            "Result",
            "User",
            "Group",
            "Type",
            "Restart",
            "MemoryCurrent",
            "TasksCurrent",
            "CPUUsageNSec",
            "ActiveEnterTimestamp",
            "ConditionResult",
            "CanStart",
            "CanStop",
            "CanReload",
            "Requires",
            "RequiredBy",
            "Wants",
            "WantedBy",
            "PartOf",
            "BindsTo",
            "Triggers",
            "TriggeredBy",
            "ReferencedBy",
            "After",
            "Before",
            "Conflicts",
            "ConflictedBy",
            "Requisite",
            "RequisiteOf",
            "OnFailure",
        ]
        show = self.run(
            ["show", "--no-pager", f"--property={','.join(properties)}", name]
        )
        if show.returncode != 0 and not show.stdout.strip():
            self._require_success(show, f"Impossible de lire {name}")

        props = self._parse_properties(show.stdout)

        status = self.run(["status", "--no-pager", "--full", "--lines=80", name])
        unit_file = self.run(["cat", "--no-pager", name])

        def command_output(
            result: CommandResult, context: str, empty_message: str
        ) -> str:
            if result.returncode != 0:
                detail = (result.stderr or result.stdout).strip()
                return f"{context} : {detail or f'code de sortie {result.returncode}'}"
            return result.stdout.strip() or empty_message

        return {
            "name": name,
            "description": props.get("Description", ""),
            "documentation": props.get("Documentation", ""),
            "fragment_path": props.get("FragmentPath", ""),
            "unit_file": command_output(
                unit_file,
                f"Impossible de lire le fichier de {name}",
                "Aucun contenu d’unité disponible.",
            ),
            "status": command_output(
                status,
                f"Impossible de lire le statut de {name}",
                "Aucune sortie status disponible.",
            ),
            "properties_raw": show.stdout.strip()
            or show.stderr.strip()
            or "Aucune propriété disponible.",
            "drop_ins": props.get("DropInPaths", ""),
            "documentation_value": props.get("Documentation", ""),
            **props,
        }

    def get_journal(self, name: str) -> str:
        self._validate_unit(name)
        journal_args = [
            "--unit",
            name,
            "--no-pager",
            "--output=short-iso",
            "--lines=20",
        ]
        result = self.run_journal(journal_args, timeout=40)
        if (
            result.returncode != 0
            and not self.user
            and self._journal_permission_denied(result)
        ):
            # System journals are often readable only by root or by members
            # of systemd-journal. Ask Polkit for a one-shot privileged read
            # instead of requiring a group-membership change.
            result = self._run_privileged_journal(journal_args, timeout=40)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            return f"Impossible de lire le journal de {name} : {detail or f'code de sortie {result.returncode}'}"
        return result.stdout.strip() or "Aucune entrée de journal pour cette unité."

    @staticmethod
    def _journal_permission_denied(result: CommandResult) -> bool:
        output = f"{result.stdout}\n{result.stderr}".casefold()
        return any(
            marker in output
            for marker in (
                "insufficient permissions",
                "permission denied",
                "access denied",
            )
        )

    def _run_privileged_journal(
        self, args: list[str], timeout: int = 40
    ) -> CommandResult:
        # Use the root-owned system paths for this privilege boundary; never
        # resolve either executable from a user-controlled PATH.
        pkexec = Path("/usr/bin/pkexec")
        journalctl = Path("/usr/bin/journalctl")
        if not pkexec.is_file() or not os.access(pkexec, os.X_OK):
            return CommandResult(127, "", "pkexec est introuvable.")
        if not journalctl.is_file() or not os.access(journalctl, os.X_OK):
            return CommandResult(127, "", "journalctl est introuvable.")
        return self._run_program(
            [os.fspath(pkexec), os.fspath(journalctl), *self._journalctl_args(args)],
            timeout,
        )

    def execute(self, action: str, name: str) -> CommandResult:
        self._validate_unit(name)
        commands = {
            "start": ["start", name],
            "stop": ["stop", name],
            "restart": ["restart", name],
            "reload": ["reload", name],
            "enable_now": ["enable", "--now", name],
            "disable_now": ["disable", "--now", name],
            "mask": ["mask", name],
            "unmask": ["unmask", name],
        }
        if action not in commands:
            raise SystemctlError("Action inconnue.")
        return self.run(commands[action], timeout=60)

    def _removable_roots(self) -> tuple[Path, ...]:
        if self.user:
            return (
                Path.home() / ".config" / "systemd" / "user",
                Path.home() / ".local" / "share" / "systemd" / "user",
            )
        # /usr/lib, /lib and /run deliberately do not appear here: they can
        # contain package-owned or runtime-generated units and must never be
        # deleted by this application.
        return (Path("/etc/systemd/system"),)

    @staticmethod
    def _lexists(path: Path) -> bool:
        return os.path.lexists(os.fspath(path))

    @staticmethod
    def _is_under(path: Path, root: Path) -> bool:
        try:
            return os.path.commonpath(
                [os.path.abspath(os.fspath(path)), os.path.abspath(os.fspath(root))]
            ) == os.path.abspath(os.fspath(root))
        except ValueError:
            return False

    def _removable_root_for(self, path: Path) -> Optional[Path]:
        if not path.is_absolute():
            return None
        for root in self._removable_roots():
            if self._is_under(path, root):
                return root
        return None

    def _collect_local_entries(self, name: str) -> dict[str, RemovalItem]:
        entries: dict[str, RemovalItem] = {}

        def add(path: Path, kind: str) -> None:
            root = self._removable_root_for(path)
            if root is None:
                return
            normalized = os.path.abspath(os.fspath(path))
            entries[normalized] = RemovalItem(
                path=normalized,
                kind=kind,
                removable=True,
                exists=self._lexists(path),
            )

        for root in self._removable_roots():
            if not root.is_dir():
                continue
            drop_in_dir = root / f"{name}.d"
            if self._lexists(drop_in_dir):
                add(drop_in_dir, "répertoire de drop-ins")

            for current, directories, files in os.walk(
                os.fspath(root), topdown=True, followlinks=False
            ):
                current_path = Path(current)
                # Do not descend through a directory symlink.  The symlink
                # itself may be listed and removed if it belongs to this
                # exact unit, but its target is outside our deletion scope.
                directories[:] = [
                    directory
                    for directory in directories
                    if not os.path.islink(os.path.join(current, directory))
                ]
                for directory in directories:
                    path = current_path / directory
                    if directory == f"{name}.d" or drop_in_dir in path.parents:
                        add(path, "répertoire de drop-ins")
                for filename in files:
                    path = current_path / filename
                    if filename == name:
                        add(path, "fichier ou lien du service")
                    elif drop_in_dir in path.parents:
                        add(path, "drop-in")
        return entries

    def _removal_item_for_path(
        self,
        path_value: str,
        kind: str,
        entries: dict[str, RemovalItem],
    ) -> None:
        if not path_value:
            return
        path = Path(path_value)
        if not path.is_absolute():
            entries[path_value] = RemovalItem(
                path=path_value,
                kind=kind,
                removable=False,
                exists=False,
                reason="chemin non absolu",
            )
            return
        root = self._removable_root_for(path)
        normalized = os.path.abspath(os.fspath(path))
        if root is None:
            entries[normalized] = RemovalItem(
                path=normalized,
                kind=kind,
                removable=False,
                exists=self._lexists(path),
                reason="fichier système ou emplacement protégé",
            )
            return
        entries[normalized] = RemovalItem(
            path=normalized,
            kind=kind,
            removable=True,
            exists=self._lexists(path),
        )

    @staticmethod
    def _references_from_details(
        details: dict[str, str], name: str
    ) -> list[str]:
        references: list[str] = []
        for key in (
            "Requires",
            "RequiredBy",
            "Wants",
            "WantedBy",
            "PartOf",
            "BindsTo",
            "Triggers",
            "TriggeredBy",
            "ReferencedBy",
        ):
            value = details.get(key, "").strip()
            if not value or value == "-":
                continue
            units = [unit for unit in value.split() if unit != name]
            if units:
                references.append(f"{key} : {' '.join(units)}")
        return references

    def get_removal_plan(self, name: str) -> RemovalPlan:
        self._validate_unit(name)
        details = self.get_details(name)
        entries = self._collect_local_entries(name)
        self._removal_item_for_path(
            details.get("FragmentPath", ""), "fichier d’unité", entries
        )
        for path_value in details.get("DropInPaths", "").split():
            self._removal_item_for_path(path_value, "drop-in", entries)
        return RemovalPlan(
            name=name,
            scope=self.scope_name,
            load_state=details.get("LoadState", "") or "unknown",
            active_state=details.get("ActiveState", "") or "unknown",
            unit_file_state=details.get("UnitFileState", "") or "unknown",
            items=sorted(entries.values(), key=lambda item: item.path),
            references=self._references_from_details(details, name),
        )

    @staticmethod
    def _result_detail(result: CommandResult) -> str:
        return (result.stderr or result.stdout).strip() or (
            f"code de sortie {result.returncode}"
        )

    def _helper_path(self) -> Optional[Path]:
        installed = Path("/usr/lib/systemd-gui/systemd-file-helper")
        local_candidates = (
            Path(__file__).with_name("systemd-file-helper"),
            Path(__file__).with_name("systemd-file-helper.py"),
        )
        if not self.user and os.geteuid() != 0:
            # A system-scope helper must be root-owned in the conventional
            # system location before pkexec is allowed to execute it.
            if installed.is_file() and os.access(installed, os.X_OK):
                return installed
            return None
        for candidate in (installed, *local_candidates):
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return candidate
        return None

    def _remove_local_files(self, name: str) -> RemovalResult:
        helper = self._helper_path()
        if helper is None:
            if self.user:
                raise SystemctlError(
                    "L’assistant de suppression est introuvable dans l’installation."
                )
            raise SystemctlError(
                "L’assistant de suppression système est introuvable. "
                "Réinstallez systemd-gui pour activer cette fonction."
            )

        command = [
            os.fspath(helper),
            "--user" if self.user else "--system",
            name,
        ]
        if not self.user and os.geteuid() != 0:
            command.insert(0, "pkexec")
        result = self._run_program(command, timeout=60)
        if result.returncode != 0:
            raise SystemctlError(
                f"Impossible de supprimer les fichiers locaux de {name} : "
                f"{self._result_detail(result)}"
            )

        removed: list[str] = []
        warnings: list[str] = []
        for line in result.stdout.splitlines():
            if line.startswith("REMOVED\t"):
                removed.append(line.split("\t", 1)[1])
            elif line.startswith("WARN\t"):
                warnings.append(line.split("\t", 1)[1])
        return RemovalResult(removed=removed, warnings=warnings)

    def remove_complete(self, name: str) -> RemovalResult:
        """Stop, detach and remove only the selected unit's local entries."""

        plan = self.get_removal_plan(name)
        warnings: list[str] = []

        if plan.active_state in {"active", "activating", "reloading", "deactivating"}:
            stopped = self.run(["stop", name], timeout=60)
            if stopped.returncode != 0:
                raise SystemctlError(
                    f"Impossible d’arrêter {name} avant sa suppression : "
                    f"{self._result_detail(stopped)}"
                )

        if plan.unit_file_state in {"masked", "masked-runtime"}:
            unmasked = self.run(["unmask", name], timeout=60)
            if unmasked.returncode != 0:
                raise SystemctlError(
                    f"Impossible de désmasquer {name} avant sa suppression : "
                    f"{self._result_detail(unmasked)}"
                )

        disabled = self.run(["disable", "--now", name], timeout=60)
        if disabled.returncode != 0:
            # For a static, transient or already-absent unit this is an
            # expected no-op.  An enabled unit failing here is not ignored.
            ignorable_states = {
                "static",
                "indirect",
                "generated",
                "transient",
                "disabled",
                "masked",
                "masked-runtime",
                "not-found",
                "unknown",
            }
            if not plan.is_ghost and plan.unit_file_state not in ignorable_states:
                raise SystemctlError(
                    f"Impossible de désactiver {name} avant sa suppression : "
                    f"{self._result_detail(disabled)}"
                )
            if not plan.is_ghost:
                warnings.append(self._result_detail(disabled))

        removal = self._remove_local_files(name)
        warnings.extend(removal.warnings)

        reloaded = self.run(["daemon-reload"], timeout=60)
        if reloaded.returncode != 0:
            raise SystemctlError(
                f"Les fichiers ont été traités, mais daemon-reload a échoué : "
                f"{self._result_detail(reloaded)}"
            )

        reset = self.run(["reset-failed", name], timeout=60)
        reset_detail = self._result_detail(reset)
        if reset.returncode != 0 and not (
            plan.is_ghost
            and any(
                marker in reset_detail.casefold()
                for marker in (
                    "not found",
                    "not loaded",
                    "does not exist",
                    "no such file",
                )
            )
        ):
            warnings.append(reset_detail)
        return RemovalResult(removed=removal.removed, warnings=warnings)

    @staticmethod
    def _parse_properties(output: str) -> dict[str, str]:
        properties: dict[str, str] = {}
        for line in output.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            properties[key] = value
        return properties


class ServiceRow(Gtk.ListBoxRow):
    """Compact two-line row: name, small description, one coloured state icon.

    The execution and activation states that used to fill a second column
    now live in the tooltip, which also shows the full, untruncated name.
    """

    def __init__(self, service: Service):
        super().__init__()
        self.service_name = service.name
        self.add_css_class("systemd-service-row")
        self.set_activatable(True)
        self.set_selectable(True)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_top(4)
        box.set_margin_bottom(4)
        box.set_margin_start(8)
        box.set_margin_end(8)

        selection_accent = Gtk.Box()
        selection_accent.set_size_request(3, -1)
        selection_accent.set_vexpand(True)
        selection_accent.set_valign(Gtk.Align.FILL)
        selection_accent.add_css_class("systemd-selection-accent")
        box.append(selection_accent)

        self.icon = themed_icon(service.state_icon, ICON_STOPPED, pixel_size=16)
        self.icon.set_valign(Gtk.Align.CENTER)
        box.append(self.icon)

        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        labels.set_hexpand(True)
        labels.set_valign(Gtk.Align.CENTER)
        self.name_label = Gtk.Label(xalign=0)
        self.name_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        self.name_label.set_single_line_mode(True)
        self.name_label.add_css_class("systemd-row-title")
        labels.append(self.name_label)

        self.description_label = Gtk.Label(xalign=0)
        self.description_label.add_css_class("dimmed")
        self.description_label.add_css_class("caption")
        self.description_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.description_label.set_single_line_mode(True)
        labels.append(self.description_label)
        box.append(labels)

        self.set_child(box)
        self._apply(service)

    @staticmethod
    def _secondary_text(service: Service) -> str:
        return service.description or (
            "Fichier absent" if service.is_not_found else service.state_text
        )

    @staticmethod
    def _activation_text(service: Service) -> str:
        return (
            "introuvable"
            if service.is_not_found
            else _fr(UNIT_FILE_STATE_FR, service.unit_file_state)
        )

    def _apply(self, service: Service) -> None:
        secondary = self._secondary_text(service)
        self.name_label.set_text(service.name)
        self.description_label.set_text(secondary)

        # Refresh the icon and its colour as well as the text.  Without this,
        # a five-second refresh could update the counters while leaving an
        # individual row visually stuck on its previous state.
        icon_name = available_icon_name(service.state_icon, ICON_STOPPED)
        if icon_name:
            self.icon.set_from_icon_name(icon_name)
            self.icon.set_visible(True)
        for css_class in ROW_ICON_CLASSES:
            self.icon.remove_css_class(css_class)
        self.icon.add_css_class(_state_icon_css_class(service))

        lines = [service.name]
        if service.description:
            lines.append(service.description)
        lines.append(f"{service.state_text} · {self._activation_text(service)}")
        self.set_tooltip_text("\n".join(lines))

    def update(self, service: Service) -> None:
        self.service_name = service.name
        self._apply(service)


class CategoryRow(Gtk.ListBoxRow):
    def __init__(self, key: str, title: str, icon_name: str):
        super().__init__()
        self.category_key = key
        self.count_label = Gtk.Label(label="0")
        self.count_label.add_css_class("dimmed")

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_top(4)
        box.set_margin_bottom(4)
        box.set_margin_start(10)
        box.set_margin_end(10)

        icon = themed_icon(icon_name, pixel_size=16)
        box.append(icon)
        label = Gtk.Label(label=title, xalign=0)
        label.set_hexpand(True)
        box.append(label)
        box.append(self.count_label)
        self.set_child(box)


def service_subtitle(service: Optional[Service]) -> str:
    if service is None:
        return ""
    return service.description or ""


def clear_container(container: Gtk.Widget) -> None:
    child = container.get_first_child()
    while child is not None:
        next_child = child.get_next_sibling()
        container.remove(child)
        child = next_child


def set_margins(widget: Gtk.Widget, value: int) -> None:
    widget.set_margin_top(value)
    widget.set_margin_bottom(value)
    widget.set_margin_start(value)
    widget.set_margin_end(value)


class SystemdManager(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.window: Optional[Adw.ApplicationWindow] = None
        self.systemctl = Systemctl()
        self.services: list[Service] = []
        self.services_by_name: dict[str, Service] = {}
        self.selected_name: Optional[str] = None
        self.selected_snapshot: Optional[tuple[str, ...]] = None
        self.current_details: Optional[dict[str, str]] = None
        self.current_category = "all"
        self.current_unit_type = "all"
        self.refresh_generation = 0
        self.selection_generation = 0
        self.details_generation = 0
        self.journal_generation = 0
        self.services_loading = False
        self.action_in_flight = False
        self.category_rows: dict[str, CategoryRow] = {}
        self.service_rows: dict[str, ServiceRow] = {}
        self.action_buttons: dict[str, Gtk.Button] = {}
        self.output_text_views: list[Gtk.TextView] = []
        self.journal_for: Optional[str] = None
        self.journal_hint: Optional[Gtk.Label] = None
        self.sidebar_width = self._load_sidebar_width()
        self._resizing = False
        self._resize_start_width = self.sidebar_width

        self._install_actions()

    def _install_css(self) -> None:
        display = Gdk.Display.get_default()
        if display is None:
            return
        provider = Gtk.CssProvider()
        provider.load_from_data(APP_CSS.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            display,
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
        self.css_provider = provider

    def _install_actions(self) -> None:
        refresh = Gio.SimpleAction.new("refresh", None)
        refresh.connect("activate", lambda *_: self.refresh_services())
        self.add_action(refresh)

        about = Gio.SimpleAction.new("about", None)
        about.connect("activate", lambda *_: self.show_about())
        self.add_action(about)

        search = Gio.SimpleAction.new("search", None)
        search.connect("activate", lambda *_: self._focus_search())
        self.add_action(search)

        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.quit())
        self.add_action(quit_action)

        self.set_accels_for_action("app.refresh", ["<Control>r", "F5"])
        self.set_accels_for_action("app.search", ["<Control>f"])
        self.set_accels_for_action("app.quit", ["<Control>q"])
        self.set_accels_for_action("window.close", ["<Control>w"])

    def _focus_search(self) -> None:
        if self.window is None:
            return
        if self.split_view.get_collapsed():
            self.split_view.set_show_content(False)
        self.search_entry.grab_focus()

    def do_activate(self) -> None:
        if self.window is None:
            self._build_ui()
        self.window.present()
        if not self.services:
            self.refresh_services()

    def _build_ui(self) -> None:
        self._install_css()
        self.style_manager = Adw.StyleManager.get_default()
        self.style_manager.connect("notify::dark", self._style_changed)
        self.window = Adw.ApplicationWindow(application=self)
        self.window.set_title(APP_NAME)
        self.window.set_default_size(1100, 720)
        self.window.set_size_request(360, 294)

        toast_overlay = Adw.ToastOverlay()
        self.toast_overlay = toast_overlay

        split_view = Adw.NavigationSplitView()
        # The sidebar width is chosen by the user (drag its right edge) and
        # remembered.  It is capped by a fraction of the window so the detail
        # pane always keeps room when the window gets smaller.
        split_view.set_sidebar_width_unit(Adw.LengthUnit.PX)
        split_view.set_sidebar_width_fraction(SIDEBAR_MAX_FRACTION)
        split_view.set_min_sidebar_width(SIDEBAR_MIN_WIDTH)
        split_view.set_max_sidebar_width(self.sidebar_width)
        self.split_view = split_view

        breakpoint = Adw.Breakpoint.new(
            Adw.BreakpointCondition.parse(COLLAPSE_BREAKPOINT)
        )
        breakpoint.add_setter(split_view, "collapsed", True)
        self.window.add_breakpoint(breakpoint)

        sidebar_page = self._build_sidebar()
        detail_page = self._build_detail()
        self.sidebar_page = sidebar_page
        split_view.set_sidebar(sidebar_page)
        split_view.set_content(detail_page)
        toast_overlay.set_child(split_view)
        self.window.set_content(toast_overlay)
        self._install_sidebar_resize(toast_overlay)

        GLib.timeout_add_seconds(5, self._automatic_refresh)

    # ----------------------------------------------------------------
    # Resizable sidebar
    # ----------------------------------------------------------------

    @staticmethod
    def _ui_state_path() -> Path:
        return Path(GLib.get_user_config_dir()) / "systemd-gui" / "ui.json"

    def _load_sidebar_width(self) -> int:
        width = SIDEBAR_DEFAULT_WIDTH
        try:
            data = json.loads(self._ui_state_path().read_text(encoding="utf-8"))
            width = int(data.get("sidebar_width", SIDEBAR_DEFAULT_WIDTH))
        except (OSError, ValueError, TypeError, AttributeError):
            width = SIDEBAR_DEFAULT_WIDTH
        return max(SIDEBAR_MIN_WIDTH, min(width, 1600))

    def _save_sidebar_width(self) -> None:
        path = self._ui_state_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps({"sidebar_width": self.sidebar_width}), encoding="utf-8"
            )
        except OSError as error:
            self.toast_overlay.add_toast(
                Adw.Toast.new(f"Largeur du panneau non enregistrée : {error}")
            )

    def _install_sidebar_resize(self, area: Gtk.Widget) -> None:
        """Let the user drag the boundary between the list and the details.

        Adw.NavigationSplitView has no resize handle, so the gestures live on a
        stable ancestor (they would jitter if attached to a widget that moves
        while it is being dragged).  They only claim a press that starts within
        a few pixels of the boundary; every other click reaches its target.
        """

        drag = Gtk.GestureDrag()
        drag.set_button(Gdk.BUTTON_PRIMARY)
        drag.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        drag.connect("drag-begin", self._resize_begin)
        drag.connect("drag-update", self._resize_update)
        drag.connect("drag-end", self._resize_end)
        area.add_controller(drag)

        motion = Gtk.EventControllerMotion()
        motion.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        motion.connect("motion", self._resize_motion)
        motion.connect("leave", lambda *_: self._set_resize_cursor(False))
        area.add_controller(motion)
        self._resize_area = area

    def _current_sidebar_width(self) -> int:
        return self.sidebar_page.get_width()

    def _near_sidebar_edge(self, x: float) -> bool:
        if self.split_view.get_collapsed():
            return False
        if self.window is not None and self.window.get_direction() != Gtk.TextDirection.LTR:
            return False
        return abs(x - self._current_sidebar_width()) <= SIDEBAR_GRAB_PX

    def _set_resize_cursor(self, active: bool) -> None:
        if self._resizing:
            active = True
        self._resize_area.set_cursor_from_name("col-resize" if active else None)

    def _resize_motion(self, _controller: Gtk.EventControllerMotion, x: float, _y: float) -> None:
        self._set_resize_cursor(self._near_sidebar_edge(x))

    def _resize_begin(self, gesture: Gtk.GestureDrag, x: float, _y: float) -> None:
        if not self._near_sidebar_edge(x):
            self._resizing = False
            gesture.set_state(Gtk.EventSequenceState.DENIED)
            return
        self._resizing = True
        self._resize_start_width = self._current_sidebar_width()
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)

    def _resize_update(self, _gesture: Gtk.GestureDrag, offset_x: float, _offset_y: float) -> None:
        if not self._resizing:
            return
        window_width = self.window.get_width() if self.window is not None else 0
        limit = int(window_width * SIDEBAR_MAX_FRACTION) if window_width > 0 else 1600
        width = int(self._resize_start_width + offset_x)
        width = max(SIDEBAR_MIN_WIDTH, min(width, max(SIDEBAR_MIN_WIDTH, limit)))
        self.sidebar_width = width
        self.split_view.set_max_sidebar_width(width)

    def _resize_end(self, _gesture: Gtk.GestureDrag, _offset_x: float, _offset_y: float) -> None:
        if not self._resizing:
            return
        self._resizing = False
        self._set_resize_cursor(False)
        self._save_sidebar_width()

    def _build_sidebar(self) -> Adw.NavigationPage:
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle.new("Services", ""))

        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name(
            available_icon_name("open-menu-symbolic") or "open-menu-symbolic"
        )
        menu_button.set_tooltip_text("Menu principal")
        menu_button.set_primary(True)
        menu = Gio.Menu()
        menu.append("_Actualiser", "app.refresh")
        menu.append("_Rechercher", "app.search")
        menu.append("À _propos de Services systemd", "app.about")
        menu_button.set_menu_model(menu)
        header.pack_end(menu_button)

        refresh = Gtk.Button()
        refresh.set_icon_name(
            available_icon_name("view-refresh-symbolic") or "view-refresh-symbolic"
        )
        refresh.set_tooltip_text("Actualiser (Ctrl+R)")
        refresh.set_action_name("app.refresh")
        header.pack_end(refresh)
        toolbar.add_top_bar(header)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        scope_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        set_margins(scope_box, 8)
        scope_box.set_halign(Gtk.Align.END)
        scope_model = Gtk.StringList.new(["Système", "Utilisateur"])
        self.scope_dropdown = Gtk.DropDown(model=scope_model)
        self.scope_dropdown.set_selected(0)
        self.scope_dropdown.connect("notify::selected", self._scope_changed)
        scope_box.append(self.scope_dropdown)
        content.append(scope_box)

        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        set_margins(search_box, 8)
        search_box.set_hexpand(True)
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Rechercher un service…")
        self.search_entry.set_hexpand(True)
        search_box.append(self.search_entry)
        self.results_count = Gtk.Label(label="0 service", xalign=1)
        self.results_count.add_css_class("dimmed")
        self.results_count.set_width_chars(8)
        self.results_count.set_xalign(1)
        search_box.append(self.results_count)
        # Gtk.Editable::changed is emitted for every typed, pasted or deleted
        # character.  It is more reliable here than waiting for the
        # SearchEntry-specific search signal.
        self.search_entry.connect("changed", self._search_changed)
        content.append(search_box)

        # Keep the filter section collapsible so the unit list can use the
        # sidebar space without losing the selected filters.
        self.filter_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        type_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        type_box.set_margin_start(12)
        type_box.set_margin_end(12)
        type_box.set_margin_bottom(6)
        type_label = Gtk.Label(label="Type d’unité", xalign=0)
        type_label.set_hexpand(True)
        type_box.append(type_label)
        type_model = Gtk.StringList.new(
            ["Tous", "Services", "Timers", "Sockets", "Mounts", "Targets",
             "Paths", "Devices", "Swaps", "Slices", "Scopes"]
        )
        self.type_dropdown = Gtk.DropDown(model=type_model)
        self.type_dropdown.connect("notify::selected", self._unit_type_changed)
        type_box.append(self.type_dropdown)
        self.filter_section.append(type_box)

        self.category_list = Gtk.ListBox()
        self.category_list.add_css_class("navigation-sidebar")
        self.category_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.category_list.connect("row-selected", self._category_selected)
        categories = [
            ("all", "Tous les services", "view-list-symbolic"),
            ("active", "En cours", ICON_ACTIVE),
            ("inactive", "Arrêtés", ICON_STOPPED),
            ("failed", "En échec", ICON_FAILED),
            ("masked", "Masqués", ICON_MASKED),
            ("enabled", "Activés", "system-run-symbolic"),
            ("disabled", "Désactivés", "process-stop-symbolic"),
            ("not_found", "Introuvables", ICON_NOT_FOUND),
        ]
        for key, label, icon in categories:
            row = CategoryRow(key, label, icon)
            self.category_rows[key] = row
            self.category_list.append(row)
        self.filter_section.append(self.category_list)

        self.filter_visibility_button = Gtk.ToggleButton()
        self.filter_visibility_button.set_active(True)
        self.filter_visibility_button.add_css_class("flat")
        self.filter_visibility_button.connect(
            "toggled", self._filter_visibility_toggled
        )

        filter_toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        filter_toolbar.set_margin_start(12)
        filter_toolbar.set_margin_end(12)
        filter_toolbar.set_margin_top(2)
        filter_toolbar.set_margin_bottom(4)
        filter_label = Gtk.Label(label="Filtres", xalign=0)
        filter_label.set_hexpand(True)
        filter_label.add_css_class("heading")
        filter_toolbar.append(filter_label)
        filter_toolbar.append(self.filter_visibility_button)
        content.append(filter_toolbar)
        content.append(self.filter_section)
        self._update_filter_visibility_button()

        units_title = Gtk.Label(label="Unités", xalign=0)
        units_title.add_css_class("heading")
        units_title.add_css_class("dimmed")
        units_title.set_margin_start(12)
        units_title.set_margin_top(6)
        units_title.set_margin_bottom(3)
        content.append(units_title)

        service_scroll = Gtk.ScrolledWindow()
        service_scroll.set_vexpand(True)
        service_scroll.set_hexpand(True)
        service_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.service_list = Gtk.ListBox()
        self.service_list.add_css_class("navigation-sidebar")
        self.service_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.service_list.connect("row-selected", self._service_selected)
        self.service_list.set_placeholder(
            Gtk.Label(label="Aucun service correspondant.", margin_top=18, margin_bottom=18)
        )
        service_scroll.set_child(self.service_list)
        content.append(service_scroll)
        self.category_list.select_row(self.category_rows["all"])

        self.sidebar_status = Gtk.Label(label="Prêt", xalign=0)
        self.sidebar_status.add_css_class("dimmed")
        self.sidebar_status.set_wrap(True)
        set_margins(self.sidebar_status, 8)
        content.append(self.sidebar_status)

        toolbar.set_content(content)
        return Adw.NavigationPage.new(toolbar, "Services")

    def _build_detail(self) -> Adw.NavigationPage:
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        self.detail_title = Adw.WindowTitle.new(APP_NAME, "")
        header.set_title_widget(self.detail_title)

        # Primary runtime controls live in the header bar; the rarer
        # enable/disable/mask/remove operations are grouped behind a
        # secondary menu, as recommended by the GNOME HIG.
        self.action_buttons = {}
        self.action_header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.action_header_box.set_visible(False)
        self.action_revealer = self.action_header_box
        self._add_action_button(
            self.action_header_box, "start", "Démarrer", "media-playback-start-symbolic",
            icon_only=True,
        )
        self._add_action_button(
            self.action_header_box, "stop", "Arrêter", "media-playback-stop-symbolic",
            icon_only=True,
        )
        self._add_action_button(
            self.action_header_box, "restart", "Redémarrer", "view-refresh-symbolic",
            icon_only=True,
        )

        more_popover = Gtk.Popover()
        more_popover.add_css_class("menu")
        more_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        set_margins(more_box, 4)
        more_popover.set_child(more_box)
        self.more_popover = more_popover
        self._add_action_button(more_box, "reload", "Recharger la configuration", "view-refresh-symbolic", menu=True)
        more_box.append(Gtk.Separator(margin_top=4, margin_bottom=4))
        self._add_action_button(more_box, "enable_now", "Activer au démarrage", "system-run-symbolic", menu=True)
        self._add_action_button(more_box, "disable_now", "Désactiver au démarrage", "process-stop-symbolic", menu=True)
        more_box.append(Gtk.Separator(margin_top=4, margin_bottom=4))
        self._add_action_button(more_box, "mask", "Masquer", ICON_MASKED, menu=True)
        self._add_action_button(more_box, "unmask", "Démasquer", ICON_UNMASKED, menu=True)
        more_box.append(Gtk.Separator(margin_top=4, margin_bottom=4))
        self._add_action_button(more_box, "remove", "Supprimer complètement…", "user-trash-symbolic", menu=True)

        more_button = Gtk.MenuButton()
        more_button.set_icon_name(
            available_icon_name("view-more-symbolic", "open-menu-symbolic") or "view-more-symbolic"
        )
        more_button.set_tooltip_text("Autres actions")
        more_button.set_popover(more_popover)
        self.action_header_box.append(more_button)
        header.pack_end(self.action_header_box)
        toolbar.add_top_bar(header)

        self.state_revealer = Gtk.Revealer()
        self.state_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.state_revealer.set_reveal_child(False)
        state_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        state_box.set_margin_top(12)
        state_box.set_margin_start(16)
        state_box.set_margin_end(16)
        state_box.set_margin_bottom(4)
        self.state_group = Adw.PreferencesGroup()
        self.state_group.set_title("État actuel")

        self.state_execution_row = Adw.ActionRow(
            title="État d’exécution", subtitle="Chargement…"
        )
        self.state_badge = Gtk.Label(label="Chargement…")
        self.state_badge.set_xalign(1)
        self.state_badge.set_valign(Gtk.Align.CENTER)
        self.state_execution_row.add_suffix(self.state_badge)
        self.state_group.add(self.state_execution_row)

        self.state_activation_row = Adw.ActionRow(
            title="État d’activation", subtitle="Chargement…"
        )
        self.state_group.add(self.state_activation_row)

        self.state_source_row = Adw.ActionRow(title="Source", subtitle="Chargement…")
        self.state_source_row.set_subtitle_selectable(True)
        self.state_source_row.set_subtitle_lines(2)
        self.state_group.add(self.state_source_row)

        state_box.append(self.state_group)
        self.state_revealer.set_child(state_box)

        self.view_stack = Adw.ViewStack()
        self.view_stack.set_vexpand(True)
        self.view_stack.set_hexpand(True)
        self.view_stack.connect("notify::visible-child-name", self._view_changed)

        self.overview_scroll = Gtk.ScrolledWindow()
        self.overview_scroll.set_vexpand(True)
        self.overview_scroll.set_hexpand(True)
        self.overview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        set_margins(self.overview_box, 20)
        self.overview_scroll.set_child(self.overview_box)
        self._add_view_page(
            self.overview_scroll,
            "overview",
            "Vue d’ensemble",
            "view-list-symbolic",
            "view-app-grid-symbolic",
            "view-grid-symbolic",
        )

        status_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        set_margins(status_page, 16)
        status_hint = Gtk.Label(
            label="Sortie de systemctl status", xalign=0
        )
        status_hint.add_css_class("dimmed")
        status_page.append(status_hint)
        status_scroll = Gtk.ScrolledWindow()
        status_scroll.set_vexpand(True)
        status_scroll.set_hexpand(True)
        self.status_text = Gtk.TextView()
        self._configure_text_view(self.status_text, "status")
        status_scroll.set_child(self.status_text)
        status_page.append(status_scroll)
        self._add_view_page(
            status_page,
            "status",
            "Statut",
            "dialog-information-symbolic",
            "system-run-symbolic",
        )

        unit_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        set_margins(unit_page, 16)
        self.unit_path_label = Gtk.Label(label="", xalign=0)
        self.unit_path_label.add_css_class("dimmed")
        self.unit_path_label.set_selectable(True)
        unit_page.append(self.unit_path_label)
        unit_scroll = Gtk.ScrolledWindow()
        unit_scroll.set_vexpand(True)
        unit_scroll.set_hexpand(True)
        self.unit_text = Gtk.TextView()
        self._configure_text_view(self.unit_text, "unit")
        unit_scroll.set_child(self.unit_text)
        unit_page.append(unit_scroll)
        self._add_view_page(
            unit_page,
            "unit",
            "Fichier d’unité",
            "document-open-symbolic",
            "document-properties-symbolic",
            "text-x-generic-symbolic",
        )

        journal_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        set_margins(journal_page, 16)
        journal_toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.journal_hint = Gtk.Label(label="20 dernières entrées", xalign=0)
        self.journal_hint.add_css_class("dimmed")
        self.journal_hint.set_hexpand(True)
        self.journal_toolbar = journal_toolbar
        journal_toolbar.append(self.journal_hint)
        self.journal_refresh = Gtk.Button()
        self.journal_refresh.set_child(themed_icon("view-refresh-symbolic", pixel_size=18))
        self.journal_refresh.set_tooltip_text("Actualiser le journal")
        self.journal_refresh.connect("clicked", lambda *_: self._load_journal())
        journal_toolbar.append(self.journal_refresh)
        journal_page.append(journal_toolbar)
        journal_scroll = Gtk.ScrolledWindow()
        journal_scroll.set_vexpand(True)
        journal_scroll.set_hexpand(True)
        self.journal_text = Gtk.TextView()
        self._configure_text_view(self.journal_text, "journal")
        journal_scroll.set_child(self.journal_text)
        journal_page.append(journal_scroll)
        self._add_view_page(
            journal_page,
            "journal",
            "Journal",
            "utilities-terminal-symbolic",
            "terminal-symbolic",
            "application-x-executable-symbolic",
        )

        self.view_stack.set_visible_child_name("overview")
        self._set_text(self.status_text, "Sélectionnez un service pour lire son statut.")
        self._set_text(self.unit_text, "Sélectionnez un service pour lire son fichier d’unité.")
        self._set_text(self.journal_text, "Sélectionnez un service pour lire son journal.")
        self.unit_path_label.set_text("Source : aucune unité sélectionnée")

        self.view_switcher = Adw.ViewSwitcherBar()
        self.view_switcher.set_stack(self.view_stack)
        self.view_switcher.set_reveal(False)
        toolbar.add_bottom_bar(self.view_switcher)

        self.detail_stack = Gtk.Stack()
        self.detail_stack.set_vexpand(True)
        self.detail_stack.set_hexpand(True)
        empty = Adw.StatusPage()
        empty_icon = available_icon_name(
            "system-run-symbolic", "applications-system-symbolic", "dialog-information-symbolic"
        )
        if empty_icon:
            empty.set_icon_name(empty_icon)
        empty.set_title("Sélectionnez un service")
        empty.set_description(
            "Choisissez une unité dans la liste pour consulter son état, son fichier et son journal."
        )
        self.detail_stack.add_named(empty, "empty")
        self.detail_stack.add_named(self.view_stack, "service")
        self.detail_stack.set_visible_child_name("empty")
        detail_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        detail_content.set_vexpand(True)
        detail_content.set_hexpand(True)
        detail_content.append(self.state_revealer)
        detail_content.append(self.detail_stack)
        toolbar.set_content(detail_content)
        return Adw.NavigationPage.new(toolbar, "Service")

    def _add_view_page(
        self,
        child: Gtk.Widget,
        name: str,
        title: str,
        *icon_names: str,
    ) -> None:
        icon_name = available_icon_name(*icon_names)
        if icon_name:
            self.view_stack.add_titled_with_icon(child, name, title, icon_name)
        else:
            # Do not manufacture an image widget: an icon-less page is still
            # preferable to a broken placeholder in a non-standard theme.
            self.view_stack.add_titled(child, name, title)

    def _configure_text_view(
        self, text_view: Gtk.TextView, kind: str = "generic"
    ) -> None:
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.set_wrap_mode(Gtk.WrapMode.NONE)
        text_view.set_top_margin(10)
        text_view.set_bottom_margin(10)
        text_view.set_left_margin(10)
        text_view.set_right_margin(10)
        text_view.add_css_class("view")
        text_view.add_css_class("monospace")
        if kind != "generic":
            text_view.add_css_class(f"systemd-output-{kind}")

        tag_table = text_view.get_buffer().get_tag_table()
        tag_specs = {
            "systemd-section": (Pango.Weight.BOLD, None),
            "systemd-key": (Pango.Weight.BOLD, None),
            "systemd-value": (None, None),
            "systemd-comment": (None, None),
            "systemd-output-error": (Pango.Weight.BOLD, None),
            "systemd-output-warning": (Pango.Weight.BOLD, None),
            "systemd-output-success": (None, None),
        }
        for name, (weight, style) in tag_specs.items():
            tag = Gtk.TextTag.new(name)
            if weight is not None:
                tag.set_property("weight", weight)
            if style is not None:
                tag.set_property("style", style)
            tag_table.add(tag)
        self.output_text_views.append(text_view)
        self._apply_output_tag_colors(text_view)

    def _style_changed(self, *_args: object) -> None:
        for text_view in self.output_text_views:
            self._apply_output_tag_colors(text_view)

    @staticmethod
    def _apply_output_tag_colors(text_view: Gtk.TextView) -> None:
        # Gtk.TextTag foregrounds cannot directly consume Adwaita CSS
        # variables. Choose the matching GNOME palette contrast for the
        # current light/dark style instead of forcing dark-theme colors into
        # light mode.
        dark = Adw.StyleManager.get_default().get_dark()
        if dark:
            colors = {
                "systemd-section": "#99c1f1",
                "systemd-key": "#81d0ff",
                "systemd-value": "#8ff0a4",
                "systemd-comment": "#c0bfbc",
                "systemd-output-error": "#ff888c",
                "systemd-output-warning": "#ffc252",
                "systemd-output-success": "#78e9ab",
            }
        else:
            colors = {
                "systemd-section": "#1a5fb4",
                "systemd-key": "#0461be",
                "systemd-value": "#26a269",
                "systemd-comment": "#5e5c64",
                "systemd-output-error": "#c00023",
                "systemd-output-warning": "#905400",
                "systemd-output-success": "#007c3d",
            }
        tag_table = text_view.get_buffer().get_tag_table()
        for name, color in colors.items():
            tag = tag_table.lookup(name)
            if tag is not None:
                tag.set_property("foreground", color)

    def _set_text(self, text_view: Gtk.TextView, value: str) -> None:
        value = value or ""
        buffer = text_view.get_buffer()
        buffer.set_text(value)
        if text_view.has_css_class("systemd-output-unit"):
            kind = "unit"
        elif text_view.has_css_class("systemd-output-status"):
            kind = "status"
        elif text_view.has_css_class("systemd-output-journal"):
            kind = "journal"
        else:
            kind = "generic"
        self._highlight_buffer(buffer, value, kind)

    @staticmethod
    def _highlight_buffer(
        buffer: Gtk.TextBuffer, value: str, kind: str
    ) -> None:
        start, end = buffer.get_bounds()
        buffer.remove_all_tags(start, end)
        if not value:
            return

        def apply_tag(tag_name: str, start_offset: int, end_offset: int) -> None:
            if end_offset <= start_offset:
                return
            tag_start = buffer.get_iter_at_offset(start_offset)
            tag_end = buffer.get_iter_at_offset(end_offset)
            buffer.apply_tag_by_name(tag_name, tag_start, tag_end)

        offset = 0
        for raw_line in value.splitlines(keepends=True):
            line = raw_line.rstrip("\r\n")
            line_end = offset + len(line)
            if kind == "unit":
                stripped = line.strip()
                if re.fullmatch(r"\[[^\]]+\]", stripped):
                    apply_tag("systemd-section", offset, line_end)
                elif stripped.startswith(("#", ";")):
                    apply_tag("systemd-comment", offset, line_end)
                else:
                    key_match = re.match(
                        r"^\s*([A-Za-z][A-Za-z0-9_.-]*)(\s*=)", line
                    )
                    if key_match:
                        apply_tag(
                            "systemd-key",
                            offset + key_match.start(1),
                            offset + key_match.end(1),
                        )
                        value_start = offset + key_match.end(2)
                        for value_match in re.finditer(
                            r"\b(?:yes|no|true|false|on|off|auto|always|never)\b",
                            line[key_match.end(2) :],
                            flags=re.IGNORECASE,
                        ):
                            apply_tag(
                                "systemd-value",
                                value_start + value_match.start(),
                                value_start + value_match.end(),
                            )
                    comment_index = next(
                        (
                            index
                            for index, character in enumerate(line)
                            if character in "#;"
                        ),
                        -1,
                    )
                    if comment_index >= 0:
                        apply_tag(
                            "systemd-comment",
                            offset + comment_index,
                            line_end,
                        )
            elif kind in {"status", "journal"}:
                lowered = line.casefold()
                if re.search(r"\b(failed|failure|error|fatal|panic)\b", lowered):
                    apply_tag("systemd-output-error", offset, line_end)
                elif re.search(r"\b(warn|warning)\b", lowered):
                    apply_tag("systemd-output-warning", offset, line_end)
                elif re.search(
                    r"\b(active|running|started|succeeded|listening|finished)\b",
                    lowered,
                ):
                    apply_tag("systemd-output-success", offset, line_end)
            offset += len(raw_line)

    def _update_state_summary(
        self,
        service: Service,
        details: Optional[dict[str, str]],
        loading: bool,
        error: Optional[str] = None,
    ) -> None:
        details = details or {}
        active = details.get("ActiveState") or service.active_state
        sub = details.get("SubState") or service.sub_state
        load = details.get("LoadState") or service.load_state
        unit_file_state = details.get("UnitFileState") or service.unit_file_state
        fragment_path = details.get("FragmentPath", "")

        if loading:
            badge_text = "Chargement…"
            badge_class = "dimmed"
        elif load == "not-found":
            badge_text = "Introuvable"
            badge_class = "warning"
        elif unit_file_state in {"masked", "masked-runtime"}:
            badge_text = "Masqué"
            badge_class = "warning"
        elif active == "failed":
            badge_text = "En échec"
            badge_class = "error"
        elif active in {"active", "reloading"}:
            badge_text = "Actif"
            if sub and sub not in {"running", "listening"}:
                badge_text = f"Actif · {_fr(SUB_STATE_FR, sub)}"
            badge_class = "success"
        elif active in {"activating", "deactivating"}:
            badge_text = "Transition en cours"
            badge_class = "warning"
        else:
            badge_text = "Arrêté"
            badge_class = "dimmed"

        for css_class in ("success", "warning", "error", "dimmed"):
            self.state_badge.remove_css_class(css_class)
        self.state_badge.add_css_class(badge_class)
        self.state_badge.set_text(badge_text)

        execution = (
            f"{_fr(ACTIVE_STATE_FR, active)} · {_fr(SUB_STATE_FR, sub)}"
            f" · {_fr(LOAD_STATE_FR, load)}"
        )
        if error:
            execution = f"{execution} · lecture détaillée impossible"
        self.state_execution_row.set_subtitle(execution)
        self.state_activation_row.set_subtitle(
            _fr(UNIT_FILE_STATE_FR, unit_file_state) if unit_file_state else "—"
        )
        if fragment_path:
            source = fragment_path
        elif load == "not-found":
            source = "Fichier absent / unité fantôme"
        else:
            source = "Aucun fichier d’unité identifié"
        self.state_source_row.set_subtitle(source)

    def _scope_changed(self, dropdown: Gtk.DropDown, _param: object) -> None:
        user_scope = dropdown.get_selected() == 1
        if user_scope == self.systemctl.user:
            return
        self.selection_generation += 1
        self.systemctl = Systemctl(user=user_scope)
        self.selected_name = None
        self.selected_snapshot = None
        self.current_details = None
        self.detail_title.set_title(APP_NAME)
        self.detail_title.set_subtitle("")
        self.detail_stack.set_visible_child_name("empty")
        self.view_switcher.set_reveal(False)
        self.action_header_box.set_visible(False)
        self.state_revealer.set_reveal_child(False)
        self.journal_for = None
        self.journal_refresh.set_sensitive(False)
        self.refresh_services()

    def _filter_visibility_toggled(self, button: Gtk.ToggleButton) -> None:
        visible = button.get_active()
        self.filter_section.set_visible(visible)
        self._update_filter_visibility_button()

    def _update_filter_visibility_button(self) -> None:
        visible = self.filter_visibility_button.get_active()
        icon_key = "view-conceal-symbolic" if visible else "view-reveal-symbolic"
        fallback = "go-up-symbolic" if visible else "go-down-symbolic"
        icon_name = available_icon_name(icon_key, fallback) or fallback
        self.filter_visibility_button.set_icon_name(icon_name)
        self.filter_visibility_button.set_label("Masquer" if visible else "Afficher")
        self.filter_visibility_button.set_tooltip_text(
            "Masquer les filtres" if visible else "Afficher les filtres"
        )

    def _category_selected(self, _list_box: Gtk.ListBox, row: Optional[CategoryRow]) -> None:
        if row is None:
            return
        self.current_category = row.category_key
        self._update_service_list()

    def _unit_type_changed(self, dropdown: Gtk.DropDown, _param: object) -> None:
        selected = dropdown.get_selected()
        self.current_unit_type = "all" if selected == 0 else UNIT_TYPES[selected - 1]
        self._update_category_counts()
        self._update_service_list()

    def _search_changed(self, entry: Gtk.SearchEntry) -> None:
        self._update_service_list()

    def _service_selected(self, _list_box: Gtk.ListBox, row: Optional[ServiceRow]) -> None:
        if row is None:
            return
        name = row.service_name
        if name == self.selected_name and self.current_details is not None:
            return
        self.selection_generation += 1
        selection_generation = self.selection_generation
        self.selected_name = name
        self.selected_snapshot = None
        self.current_details = None
        self.detail_title.set_title(name)
        self.detail_title.set_subtitle(service_subtitle(self.services_by_name.get(name)))
        self.detail_stack.set_visible_child_name("service")
        if self.split_view.get_collapsed():
            self.split_view.set_show_content(True)
        self.view_switcher.set_reveal(True)
        self.action_header_box.set_visible(True)
        self.state_revealer.set_reveal_child(True)
        self.journal_for = None
        service = self.services_by_name.get(name, Service(name=name))
        self._update_state_summary(service, {}, loading=True)
        try:
            self._populate_overview(service, {}, loading=True)
        except Exception as exc:
            # A rendering mistake must not leave the service controls locked
            # or prevent the asynchronous detail requests from starting.
            message = f"Impossible d’afficher le panneau de {name} : {exc}"
            self._set_text(self.status_text, message)
            self._set_text(self.unit_text, message)
            self._update_state_summary(service, {}, loading=False, error=message)
            self._set_action_sensitivity(service, {}, loading=False)
            self._show_error(message)
        self._set_text(self.status_text, "Chargement de systemctl status…")
        self._set_text(self.journal_text, "Chargement du journal…")
        if self.journal_hint is not None:
            self.journal_hint.set_text("Chargement du journal…")
        self.unit_path_label.set_text("Source : chargement…")
        self._load_details(name, selection_generation)
        if self.view_stack.get_visible_child_name() == "journal":
            self._load_journal(selection_generation)

    def _view_changed(self, stack: Adw.ViewStack, _param: object) -> None:
        if stack.get_visible_child_name() == "journal" and self.selected_name:
            if self.journal_for != self.selected_name:
                self._load_journal(self.selection_generation)

    def _automatic_refresh(self) -> bool:
        if self.window is None:
            return False
        if not self.services_loading and not self.action_in_flight:
            self.refresh_services(silent=True)
        return True

    def refresh_services(self, silent: bool = False) -> None:
        if self.services_loading:
            return
        self.services_loading = True
        self.refresh_generation += 1
        generation = self.refresh_generation
        controller = self.systemctl
        if not silent:
            self.sidebar_status.set_text(f"Actualisation · {controller.scope_name.lower()}…")

        def finished(value: object, error: Optional[BaseException]) -> bool:
            if generation != self.refresh_generation:
                return False
            self.services_loading = False
            if error is not None:
                self.sidebar_status.set_text("Impossible de lire les services")
                self._show_error(str(error))
                return False
            self._services_loaded(value)  # type: ignore[arg-type]
            return False

        self._run_background(controller.list_services, finished)

    def _services_loaded(self, services: list[Service]) -> None:
        selected_before = self.selected_name
        previous = self.services_by_name.get(selected_before or "")
        previous_snapshot = self._service_snapshot(previous) if previous else None
        self.services = services
        self.services_by_name = {service.name: service for service in services}
        self._update_category_counts()
        self._update_service_list()
        self.sidebar_status.set_text(
            f"{len(services)} service(s) · {self.systemctl.scope_name.lower()}"
        )

        if selected_before and selected_before in self.services_by_name:
            current = self.services_by_name[selected_before]
            current_snapshot = self._service_snapshot(current)
            if previous_snapshot != current_snapshot:
                self.current_details = None
                self._populate_overview(current, {}, loading=True)
                self._update_state_summary(current, {}, loading=True)
                self._load_details(selected_before, self.selection_generation)
            elif self.current_details is not None:
                self._update_state_summary(current, self.current_details, loading=False)
        elif selected_before:
            self.selection_generation += 1
            self.selected_name = None
            self.selected_snapshot = None
            self.current_details = None
            self.detail_title.set_title(APP_NAME)
            self.detail_title.set_subtitle("")
            self.detail_stack.set_visible_child_name("empty")
            self.view_switcher.set_reveal(False)
            self.action_header_box.set_visible(False)
            self.state_revealer.set_reveal_child(False)
            self.journal_for = None
            self.journal_refresh.set_sensitive(False)

    @staticmethod
    def _service_snapshot(service: Optional[Service]) -> Optional[tuple[str, ...]]:
        if service is None:
            return None
        return (
            service.unit_file_state,
            service.load_state,
            service.active_state,
            service.sub_state,
            service.description,
        )

    def _matches_category(self, service: Service) -> bool:
        category = self.current_category
        if category == "all":
            return True
        if category == "active":
            return service.is_active
        if category == "inactive":
            return service.is_stopped
        if category == "failed":
            return service.is_failed
        if category == "masked":
            return service.is_masked
        if category == "enabled":
            return service.is_enabled
        if category == "disabled":
            return service.is_disabled
        if category == "not_found":
            return service.is_not_found
        return True

    def _visible_services(self) -> list[Service]:
        query = self.search_entry.get_text().strip().casefold()
        visible = []
        for service in self.services:
            # A non-empty search is global: the selected category must not
            # hide a service the user is explicitly looking for.  Once the
            # field is empty, the selected category is applied normally.
            if not query and not self._matches_category(service):
                continue
            if (
                self.current_unit_type != "all"
                and service.unit_type != self.current_unit_type
            ):
                continue
            haystack = f"{service.name} {service.description}".casefold()
            if query and query not in haystack:
                continue
            visible.append(service)
        return visible

    def _update_category_counts(self) -> None:
        # ``services`` is the complete inventory from list-unit-files.  Runtime
        # counters must instead be based on units for which list-units actually
        # returned a state.  This prevents every installed-but-unloaded socket,
        # timer, etc. from being counted as "Arrêté".  The selected unit type
        # is also applied so the sidebar answers e.g. "combien de sockets sont
        # actifs ?" rather than showing totals for every unit kind.
        typed = [
            service
            for service in self.services
            if self.current_unit_type == "all"
            or service.unit_type == self.current_unit_type
        ]
        runtime = [service for service in typed if service.has_runtime_state]
        categories = {
            "all": len(typed),
            "active": sum(service.is_active for service in runtime),
            "inactive": sum(service.is_stopped for service in runtime),
            "failed": sum(service.is_failed for service in runtime),
            "masked": sum(service.is_masked for service in typed),
            "enabled": sum(service.is_enabled for service in typed),
            "disabled": sum(service.is_disabled for service in typed),
            "not_found": sum(service.is_not_found for service in typed),
        }
        for key, count in categories.items():
            if key in self.category_rows:
                self.category_rows[key].count_label.set_text(str(count))

    def _update_service_list(self) -> None:
        selected = self.selected_name
        visible = self._visible_services()
        query = self.search_entry.get_text().strip()
        if query:
            noun = "résultat" if len(visible) == 1 else "résultats"
        else:
            noun = "service" if len(visible) == 1 else "services"
        self.results_count.set_text(f"{len(visible)} {noun}")
        visible_names = {service.name for service in visible}
        for name, row in list(self.service_rows.items()):
            if name not in visible_names:
                self.service_list.remove(row)
                del self.service_rows[name]
        for service in visible:
            row = self.service_rows.get(service.name)
            if row is None:
                row = ServiceRow(service)
                self.service_rows[service.name] = row
                self.service_list.append(row)
            else:
                row.update(service)

        if selected and selected in self.service_rows:
            self.service_list.select_row(self.service_rows[selected])
        elif selected is not None:
            # The current service may be hidden by the search/category.  Clear
            # the stale ListBox selection so the filtered rows remain usable.
            self.service_list.unselect_all()
        elif visible:
            # The first service is selected only on the first load, not when a
            # search/category temporarily hides the current selection.
            if self.selected_name is None:
                first_row = next(iter(self.service_rows.values()))
                self.service_list.select_row(first_row)
                # GTK normally emits row-selected synchronously.  Keep a
                # direct fallback for the first population, where a list can
                # still be attached to the window and not yet be mapped.
                if self.selected_name is None:
                    self._service_selected(self.service_list, first_row)

    def _load_details(
        self, name: str, selection_generation: Optional[int] = None
    ) -> None:
        if selection_generation is None:
            selection_generation = self.selection_generation
        self.details_generation += 1
        request_generation = self.details_generation
        controller = self.systemctl
        self._set_text(self.unit_text, "Chargement du fichier d’unité…")
        self._set_text(self.status_text, "Chargement de systemctl status…")

        def finished(value: object, error: Optional[BaseException]) -> bool:
            if (
                selection_generation != self.selection_generation
                or request_generation != self.details_generation
                or name != self.selected_name
                or controller is not self.systemctl
            ):
                return False
            if error is not None:
                self.current_details = {}
                message = f"Impossible de charger les détails : {error}"
                self._set_text(self.status_text, message)
                self._set_text(self.unit_text, message)
                self._update_state_summary(
                    self.services_by_name.get(name, Service(name=name)),
                    {},
                    loading=False,
                    error=message,
                )
                self._populate_overview(
                    self.services_by_name.get(name, Service(name=name)),
                    {},
                    loading=False,
                    error=message,
                )
                self._show_error(message)
                return False
            details = value if isinstance(value, dict) else {}
            self.current_details = details
            self._set_text(
                self.status_text,
                details.get("status", "").strip()
                or "systemctl status n’a renvoyé aucune sortie.",
            )
            self._set_text(
                self.unit_text,
                details.get("unit_file", "").strip()
                or "systemctl cat n’a renvoyé aucun contenu pour cette unité.",
            )
            self.unit_path_label.set_text(
                f"Source : {details.get('fragment_path') or 'fichier non identifié'}"
            )
            service = self.services_by_name.get(name, Service(name=name))
            self._update_state_summary(service, details, loading=False)
            self._populate_overview(
                service, details, loading=False
            )
            if (
                self.view_stack.get_visible_child_name() == "journal"
                and self.journal_for != name
            ):
                self._load_journal(selection_generation)
            return False

        self._run_background(lambda: controller.get_details(name), finished)

    def _load_journal(self, selection_generation: Optional[int] = None) -> None:
        if not self.selected_name:
            return
        if selection_generation is None:
            selection_generation = self.selection_generation
        self.journal_generation += 1
        request_generation = self.journal_generation
        name = self.selected_name
        controller = self.systemctl
        self.journal_for = name
        self._set_text(self.journal_text, "Chargement du journal…")
        if self.journal_hint is not None:
            self.journal_hint.set_text("Chargement du journal…")
        self.journal_refresh.set_sensitive(False)

        def finished(value: object, error: Optional[BaseException]) -> bool:
            if (
                selection_generation != self.selection_generation
                or request_generation != self.journal_generation
                or name != self.selected_name
                or controller is not self.systemctl
            ):
                return False
            self.journal_refresh.set_sensitive(True)
            if error is not None:
                self._set_text(self.journal_text, str(error))
                if self.journal_hint is not None:
                    self.journal_hint.set_text("Journal indisponible")
                self._show_error(str(error))
                return False
            journal = str(value)
            self._set_text(self.journal_text, journal)
            if self.journal_hint is not None:
                if journal.startswith("Impossible de lire le journal"):
                    self.journal_hint.set_text(
                        "Journal indisponible · vérifiez les droits d’accès"
                    )
                elif journal.startswith("Aucune entrée de journal"):
                    self.journal_hint.set_text("Aucune entrée de journal")
                else:
                    self.journal_hint.set_text("20 dernières entrées")
            return False

        self._run_background(lambda: controller.get_journal(name), finished)

    def _populate_overview(
        self,
        service: Service,
        details: Optional[dict[str, str]],
        loading: bool,
        error: Optional[str] = None,
    ) -> None:
        clear_container(self.overview_box)
        details = details or {}
        description = details.get("Description") or service.description
        if loading and not description:
            description = "Lecture de la description officielle…"
        if not description:
            description = "Aucune description fournie par l’unité."

        identity = Adw.PreferencesGroup()
        identity.set_title(service.name)
        identity_row = Adw.ActionRow(title="Description officielle", subtitle=description)
        identity_row.set_subtitle_lines(3)
        identity.add(identity_row)
        self.overview_box.append(identity)

        if error:
            error_group = Adw.PreferencesGroup()
            error_group.set_title("Lecture détaillée")
            error_row = Adw.ActionRow(title="Erreur", subtitle=error)
            error_row.add_css_class("error")
            error_group.add(error_row)
            self.overview_box.append(error_group)

        info_group = Adw.PreferencesGroup()
        info_group.set_title("Paramètres d’exécution")
        self._add_info_row(info_group, "Preset", details.get("UnitFilePreset") or service.preset)
        self._add_info_row(info_group, "PID principal", details.get("MainPID", ""))
        self._add_info_row(info_group, "Résultat", details.get("Result", ""))
        self._add_info_row(info_group, "Utilisateur", details.get("User", ""))
        self._add_info_row(info_group, "Type", details.get("Type", ""))
        self._add_info_row(info_group, "Démarré depuis", details.get("ActiveEnterTimestamp", ""))
        self._add_info_row(info_group, "Drop-ins", details.get("DropInPaths", ""))
        self.overview_box.append(info_group)
        self.overview_box.append(self._dependency_group(details, loading))

        documentation = details.get("Documentation") or details.get("documentation_value")
        if documentation:
            docs_group = Adw.PreferencesGroup()
            docs_group.set_title("Documentation")
            docs_row = Adw.ActionRow(title="Références systemd", subtitle=documentation)
            docs_row.set_subtitle_lines(3)
            docs_row.set_selectable(True)
            docs_group.add(docs_row)
            self.overview_box.append(docs_group)

        if not loading:
            status_group = Adw.PreferencesGroup()
            status_group.set_title("Sortie systemctl status")
            status_row = Adw.ActionRow(
                title="Consulter l’état détaillé",
                subtitle="Ouvre la sortie complète de systemctl status dans l’onglet Statut.",
            )
            status_button = Gtk.Button(label="Afficher")
            status_button.add_css_class("flat")
            status_button.connect("clicked", lambda *_: self._show_status_tab(service.name))
            status_row.add_suffix(status_button)
            status_group.add(status_row)
            self.overview_box.append(status_group)

        self._set_action_sensitivity(service, details, loading)

    @staticmethod
    def _dependency_group(
        details: dict[str, str], loading: bool
    ) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup()
        group.set_title("Dépendances")
        if loading:
            group.add(
                Adw.ActionRow(
                    title="Lecture des relations…",
                    subtitle="systemctl show est en cours d’exécution.",
                )
            )
            return group

        relation_fields = [
            ("Requiert", "Requires"),
            ("Requis par", "RequiredBy"),
            ("Souhaite", "Wants"),
            ("Souhaité par", "WantedBy"),
            ("Après", "After"),
            ("Avant", "Before"),
            ("En conflit avec", "Conflicts"),
            ("En conflit avec lui", "ConflictedBy"),
            ("Partie de", "PartOf"),
            ("Lié à", "BindsTo"),
            ("Déclenche", "Triggers"),
            ("Déclenché par", "TriggeredBy"),
            ("En cas d’échec", "OnFailure"),
            ("Référencé par", "ReferencedBy"),
        ]
        added = False
        for title, key in relation_fields:
            units = [
                unit
                for unit in (details.get(key, "") or "").split()
                if unit and unit != "-"
            ]
            if not units:
                continue
            added = True
            row = Adw.ActionRow(
                title=f"{title} ({len(units)})",
                subtitle=" ".join(units),
            )
            row.add_css_class("property")
            row.set_subtitle_selectable(True)
            row.set_subtitle_lines(4)
            group.add(row)

        if not added:
            group.add(
                Adw.ActionRow(
                    title="Aucune relation déclarée",
                    subtitle="Cette unité ne fournit aucune relation affichable.",
                )
            )
        return group

    def _add_action_button(
        self,
        container: Gtk.Box | Gtk.FlowBox,
        action: str,
        label: str,
        icon_name: str,
        *,
        icon_only: bool = False,
        menu: bool = False,
    ) -> None:
        button = Gtk.Button()
        resolved_icon = available_icon_name(
            icon_name,
            "applications-system-symbolic",
            "dialog-information-symbolic",
        )
        if icon_only:
            if resolved_icon is not None:
                button.set_icon_name(resolved_icon)
            else:
                button.set_label(label)
            button.set_tooltip_text(label)
        else:
            content = Adw.ButtonContent()
            content.set_label(label)
            content.set_halign(Gtk.Align.START)
            if resolved_icon is not None:
                content.set_icon_name(resolved_icon)
            button.set_child(content)
        if menu:
            button.add_css_class("flat")
            button.set_halign(Gtk.Align.FILL)

        def clicked(*_: object) -> None:
            if menu:
                self.more_popover.popdown()
            self._request_action(action)

        button.connect("clicked", clicked)
        button.set_valign(Gtk.Align.CENTER)
        container.append(button)
        self.action_buttons[action] = button

    @staticmethod
    def _add_info_row(group: Adw.PreferencesGroup, title: str, value: str) -> None:
        if not value or value in {"[not set]", "n/a"}:
            value = "—"
        row = Adw.ActionRow(title=title, subtitle=value)
        row.add_css_class("property")
        row.set_subtitle_selectable(True)
        row.set_subtitle_lines(2)
        group.add(row)

    @staticmethod
    def _state_css_class(service: Service) -> str:
        if service.is_failed:
            return "error"
        if service.is_masked or service.is_not_found:
            return "warning"
        if service.is_active:
            return "success"
        return "dimmed"

    @staticmethod
    def _execution_text(service: Service, details: dict[str, str]) -> str:
        active = details.get("ActiveState") or service.active_state
        sub = details.get("SubState") or service.sub_state
        load = details.get("LoadState") or service.load_state
        return (
            f"{_fr(ACTIVE_STATE_FR, active)} · {_fr(SUB_STATE_FR, sub)}"
            f" · {_fr(LOAD_STATE_FR, load)}"
        )

    def _set_action_sensitivity(
        self, service: Service, details: dict[str, str], loading: bool
    ) -> None:
        for button in self.action_buttons.values():
            button.set_sensitive(not loading and not self.action_in_flight)
            button.remove_css_class("destructive-action")
            button.remove_css_class("suggested-action")
        if loading:
            return

        unit_file_state = details.get("UnitFileState") or service.unit_file_state
        active_state = details.get("ActiveState") or service.active_state
        masked = unit_file_state in {"masked", "masked-runtime"}

        # Keep actions visible, but grey out the ones that make no sense in the
        # current state (Démarrer on a running service, Arrêter on a stopped
        # one...).  The final authority still remains systemctl and polkit.
        load_state = details.get("LoadState") or service.load_state
        not_found = load_state == "not-found"
        running = active_state in {"active", "reloading", "activating"}
        usable = not masked and not not_found

        allowed = {
            "start": usable and not running and active_state != "deactivating",
            "stop": running,
            "restart": usable and running,
            "reload": usable and active_state in {"active", "reloading"},
            "enable_now": unit_file_state == "disabled" and not not_found,
            "disable_now": unit_file_state in {"enabled", "enabled-runtime"},
            "mask": not masked,
            "unmask": masked,
        }
        for action, ok in allowed.items():
            if action in self.action_buttons and not ok:
                self.action_buttons[action].set_sensitive(False)

        if unit_file_state in {"enabled", "enabled-runtime"}:
            if "disable_now" in self.action_buttons:
                self.action_buttons["disable_now"].add_css_class("destructive-action")
        if "remove" in self.action_buttons:
            self.action_buttons["remove"].add_css_class("destructive-action")

    def _request_action(self, action: str) -> None:
        if not self.selected_name or self.action_in_flight:
            return
        if action == "remove":
            self._request_remove()
            return
        if action in {"mask", "disable_now", "stop"}:
            labels = {
                "mask": ("Masquer cette unité ?", "Le service ne pourra plus être démarré tant qu’il ne sera pas désmasqué."),
                "disable_now": ("Désactiver ce service ?", "Le service sera arrêté puis retiré du démarrage automatique."),
                "stop": ("Arrêter ce service ?", "Les applications qui en dépendent peuvent être affectées."),
            }
            heading, body = labels[action]
            self._confirm_action(action, heading, body)
            return
        self._execute_action(action)

    def _confirm_action(self, action: str, heading: str, body: str) -> None:
        dialog = Adw.AlertDialog.new(heading, body)
        dialog.add_response("cancel", "Annuler")
        dialog.add_response("confirm", "Confirmer")
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        try:
            dialog.set_response_appearance("confirm", Adw.ResponseAppearance.DESTRUCTIVE)
        except (AttributeError, TypeError):
            pass

        def response(_dialog: Adw.AlertDialog, response_id: str) -> None:
            if response_id == "confirm":
                self._execute_action(action)

        dialog.connect("response", response)
        dialog.present(self.window)

    def _execute_action(self, action: str) -> None:
        if not self.selected_name:
            return
        name = self.selected_name
        controller = self.systemctl
        self.action_in_flight = True
        for button in self.action_buttons.values():
            button.set_sensitive(False)
        self.sidebar_status.set_text(f"Action en cours · {name}")

        def finished(value: object, error: Optional[BaseException]) -> bool:
            self.action_in_flight = False
            if controller is not self.systemctl or name != self.selected_name:
                return False
            if error is not None:
                self._show_error(str(error))
            else:
                result = value  # type: ignore[assignment]
                if result.returncode == 0:
                    self._show_toast(f"Action effectuée : {self._action_label(action)}")
                else:
                    detail = (result.stderr or result.stdout).strip()
                    self._show_error(detail or f"systemctl a renvoyé le code {result.returncode}")
            if self.selected_name == name:
                service = self.services_by_name.get(name, Service(name=name))
                self._populate_overview(
                    service,
                    {},
                    loading=True,
                )
                self._update_state_summary(service, {}, loading=True)
                self._load_details(name, self.selection_generation)
            self.refresh_services()
            return False

        self._run_background(lambda: controller.execute(action, name), finished)

    def _show_status_tab(self, name: str) -> None:
        if name != self.selected_name:
            return
        self.view_stack.set_visible_child_name("status")

    @staticmethod
    def _removal_plan_text(plan: RemovalPlan) -> str:
        lines = [
            f"Contexte : {plan.scope}",
            f"État systemd : {plan.load_state} · {plan.active_state}",
            f"Activation : {plan.unit_file_state}",
        ]
        if plan.is_ghost:
            lines.append(
                "Aucun fichier local trouvé : cette unité semble fantôme. "
                "Le nettoyage rechargera systemd et réinitialisera son état."
            )
        else:
            removable = [item for item in plan.existing_items if item.removable]
            if removable:
                lines.append("Entrées locales qui seront supprimées :")
                lines.extend(f"• {item.path}" for item in removable)
            else:
                lines.append("Aucune entrée locale supprimable trouvée.")
            protected = [item for item in plan.existing_items if not item.removable]
            if protected:
                lines.append(
                    "Éléments protégés, conservés (fichiers fournis par le système) :"
                )
                lines.extend(f"• {item.path}" for item in protected)
        if plan.references:
            lines.append(
                "Unités qui référencent celle-ci ; leurs fichiers ne seront pas supprimés :"
            )
            lines.extend(f"• {reference}" for reference in plan.references)
        lines.append("Les journaux systemd ne sont jamais supprimés par cette action.")
        return "\n".join(lines)

    def _request_remove(self) -> None:
        if not self.selected_name or self.action_in_flight:
            return
        name = self.selected_name
        controller = self.systemctl
        selection_generation = self.selection_generation
        self.action_in_flight = True
        for button in self.action_buttons.values():
            button.set_sensitive(False)
        self.sidebar_status.set_text(f"Préparation de la suppression · {name}")

        def finished(value: object, error: Optional[BaseException]) -> bool:
            if (
                selection_generation != self.selection_generation
                or name != self.selected_name
                or controller is not self.systemctl
            ):
                self.action_in_flight = False
                return False
            self.action_in_flight = False
            if error is not None:
                self._show_error(str(error))
                return False
            if not isinstance(value, RemovalPlan):
                self._show_error("Le plan de suppression reçu est invalide.")
                return False
            self._show_remove_dialog(value)
            return False

        self._run_background(lambda: controller.get_removal_plan(name), finished)

    def _show_remove_dialog(self, plan: RemovalPlan) -> None:
        if plan.name != self.selected_name:
            return
        dialog = Adw.AlertDialog.new(
            "Nettoyer cette unité ?"
            if plan.is_ghost
            else "Supprimer complètement cette unité ?",
            "Cette opération arrête et désactive l’unité, retire ses fichiers "
            "locaux et recharge systemd. Elle est irréversible pour ces fichiers.",
        )
        dialog.add_response("cancel", "Annuler")
        dialog.add_response("confirm", "Supprimer")
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        try:
            dialog.set_response_appearance("confirm", Adw.ResponseAppearance.DESTRUCTIVE)
            dialog.set_response_enabled("confirm", False)
        except (AttributeError, TypeError):
            pass

        extra = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        plan_label = Gtk.Label(label=self._removal_plan_text(plan), xalign=0)
        plan_label.set_wrap(True)
        plan_label.set_selectable(True)
        plan_label.set_max_width_chars(100)
        plan_scroll = Gtk.ScrolledWindow()
        plan_scroll.set_min_content_height(220)
        plan_scroll.set_max_content_height(360)
        plan_scroll.set_child(plan_label)
        extra.append(plan_scroll)

        confirmation_label = Gtk.Label(
            label=f"Pour confirmer, saisissez exactement : {plan.name}", xalign=0
        )
        confirmation_label.set_wrap(True)
        extra.append(confirmation_label)
        confirmation_entry = Gtk.Entry()
        confirmation_entry.set_placeholder_text(plan.name)
        confirmation_entry.set_hexpand(True)
        extra.append(confirmation_entry)
        dialog.set_extra_child(extra)

        def changed(entry: Gtk.Entry, *_args: object) -> None:
            try:
                dialog.set_response_enabled(
                    "confirm", entry.get_text().strip() == plan.name
                )
            except (AttributeError, TypeError):
                pass

        confirmation_entry.connect("changed", changed)

        def response(_dialog: Adw.AlertDialog, response_id: str) -> None:
            if response_id == "confirm" and confirmation_entry.get_text().strip() == plan.name:
                self._execute_remove(plan.name)

        dialog.connect("response", response)
        dialog.present(self.window)

    def _execute_remove(self, name: str) -> None:
        if name != self.selected_name or self.action_in_flight:
            return
        controller = self.systemctl
        selection_generation = self.selection_generation
        self.action_in_flight = True
        for button in self.action_buttons.values():
            button.set_sensitive(False)
        self.sidebar_status.set_text(f"Suppression en cours · {name}")

        def finished(value: object, error: Optional[BaseException]) -> bool:
            if (
                selection_generation != self.selection_generation
                or name != self.selected_name
                or controller is not self.systemctl
            ):
                self.action_in_flight = False
                return False
            self.action_in_flight = False
            if error is not None:
                self._show_error(str(error))
                self._set_action_sensitivity(
                    self.services_by_name.get(name, Service(name=name)),
                    self.current_details or {},
                    loading=False,
                )
                return False

            result = value if isinstance(value, RemovalResult) else RemovalResult([], [])
            count = len(result.removed)
            if count:
                message = f"{name} supprimé · {count} entrée(s) retirée(s)."
            else:
                message = f"{name} nettoyé : aucune entrée locale à retirer."
            self._show_toast(message)
            for warning in result.warnings:
                self._show_error(warning)
            self.current_details = None
            self._update_state_summary(
                self.services_by_name.get(name, Service(name=name)),
                {},
                loading=True,
            )
            self.refresh_services()
            return False

        self._run_background(lambda: controller.remove_complete(name), finished)

    @staticmethod
    def _action_label(action: str) -> str:
        return {
            "start": "démarrage",
            "stop": "arrêt",
            "restart": "redémarrage",
            "reload": "rechargement",
            "enable_now": "activation + démarrage",
            "disable_now": "désactivation + arrêt",
            "mask": "masquage",
            "unmask": "désmasquage",
            "remove": "suppression complète",
        }.get(action, action)

    def _run_background(
        self,
        worker: Callable[[], object],
        callback: Callable[[object, Optional[BaseException]], bool],
    ) -> None:
        def run() -> None:
            try:
                value = worker()
                error: Optional[BaseException] = None
            except BaseException as exc:  # forwarded to the GTK thread below
                value = None
                error = exc
            GLib.idle_add(callback, value, error)

        threading.Thread(target=run, daemon=True).start()

    def _show_toast(self, message: str) -> None:
        self.toast_overlay.add_toast(Adw.Toast.new(message))

    def _show_error(self, message: str) -> None:
        self.toast_overlay.add_toast(Adw.Toast.new(message))

    def show_about(self) -> None:
        dialog = Adw.AboutDialog()
        dialog.set_application_name(APP_NAME)
        app_icon = available_icon_name(
            APP_ID, "applications-system-symbolic", "system-run-symbolic"
        )
        if app_icon:
            dialog.set_application_icon(app_icon)
        dialog.set_version(APP_VERSION)
        dialog.set_comments(
            "systemd est une interface native GTK4/libadwaita pour gérer les services systemd. Les informations et les actions sont fournies par systemctl."
        )
        dialog.set_website("https://systemd.io/")
        dialog.present(self.window)


def main() -> int:
    app = SystemdManager()
    return app.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
