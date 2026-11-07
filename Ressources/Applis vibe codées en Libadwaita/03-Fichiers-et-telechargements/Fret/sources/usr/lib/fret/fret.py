#!/usr/bin/env python3
"""Fret — un mini gestionnaire de fichiers libadwaita à deux emplacements.

Les emplacements sont des Gio.File : les chemins locaux et les URI prises en
charge par GVfs (ftp://, sftp://, smb://, ...) utilisent donc le même code.
"""

import ctypes
import json
import errno
import hashlib
import locale
import os
import sys
import threading
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

try:
    locale.setlocale(locale.LC_ALL, "")
except locale.Error:
    pass

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GLib, Graphene, Gtk, Pango


APP_ID = "io.github.fret.Fret"
APP_NAME = "Fret"
CHUNK_SIZE = 1024 * 1024
NATIVE_COPY_CHUNK_SIZE = 16 * 1024 * 1024
VIDEO_EXTENSION_ORDER = (
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".flv",
    ".wmv",
    ".mpeg",
    ".mpg",
    ".webm",
)
VIDEO_EXTENSIONS = frozenset(VIDEO_EXTENSION_ORDER)
VIDEO_SOURCE_DIR_NAME = "Téléchargements"
VIDEO_DESTINATION_DIR_NAME = "Vidéos"


def default_import_settings():
    return {
        "source": str(Path.home() / VIDEO_SOURCE_DIR_NAME),
        "destination": str(
            Path.home() / VIDEO_DESTINATION_DIR_NAME / ".DEV"
        ),
        "mode": "move",
        "extensions": ", ".join(VIDEO_EXTENSION_ORDER),
        "recursive": True,
        "cleanup_empty_dirs": True,
        "preserve_vdh": True,
    }


def format_bytes(value):
    """Formate une taille avec les unités GLib et le format local."""

    if value is None:
        return "—"
    return GLib.format_size(int(max(0, value)))


def format_speed(value):
    if not value or value < 1:
        return "—"
    return f"{format_bytes(value)}/s"


def format_duration(seconds):
    """Formate une durée d’estimation de façon compacte et lisible."""

    if seconds is None or seconds < 0:
        return "—"
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds} s"
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes} min {seconds:02d} s"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours} h {minutes:02d} min"
    days, hours = divmod(hours, 24)
    return f"{days} j {hours:02d} h"


def file_from_location(value):
    """Transforme un chemin ou une URI en Gio.File."""

    text = (value or "").strip()
    if not text:
        text = os.path.expanduser("~")

    if "://" in text:
        return Gio.File.new_for_uri(text)

    return Gio.File.new_for_path(os.path.abspath(os.path.expanduser(text)))


def location_to_text(file_object):
    path = file_object.get_path()
    return path if path is not None else file_object.get_uri()


def same_location(first, second):
    if first is None or second is None:
        return False
    return first.get_uri().rstrip("/") == second.get_uri().rstrip("/")


def is_same_or_descendant(location, possible_parent):
    """Indique si location est possible_parent ou l'un de ses descendants."""

    if location is None or possible_parent is None:
        return False

    location_uri = location.get_uri().rstrip("/")
    parent_uri = possible_parent.get_uri().rstrip("/")
    return location_uri == parent_uri or location_uri.startswith(parent_uri + "/")


def error_text(error):
    text = str(error).strip()
    return text or error.__class__.__name__


def full_color_icon(icon):
    """Place la variante colorée avant la variante symbolique d'une icône."""

    if icon is None or not isinstance(icon, Gio.ThemedIcon):
        return icon

    names = []
    for name in icon.get_names():
        color_name = (
            name[: -len("-symbolic")]
            if name.endswith("-symbolic")
            else name
        )
        for candidate in (color_name, name):
            if candidate and candidate not in names:
                names.append(candidate)

    return Gio.ThemedIcon.new_from_names(names) if names else icon


def is_remote_location(file_object):
    """Indique si Gio devra passer par un backend GVfs distant."""

    try:
        return not file_object.is_native()
    except AttributeError:
        return file_object.get_path() is None


def safe_location_uri(file_object):
    """Retourne une URI utilisable sans mémoriser un mot de passe."""

    uri = file_object.get_uri()
    try:
        parts = urlsplit(uri)
        if parts.password is None:
            return uri

        hostname = parts.hostname or ""
        if ":" in hostname and not hostname.startswith("["):
            hostname = f"[{hostname}]"
        if parts.port is not None:
            hostname = f"{hostname}:{parts.port}"
        username = quote(parts.username or "", safe="")
        netloc = f"{username}@{hostname}" if username else hostname
        return urlunsplit(
            (parts.scheme, netloc, parts.path, parts.query, parts.fragment)
        )
    except (AttributeError, TypeError, ValueError):
        return uri


# ---------------------------------------------------------------------------
# Réglages de transfert adaptés au support de destination
# ---------------------------------------------------------------------------
#
# Linux garde volontiers des gigaoctets de données « sales » en RAM avant de
# les écrire : la copie paraît instantanée puis le démontage n'en finit pas.
# Pour les supports amovibles, Fret force donc l'écriture réelle (syncfs) tous
# les N Mo : la barre de progression avance au rythme du support, et
# « terminé » veut dire que les données sont vraiment sur la clé.

MIB = 1024 * 1024
FAT32_MAX_FILE_SIZE = 4 * 1024 * 1024 * 1024 - 1
FAT32_TYPES = {"vfat", "msdos", "fat"}

TRANSFER_PROFILES = {
    "local": {
        "label": "Disque interne",
        "icons": ("drive-harddisk-symbolic",),
        "chunk": 16 * MIB,
        "sync_bytes": 0,
        "sync_files": 0,
        "final_sync": False,
        "description": "Copie directe par le noyau, sans écriture forcée.",
    },
    "stick": {
        "label": "Clé USB",
        "icons": ("media-removable-symbolic", "drive-removable-media-symbolic"),
        "chunk": 4 * MIB,
        "sync_bytes": 32 * MIB,
        "sync_files": 128,
        "final_sync": True,
        "description": "Écriture forcée tous les 32 Mo : progression fidèle.",
    },
    "ssd": {
        "label": "SSD externe",
        "icons": (
            "drive-harddisk-usb-symbolic",
            "drive-harddisk-symbolic",
        ),
        "chunk": 16 * MIB,
        "sync_bytes": 256 * MIB,
        "sync_files": 1024,
        "final_sync": True,
        "description": "Écriture forcée tous les 256 Mo : plein débit.",
    },
    "network": {
        "label": "Réseau",
        "icons": ("network-server-symbolic", "network-workgroup-symbolic"),
        "chunk": 1 * MIB,
        "sync_bytes": 0,
        "sync_files": 0,
        "final_sync": False,
        "description": "Transfert GVfs (FTP, SFTP, SMB…).",
    },
}
TRANSFER_PROFILE_ORDER = ("stick", "ssd", "local", "network")


def themed_icon(names):
    return Gio.ThemedIcon.new_from_names(list(names))


def _read_sys(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read().strip()
    except OSError:
        return ""


def _unescape_mountinfo(value):
    """Décode les échappements octaux de /proc/self/mountinfo (\\040…)."""

    result = []
    index = 0
    while index < len(value):
        chunk = value[index + 1 : index + 4]
        if value[index] == "\\" and len(chunk) == 3 and all(c in "01234567" for c in chunk):
            result.append(chr(int(value[index + 1 : index + 4], 8)))
            index += 4
        else:
            result.append(value[index])
            index += 1
    return "".join(result)


def find_mount_for_path(path):
    """Retourne (point de montage, type, source) du montage contenant path."""

    try:
        real = os.path.realpath(path)
        with open("/proc/self/mountinfo", "r", encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError:
        return None

    best = None
    for line in lines:
        left, separator, right = line.partition(" - ")
        if not separator:
            continue
        fields = left.split()
        right_fields = right.split()
        if len(fields) < 5 or len(right_fields) < 2:
            continue
        mount_point = _unescape_mountinfo(fields[4])
        if real != mount_point and not real.startswith(mount_point.rstrip("/") + "/"):
            continue
        if best is None or len(mount_point) >= len(best[0]):
            best = (mount_point, right_fields[0], _unescape_mountinfo(right_fields[1]))
    return best


def _usb_disk_key(disk_name):
    """Identifiant stable d'un disque USB (modèle + numéro de série)."""

    try:
        for entry in sorted(os.listdir("/dev/disk/by-id")):
            if not entry.startswith("usb-") or "-part" in entry:
                continue
            target = os.path.realpath(os.path.join("/dev/disk/by-id", entry))
            if os.path.basename(target) == disk_name:
                return entry
    except OSError:
        pass
    vendor = _read_sys(f"/sys/block/{disk_name}/device/vendor")
    model = _read_sys(f"/sys/block/{disk_name}/device/model")
    return f"{vendor}_{model}".strip("_") or disk_name


def _usb_storage_driver(sys_path):
    """Pilote USB du disque : « uas » (SSD, clés haut de gamme) ou « usb-storage »."""

    current = sys_path
    for _ in range(12):
        current = os.path.dirname(current)
        if not current or current == "/":
            break
        driver = os.path.join(current, "driver")
        if os.path.islink(driver):
            name = os.path.basename(os.path.realpath(driver))
            if name in ("uas", "usb-storage"):
                return name
    return ""


def detect_device(file_object):
    """Devine le type de support d'un emplacement, sans droits root.

    Retourne un dict : kind (local/stick/ssd/network), key (identifiant
    stable pour mémoriser un réglage), name (nom affiché) et fs_type."""

    local = {"kind": "local", "key": "local", "name": "Disque interne", "fs_type": ""}
    if file_object is None:
        return local

    if is_remote_location(file_object):
        uri = file_object.get_uri()
        try:
            parts = urlsplit(uri)
            scheme = parts.scheme or "gvfs"
            host = parts.hostname or ""
        except ValueError:
            scheme, host = "gvfs", ""
        return {
            "kind": "network",
            "key": f"net:{scheme}:{host}",
            "name": host or scheme.upper(),
            "fs_type": scheme,
        }

    path = file_object.get_path()
    if not path:
        return local
    mount = find_mount_for_path(path)
    if mount is None:
        return local
    mount_point, fs_type, source = mount
    local = dict(local, fs_type=fs_type)

    if fs_type.startswith("fuse.gvfs") or fs_type in (
        "nfs", "nfs4", "cifs", "smb3", "fuse.sshfs", "fuse.rclone", "9p",
    ):
        return {
            "kind": "network",
            "key": f"net:{fs_type}:{source}",
            "name": os.path.basename(mount_point) or source,
            "fs_type": fs_type,
        }

    if not source.startswith("/dev/"):
        return local
    try:
        rdev = os.stat(source).st_rdev
    except OSError:
        return local
    sys_path = os.path.realpath(f"/sys/dev/block/{os.major(rdev)}:{os.minor(rdev)}")
    if os.path.exists(os.path.join(sys_path, "partition")):
        sys_path = os.path.dirname(sys_path)
    if "/usb" not in sys_path:
        return local

    disk_name = os.path.basename(sys_path)
    removable = _read_sys(os.path.join(sys_path, "removable")) == "1"
    driver = _usb_storage_driver(sys_path)
    rotational = _read_sys(os.path.join(sys_path, "queue", "rotational")) == "1"
    if removable:
        kind = "stick"
    elif driver == "uas" or rotational:
        kind = "ssd"
    else:
        kind = "stick"
    return {
        "kind": kind,
        "key": f"usb:{_usb_disk_key(disk_name)}",
        "name": os.path.basename(mount_point) or disk_name,
        "fs_type": fs_type,
    }


try:
    _LIBC = ctypes.CDLL(None, use_errno=True)
    _LIBC_SYNCFS = _LIBC.syncfs
    _LIBC_SYNCFS.argtypes = [ctypes.c_int]
    _LIBC_SYNCFS.restype = ctypes.c_int
except (OSError, AttributeError):
    _LIBC_SYNCFS = None


def syncfs_path(path):
    """Écrit réellement sur le support toutes les données en attente de path."""

    if not path:
        return
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    except OSError:
        return
    try:
        if _LIBC_SYNCFS is not None:
            _LIBC_SYNCFS(descriptor)
        else:
            os.fsync(descriptor)
            os.sync()
    finally:
        os.close(descriptor)


class LocationStore:
    """Mémorise les deux derniers emplacements et les favoris."""

    def __init__(self):
        self.config_dir = os.path.join(GLib.get_user_config_dir(), "fret")
        self.path = os.path.join(self.config_dir, "locations.json")
        self.last_locations = [None, None]
        self.favorites = []
        self.show_hidden = False
        self.import_settings = default_import_settings()
        # Réglage de transfert choisi à la main, par support (clé, SSD…).
        self.transfer_profiles = {}
        self.load()

    @staticmethod
    def _location_list(value):
        if not isinstance(value, list):
            return []
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError, TypeError):
            return
        if not isinstance(data, dict):
            return

        last_locations = data.get("last_locations")
        if isinstance(last_locations, list):
            cleaned = [
                item.strip() if isinstance(item, str) and item.strip() else None
                for item in last_locations[:2]
            ]
            self.last_locations = cleaned + [None] * (2 - len(cleaned))
        self.favorites = self._location_list(data.get("favorites"))
        self.show_hidden = bool(data.get("show_hidden", False))
        saved_import = data.get("import_settings")
        if isinstance(saved_import, dict):
            for key in ("source", "destination", "extensions"):
                value = saved_import.get(key)
                if isinstance(value, str) and value.strip():
                    self.import_settings[key] = value.strip()
            if saved_import.get("mode") in ("move", "copy"):
                self.import_settings["mode"] = saved_import["mode"]
            for key in ("recursive", "cleanup_empty_dirs", "preserve_vdh"):
                if isinstance(saved_import.get(key), bool):
                    self.import_settings[key] = saved_import[key]
        profiles = data.get("transfer_profiles")
        if isinstance(profiles, dict):
            self.transfer_profiles = {
                str(key): value
                for key, value in profiles.items()
                if value in TRANSFER_PROFILES
            }
        if "recent_locations" in data:
            # Nettoie l'ancien réglage devenu inutile dès la première lecture.
            self.save()

    def save(self):
        data = {
            "last_locations": self.last_locations,
            "favorites": self.favorites,
            "show_hidden": self.show_hidden,
            "import_settings": self.import_settings,
            "transfer_profiles": self.transfer_profiles,
        }
        temporary_path = f"{self.path}.tmp"
        try:
            os.makedirs(self.config_dir, mode=0o700, exist_ok=True)
            with open(temporary_path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(temporary_path, self.path)
        except OSError:
            # Le gestionnaire reste utilisable même si la configuration n'est pas
            # accessible (support en lecture seule, profil itinérant, etc.).
            pass

    def record(self, file_object, slot):
        uri = safe_location_uri(file_object)
        if slot in (0, 1):
            self.last_locations[slot] = uri
        self.save()

    def is_favorite(self, file_object):
        return safe_location_uri(file_object) in self.favorites

    def toggle_favorite(self, file_object):
        uri = safe_location_uri(file_object)
        if uri in self.favorites:
            self.favorites.remove(uri)
            favorite = False
        else:
            self.favorites.insert(0, uri)
            favorite = True
        self.save()
        return favorite


@dataclass
class FileItem:
    file: Gio.File
    name: str
    display_name: str
    is_dir: bool
    size: int
    modified: str
    kind: str
    icon: Gio.Icon


@dataclass
class ManifestEntry:
    kind: str
    source: Gio.File
    target: Gio.File
    size: int = 0


class TransferStopped(Exception):
    """Exception interne utilisée pour arrêter proprement un transfert."""


class TransferError(Exception):
    """Erreur lisible produite par le moteur de transfert."""


class TransferJob:
    """Copie/déplacement asynchrone avec fichiers partiels reprenables."""

    def __init__(
        self,
        sources,
        destination,
        mode,
        on_finish,
        cleanup_dirs=None,
        cleanup_root=None,
        preserve_dir=None,
        completion_message="Transfert terminé.",
        clear_clipboard=True,
        on_item_changed=None,
        on_conflict=None,
        device=None,
        profile_key="local",
    ):
        self.sources = sources
        self.destination = destination
        self.mode = mode  # "copy" ou "move"
        self.renamed_names = []
        self.failed_files = []
        self._failed_dir_uris = []
        self._consecutive_failures = 0
        self._fat_like = False
        self.on_finish = on_finish
        self.cleanup_dirs = list(cleanup_dirs or [])
        self.cleanup_root = cleanup_root
        self.preserve_dir = preserve_dir
        self.completion_message = completion_message
        self.clear_clipboard = clear_clipboard
        self.on_item_changed = on_item_changed
        self.on_conflict = on_conflict

        self.manifest = None
        self.current_index = 0
        self.total_files = 0
        self.total_bytes = 0
        self.completed_files = 0
        self.completed_bytes = 0
        self.current_file_name = ""
        self.current_file_size = 0
        self.current_file_done = 0
        self.current_file_active = False
        self.prepare_name = ""
        self.error = ""
        self.state = "preparing"
        self.started_at = None
        self.paused_started_at = None
        self.paused_duration = 0.0
        self.missing_files = []
        self._missing_source_uris = set()
        self.skipped_files = 0
        self.move_errors = []
        self._externally_deleted_sources = set()
        self._native_moved_sources = set()
        self._conflict_policies = {}
        self._pending_conflict = None

        # Support de destination et réglage de transfert (modifiable en cours
        # de route depuis la pastille du panneau de transfert).
        self.device = device or detect_device(destination)
        self.profile_key = profile_key if profile_key in TRANSFER_PROFILES else "local"
        self._sync_path = destination.get_path() if destination.is_native() else None
        self._unsynced_bytes = 0
        self._files_since_sync = 0
        self.prechecked = False

        self.pause_event = threading.Event()
        self.pause_event.set()
        self.stop_event = threading.Event()
        self.cancellable = None
        self.lock = threading.RLock()

    def set_state(self, state):
        with self.lock:
            self.state = state

    def request_pause(self):
        with self.lock:
            if self.state in ("running", "preparing"):
                self.pause_event.clear()
                if self.state == "running":
                    self.paused_started_at = time.monotonic()
                    self.state = "paused"

    def request_resume(self):
        with self.lock:
            if self.state == "paused":
                if self.paused_started_at is not None:
                    self.paused_duration += max(0.0, time.monotonic() - self.paused_started_at)
                    self.paused_started_at = None
                self.pause_event.set()
                self.state = "running"

    def request_stop(self):
        self.stop_event.set()
        self.pause_event.set()
        with self.lock:
            self.state = "stopping"
            cancellable = self.cancellable
            pending_conflict = self._pending_conflict
        if cancellable is not None:
            cancellable.cancel()
        if pending_conflict is not None:
            pending_conflict["response"] = "cancel"
            pending_conflict["event"].set()

    def mark_sources_deleted(self, source_uris):
        """Signale les sources supprimées par l’utilisateur pendant ce transfert."""

        with self.lock:
            self._externally_deleted_sources.update(source_uris)

    @staticmethod
    def _is_missing_error(error):
        """Reconnaît une source qui a disparu entre deux étapes du transfert."""

        if isinstance(error, GLib.Error):
            not_found = getattr(Gio.IOErrorEnum, "NOT_FOUND", None)
            if not_found is not None:
                try:
                    if error.matches(Gio.io_error_quark(), not_found):
                        return True
                except GLib.Error:
                    pass

        text = error_text(error).casefold()
        return any(
            marker in text
            for marker in (
                "not found",
                "no such file",
                "introuvable",
                "n’existe",
                "n'existe",
                "does not exist",
            )
        )

    def _source_is_missing(self, entry, error=None):
        if error is not None and self._is_missing_error(error):
            return True
        try:
            return not entry.source.query_exists(None)
        except GLib.Error:
            return False

    def _under_failed_directory(self, entry):
        uri = entry.target.get_uri()
        return any(
            uri == failed or uri.startswith(failed + "/")
            for failed in self._failed_dir_uris
        )

    def _record_skipped_child(self, entry):
        with self.lock:
            self._missing_source_uris.add(entry.source.get_uri())
            self.skipped_files += 1
            self.skipped_children = getattr(self, "skipped_children", 0) + (
                1 if entry.kind == "file" else 0
            )

    def _record_failure(self, entry, error, is_directory=False):
        """Mémorise l'échec d'un élément et poursuit le transfert.

        Arrête tout seul le transfert si le disque est plein ou si les échecs
        s'enchaînent (clé retirée, système de fichiers en lecture seule…)."""

        message = error_text(error)
        if isinstance(error, GLib.Error) and error.matches(
            Gio.io_error_quark(), Gio.IOErrorEnum.NO_SPACE
        ):
            raise TransferError(
                f"Plus d'espace disponible sur la destination ({entry.source.get_basename()})"
            ) from error

        name = entry.source.get_parse_name() or entry.source.get_basename() or "?"
        with self.lock:
            self.failed_files.append((name, message))
            self._missing_source_uris.add(entry.source.get_uri())
            self.skipped_files += 1
            if is_directory:
                self._failed_dir_uris.append(entry.target.get_uri())
        self._consecutive_failures += 1
        if self._consecutive_failures >= 8:
            raise TransferError(
                f"Transfert interrompu après {self._consecutive_failures} échecs consécutifs : {message}"
            ) from error

    def _record_missing(self, entry, skipped=True):
        uri = entry.source.get_uri()
        with self.lock:
            if uri in self._missing_source_uris:
                return
            self._missing_source_uris.add(uri)
            name = entry.source.get_parse_name() or entry.source.get_basename() or uri
            self.missing_files.append(name)
            if skipped:
                self.skipped_files += 1

    def _notify_item_changed(self, entry, status):
        if self.on_item_changed is not None:
            GLib.idle_add(self.on_item_changed, self, entry, status)

    FAT_LIKE_TYPES = {
        "vfat", "msdos", "fat", "exfat", "ntfs", "ntfs3", "fuseblk",
        "fuse.exfat", "fuse.ntfs-3g", "ntfs-3g", "udf",
    }
    WINDOWS_RESERVED = {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }

    def _destination_is_fat_like(self):
        try:
            info = self.destination.query_filesystem_info("filesystem::type", None)
            fs_type = (info.get_attribute_string("filesystem::type") or "").lower()
        except GLib.Error:
            return False
        return fs_type in self.FAT_LIKE_TYPES

    def _destination_name(self, name, used):
        """Adapte un nom aux systèmes de fichiers FAT/exFAT/NTFS (comme Nautilus).

        Remplace les caractères interdits par « _ », retire les espaces et points
        finaux, évite les noms réservés et garde la longueur sous 255 caractères.
        Les doublons créés par ces remplacements reçoivent un numéro."""

        if not getattr(self, "_fat_like", False):
            return name

        clean = "".join(
            "_" if (ch in '<>:"/\\|?*' or ord(ch) < 32) else ch for ch in name
        )
        clean = clean.rstrip(" .") or "_"
        stem, dot, ext = clean.partition(".")
        if stem.upper() in self.WINDOWS_RESERVED:
            clean = "_" + clean
        if len(clean) > 255:
            base, extension = os.path.splitext(clean)
            clean = base[: 255 - len(extension)] + extension

        candidate = clean
        index = 1
        while candidate.casefold() in used:
            base, extension = os.path.splitext(clean)
            candidate = f"{base} ({index}){extension}"
            index += 1
        used.add(candidate.casefold())
        if candidate != name:
            self.renamed_names.append(f"{name} → {candidate}")
        return candidate

    @staticmethod
    def _partial_name(basename):
        """Nom du fichier partiel : court et sans caractère exotique.

        Un nom construit à partir du nom d'origine dépasse la limite de 255
        caractères ou contient des caractères refusés (FAT, exFAT, NTFS)."""

        digest = hashlib.sha1(basename.encode("utf-8", "surrogateescape")).hexdigest()[:16]
        return f".fret-{digest}.part"

    @staticmethod
    def _unique_target(target):
        parent = target.get_parent()
        if parent is None:
            raise TransferError("Destination invalide")

        name = target.get_basename() or "fichier"
        stem, suffix = os.path.splitext(name)
        index = 1
        while True:
            candidate = parent.get_child(f"{stem} ({index}){suffix}")
            try:
                candidate.query_info(
                    "standard::type", Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, None
                )
            except GLib.Error as error:
                if TransferJob._is_missing_error(error):
                    return candidate
                raise TransferError(
                    f"Impossible de vérifier si « {candidate.get_basename()} » "
                    "est disponible dans la destination."
                ) from error
            index += 1

    def _resolve_conflict(self, entry):
        """Résout un conflit uniquement après un choix explicite."""

        try:
            info = entry.target.query_info(
                "standard::type", Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, None
            )
        except GLib.Error as error:
            if self._is_missing_error(error):
                return None
            raise TransferError(
                f"Impossible de vérifier « {entry.target.get_basename()} » "
                "dans la destination."
            ) from error

        source_is_dir = entry.kind == "dir"
        target_type = info.get_file_type()
        target_is_dir = target_type == Gio.FileType.DIRECTORY
        if source_is_dir and target_is_dir:
            conflict_kind = "directory"
            allowed_responses = ("merge", "rename")
        elif not source_is_dir and target_type == Gio.FileType.REGULAR:
            conflict_kind = "file"
            allowed_responses = ("replace", "rename")
        else:
            conflict_kind = "type-mismatch"
            allowed_responses = ("rename",)

        policy = self._conflict_policies.get("all")
        if policy is None:
            policy = self._conflict_policies.get(conflict_kind)
        if policy not in allowed_responses:
            policy = None
        if policy is None:
            if self.on_conflict is None:
                raise TransferError("Un élément du même nom existe déjà")

            request = {
                "event": threading.Event(),
                "response": None,
                "apply_all": False,
                "conflict_kind": conflict_kind,
                "allowed_responses": allowed_responses,
                "source_is_dir": source_is_dir,
                "target_is_dir": target_is_dir,
                "target_is_file": target_type == Gio.FileType.REGULAR,
            }
            with self.lock:
                self._pending_conflict = request
                self.state = "waiting"
            GLib.idle_add(self.on_conflict, self, entry, request)
            try:
                while not request["event"].wait(0.2):
                    self._check_stop()
                self._check_stop()
            finally:
                with self.lock:
                    if self._pending_conflict is request:
                        self._pending_conflict = None
                    if self.state == "waiting":
                        self.state = (
                            "paused" if not self.pause_event.is_set() else "running"
                        )

            response = request.get("response")
            if response not in allowed_responses:
                raise TransferStopped()
            if request.get("apply_all"):
                if response == "rename":
                    self._conflict_policies["all"] = "rename"
                else:
                    self._conflict_policies[conflict_kind] = response
            policy = response

        if policy == "rename":
            old_target = entry.target
            entry.target = self._unique_target(old_target)
            if entry.kind == "dir" and self.manifest is not None:
                for descendant in self.manifest[self.current_index + 1 :]:
                    relative_path = old_target.get_relative_path(descendant.target)
                    if relative_path is not None:
                        descendant.target = entry.target.resolve_relative_path(
                            relative_path
                        )
        return policy

    def _delete_source_after_copy(self, entry):
        """Réalise le déplacement distant par fichier, dès sa copie terminée."""

        if self.mode != "move" or entry.source.get_uri() in self._native_moved_sources:
            return

        self._check_stop()
        try:
            entry.source.delete(None)
        except Exception as error:  # noqa: BLE001 — reporté comme avertissement
            if self._source_is_missing(entry, error):
                self._record_missing(entry, skipped=False)
                return
            with self.lock:
                self.move_errors.append(
                    f"{entry.source.get_parse_name()} : {error_text(error)}"
                )

    @staticmethod
    def _discard_partial(entry):
        target = entry.target
        parent = target.get_parent()
        if parent is None:
            return
        basename = target.get_basename() or "fichier"
        partial = parent.get_child(TransferJob._partial_name(basename))
        try:
            partial.delete(None)
        except GLib.Error:
            pass

    def _remove_empty_manifest_directories(self):
        """Retire uniquement les dossiers source devenus vides après un déplacement."""

        if self.mode != "move" or not self.manifest:
            return

        directories = [entry for entry in self.manifest if entry.kind == "dir"]
        directories.sort(
            key=lambda entry: len(entry.source.get_uri()), reverse=True
        )
        preserve_file = (
            Gio.File.new_for_path(self.preserve_dir) if self.preserve_dir else None
        )
        for entry in directories:
            directory = entry.source
            self._check_stop()
            if preserve_file and same_location(directory, preserve_file):
                continue
            try:
                enumerator = directory.enumerate_children(
                    "standard::name",
                    Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                    None,
                )
                try:
                    empty = enumerator.next_file(None) is None
                finally:
                    enumerator.close(None)
                if empty:
                    directory.delete(None)
                    self._notify_item_changed(entry, "removed")
            except GLib.Error as error:
                if not self._is_missing_error(error):
                    continue

    @property
    def profile(self):
        return TRANSFER_PROFILES.get(self.profile_key, TRANSFER_PROFILES["local"])

    def set_profile(self, profile_key):
        if profile_key in TRANSFER_PROFILES:
            with self.lock:
                self.profile_key = profile_key

    def _flush_destination(self):
        syncfs_path(self._sync_path)
        self._unsynced_bytes = 0
        self._files_since_sync = 0

    def _after_write(self, count):
        """Force l'écriture réelle sur le support tous les N Mo."""

        threshold = self.profile["sync_bytes"]
        if not threshold or not self._sync_path:
            return
        self._unsynced_bytes += count
        if self._unsynced_bytes >= threshold:
            self._flush_destination()

    def _after_file(self):
        """Pour les nombreux petits fichiers : écriture forcée tous les N fichiers."""

        limit = self.profile["sync_files"]
        if not limit or not self._sync_path:
            return
        self._files_since_sync += 1
        if self._files_since_sync >= limit:
            self._flush_destination()

    def _precheck(self):
        """Vérifications avant copie : limite FAT32 de 4 Go et espace libre."""

        fs_type = ""
        free = None
        try:
            info = self.destination.query_filesystem_info(
                "filesystem::type,filesystem::free", None
            )
            fs_type = (info.get_attribute_string("filesystem::type") or "").lower()
            if info.has_attribute("filesystem::free"):
                free = int(info.get_attribute_uint64("filesystem::free"))
        except GLib.Error:
            pass
        if not fs_type:
            fs_type = (self.device.get("fs_type") or "").lower()

        if fs_type in FAT32_TYPES:
            for entry in self.manifest:
                if entry.kind == "file" and entry.size > FAT32_MAX_FILE_SIZE:
                    entry.kind = "toobig"

        needed = sum(entry.size for entry in self.manifest if entry.kind == "file")
        if self.mode == "move" and self.sources:
            # Un déplacement sur le même système de fichiers n'occupe rien de plus.
            source_path = self._native_path(self.sources[0])
            destination_path = self._native_path(self.destination)
            if source_path and destination_path:
                try:
                    if os.stat(source_path).st_dev == os.stat(destination_path).st_dev:
                        needed = 0
                except OSError:
                    pass
        if free is not None and free > 0 and needed > free:
            raise TransferError(
                "Espace insuffisant sur la destination : "
                f"{format_bytes(needed)} nécessaires, {format_bytes(free)} disponibles"
            )

    def _check_stop(self):
        if self.stop_event.is_set():
            raise TransferStopped()

    def _wait_if_paused(self):
        while not self.pause_event.wait(0.2):
            self._check_stop()
        self._check_stop()

    def _prepare_manifest(self):
        manifest = []
        self.renamed_names = []
        self._fat_like = self._destination_is_fat_like()

        def walk(source, target):
            self._check_stop()
            self.prepare_name = source.get_parse_name()
            info = source.query_info(
                "standard::name,standard::type,standard::size",
                Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                None,
            )
            file_type = info.get_file_type()

            if file_type == Gio.FileType.DIRECTORY:
                manifest.append(ManifestEntry("dir", source, target, 0))
                children = []
                enumerator = source.enumerate_children(
                    "standard::name,standard::type,standard::size",
                    Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                    None,
                )
                try:
                    while True:
                        self._check_stop()
                        child_info = enumerator.next_file(None)
                        if child_info is None:
                            break
                        children.append(child_info)
                finally:
                    enumerator.close(None)

                children.sort(key=lambda item: locale.strxfrm(item.get_name().casefold()))
                used_names = set()
                for child_info in children:
                    child_name = child_info.get_name()
                    child_source = source.get_child(child_name)
                    child_target = target.get_child(
                        self._destination_name(child_name, used_names)
                    )
                    try:
                        walk(child_source, child_target)
                    except Exception as error:  # noqa: BLE001 — la source peut disparaître
                        if self._is_missing_error(error):
                            manifest.append(
                                ManifestEntry("missing", child_source, child_target, 0)
                            )
                        else:
                            raise
                return

            size = int(info.get_size())
            manifest.append(ManifestEntry("file", source, target, size))

        top_used = set()
        for source in self.sources:
            self._check_stop()
            basename = source.get_basename()
            if not basename:
                raise TransferError("La source sélectionnée n’a pas de nom valide")
            target = self.destination.get_child(
                self._destination_name(basename, top_used)
            )
            try:
                walk(source, target)
            except Exception as error:  # noqa: BLE001 — la source peut disparaître
                if self._is_missing_error(error):
                    manifest.append(ManifestEntry("missing", source, target, 0))
                else:
                    raise

        if not manifest:
            raise TransferError("Aucun élément à transférer")
        return manifest

    def _recalculate_completed_progress(self):
        with self.lock:
            completed = self.manifest[: self.current_index] if self.manifest else []
            self.completed_files = sum(
                1
                for entry in completed
                if entry.kind == "file"
                and entry.source.get_uri() not in self._missing_source_uris
            )
            self.completed_bytes = sum(
                entry.size
                for entry in completed
                if entry.kind == "file"
                and entry.source.get_uri() not in self._missing_source_uris
            )
            self.skipped_files = sum(
                1
                for entry in completed
                if entry.source.get_uri() in self._missing_source_uris
            )
            self.current_file_name = ""
            self.current_file_size = 0
            self.current_file_done = 0
            self.current_file_active = False

    def _ensure_directory(self, target):
        self._check_stop()
        try:
            target.make_directory_with_parents(None)
        except GLib.Error:
            try:
                info = target.query_info(
                    "standard::type", Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, None
                )
                if info.get_file_type() == Gio.FileType.DIRECTORY:
                    raise TransferError(
                        "Le dossier est apparu dans la destination après la vérification; "
                        "son contenu n’a pas été fusionné sans confirmation."
                    )
            except GLib.Error:
                pass

            # Certains backends GVfs (notamment FTP) ne fournissent pas
            # make_directory_with_parents mais savent créer un dossier simple.
            target.make_directory(None)

    @staticmethod
    def _read_partial_size(partial):
        try:
            info = partial.query_info("standard::size", Gio.FileQueryInfoFlags.NONE, None)
            return int(info.get_size())
        except GLib.Error:
            return 0

    @staticmethod
    def _read_chunk(input_stream, count, cancellable):
        """Lit un bloc avec l'API GIO compatible avec PyGObject."""

        data = input_stream.read_bytes(count, cancellable)
        if data is None:
            return b""
        if isinstance(data, bytes):
            return data
        try:
            data = data.get_data()
        except AttributeError:
            data = bytes(data)
        if isinstance(data, tuple):
            data = data[0]
        return bytes(data)

    def _skip_input(self, input_stream, amount, cancellable):
        if amount <= 0:
            return

        try:
            if input_stream.can_seek():
                input_stream.seek(amount, GLib.SeekType.SET, cancellable)
                return
        except (AttributeError, GLib.Error):
            pass

        remaining = amount
        while remaining > 0:
            self._wait_if_paused()
            chunk = self._read_chunk(
                input_stream, min(CHUNK_SIZE, remaining), cancellable
            )
            if not chunk:
                raise TransferError("Impossible de reprendre le fichier partiel")
            remaining -= len(chunk)

    @staticmethod
    def _write_all(output_stream, data, cancellable):
        written = 0
        while written < len(data):
            count = output_stream.write(data[written:], cancellable)
            if not count:
                raise TransferError("Écriture interrompue")
            written += count

    @staticmethod
    def _native_path(file_object):
        try:
            return file_object.get_path()
        except (AttributeError, GLib.Error):
            return None

    @staticmethod
    def _same_filesystem(source_path, destination_path):
        """Vérifie si un renommage local peut rester atomique."""

        if not source_path or not destination_path:
            return False
        destination_parent = os.path.dirname(destination_path)
        try:
            return os.stat(source_path).st_dev == os.stat(destination_parent).st_dev
        except OSError:
            return False

    def _try_native_move(self, entry, size):
        """Déplace instantanément un fichier local sur le même système de fichiers."""

        source_path = self._native_path(entry.source)
        target_path = self._native_path(entry.target)
        if self.mode != "move" or not self._same_filesystem(source_path, target_path):
            return False

        try:
            os.replace(source_path, target_path)
        except OSError as error:
            if error.errno in (
                errno.EXDEV,
                errno.EINVAL,
                errno.ENOSYS,
                errno.EOPNOTSUPP,
                errno.ENOTSUP,
            ):
                return False
            raise

        partial_path = os.path.join(
            os.path.dirname(target_path),
            TransferJob._partial_name(os.path.basename(target_path)),
        )
        try:
            os.unlink(partial_path)
        except FileNotFoundError:
            pass
        except OSError:
            pass

        self._native_moved_sources.add(entry.source.get_uri())
        with self.lock:
            self.current_file_done = size
        return True

    @staticmethod
    def _write_fd_all(file_descriptor, data):
        view = memoryview(data)
        while view:
            written = os.write(file_descriptor, view)
            if not written:
                raise TransferError("Écriture interrompue")
            view = view[written:]

    def _try_native_copy(self, entry, partial, target, size, partial_size):
        """Copie un fichier local avec les primitives de copie du noyau."""

        # Toute copie entre deux chemins locaux (disque interne, clé, SSD)
        # passe par ici : copy_file_range (reflink sur Btrfs) puis read/write.
        # Les emplacements GVfs (FTP, SFTP…) restent sur le chemin GIO.
        if not (entry.source.is_native() and partial.is_native()):
            return False
        source_path = self._native_path(entry.source)
        partial_path = self._native_path(partial)
        target_path = self._native_path(target)
        if not source_path or not partial_path:
            return False

        source_fd = None
        partial_fd = None
        source_stat = None
        try:
            source_fd = os.open(source_path, os.O_RDONLY)
            source_stat = os.fstat(source_fd)
            partial_fd = os.open(partial_path, os.O_WRONLY | os.O_CREAT, 0o600)
            try:
                os.fchmod(partial_fd, source_stat.st_mode & 0o7777)
            except OSError:
                pass  # FAT/exFAT : pas de droits Unix.
            os.ftruncate(partial_fd, partial_size)
            os.lseek(source_fd, partial_size, os.SEEK_SET)
            os.lseek(partial_fd, partial_size, os.SEEK_SET)

            transferred = partial_size
            use_copy_range = hasattr(os, "copy_file_range")
            while transferred < size:
                self._wait_if_paused()
                remaining = size - transferred
                chunk_size = self.profile["chunk"] or NATIVE_COPY_CHUNK_SIZE
                count = min(chunk_size, remaining)
                copied = 0

                if use_copy_range:
                    try:
                        copied = os.copy_file_range(source_fd, partial_fd, count)
                    except OSError as error:
                        if error.errno in (
                            errno.EXDEV,
                            errno.EINVAL,
                            errno.ENOSYS,
                            errno.EOPNOTSUPP,
                            errno.ENOTSUP,
                        ):
                            use_copy_range = False
                        else:
                            raise

                if copied <= 0:
                    data = os.read(source_fd, count)
                    if not data:
                        break
                    self._write_fd_all(partial_fd, data)
                    copied = len(data)

                transferred += copied
                with self.lock:
                    self.current_file_done = transferred
                self._after_write(copied)

            if transferred < size:
                raise TransferError("Le fichier source a été interrompu avant sa fin")
            os.ftruncate(partial_fd, size)
        finally:
            if partial_fd is not None:
                os.close(partial_fd)
            if source_fd is not None:
                os.close(source_fd)

        self._finalize_partial(partial, target, target_path)
        if source_stat is not None and target_path:
            try:
                os.utime(
                    target_path,
                    ns=(source_stat.st_atime_ns, source_stat.st_mtime_ns),
                )
            except OSError:
                pass
        return True

    @staticmethod
    def _finalize_partial(partial, target, target_path=None):
        partial_path = TransferJob._native_path(partial)
        target_path = target_path or TransferJob._native_path(target)
        if partial_path and target_path:
            try:
                os.replace(partial_path, target_path)
                return
            except OSError:
                # EXDEV, EPERM, EINVAL… selon le système de fichiers (FAT,
                # exFAT, NTFS) : on laisse GIO terminer le renommage.
                pass
        partial.move(target, Gio.FileCopyFlags.OVERWRITE, None, None, None)

    def _copy_file(self, entry):
        source = entry.source
        source_info = source.query_info("standard::size", Gio.FileQueryInfoFlags.NONE, None)
        size = int(source_info.get_size())
        conflict_action = self._resolve_conflict(entry)
        target = entry.target
        parent = target.get_parent()
        if parent is None:
            raise TransferError("Destination invalide")

        basename = target.get_basename() or "fichier"
        partial = parent.get_child(TransferJob._partial_name(basename))

        partial_exists = partial.query_exists(None)
        partial_size = self._read_partial_size(partial) if partial_exists else 0
        if partial_size > size:
            try:
                partial.delete(None)
            except GLib.Error:
                pass
            partial_size = 0
            partial_exists = False

        with self.lock:
            self.current_file_size = size
            self.current_file_done = partial_size
            self.current_file_active = True

        if self._try_native_move(entry, size):
            return True

        if partial_exists and partial_size == size:
            self._check_stop()
            self._finalize_partial(partial, target)
            return True

        if self._try_native_copy(entry, partial, target, size, partial_size):
            return True

        cancellable = Gio.Cancellable()
        with self.lock:
            self.cancellable = cancellable

        input_stream = None
        output_stream = None
        try:
            input_stream = source.read(cancellable)
            self._skip_input(input_stream, partial_size, cancellable)
            if partial_size:
                output_stream = partial.append_to(Gio.FileCreateFlags.NONE, cancellable)
            else:
                try:
                    output_stream = partial.create(Gio.FileCreateFlags.NONE, cancellable)
                except GLib.Error as create_error:
                    if not create_error.matches(Gio.io_error_quark(), Gio.IOErrorEnum.EXISTS):
                        raise
                    output_stream = partial.replace(
                        None, False, Gio.FileCreateFlags.NONE, cancellable
                    )

            transferred = partial_size
            while transferred < size:
                self._wait_if_paused()
                data = self._read_chunk(input_stream, CHUNK_SIZE, cancellable)
                if not data:
                    break
                self._wait_if_paused()
                self._write_all(output_stream, data, cancellable)
                transferred += len(data)
                with self.lock:
                    self.current_file_done = transferred
                if self._sync_path and self.profile["sync_bytes"]:
                    if self._unsynced_bytes + len(data) >= self.profile["sync_bytes"]:
                        output_stream.flush(cancellable)
                    self._after_write(len(data))

            if transferred < size:
                raise TransferError("Le fichier source a été interrompu avant sa fin")

            self._check_stop()
            output_stream.close(None)
            output_stream = None
            self._finalize_partial(partial, target)
            return True
        finally:
            if output_stream is not None:
                try:
                    output_stream.close(None)
                except GLib.Error:
                    pass
            if input_stream is not None:
                try:
                    input_stream.close(None)
                except GLib.Error:
                    pass
            with self.lock:
                self.cancellable = None

    def _cleanup_empty_dirs(self):
        """Supprime les dossiers vides du dossier source, sans supprimer sa racine."""

        if not self.cleanup_root:
            return

        root = os.path.abspath(self.cleanup_root)
        preserve = (
            os.path.abspath(self.preserve_dir) if self.preserve_dir else None
        )
        for start in self.cleanup_dirs:
            current = os.path.abspath(start)
            while current != root and current.startswith(root + os.sep):
                if preserve and current == preserve:
                    break
                try:
                    os.rmdir(current)
                except OSError:
                    break
                current = os.path.dirname(current)

    def run(self):
        try:
            if self.manifest is None:
                self.set_state("preparing")
                self.manifest = self._prepare_manifest()
            if not self.prechecked:
                self._precheck()
                self.prechecked = True
                with self.lock:
                    self.total_files = sum(
                        1 for entry in self.manifest if entry.kind == "file"
                    )
                    self.total_bytes = sum(
                        entry.size for entry in self.manifest if entry.kind == "file"
                    )

            self._recalculate_completed_progress()
            if self.started_at is None:
                self.started_at = time.monotonic()
            self.set_state("paused" if not self.pause_event.is_set() else "running")

            while self.current_index < len(self.manifest):
                self._check_stop()
                entry = self.manifest[self.current_index]
                if self._under_failed_directory(entry):
                    self._record_skipped_child(entry)
                    self.current_index += 1
                    continue

                if entry.kind == "dir":
                    try:
                        conflict_action = self._resolve_conflict(entry)
                        if conflict_action != "merge":
                            self._ensure_directory(entry.target)
                    except TransferStopped:
                        raise
                    except Exception as error:  # noqa: BLE001 — listé en fin de transfert
                        self._record_failure(entry, error, is_directory=True)
                        self.current_index += 1
                        continue
                    self._notify_item_changed(entry, "arrived")
                    self.current_index += 1
                    continue

                if entry.kind == "toobig":
                    name = entry.source.get_parse_name() or entry.source.get_basename() or "?"
                    with self.lock:
                        self.failed_files.append(
                            (
                                name,
                                f"{format_bytes(entry.size)} : trop volumineux pour une "
                                "clé en FAT32 (4 Go maximum par fichier). "
                                "Formate-la en exFAT pour copier ce fichier.",
                            )
                        )
                        self._missing_source_uris.add(entry.source.get_uri())
                        self.skipped_files += 1
                    self.current_index += 1
                    continue

                if entry.kind == "missing":
                    self._record_missing(entry)
                    self._discard_partial(entry)
                    self._notify_item_changed(entry, "missing")
                    self.current_index += 1
                    continue

                source_uri = entry.source.get_uri()
                with self.lock:
                    source_deleted = source_uri in self._externally_deleted_sources
                if source_deleted:
                    self._record_missing(entry)
                    self._notify_item_changed(entry, "missing")
                    self.current_index += 1
                    continue

                with self.lock:
                    self.current_file_name = entry.source.get_parse_name()
                    self.current_file_size = entry.size
                    self.current_file_active = True

                try:
                    self._copy_file(entry)
                except Exception as error:  # noqa: BLE001 — source possiblement supprimée
                    if isinstance(error, TransferStopped):
                        raise
                    if not self._source_is_missing(entry, error):
                        self._record_failure(entry, error)
                        self._discard_partial(entry)
                        self._notify_item_changed(entry, "missing")
                        with self.lock:
                            self.current_file_name = ""
                            self.current_file_size = 0
                            self.current_file_done = 0
                            self.current_file_active = False
                        self.current_index += 1
                        continue
                    self._record_missing(entry)
                    self._discard_partial(entry)
                    self._notify_item_changed(entry, "missing")
                    with self.lock:
                        self.current_file_name = ""
                        self.current_file_size = 0
                        self.current_file_done = 0
                        self.current_file_active = False
                    self.current_index += 1
                    continue

                self._consecutive_failures = 0
                self._after_file()
                self._delete_source_after_copy(entry)
                self._notify_item_changed(
                    entry, "moved" if self.mode == "move" else "copied"
                )
                with self.lock:
                    self.current_file_name = ""
                    self.current_file_size = 0
                    self.completed_files += 1
                    self.completed_bytes += entry.size
                    self.current_file_done = 0
                    self.current_file_active = False
                self.current_index += 1

            self._check_stop()
            if self.profile["final_sync"] and self._sync_path:
                # « Terminé » doit vouloir dire : tout est écrit sur le support.
                self.set_state("flushing")
                self._flush_destination()
            if self.mode == "move":
                self.set_state("finalizing")
                self._cleanup_empty_dirs()
                self._remove_empty_manifest_directories()
            with self.lock:
                self.current_file_name = ""
                self.current_file_size = 0
                self.current_file_active = False
            if self.missing_files or self.move_errors or self.renamed_names or self.failed_files:
                missing_count = len(self.missing_files)
                move_error_count = len(self.move_errors)
                parts = []
                if missing_count:
                    noun = "fichier absent" if missing_count == 1 else "fichiers absents"
                    parts.append(f"{missing_count} {noun} ou supprimé(s)")
                if move_error_count:
                    noun = "source non supprimée" if move_error_count == 1 else "sources non supprimées"
                    parts.append(f"{move_error_count} {noun}")
                if self.failed_files:
                    count = len(self.failed_files)
                    noun = "élément non copié" if count == 1 else "éléments non copiés"
                    parts.append(f"{count} {noun}")
                if self.renamed_names:
                    count = len(self.renamed_names)
                    noun = "nom adapté" if count == 1 else "noms adaptés"
                    parts.append(f"{count} {noun} au système de fichiers de la destination")
                self.error = "Transfert terminé avec avertissement : " + "; ".join(parts)
                self.set_state("warning")
            else:
                self.set_state("done")
        except TransferStopped:
            self.set_state("stopped")
        except Exception as exc:  # noqa: BLE001 — l'erreur est affichée dans l'interface
            self.error = error_text(exc)
            self.set_state("error")
            traceback.print_exc()
        finally:
            with self.lock:
                self.cancellable = None
            GLib.idle_add(self.on_finish, self)

    def snapshot(self):
        with self.lock:
            total_files = self.total_files
            total_bytes = self.total_bytes
            completed_files = self.completed_files
            completed_bytes = self.completed_bytes
            current_done = self.current_file_done
            current_size = self.current_file_size
            current_active = self.current_file_active
            current_name = self.current_file_name
            state = self.state
            started_at = self.started_at
            prepare_name = self.prepare_name
            error = self.error
            skipped_files = self.skipped_files
            missing_files = list(self.missing_files)

        done_bytes = completed_bytes + (current_done if current_active else 0)
        if total_bytes:
            fraction = min(1.0, done_bytes / total_bytes)
        elif self.manifest:
            fraction = min(1.0, self.current_index / len(self.manifest))
        else:
            fraction = 0.0

        with self.lock:
            paused_duration = self.paused_duration
            if state == "paused" and self.paused_started_at is not None:
                paused_duration += max(0.0, time.monotonic() - self.paused_started_at)
        elapsed = max(0.0, time.monotonic() - started_at - paused_duration) if started_at else 0.0
        # Le débit n'est affiché que pendant la copie active. Une fois le
        # transfert terminé, le chronomètre ne doit plus produire un faux
        # débit qui continue à varier.
        speed = done_bytes / elapsed if elapsed > 0 and state == "running" else 0
        remaining_bytes = max(0, total_bytes - done_bytes)
        remaining_seconds = (remaining_bytes / speed) if speed > 0 and state == "running" else None
        current_number = completed_files + skipped_files + (1 if current_active else 0)
        remaining = max(0, total_files - current_number)

        return {
            "state": state,
            "fraction": fraction,
            "done_bytes": done_bytes,
            "total_bytes": total_bytes,
            "speed": speed,
            "remaining_seconds": remaining_seconds,
            "total_files": total_files,
            "completed_files": completed_files,
            "skipped_files": skipped_files,
            "current_number": current_number,
            "current_name": current_name,
            "current_size": current_size,
            "current_done": current_done,
            "remaining": remaining,
            "prepare_name": prepare_name,
            "error": error,
            "missing_files": missing_files,
        }


class LocationPane(Gtk.Box):
    """Un emplacement de navigation et de sélection de fichiers."""

    def __init__(self, window, slot, initial_location):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window = window
        self.slot = slot
        self.location_file = None
        self.location_ready = False
        self.items = []
        self.rows = []
        self.load_token = 0
        self._mount_operation = None
        self._mount_cancellable = None
        self._setting_favorite = False
        self._context_popover = None
        self._delete_busy = False

        self.add_css_class("card")
        self.add_css_class("fret-panel")
        self.add_css_class("pane-left" if slot == 0 else "pane-right")
        self.set_margin_top(6)
        self.set_margin_bottom(6)
        self.set_margin_start(6)
        self.set_margin_end(6)

        self._install_actions()
        self._build_header()
        self._build_actions()
        self._build_content()
        self._install_activation_controllers()
        self.load_location(file_object=initial_location)

    def _install_activation_controllers(self):
        # Un clic n'importe où dans le panneau (en-tête, barre de chemin, zone
        # vide de la liste…) le rend actif. Phase CAPTURE : on observe le clic
        # sans le consommer, les boutons et les lignes réagissent comme avant.
        click = Gtk.GestureClick()
        click.set_button(0)
        click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        click.connect("pressed", lambda *_: self.window.set_active_pane(self))
        self.add_controller(click)

        # Le focus clavier (Tab, raccourcis) fait aussi basculer le panneau actif.
        focus = Gtk.EventControllerFocus()
        focus.connect("enter", lambda *_: self.window.set_active_pane(self))
        self.add_controller(focus)

    def _icon_button(self, icon_name, tooltip):
        button = Gtk.Button.new_from_icon_name(icon_name)
        button.set_tooltip_text(tooltip)
        button.add_css_class("flat")
        return button

    def _build_header(self):
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        header.add_css_class("pane-header")
        header.set_margin_top(10)
        header.set_margin_start(10)
        header.set_margin_end(10)
        header.set_margin_bottom(6)

        self.spinner = Gtk.Spinner()
        self.spinner.set_visible(False)
        header.append(self.spinner)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header.append(spacer)

        self.favorite_button = Gtk.ToggleButton.new()
        self.favorite_button.set_icon_name("non-starred-symbolic")
        self.favorite_button.set_tooltip_text("Ajouter aux favoris")
        self.favorite_button.add_css_class("flat")
        self.favorite_button.set_sensitive(False)
        self.favorite_button.connect("toggled", self._favorite_toggled)
        header.append(self.favorite_button)

        self.up_button = self._icon_button("go-up-symbolic", "Dossier parent")
        self.up_button.connect("clicked", self._go_up)
        header.append(self.up_button)

        self.refresh_button = self._icon_button("view-refresh-symbolic", "Actualiser")
        self.refresh_button.connect("clicked", lambda *_: self.refresh())
        header.append(self.refresh_button)

        self.append(header)

        location_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        location_row.add_css_class("pane-location")
        location_row.set_margin_start(10)
        location_row.set_margin_end(10)
        location_row.set_margin_bottom(8)

        # Barre de chemin native Adwaita : les segments sont de vrais boutons.
        # Lorsque le chemin est trop long, les parents intermédiaires sont
        # regroupés dans un bouton « … » avec un popover, comme les barres
        # de navigation GNOME, plutôt que d'afficher une barre de défilement.
        self.breadcrumb_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.breadcrumb_box.add_css_class("path-bar")
        self.breadcrumb_box.set_valign(Gtk.Align.CENTER)
        self.breadcrumb_box.set_hexpand(True)
        location_row.append(self.breadcrumb_box)

        self.browse_button = self._icon_button("folder-open-symbolic", "Choisir un dossier")
        self.browse_button.connect("clicked", self._browse)
        location_row.append(self.browse_button)
        self.append(location_row)

    def _breadcrumb_icon_name(self, file_object, current=False):
        """Retourne uniquement une icône pour un segment de chemin."""
        if file_object is None:
            return "folder-symbolic"

        path = file_object.get_path()
        if path == os.path.sep:
            return "drive-harddisk-symbolic"

        if path is not None:
            try:
                resolved = Path(path).expanduser().resolve()
                if resolved == Path.home().resolve():
                    return "__FRET_HOME__"

                special_dirs = (
                    (GLib.UserDirectory.DIRECTORY_DESKTOP, "user-desktop-symbolic"),
                    (GLib.UserDirectory.DIRECTORY_DOCUMENTS, "folder-documents-symbolic"),
                    (GLib.UserDirectory.DIRECTORY_DOWNLOAD, "folder-download-symbolic"),
                    (GLib.UserDirectory.DIRECTORY_MUSIC, "folder-music-symbolic"),
                    (GLib.UserDirectory.DIRECTORY_PICTURES, "folder-pictures-symbolic"),
                    (GLib.UserDirectory.DIRECTORY_VIDEOS, "folder-videos-symbolic"),
                    (GLib.UserDirectory.DIRECTORY_PUBLIC_SHARE, "folder-publicshare-symbolic"),
                    (GLib.UserDirectory.DIRECTORY_TEMPLATES, "folder-templates-symbolic"),
                )
                for directory, icon_name in special_dirs:
                    special_path = GLib.get_user_special_dir(directory)
                    if special_path:
                        try:
                            if resolved == Path(special_path).expanduser().resolve():
                                return icon_name
                        except OSError:
                            pass
            except OSError:
                pass

        return "folder-open-symbolic" if current else "folder-symbolic"

    _BREADCRUMB_TOOLTIPS = {
        "__FRET_HOME__": "Dossier personnel",
        "drive-harddisk-symbolic": "Système de fichiers",
        "user-desktop-symbolic": "Bureau",
        "folder-documents-symbolic": "Documents",
        "folder-download-symbolic": "Téléchargements",
        "folder-music-symbolic": "Musique",
        "folder-pictures-symbolic": "Images",
        "folder-videos-symbolic": "Vidéos",
        "folder-publicshare-symbolic": "Partage public",
        "folder-templates-symbolic": "Modèles",
    }

    def _breadcrumb_tooltip(self, file_object, icon_name):
        """Nom court d'un segment de chemin, jamais l'URI brute file:///…"""
        label = self._BREADCRUMB_TOOLTIPS.get(icon_name)
        if label:
            return label
        return file_object.get_basename() or file_object.get_parse_name()

    def _make_path_button(self, file_object, current=False):
        """Crée un bouton de breadcrumb GTK4 compact, sans aucun texte."""
        icon_name = self._breadcrumb_icon_name(file_object, current=current)
        button = Gtk.Button()
        button.add_css_class("flat")
        button.add_css_class("path-segment")
        button.set_size_request(34, 34)
        button.set_tooltip_text(self._breadcrumb_tooltip(file_object, icon_name))
        button.set_focus_on_click(False)
        button.set_valign(Gtk.Align.CENTER)
        button.connect(
            "clicked",
            lambda _button, location=file_object: self.load_location(
                file_object=location
            ),
        )

        if icon_name == "__FRET_HOME__":
            home_icon = Path(__file__).resolve().parent / "data" / "home.png"
            image = Gtk.Image.new_from_file(str(home_icon))
            image.set_pixel_size(18)
        else:
            image = Gtk.Image.new_from_icon_name(icon_name)
            image.set_pixel_size(18)
        image.set_size_request(18, 18)
        image.set_halign(Gtk.Align.CENTER)
        image.set_valign(Gtk.Align.CENTER)
        button.set_child(image)

        if current:
            button.add_css_class("current-path")
            button.set_sensitive(False)

        return button

    def _make_hidden_paths_popover(self, menu_button, hidden):
        popover = Gtk.Popover()
        popover.set_has_arrow(True)
        popover.add_css_class("path-popover")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(6)
        box.set_margin_end(6)

        for file_object in hidden:
            button = self._make_path_button(file_object)
            path = file_object.get_path() or file_object.get_uri()
            button.set_tooltip_text(path)
            button.add_css_class("popover-path-item")
            button.connect("clicked", lambda *_: popover.popdown())
            box.append(button)

        popover.set_child(box)
        menu_button.set_popover(popover)

    def _make_ellipsis_button(self, hidden):
        button = Gtk.MenuButton()
        button.add_css_class("flat")
        button.add_css_class("path-ellipsis")
        button.set_size_request(34, 34)
        button.set_tooltip_text("Afficher les dossiers parents")
        image = Gtk.Image.new_from_icon_name("view-more-horizontal-symbolic")
        image.set_pixel_size(18)
        button.set_child(image)
        self._make_hidden_paths_popover(button, hidden)
        return button

    def _rebuild_breadcrumbs(self):
        """Reconstruit une barre de chemin GTK4 minimaliste, uniquement avec des icônes."""
        while True:
            child = self.breadcrumb_box.get_first_child()
            if child is None:
                break
            self.breadcrumb_box.remove(child)

        if self.location_file is None:
            return

        chain = []
        current = self.location_file
        while current is not None:
            chain.append(current)
            current = current.get_parent()
        chain.reverse()
        if not chain:
            chain = [self.location_file]

        # Les chemins restent compacts : seuls les extrêmes sont visibles.
        # Le milieu est accessible par un unique bouton d'icône. Aucun texte
        # n'est placé dans la barre elle-même.
        if len(chain) <= 6:
            visible = list(enumerate(chain))
            hidden = []
        else:
            visible = [(0, chain[0]), (1, chain[1])]
            hidden = chain[2:-3]
            visible.extend((i, chain[i]) for i in range(len(chain) - 3, len(chain)))

        for visible_index, (index, file_object) in enumerate(visible):
            if visible_index:
                separator = Gtk.Image.new_from_icon_name("go-next-symbolic")
                separator.set_pixel_size(12)
                separator.set_size_request(14, 14)
                separator.add_css_class("path-chevron")
                self.breadcrumb_box.append(separator)

            if hidden and visible_index == 2:
                self.breadcrumb_box.append(self._make_ellipsis_button(hidden))
                separator = Gtk.Image.new_from_icon_name("go-next-symbolic")
                separator.set_pixel_size(12)
                separator.set_size_request(14, 14)
                separator.add_css_class("path-chevron")
                self.breadcrumb_box.append(separator)

            self.breadcrumb_box.append(
                self._make_path_button(
                    file_object, current=(index == len(chain) - 1)
                )
            )

    def _build_actions(self):
        action_bar = Gtk.ActionBar()

        self.select_all_button = self._icon_button(
            "edit-select-all-symbolic", "Sélectionner tous les fichiers"
        )
        self.select_all_button.connect("clicked", lambda *_: self.toggle_select_all())
        action_bar.pack_start(self.select_all_button)

        transfer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        transfer_box.add_css_class("linked")

        self.copy_to_button = Gtk.Button.new_from_icon_name("edit-copy-symbolic")
        self.copy_to_button.set_tooltip_text("Copier vers l’autre panneau")
        self.copy_to_button.set_sensitive(False)
        self.copy_to_button.connect("clicked", lambda *_: self.copy_to_adjacent())
        transfer_box.append(self.copy_to_button)

        self.move_to_button = Gtk.Button.new_from_icon_name("edit-cut-symbolic")
        self.move_to_button.set_tooltip_text("Déplacer vers l’autre panneau")
        self.move_to_button.set_sensitive(False)
        self.move_to_button.connect("clicked", lambda *_: self.move_to_adjacent())
        transfer_box.append(self.move_to_button)
        action_bar.pack_start(transfer_box)

        self.selection_label = Gtk.Label(label="0 sélectionné")
        self.selection_label.add_css_class("dim-label")
        self.selection_label.set_xalign(0)
        action_bar.pack_start(self.selection_label)

        self.append(action_bar)

    def _build_content(self):
        self.content_stack = Gtk.Stack()
        self.content_stack.set_vexpand(True)
        self.content_stack.set_hexpand(True)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.listbox.set_activate_on_single_click(False)
        self.listbox.set_show_separators(False)
        self.listbox.add_css_class("navigation-sidebar")
        self.listbox.connect("row-activated", self._row_activated)
        self.listbox.connect("selected-rows-changed", self._selected_rows_changed)
        click_controller = Gtk.GestureClick()
        click_controller.connect("pressed", lambda *_: self.window.set_active_pane(self))
        self.listbox.add_controller(click_controller)

        empty_label = Gtk.Label(label="Ce dossier est vide")
        empty_label.add_css_class("dim-label")
        empty_label.set_margin_top(32)
        self.listbox.set_placeholder(empty_label)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(self.listbox)
        self.content_stack.add_named(scrolled, "list")

        loading_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=10, halign=Gtk.Align.CENTER
        )
        loading_box.set_valign(Gtk.Align.CENTER)
        loading_spinner = Gtk.Spinner()
        loading_spinner.set_size_request(32, 32)
        loading_spinner.start()
        loading_box.append(loading_spinner)
        loading_box.append(Gtk.Label(label="Lecture de l’emplacement…"))
        self.content_stack.add_named(loading_box, "loading")

        self.error_page = Adw.StatusPage()
        self.error_page.set_icon_name("dialog-error-symbolic")
        self.error_page.set_title("Impossible d’ouvrir cet emplacement")
        self.error_page.set_description("")
        self.error_page.add_css_class("compact")
        self.content_stack.add_named(self.error_page, "error")

        self.context_menu = Gtk.PopoverMenu.new_from_model(self._context_menu_model())
        self.context_menu.set_parent(self)
        self.context_menu.set_has_arrow(False)
        self.context_menu.set_halign(Gtk.Align.START)

        self.append(self.content_stack)

    def _clear_rows(self):
        for row in self.rows:
            self.listbox.remove(row)
        self.rows.clear()

    def _make_row(self, item):
        row = Gtk.ListBoxRow()
        row.set_activatable(True)
        row.set_selectable(True)
        row.item = item

        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        content.set_margin_top(6)
        content.set_margin_bottom(6)
        content.set_margin_start(6)
        content.set_margin_end(6)

        check = Gtk.CheckButton()
        check.set_tooltip_text("Sélectionner cet élément")
        check.set_can_focus(False)
        check.add_css_class("selection-mode")
        check.connect("toggled", self._row_selection_toggled, row)
        content.append(check)
        row.check_button = check

        image = Gtk.Image.new_from_gicon(item.icon)
        image.set_pixel_size(32)
        image.add_css_class("lowres-icon")
        content.append(image)

        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        labels.set_hexpand(True)
        name_label = Gtk.Label(label=item.display_name)
        name_label.set_xalign(0)
        name_label.set_ellipsize(Pango.EllipsizeMode.END)
        name_label.set_hexpand(True)
        labels.append(name_label)

        details = []
        if item.is_dir:
            details.append("Dossier")
        else:
            details.append(format_bytes(item.size))
        if item.modified:
            details.append(item.modified)
        metadata = Gtk.Label(label=" · ".join(details))
        metadata.set_xalign(0)
        metadata.add_css_class("dim-label")
        metadata.add_css_class("caption")
        metadata.set_ellipsize(Pango.EllipsizeMode.END)
        labels.append(metadata)
        content.append(labels)

        row.set_child(content)
        secondary_click = Gtk.GestureClick()
        secondary_click.set_button(3)
        secondary_click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        secondary_click.connect("pressed", self._row_secondary_pressed, row)
        row.add_controller(secondary_click)
        self.rows.append(row)
        return row

    def _row_secondary_pressed(self, gesture, n_press, _x, _y, row):
        if n_press != 1 or self._delete_busy:
            return

        self.window.set_active_pane(self)
        if not row.check_button.get_active():
            for candidate in self.rows:
                if candidate is not row and candidate.check_button.get_active():
                    candidate.check_button.set_active(False)
            row.check_button.set_active(True)

        self._show_context_menu(row, _x, _y)
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)

    @staticmethod
    def _context_menu_model():
        menu = Gio.Menu()
        transfer_section = Gio.Menu()
        transfer_section.append("Copier vers l’autre panneau", "pane.copy-to")
        transfer_section.append("Déplacer vers l’autre panneau", "pane.move-to")
        menu.append_section(None, transfer_section)
        selection_section = Gio.Menu()
        selection_section.append("Tout sélectionner", "pane.select-all")
        menu.append_section(None, selection_section)
        delete_section = Gio.Menu()
        delete_section.append("Mettre à la corbeille", "pane.trash")
        menu.append_section(None, delete_section)
        return menu

    def _install_actions(self):
        group = Gio.SimpleActionGroup()
        self._pane_actions = {}
        for name, callback in (
            ("copy-to", lambda *_: self.copy_to_adjacent()),
            ("move-to", lambda *_: self.move_to_adjacent()),
            ("select-all", lambda *_: self.toggle_select_all()),
            ("trash", lambda *_: self._confirm_delete(self._effective_selected_items())),
        ):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            group.add_action(action)
            self._pane_actions[name] = action
        self.insert_action_group("pane", group)

    def _show_context_menu(self, row, x, y):
        ok, point = row.compute_point(self, Graphene.Point().init(x, y))
        if ok:
            rect = Gdk.Rectangle()
            rect.x, rect.y, rect.width, rect.height = int(point.x), int(point.y), 1, 1
            self.context_menu.set_pointing_to(rect)
        self.context_menu.popup()

    def _effective_selected_items(self):
        selected = self.get_selected_items()
        effective = []
        for item in selected:
            if any(
                other is not item
                and is_same_or_descendant(item.file, other.file)
                for other in selected
            ):
                continue
            effective.append(item)
        return effective

    def _confirm_delete(self, items):
        if not items:
            self.window.toast("Aucun fichier sélectionné.")
            return

        names = [item.display_name for item in items]
        if len(names) == 1:
            body = (
                f"Voulez-vous déplacer « {names[0]} » vers la corbeille ?"
            )
        else:
            listed_names = "\n".join(f"• {name}" for name in names[:8])
            if len(names) > 8:
                listed_names += f"\n• … et {len(names) - 8} autre(s)"
            body = (
                f"Voulez-vous déplacer ces {len(names)} éléments vers la corbeille ?\n\n"
                f"{listed_names}"
            )

        dialog = Adw.AlertDialog.new("Supprimer les fichiers ?", body)
        dialog.add_response("cancel", "Annuler")
        dialog.add_response("delete", "Supprimer")
        dialog.set_response_appearance(
            "delete", Adw.ResponseAppearance.DESTRUCTIVE
        )
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._delete_confirmation_response, items)
        dialog.present(self.window)

    def _delete_confirmation_response(self, _dialog, response, items):
        if response == "delete":
            self._start_delete(items)

    def _set_delete_busy(self, busy):
        self._delete_busy = busy
        self.spinner.set_visible(busy)
        if busy:
            self.spinner.start()
        else:
            self.spinner.stop()

        for widget in (
            self.favorite_button,
            self.up_button,
            self.refresh_button,
            self.browse_button,
            self.select_all_button,
            self.copy_to_button,
            self.move_to_button,
        ):
            widget.set_sensitive(not busy)
        self.listbox.set_sensitive(not busy)

        if not busy:
            self._update_favorite_button()
            self.up_button.set_sensitive(
                self.location_file is not None
                and self.location_file.get_parent() is not None
            )
            self._update_transfer_buttons()

    def _start_delete(self, items):
        if self._delete_busy:
            return

        self._set_delete_busy(True)
        threading.Thread(
            target=self._delete_worker,
            args=(list(items),),
            name="fret-delete",
            daemon=True,
        ).start()

    def _delete_worker(self, items):
        deleted = []
        errors = []
        for item in items:
            try:
                if not item.file.trash(None):
                    raise TransferError(
                        "la corbeille n’est pas disponible pour cet emplacement"
                    )
                deleted.append((item.display_name, item.file.get_uri()))
            except Exception as error:  # noqa: BLE001 — affiché dans l’interface
                errors.append(f"{item.display_name} : {error_text(error)}")
        GLib.idle_add(self._delete_finished, deleted, errors)

    def _delete_finished(self, deleted, errors):
        self._set_delete_busy(False)
        self.window.mark_transfer_sources_deleted(
            [uri for _name, uri in deleted]
        )
        self.refresh()
        if errors and deleted:
            self.window.toast(
                f"{len(deleted)} élément(s) supprimé(s), {len(errors)} échec(s)."
            )
        elif errors:
            self.window.toast(f"Suppression impossible : {errors[0]}")
        else:
            self.window.toast(f"{len(deleted)} élément(s) supprimé(s).")
        return False

    def _row_selection_toggled(self, button, row):
        if button.get_active():
            self.listbox.select_row(row)
        else:
            self.listbox.unselect_row(row)
        self._selection_changed()

    def _selected_rows_changed(self, listbox):
        selected = set(listbox.get_selected_rows())
        for row in self.rows:
            row.check_button.set_active(row in selected)
        self._selection_changed()

    def _selection_changed(self):
        count = len(self.get_selected_items())
        self.selection_label.set_text(
            f"{count} sélectionné" if count == 1 else f"{count} sélectionnés"
        )
        all_selected = bool(self.rows) and count == len(self.rows)
        self.select_all_button.set_tooltip_text(
            "Désélectionner tous les fichiers"
            if all_selected
            else "Sélectionner tous les fichiers"
        )
        self._update_transfer_buttons()

    def _update_transfer_buttons(self):
        destination_pane = self.window.other_pane(self)
        enabled = (
            bool(self.get_selected_items())
            and self.location_ready
            and destination_pane.location_ready
            and not self._delete_busy
            and not self.window._video_scan_busy
        )
        for button in (self.copy_to_button, self.move_to_button):
            button.set_sensitive(enabled)
        has_selection = bool(self.get_selected_items()) and not self._delete_busy
        self._pane_actions["copy-to"].set_enabled(enabled)
        self._pane_actions["move-to"].set_enabled(enabled)
        self._pane_actions["trash"].set_enabled(has_selection)
        self._pane_actions["select-all"].set_enabled(bool(self.rows))

    def get_selected_items(self):
        return [row.item for row in self.rows if row.check_button.get_active()]

    def toggle_select_all(self):
        self.window.set_active_pane(self)
        all_selected = bool(self.rows) and len(self.get_selected_items()) == len(self.rows)
        if all_selected:
            self.listbox.unselect_all()
        else:
            self.listbox.select_all()
        self._selection_changed()

    def _row_activated(self, _listbox, row):
        self.window.set_active_pane(self)
        item = getattr(row, "item", None)
        if item is None:
            return
        if item.is_dir:
            self.load_location(file_object=item.file)
            return
        try:
            Gio.AppInfo.launch_default_for_uri(item.file.get_uri(), None)
        except GLib.Error as error:
            self.window.toast(f"Impossible d’ouvrir le fichier : {error_text(error)}")

    def _go_up(self, *_args):
        self.window.set_active_pane(self)
        if self.location_file is None:
            return
        parent = self.location_file.get_parent()
        if parent is not None:
            self.load_location(file_object=parent)

    def _favorite_toggled(self, _button):
        if self._setting_favorite or self.location_file is None:
            return
        favorite = self.window.store.toggle_favorite(self.location_file)
        self._update_favorite_button()
        self.window._rebuild_locations_menu()
        self.window.toast(
            "Emplacement ajouté aux favoris."
            if favorite
            else "Emplacement retiré des favoris."
        )

    def _update_favorite_button(self):
        favorite = (
            self.location_file is not None
            and self.window.store.is_favorite(self.location_file)
        )
        self._setting_favorite = True
        try:
            self.favorite_button.set_active(favorite)
            self.favorite_button.set_icon_name(
                "starred-symbolic" if favorite else "non-starred-symbolic"
            )
            self.favorite_button.set_tooltip_text(
                "Retirer des favoris" if favorite else "Ajouter aux favoris"
            )
            self.favorite_button.set_sensitive(self.location_file is not None)
        finally:
            self._setting_favorite = False

    def _browse(self, *_args):
        self.window.set_active_pane(self)
        if not hasattr(Gtk, "FileDialog"):
            self.window.toast("Cette version de GTK ne fournit pas le sélecteur de dossier.")
            return
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Choisir l’emplacement")
        dialog.select_folder(self.window, None, self._browse_finished)

    def _browse_finished(self, dialog, result):
        try:
            selected = dialog.select_folder_finish(result)
        except GLib.Error as error:
            if "cancel" not in error_text(error).lower():
                self.window.toast(f"Sélection impossible : {error_text(error)}")
            return
        if selected is not None:
            self.load_location(file_object=selected)

    def load_location(self, value=None, file_object=None):
        if file_object is None:
            try:
                file_object = file_from_location(value)
            except Exception as error:  # noqa: BLE001
                self.window.toast(f"Chemin invalide : {error_text(error)}")
                return

        if self._mount_cancellable is not None:
            self._mount_cancellable.cancel()
            self._mount_cancellable = None
            self._mount_operation = None

        self.load_token += 1
        token = self.load_token
        self.location_file = file_object
        self.location_ready = False
        self._rebuild_breadcrumbs()
        self._update_favorite_button()
        self.window._update_paste_buttons()
        self._clear_rows()
        self.content_stack.set_visible_child_name("loading")
        self.spinner.set_visible(True)
        self.spinner.start()

        if is_remote_location(file_object):
            self._mount_remote(file_object, token)
        else:
            self._start_enumeration(file_object, token)

    def _mount_remote(self, location, token):
        """Monte un emplacement GVfs sur le thread GTK, avec dialogue d'authentification."""

        try:
            operation = Gtk.MountOperation.new(self.window)
            cancellable = Gio.Cancellable()
            self._mount_operation = operation
            self._mount_cancellable = cancellable
            location.mount_enclosing_volume(
                Gio.MountMountFlags.NONE,
                operation,
                cancellable,
                self._mount_finished,
                (location, token),
            )
        except Exception as error:  # noqa: BLE001 — certains backends n'exposent pas le montage
            self._mount_operation = None
            self._mount_cancellable = None
            self._enumeration_finished(token, [], error_text(error))

    def _mount_finished(self, source, result, user_data):
        location, token = user_data
        if token != self.load_token:
            return False

        self._mount_operation = None
        self._mount_cancellable = None
        try:
            source.mount_enclosing_volume_finish(result)
        except GLib.Error as error:
            already_mounted = getattr(Gio.IOErrorEnum, "ALREADY_MOUNTED", None)
            if already_mounted is None or not error.matches(
                Gio.io_error_quark(), already_mounted
            ):
                self._enumeration_finished(token, [], error_text(error))
                return False

        self._start_enumeration(location, token)
        return False

    def _start_enumeration(self, location, token):
        if token != self.load_token:
            return
        thread = threading.Thread(
            target=self._enumerate_worker, args=(location, token), daemon=True
        )
        thread.start()

    def _enumerate_worker(self, location, token):
        try:
            items = []
            enumerator = location.enumerate_children(
                "standard::name,standard::display-name,standard::type,standard::size,"
                "standard::content-type,standard::icon,time::modified",
                Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                None,
            )
            try:
                while True:
                    info = enumerator.next_file(None)
                    if info is None:
                        break
                    name = info.get_name()
                    if not self.window.show_hidden and name.startswith("."):
                        continue
                    file_type = info.get_file_type()
                    is_dir = file_type == Gio.FileType.DIRECTORY
                    content_type = info.get_content_type() or "application/octet-stream"
                    # GIO fournit l'icône complète associée à l'élément par
                    # GVfs et le thème d'icônes courant. Les icônes symboliques
                    # seraient monochromes et perdraient les couleurs du thème.
                    icon = full_color_icon(info.get_icon())
                    if icon is None:
                        if is_dir:
                            icon = Gio.ThemedIcon.new_with_default_fallbacks("folder")
                        else:
                            icon = full_color_icon(
                                Gio.content_type_get_icon(content_type)
                            )
                    if icon is None:
                        icon = Gio.ThemedIcon.new(
                            "folder" if is_dir else "text-x-generic"
                        )
                    kind = (
                        "Dossier"
                        if is_dir
                        else Gio.content_type_get_description(content_type) or "Fichier"
                    )

                    modified = ""
                    try:
                        date_time = info.get_modification_date_time()
                        if date_time is not None:
                            modified = date_time.format("%d/%m/%Y %H:%M")
                    except (AttributeError, GLib.Error):
                        pass

                    items.append(
                        FileItem(
                            file=location.get_child(name),
                            name=name,
                            display_name=info.get_display_name() or name,
                            is_dir=is_dir,
                            size=int(info.get_size()),
                            modified=modified,
                            kind=kind,
                            icon=icon,
                        )
                    )
            finally:
                enumerator.close(None)

            items.sort(
                key=lambda item: (
                    not item.is_dir,
                    locale.strxfrm(item.display_name.casefold()),
                )
            )
            GLib.idle_add(self._enumeration_finished, token, items, "")
        except Exception as error:  # noqa: BLE001
            GLib.idle_add(self._enumeration_finished, token, [], error_text(error))

    def _enumeration_finished(self, token, items, error):
        if token != self.load_token:
            return False

        self.spinner.stop()
        self.spinner.set_visible(False)
        if error:
            self.location_ready = False
            self.error_page.set_description(error)
            self.content_stack.set_visible_child_name("error")
            self._update_favorite_button()
            self.window._update_paste_buttons()
            return False

        self.location_ready = True
        self.items = items
        for item in items:
            self.listbox.append(self._make_row(item))
        self.content_stack.set_visible_child_name("list")
        self._selection_changed()
        self.up_button.set_sensitive(self.location_file is not None and self.location_file.get_parent() is not None)
        self._update_favorite_button()
        self.window.location_loaded(self)
        self.window._update_paste_buttons()
        return False

    def refresh(self):
        if self.location_file is not None:
            self.load_location(file_object=self.location_file)

    def copy_selected(self):
        self.window.set_active_pane(self)
        items = self.get_selected_items()
        if items:
            self.window.set_clipboard(items, "copy", self)
        else:
            self.window.toast("Sélectionne au moins un élément.")

    def cut_selected(self):
        self.window.set_active_pane(self)
        items = self.get_selected_items()
        if items:
            self.window.set_clipboard(items, "move", self)
        else:
            self.window.toast("Sélectionne au moins un élément.")

    def paste_here(self):
        self.window.set_active_pane(self)
        self.window.paste_into(self)

    def copy_to_adjacent(self):
        self.window.set_active_pane(self)
        self.window.transfer_selected_to_adjacent(self, "copy")

    def move_to_adjacent(self):
        self.window.set_active_pane(self)
        self.window.transfer_selected_to_adjacent(self, "move")


class FretWindow(Adw.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application)
        self.set_title(APP_NAME)
        self.set_default_size(900, 650)
        self.set_size_request(640, 520)

        self.clipboard_items = []
        self.clipboard_mode = "copy"
        self.clipboard_source = None
        self.active_pane = None
        self.active_job = None
        self.store = LocationStore()
        self.show_hidden = self.store.show_hidden
        self.menu_button = None
        self.favorites_button = None
        self.import_preferences_window = None
        self._import_preferences_widgets = None
        self._video_scan_details = ""
        self.toast_overlay = None
        self._video_scan_busy = False
        self._privacy_overlay = None
        self._privacy_panel = None
        self._queued_transfer_panes = set()
        self.transfer_queue = []
        self._pending_ejects = set()
        self._profile_context = None
        self.volume_monitor = None

        self._sync_scheme_class()
        manager = Adw.StyleManager.get_default()
        manager.connect("notify::dark", lambda *_: self._sync_scheme_class())
        manager.connect(
            "notify::high-contrast", lambda *_: self._sync_scheme_class()
        )
        self._install_css()
        self._install_actions()
        self._build_ui()
        self._update_import_button_tooltip()
        self._rebuild_locations_menu()
        self._setup_volume_monitor()
        self._rebuild_queue_ui()
        self._update_profile_pill()
        self.connect("notify::is-active", self._window_activity_changed)
        self._transfer_timer = GLib.timeout_add(200, self._refresh_transfer_ui)

    def _sync_scheme_class(self):
        """Le panneau de droite prend le schéma opposé, sauf en contraste élevé."""
        manager = Adw.StyleManager.get_default()
        self.remove_css_class("fret-dark")
        self.remove_css_class("fret-light")
        # En contraste élevé, on laisse le thème décider : forcer un panneau
        # clair en HC sombre irait contre la préférence de l'utilisateur.
        if manager.get_high_contrast():
            return
        self.add_css_class("fret-dark" if manager.get_dark() else "fret-light")

    def _install_css(self):
        css = """
        .fret-panel actionbar > revealer > box {
            background: none;
            border-top: 1px solid alpha(currentColor, 0.15);
        }
        .fret-panel scrolledwindow {
            border-top: 1px solid alpha(currentColor, 0.15);
        }
        /* Deux panneaux à fort contraste : celui de droite prend toujours le
           schéma opposé à celui du thème (sombre en thème clair, clair en
           thème sombre). On redéfinit les variables de libadwaita sur le
           panneau : tout ce qu'il contient suit. */
        window.fret-light .fret-panel.pane-right {
            --window-bg-color: #222226;
            --window-fg-color: #ffffff;
            --view-bg-color: #1d1d20;
            --view-fg-color: #ffffff;
            --card-bg-color: #2a2a2f;
            --card-fg-color: #ffffff;
            --card-shade-color: rgb(0 0 6 / 36%);
            --headerbar-bg-color: #2e2e32;
            --headerbar-fg-color: #ffffff;
            --popover-bg-color: #36363a;
            --popover-fg-color: #ffffff;
            /* Le panneau est sombre : l'accent standalone doit l'être aussi. */
            --standalone-color-oklab: max(l, 0.85) a b;
            --accent-color: oklab(from var(--accent-bg-color) var(--standalone-color-oklab));
            --sidebar-bg-color: #2e2e32;
            --sidebar-fg-color: #ffffff;
            background-color: #2a2a2f;
            color: #ffffff;
        }
        window.fret-dark .fret-panel.pane-right {
            --window-bg-color: #fafafb;
            --window-fg-color: rgb(0 0 6 / 80%);
            --view-bg-color: #ffffff;
            --view-fg-color: rgb(0 0 6 / 80%);
            --card-bg-color: #ffffff;
            --card-fg-color: rgb(0 0 6 / 80%);
            --card-shade-color: rgb(0 0 6 / 7%);
            --headerbar-bg-color: #ffffff;
            --headerbar-fg-color: rgb(0 0 6 / 80%);
            --popover-bg-color: #ffffff;
            --popover-fg-color: rgb(0 0 6 / 80%);
            /* Le panneau est clair : accent standalone version claire. */
            --standalone-color-oklab: min(l, 0.5) a b;
            --accent-color: oklab(from var(--accent-bg-color) var(--standalone-color-oklab));
            --sidebar-bg-color: #ebebed;
            --sidebar-fg-color: rgb(0 0 6 / 80%);
            background-color: #ffffff;
            color: rgb(0 0 6 / 80%);
        }
        /* Panneau actif : même vocabulaire que l'onglet actif d'Adw.TabBar. */
        .fret-panel {
            border: 2px solid transparent;
        }
        .fret-panel.active-panel {
            border-color: var(--accent-color);
        }
        .fret-panel.active-panel scrolledwindow {
            border-top-color: var(--accent-color);
            box-shadow: 0 -1px var(--accent-color);
        }
        .fret-panel:not(.active-panel) .pane-header,
        .fret-panel:not(.active-panel) .pane-location {
            opacity: 0.8;
        }
        @media (prefers-contrast: more) {
            .fret-panel:not(.active-panel) .pane-header,
            .fret-panel:not(.active-panel) .pane-location {
                opacity: 1;
            }
        }
        .profile-pill {
            border-radius: 999px;
            padding: 0;
            min-height: 26px;
        }
        .profile-pill > button {
            border-radius: 999px;
            min-height: 26px;
            padding: 0 10px;
            background-color: alpha(currentColor, 0.08);
        }
        .profile-pill > button:hover {
            background-color: alpha(currentColor, 0.14);
        }
        .queue-row {
            padding: 6px 4px;
        }
        .privacy-shield {
            background-color: var(--window-bg-color);
        }
        /* Barre de chemin GTK4 minimaliste : uniquement des icônes. */
        .path-bar {
            min-height: 36px;
            padding: 2px 0;
        }
        .path-segment {
            min-width: 34px;
            min-height: 34px;
            padding: 0;
            border-radius: 7px;
        }
        .path-segment:hover {
            background-color: alpha(currentColor, 0.08);
        }
        .path-segment:active {
            background-color: alpha(currentColor, 0.14);
        }
        .path-segment.current-path,
        .path-segment.current-path:disabled {
            background-color: alpha(currentColor, 0.06);
            color: inherit;
            opacity: 1;
            font-weight: 600;
        }
        .path-chevron {
            margin-left: 2px;
            margin-right: 2px;
            opacity: 0.55;
        }
        .path-ellipsis {
            min-width: 34px;
            min-height: 34px;
            padding: 0;
            border-radius: 7px;
        }
        .path-popover > contents {
            padding: 0;
        }
        .popover-path-item {
            min-width: 34px;
            min-height: 34px;
            padding: 0;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode("utf-8"))
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def _icon_button(self, icon_name, tooltip):
        button = Gtk.Button.new_from_icon_name(icon_name)
        button.set_tooltip_text(tooltip)
        button.add_css_class("flat")
        return button

    @staticmethod
    def _restore_location(saved, fallback):
        if not saved:
            return fallback
        try:
            candidate = file_from_location(saved)
            if not is_remote_location(candidate) and not candidate.query_exists(None):
                return fallback
            return candidate
        except (GLib.Error, ValueError, TypeError):
            return fallback

    def _set_show_hidden(self, show_hidden):
        if show_hidden == self.show_hidden:
            return
        self.show_hidden = show_hidden
        self.store.show_hidden = show_hidden
        self.store.save()
        for pane in getattr(self, "panes", []):
            pane.refresh()

    @staticmethod
    def _location_label(uri):
        try:
            return location_to_text(file_from_location(uri)) or uri
        except (GLib.Error, ValueError, TypeError):
            return uri

    def _rebuild_locations_menu(self):
        if self.favorites_button is not None:
            favorites_menu = Gio.Menu()
            favorites_section = Gio.Menu()
            if self.store.favorites:
                for uri in self.store.favorites:
                    item = Gio.MenuItem.new(self._location_label(uri), None)
                    item.set_action_and_target_value(
                        "win.open-location", GLib.Variant("s", uri)
                    )
                    favorites_section.append_item(item)
            else:
                favorites_section.append("Aucun favori enregistré", None)
            favorites_menu.append_section("Favoris", favorites_section)
            self.favorites_button.set_menu_model(favorites_menu)

        if self.menu_button is None:
            return
        app_menu = Gio.Menu()
        view_section = Gio.Menu()
        view_section.append("Afficher les fichiers cachés", "win.show-hidden")
        view_section.append("Permuter les emplacements", "win.swap-panes")
        app_menu.append_section(None, view_section)
        import_section = Gio.Menu()
        import_section.append("Importer les vidéos", "win.import-videos")
        import_section.append("Réinitialiser l’import vidéo", "win.reset-import")
        app_menu.append_section(None, import_section)
        app_section = Gio.Menu()
        app_section.append("_Préférences", "win.configure-import")
        app_section.append("_Raccourcis clavier", "win.show-help-overlay")
        app_section.append("À _propos de Fret", "win.about")
        app_menu.append_section(None, app_section)
        self.menu_button.set_menu_model(app_menu)

    def _open_location_action(self, _action, parameter):
        uri = parameter.get_string()
        pane = self.active_pane or self.left_pane
        self.set_active_pane(pane)
        pane.load_location(value=uri)

    def location_loaded(self, pane):
        self.store.record(pane.location_file, pane.slot)
        self._rebuild_locations_menu()
        self._update_profile_pill()

    def _build_ui(self):
        toast_overlay = Adw.ToastOverlay()
        toolbar_view = Adw.ToolbarView()

        header = Adw.HeaderBar()
        title = Adw.WindowTitle.new(APP_NAME, "Transferts locaux et distants")
        header.set_title_widget(title)

        self.swap_button = self._icon_button(
            "object-flip-horizontal-symbolic", "Permuter les emplacements"
        )
        self.swap_button.set_action_name("win.swap-panes")
        header.pack_start(self.swap_button)

        self.import_videos_button = self._icon_button(
            "folder-videos-symbolic", "Importer les vidéos"
        )
        self.import_videos_button.set_action_name("win.import-videos")
        header.pack_start(self.import_videos_button)

        self.menu_button = Gtk.MenuButton()
        self.menu_button.set_icon_name("open-menu-symbolic")
        self.menu_button.set_tooltip_text("Menu principal")
        self.menu_button.set_primary(True)
        header.pack_end(self.menu_button)

        self.favorites_button = Gtk.MenuButton()
        self.favorites_button.set_icon_name("starred-symbolic")
        self.favorites_button.set_tooltip_text("Favoris")
        header.pack_end(self.favorites_button)

        self.eye_button = self._icon_button(
            "view-conceal-symbolic", "Masquer l’interface"
        )
        self.eye_button.set_action_name("win.toggle-privacy")
        header.pack_end(self.eye_button)

        # Éjection : visible seulement quand un support amovible est branché.
        self.eject_button = self._icon_button("media-eject-symbolic", "Éjecter")
        self.eject_button.set_visible(False)
        header.pack_end(self.eject_button)
        self.eject_menu_button = Gtk.MenuButton()
        self.eject_menu_button.set_icon_name("media-eject-symbolic")
        self.eject_menu_button.set_tooltip_text("Éjecter un support")
        self.eject_menu_button.set_visible(False)
        header.pack_end(self.eject_menu_button)
        toolbar_view.add_top_bar(header)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.set_vexpand(True)

        home = Gio.File.new_for_path(os.path.expanduser("~"))
        downloads = home.get_child("Downloads")
        try:
            if not downloads.query_exists(None):
                downloads = home
        except GLib.Error:
            downloads = home

        left_location = self._restore_location(self.store.last_locations[0], home)
        right_location = self._restore_location(self.store.last_locations[1], downloads)

        self.left_pane = LocationPane(self, 0, left_location)
        self.right_pane = LocationPane(self, 1, right_location)

        panels_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        panels_box.set_vexpand(True)
        panels_box.set_hexpand(True)
        panels_box.set_homogeneous(True)
        self.panels_box = panels_box
        self.left_pane.set_hexpand(True)
        self.left_pane.set_vexpand(True)
        self.right_pane.set_hexpand(True)
        self.right_pane.set_vexpand(True)
        panels_box.append(self.left_pane)
        panels_box.append(self.right_pane)
        main_box.append(panels_box)

        main_box.append(self._build_transfer_panel())
        toolbar_view.set_content(main_box)
        toast_overlay.set_child(toolbar_view)
        self.toast_overlay = toast_overlay

        self._privacy_overlay = Gtk.Overlay()
        self._privacy_overlay.set_child(toast_overlay)
        self._build_privacy_shield()
        self.set_content(self._privacy_overlay)

        self.panes = [self.left_pane, self.right_pane]
        self.set_active_pane(self.left_pane)

    def _application_icon_image(self, size=128):
        """Charge l’icône de l’application depuis les sources ou le thème installé."""

        local_icon = Path(__file__).resolve().parent / "data" / f"{APP_ID}.png"
        if local_icon.is_file():
            image = Gtk.Image.new_from_file(str(local_icon))
        else:
            image = Gtk.Image.new_from_icon_name(APP_ID)
        image.set_pixel_size(size)
        image.set_size_request(size, size)
        image.set_halign(Gtk.Align.CENTER)
        image.set_valign(Gtk.Align.CENTER)
        image.add_css_class("icon-dropshadow")
        return image

    def _build_privacy_shield(self):
        shield = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        shield.add_css_class("privacy-shield")
        shield.set_hexpand(True)
        shield.set_vexpand(True)

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        top_row.set_margin_top(10)
        top_row.set_margin_end(10)
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        top_row.append(spacer)

        reveal_button = self._icon_button(
            "view-reveal-symbolic", "Afficher l’interface"
        )
        reveal_button.set_action_name("win.toggle-privacy")
        top_row.append(reveal_button)
        shield.append(top_row)

        status = Adw.StatusPage()
        status.set_vexpand(True)
        status.set_hexpand(True)
        status.set_title(APP_NAME)
        local_icon = Path(__file__).resolve().parent / "data" / f"{APP_ID}.png"
        if local_icon.is_file():
            status.set_paintable(Gdk.Texture.new_from_filename(str(local_icon)))
        else:
            status.set_icon_name(APP_ID)
        status.set_description("")
        shield.append(status)

        self._privacy_overlay.add_overlay(shield)
        self._privacy_panel = shield
        shield.set_visible(False)

    def _toggle_privacy_mode(self, *_args):
        if self._privacy_panel is None:
            return
        self._privacy_panel.set_visible(not self._privacy_panel.get_visible())

    def _build_transfer_panel(self):
        frame = Gtk.Box()
        frame.add_css_class("card")
        frame.set_margin_top(0)
        frame.set_margin_start(6)
        frame.set_margin_end(6)
        frame.set_margin_bottom(6)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(12)
        box.set_margin_end(12)

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        icon = Gtk.Image.new_from_icon_name("folder-download-symbolic")
        icon.set_pixel_size(24)
        top_row.append(icon)

        self.transfer_status_label = Gtk.Label(label="Aucun transfert en cours")
        self.transfer_status_label.add_css_class("heading")
        self.transfer_status_label.set_xalign(0)
        self.transfer_status_label.set_hexpand(True)
        self.transfer_status_label.set_ellipsize(Pango.EllipsizeMode.END)
        top_row.append(self.transfer_status_label)

        # File d'attente : visible dès qu'un transfert attend son tour.
        self.queue_button = Gtk.MenuButton()
        self.queue_button.add_css_class("flat")
        self.queue_button.set_tooltip_text("File d’attente")
        queue_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        queue_icon = Gtk.Image.new_from_gicon(
            themed_icon(("view-list-bullet-symbolic", "view-list-symbolic"))
        )
        queue_box.append(queue_icon)
        self.queue_count_label = Gtk.Label(label="0")
        queue_box.append(self.queue_count_label)
        self.queue_button.set_child(queue_box)
        self.queue_popover = Gtk.Popover()
        self.queue_button.set_popover(self.queue_popover)
        self.queue_button.set_visible(False)
        top_row.append(self.queue_button)

        # Pastille du réglage de transfert (clé, SSD, disque interne, réseau).
        self.profile_button = Gtk.MenuButton()
        self.profile_button.add_css_class("profile-pill")
        self.profile_button.set_valign(Gtk.Align.CENTER)
        pill_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.profile_icon = Gtk.Image()
        self.profile_icon.set_pixel_size(16)
        pill_box.append(self.profile_icon)
        self.profile_button.set_child(pill_box)
        self.profile_button.set_tooltip_text("Réglage de transfert")
        top_row.append(self.profile_button)

        metrics_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        self.transfer_speed_label = Gtk.Label(label="—")
        self.transfer_speed_label.add_css_class("dim-label")
        self.transfer_speed_label.set_xalign(0)
        metrics_row.append(self.transfer_speed_label)

        self.transfer_eta_label = Gtk.Label(label="Temps restant total : —")
        self.transfer_eta_label.add_css_class("dim-label")
        self.transfer_eta_label.set_xalign(1)
        self.transfer_eta_label.set_hexpand(True)
        metrics_row.append(self.transfer_eta_label)

        self.transfer_pause_button = self._icon_button(
            "media-playback-pause-symbolic", "Mettre en pause"
        )
        self.transfer_pause_button.connect("clicked", self._pause_or_resume)
        self.transfer_pause_button.set_sensitive(False)
        top_row.append(self.transfer_pause_button)

        self.transfer_stop_button = self._icon_button("process-stop-symbolic", "Arrêter")
        self.transfer_stop_button.connect("clicked", self._stop_transfer)
        self.transfer_stop_button.set_sensitive(False)
        top_row.append(self.transfer_stop_button)
        box.append(top_row)
        box.append(metrics_row)

        progress_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.transfer_progress = Gtk.ProgressBar()
        self.transfer_progress.set_hexpand(True)
        self.transfer_progress.set_show_text(False)
        progress_row.append(self.transfer_progress)
        self.transfer_progress_label = Gtk.Label(label="—")
        self.transfer_progress_label.set_width_chars(5)
        self.transfer_progress_label.set_xalign(1)
        progress_row.append(self.transfer_progress_label)
        box.append(progress_row)

        self.transfer_bytes_label = Gtk.Label(label="Données transférées : — / —")
        self.transfer_bytes_label.add_css_class("dim-label")
        self.transfer_bytes_label.set_xalign(0)
        self.transfer_bytes_label.set_ellipsize(Pango.EllipsizeMode.END)
        box.append(self.transfer_bytes_label)

        self.transfer_file_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.transfer_file_number_label = Gtk.Label()
        self.transfer_file_number_label.add_css_class("dim-label")
        self.transfer_file_number_label.set_xalign(0)
        self.transfer_file_row.append(self.transfer_file_number_label)
        self.transfer_filename_label = Gtk.Label()
        self.transfer_filename_label.add_css_class("dim-label")
        self.transfer_filename_label.set_xalign(0)
        self.transfer_filename_label.set_hexpand(True)
        self.transfer_filename_label.set_width_chars(1)
        self.transfer_filename_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        self.transfer_filename_label.set_single_line_mode(True)
        self.transfer_file_row.append(self.transfer_filename_label)
        self.transfer_file_row.set_visible(False)
        box.append(self.transfer_file_row)

        self.transfer_details_label = Gtk.Label(
            label="Sélectionner des fichiers, puis choisir Copier ou Déplacer vers l’autre panneau."
        )
        self.transfer_details_label.add_css_class("dim-label")
        self.transfer_details_label.set_xalign(0)
        self.transfer_details_label.set_wrap(True)
        self.transfer_details_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        box.append(self.transfer_details_label)

        box.set_hexpand(True)
        frame.append(box)
        return frame

    @staticmethod
    def _parse_import_extensions(value):
        extensions = []
        for raw_value in (value or "").replace(",", " ").split():
            extension = raw_value.strip().casefold()
            if not extension:
                continue
            if not extension.startswith("."):
                extension = f".{extension}"
            suffix = extension[1:]
            if not suffix or not all(
                character.isalnum() or character in "._-"
                for character in suffix
            ):
                continue
            if extension not in extensions:
                extensions.append(extension)

        if not extensions:
            raise TransferError("Indique au moins une extension de fichier.")
        return extensions

    @staticmethod
    def _local_import_path(value, fallback):
        text = (value or "").strip() or fallback
        if "://" in text:
            raise TransferError("L’import vidéo utilise des chemins locaux.")
        return Path(os.path.abspath(os.path.expanduser(text)))

    def _update_import_button_tooltip(self):
        if not hasattr(self, "import_videos_button"):
            return
        settings = self.store.import_settings
        mode = "déplacer" if settings.get("mode") == "move" else "copier"
        self.import_videos_button.set_tooltip_text(
            "Import videos : "
            f"{mode} depuis {settings.get('source', '')} vers "
            f"{settings.get('destination', '')}"
        )

    def _show_import_preferences(self, *_args):
        if self.import_preferences_window is not None:
            self.import_preferences_window.present()
            return

        settings = default_import_settings()
        settings.update(self.store.import_settings)

        preferences = Adw.PreferencesDialog()
        preferences.set_title("Préférences")
        preferences.set_search_enabled(False)
        preferences.set_content_width(640)
        preferences.set_content_height(680)
        preferences.connect("closed", self._import_preferences_closed)

        page = Adw.PreferencesPage()
        page.set_title("Import vidéo")
        page.set_icon_name("folder-videos-symbolic")
        preferences.add(page)

        paths_group = Adw.PreferencesGroup()
        paths_group.set_title("Chemins")
        paths_group.set_description(
            "Les deux chemins sont locaux. Les boutons ouvrent le sélecteur de dossiers."
        )
        page.add(paths_group)

        source_row = Adw.EntryRow()
        source_row.set_title("Dossier source")
        source_row.set_text(settings["source"])
        source_button = self._icon_button(
            "folder-open-symbolic", "Choisir le dossier source"
        )
        source_button.set_valign(Gtk.Align.CENTER)
        source_button.connect(
            "clicked",
            self._browse_import_folder,
            source_row,
            "Choisir le dossier source",
        )
        source_row.add_suffix(source_button)
        paths_group.add(source_row)

        destination_row = Adw.EntryRow()
        destination_row.set_title("Dossier destination")
        destination_row.set_text(settings["destination"])
        destination_button = self._icon_button(
            "folder-open-symbolic", "Choisir le dossier destination"
        )
        destination_button.set_valign(Gtk.Align.CENTER)
        destination_button.connect(
            "clicked",
            self._browse_import_folder,
            destination_row,
            "Choisir le dossier destination",
        )
        destination_row.add_suffix(destination_button)
        paths_group.add(destination_row)

        behavior_group = Adw.PreferencesGroup()
        behavior_group.set_title("Comportement")
        page.add(behavior_group)

        mode_row = Adw.ComboRow()
        mode_row.set_title("Action")
        mode_row.set_subtitle("Déplacer retire les sources après une copie réussie.")
        mode_row.set_model(
            Gtk.StringList.new(["Déplacer les vidéos", "Copier les vidéos"])
        )
        mode_row.set_selected(0 if settings["mode"] == "move" else 1)
        behavior_group.add(mode_row)

        extensions_row = Adw.EntryRow()
        extensions_row.set_title("Extensions")
        extensions_row.set_text(settings["extensions"])
        extensions_row.set_tooltip_text(
            "Sépare les extensions par des espaces ou des virgules, par exemple .mp4, .mkv"
        )
        behavior_group.add(extensions_row)

        options_group = Adw.PreferencesGroup()
        options_group.set_title("Options")
        page.add(options_group)

        recursive_row = Adw.SwitchRow()
        recursive_row.set_title("Rechercher dans les sous-dossiers")
        recursive_row.set_subtitle(
            "Inclut les dossiers situés sous le dossier source."
        )
        recursive_row.set_active(bool(settings["recursive"]))
        options_group.add(recursive_row)

        cleanup_row = Adw.SwitchRow()
        cleanup_row.set_title("Nettoyer les dossiers vides")
        cleanup_row.set_subtitle(
            "Après un déplacement, remonte vers la source sans supprimer sa racine."
        )
        cleanup_row.set_active(bool(settings["cleanup_empty_dirs"]))
        options_group.add(cleanup_row)

        preserve_row = Adw.SwitchRow()
        preserve_row.set_title("Conserver le dossier VDH")
        preserve_row.set_subtitle(
            "Ne supprime jamais ~/Téléchargements/VDH pendant le nettoyage."
        )
        preserve_row.set_active(bool(settings["preserve_vdh"]))
        options_group.add(preserve_row)

        action_group = Adw.PreferencesGroup()
        action_group.set_description(
            "Les modifications sont appliquées lorsque tu appuies sur Enregistrer."
        )
        page.add(action_group)
        action_row = Adw.ActionRow()
        action_row.set_title("Configuration de l’import")
        action_row.set_subtitle("Fret réutilisera ces réglages au prochain lancement.")

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        buttons.set_valign(Gtk.Align.CENTER)
        reset_button = Gtk.Button(label="Réinitialiser")
        reset_button.add_css_class("flat")
        reset_button.connect("clicked", self._reset_import_settings)
        buttons.append(reset_button)
        save_button = Gtk.Button(label="Enregistrer")
        save_button.add_css_class("suggested-action")
        buttons.append(save_button)
        action_row.add_suffix(buttons)
        action_group.add(action_row)

        self._import_preferences_widgets = {
            "window": preferences,
            "source": source_row,
            "destination": destination_row,
            "mode": mode_row,
            "extensions": extensions_row,
            "recursive": recursive_row,
            "cleanup_empty_dirs": cleanup_row,
            "preserve_vdh": preserve_row,
        }
        save_button.connect("clicked", self._save_import_preferences)
        self.import_preferences_window = preferences
        preferences.present(self)

    def _import_preferences_closed(self, dialog, *_args):
        if dialog is self.import_preferences_window:
            self.import_preferences_window = None
            self._import_preferences_widgets = None

    def _browse_import_folder(self, _button, entry, title):
        if not hasattr(Gtk, "FileDialog"):
            self.toast("Cette version de GTK ne fournit pas le sélecteur de dossier.")
            return

        dialog = Gtk.FileDialog.new()
        dialog.set_title(title)
        current = entry.get_text().strip()
        try:
            initial = self._local_import_path(current, str(Path.home()))
            if hasattr(dialog, "set_initial_folder"):
                dialog.set_initial_folder(Gio.File.new_for_path(str(initial)))
        except (TransferError, GLib.Error, ValueError, TypeError):
            pass
        dialog.select_folder(
            self,
            None,
            self._browse_import_folder_finished,
            entry,
        )

    def _browse_import_folder_finished(self, dialog, result, entry):
        try:
            selected = dialog.select_folder_finish(result)
        except GLib.Error as error:
            if "cancel" not in error_text(error).lower():
                self.toast(f"Sélection impossible : {error_text(error)}")
            return
        if selected is not None and selected.get_path() is not None:
            entry.set_text(selected.get_path())

    def _save_import_preferences(self, *_args):
        widgets = self._import_preferences_widgets
        if not widgets:
            return

        source = widgets["source"].get_text().strip()
        destination = widgets["destination"].get_text().strip()
        if not source or not destination:
            self.toast("La source et la destination sont obligatoires.")
            return

        try:
            extensions = self._parse_import_extensions(
                widgets["extensions"].get_text()
            )
            self._local_import_path(source, source)
            self._local_import_path(destination, destination)
        except TransferError as error:
            self.toast(f"Configuration invalide : {error_text(error)}")
            return

        self.store.import_settings = {
            "source": source,
            "destination": destination,
            "mode": "copy" if widgets["mode"].get_selected() == 1 else "move",
            "extensions": ", ".join(extensions),
            "recursive": widgets["recursive"].get_active(),
            "cleanup_empty_dirs": widgets["cleanup_empty_dirs"].get_active(),
            "preserve_vdh": widgets["preserve_vdh"].get_active(),
        }
        self.store.save()
        self._update_import_button_tooltip()
        widgets["window"].close()
        self.toast("Configuration de l’import enregistrée.")

    def _reset_import_settings(self, *_args):
        self.store.import_settings = default_import_settings()
        self.store.save()
        self._update_import_button_tooltip()
        if self.import_preferences_window is not None:
            self.import_preferences_window.close()
        self.toast("Configuration de l’import réinitialisée.")

    def _install_actions(self):
        about = Gio.SimpleAction.new("about", None)
        about.connect("activate", lambda *_: self._show_about())
        self.add_action(about)

        open_location = Gio.SimpleAction.new(
            "open-location", GLib.VariantType.new("s")
        )
        open_location.connect("activate", self._open_location_action)
        self.add_action(open_location)

        configure_import = Gio.SimpleAction.new("configure-import", None)
        configure_import.connect("activate", self._show_import_preferences)
        self.add_action(configure_import)

        reset_import = Gio.SimpleAction.new("reset-import", None)
        reset_import.connect("activate", self._reset_import_settings)
        self.add_action(reset_import)

        self.import_videos_action = Gio.SimpleAction.new("import-videos", None)
        self.import_videos_action.connect("activate", self._import_videos)
        self.add_action(self.import_videos_action)

        refresh = Gio.SimpleAction.new("refresh", None)
        refresh.connect(
            "activate", lambda *_: (self.active_pane or self.left_pane).refresh()
        )
        self.add_action(refresh)

        swap = Gio.SimpleAction.new("swap-panes", None)
        swap.connect("activate", lambda *_: self.swap_panes())
        self.add_action(swap)

        self.transfer_profile_action = Gio.SimpleAction.new_stateful(
            "transfer-profile",
            GLib.VariantType.new("s"),
            GLib.Variant.new_string("auto"),
        )
        self.transfer_profile_action.connect(
            "change-state", self._transfer_profile_changed
        )
        self.add_action(self.transfer_profile_action)

        eject = Gio.SimpleAction.new("eject", GLib.VariantType.new("s"))
        eject.connect("activate", self._eject_action)
        self.add_action(eject)

        privacy = Gio.SimpleAction.new("toggle-privacy", None)
        privacy.connect("activate", self._toggle_privacy_mode)
        self.add_action(privacy)

        show_hidden = Gio.SimpleAction.new_stateful(
            "show-hidden", None, GLib.Variant.new_boolean(self.show_hidden)
        )
        show_hidden.connect("change-state", self._show_hidden_state_changed)
        self.add_action(show_hidden)

        shortcuts = Gio.SimpleAction.new("show-help-overlay", None)
        shortcuts.connect("activate", lambda *_: self._show_shortcuts())
        self.add_action(shortcuts)

        key_controller = Gtk.EventControllerKey()
        key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_controller.connect("key-pressed", self._key_pressed)
        self.add_controller(key_controller)

    def _show_hidden_state_changed(self, action, value):
        action.set_state(value)
        self._set_show_hidden(value.get_boolean())

    def _show_shortcuts(self):
        if not hasattr(Adw, "ShortcutsDialog"):
            self.toast("Cette version de libadwaita ne fournit pas la fenêtre des raccourcis.")
            return
        shortcuts = Adw.ShortcutsDialog()
        for title, items in (
            (
                "Général",
                (
                    ("Préférences", "<Control>comma"),
                    ("Raccourcis clavier", "<Control>question"),
                    ("Afficher les fichiers cachés", "<Control>h"),
                    ("Masquer ou afficher l’interface", "<Control><Shift>h"),
                    ("Permuter les emplacements", "<Control>t"),
                    ("Importer les vidéos", "<Control>i"),
                    ("Quitter", "<Control>q"),
                ),
            ),
            (
                "Fichiers",
                (
                    ("Tout sélectionner", "<Control>a"),
                    ("Copier la sélection", "<Control>c"),
                    ("Couper la sélection", "<Control>x"),
                    ("Coller ici", "<Control>v"),
                    ("Actualiser", "F5"),
                ),
            ),
        ):
            section = Adw.ShortcutsSection.new(title)
            for label, accelerator in items:
                section.add(Adw.ShortcutsItem.new(label, accelerator))
            shortcuts.add(section)
        self.shortcuts_dialog = shortcuts
        shortcuts.present(self)

    def _key_pressed(self, _controller, keyval, _keycode, state):
        focus = self.get_focus()
        if isinstance(focus, Gtk.Entry):
            return False

        if not state & Gdk.ModifierType.CONTROL_MASK:
            return False

        key = Gdk.keyval_to_lower(keyval)
        pane = self.active_pane or self.left_pane
        if key == Gdk.KEY_a:
            pane.toggle_select_all()
            return True
        if key == Gdk.KEY_c:
            pane.copy_selected()
            return True
        if key == Gdk.KEY_x:
            pane.cut_selected()
            return True
        if key == Gdk.KEY_v:
            pane.paste_here()
            return True
        return False

    def _show_about(self):
        about = Adw.AboutDialog.new()
        about.set_application_name(APP_NAME)
        about.set_application_icon(APP_ID)
        about.set_version("0.2.0")
        about.set_developer_name("Fret maintainer")
        about.set_comments(
            "Un mini gestionnaire de fichiers libadwaita à deux emplacements, "
            "avec transferts locaux et GVfs."
        )
        about.present(self)

    def set_active_pane(self, pane):
        self.active_pane = pane
        for candidate in getattr(self, "panes", []):
            candidate.remove_css_class("active-panel")
        if pane is not None:
            pane.add_css_class("active-panel")
        if getattr(self, "profile_button", None) is not None:
            self._update_profile_pill()

    def other_pane(self, pane):
        return self.right_pane if pane is self.left_pane else self.left_pane

    def toast(self, message):
        if self.toast_overlay is not None:
            self.toast_overlay.add_toast(Adw.Toast.new(message))

    def set_clipboard(self, items, mode, source_pane):
        self.clipboard_items = [item.file for item in items]
        self.clipboard_mode = mode
        self.clipboard_source = source_pane
        self._update_action_buttons()

    def _update_action_buttons(self):
        for pane in getattr(self, "panes", []):
            pane._update_transfer_buttons()

    def _update_paste_buttons(self):
        """Compatibilité interne pour les appels issus de l’ancien presse-papiers."""

        self._update_action_buttons()

    def transfer_selected_to_adjacent(self, source_pane, mode):
        destination_pane = self.other_pane(source_pane)
        if not source_pane.location_ready:
            self.toast("L’emplacement source n’est pas disponible.")
            return
        if not destination_pane.location_ready or destination_pane.location_file is None:
            self.toast("L’emplacement du panneau adjacent n’est pas disponible.")
            return

        items = source_pane._effective_selected_items()
        if not items:
            self.toast("Sélectionne au moins un élément.")
            return

        destination = destination_pane.location_file
        sources = [item.file for item in items]
        for source in sources:
            parent = source.get_parent()
            if parent is not None and same_location(parent, destination):
                self.toast("La source et la destination sont identiques.")
                return
            if is_same_or_descendant(destination, source):
                self.toast("Impossible de transférer un dossier vers lui-même.")
                return

        self._start_transfer(sources, destination, mode, clear_clipboard=False)

    def _start_transfer(self, sources, destination, mode, clear_clipboard=True):
        job = self._make_job(
            list(sources),
            destination,
            mode,
            clear_clipboard=clear_clipboard,
        )
        self._submit_job(job)

    # -- File d'attente --------------------------------------------------

    def _profile_for_device(self, device):
        forced = self.store.transfer_profiles.get(device["key"])
        return forced if forced in TRANSFER_PROFILES else device["kind"]

    def _make_job(self, sources, destination, mode, **kwargs):
        device = detect_device(destination)
        return TransferJob(
            sources,
            destination,
            mode,
            self._job_finished,
            on_item_changed=self._transfer_item_changed,
            on_conflict=self._ask_transfer_conflict,
            device=device,
            profile_key=self._profile_for_device(device),
            **kwargs,
        )

    def _active_job_stopped(self):
        return (
            self.active_job is not None
            and self.active_job.snapshot()["state"] == "stopped"
        )

    def _submit_job(self, job):
        """Lance le transfert, ou le met en file s'il y en a déjà un."""

        if self._job_is_active() or (self._active_job_stopped() and self.transfer_queue):
            self.transfer_queue.append(job)
            self._rebuild_queue_ui()
            count = len(self.transfer_queue)
            self.toast(
                "Ajouté à la file d’attente"
                + (f" ({count} en attente)." if count > 1 else ".")
            )
            self._update_action_buttons()
            return
        self._run_job(job)

    def _run_job(self, job):
        self.active_job = job
        self._update_action_buttons()
        self._update_profile_pill()
        self._rebuild_queue_ui()
        self._refresh_transfer_ui()
        threading.Thread(target=job.run, name="fret-transfer", daemon=True).start()

    def _start_next_queued(self):
        if not self.transfer_queue:
            return False
        self._run_job(self.transfer_queue.pop(0))
        return True

    def _skip_to_next(self, *_args):
        self.queue_popover.popdown()
        if self._job_is_active():
            return
        self._start_next_queued()

    def _remove_queued(self, _button, job):
        if job in self.transfer_queue:
            self.transfer_queue.remove(job)
        self._rebuild_queue_ui()
        self._process_pending_ejects()

    @staticmethod
    def _job_title(job):
        verb = "Déplacement" if job.mode == "move" else "Copie"
        if len(job.sources) == 1:
            name = job.sources[0].get_basename() or "élément"
            return f"{verb} de « {name} »"
        return f"{verb} de {len(job.sources)} éléments"

    def _rebuild_queue_ui(self):
        count = len(self.transfer_queue)
        self.queue_count_label.set_text(str(count))
        self.queue_button.set_visible(count > 0)
        self.queue_button.set_tooltip_text(
            f"{count} transfert en attente" if count == 1 else f"{count} transferts en attente"
        )

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(6)
        box.set_margin_end(6)
        header = Gtk.Label(label="En attente")
        header.add_css_class("heading")
        header.set_xalign(0)
        box.append(header)

        if self._active_job_stopped() and count:
            skip = Gtk.Button(label="Abandonner l’arrêté et passer au suivant")
            skip.add_css_class("suggested-action")
            skip.connect("clicked", self._skip_to_next)
            box.append(skip)

        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.add_css_class("boxed-list")
        for job in self.transfer_queue:
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row_box.add_css_class("queue-row")
            icon = Gtk.Image.new_from_gicon(
                themed_icon(TRANSFER_PROFILES[job.profile_key]["icons"])
            )
            row_box.append(icon)
            texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            texts.set_hexpand(True)
            title = Gtk.Label(label=self._job_title(job))
            title.set_xalign(0)
            title.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
            title.set_max_width_chars(36)
            texts.append(title)
            subtitle = Gtk.Label(label=f"vers {location_to_text(job.destination)}")
            subtitle.add_css_class("dim-label")
            subtitle.add_css_class("caption")
            subtitle.set_xalign(0)
            subtitle.set_ellipsize(Pango.EllipsizeMode.START)
            subtitle.set_max_width_chars(36)
            texts.append(subtitle)
            row_box.append(texts)
            remove = Gtk.Button.new_from_icon_name("window-close-symbolic")
            remove.add_css_class("flat")
            remove.add_css_class("circular")
            remove.set_valign(Gtk.Align.CENTER)
            remove.set_tooltip_text("Retirer de la file")
            remove.connect("clicked", self._remove_queued, job)
            row_box.append(remove)
            listbox.append(row_box)
        box.append(listbox)
        self.queue_popover.set_child(box)
        if not count:
            self.queue_popover.popdown()

    # -- Réglage de transfert (pastille) -----------------------------------

    def _current_profile_device(self):
        if self._job_is_active():
            return self.active_job.device
        pane = self.active_pane or getattr(self, "left_pane", None)
        if pane is None:
            return None
        destination = self.other_pane(pane).location_file
        if destination is None:
            return None
        return detect_device(destination)

    def _update_profile_pill(self):
        if getattr(self, "profile_button", None) is None:
            return
        device = self._current_profile_device()
        self._profile_context = device
        if device is None:
            self.profile_button.set_visible(False)
            return
        self.profile_button.set_visible(True)

        forced = self.store.transfer_profiles.get(device["key"])
        if forced not in TRANSFER_PROFILES:
            forced = None
        profile_key = forced or device["kind"]
        profile = TRANSFER_PROFILES[profile_key]
        self.profile_icon.set_from_gicon(themed_icon(profile["icons"]))
        how = "choisi manuellement" if forced else "détecté automatiquement"
        accessible_label = (
            f"Réglage de transfert pour {device['name']} : {profile['label']}"
        )
        self.profile_button.update_property(
            [Gtk.AccessibleProperty.LABEL], [accessible_label]
        )
        self.profile_button.set_tooltip_text(
            f"Réglage pour « {device['name']} » : {profile['label']} ({how}).\n"
            f"{profile['description']}"
        )
        self.transfer_profile_action.set_state(
            GLib.Variant.new_string(forced or "auto")
        )

        menu = Gio.Menu()
        auto_section = Gio.Menu()
        detected = TRANSFER_PROFILES[device["kind"]]["label"]
        item = Gio.MenuItem.new(f"Automatique ({detected})", None)
        item.set_action_and_target_value(
            "win.transfer-profile", GLib.Variant.new_string("auto")
        )
        auto_section.append_item(item)
        menu.append_section(f"Réglage pour « {device['name']} »", auto_section)
        manual_section = Gio.Menu()
        for key in TRANSFER_PROFILE_ORDER:
            item = Gio.MenuItem.new(TRANSFER_PROFILES[key]["label"], None)
            item.set_action_and_target_value(
                "win.transfer-profile", GLib.Variant.new_string(key)
            )
            manual_section.append_item(item)
        menu.append_section(None, manual_section)
        self.profile_button.set_menu_model(menu)

    def _transfer_profile_changed(self, action, value):
        device = self._profile_context
        if device is None:
            return
        choice = value.get_string()
        if choice == "auto":
            self.store.transfer_profiles.pop(device["key"], None)
        elif choice in TRANSFER_PROFILES:
            self.store.transfer_profiles[device["key"]] = choice
        else:
            return
        self.store.save()
        action.set_state(value)

        profile_key = self._profile_for_device(device)
        jobs = list(self.transfer_queue)
        if self.active_job is not None:
            jobs.append(self.active_job)
        for job in jobs:
            if job.device.get("key") == device["key"]:
                job.set_profile(profile_key)
        self._update_profile_pill()
        self._rebuild_queue_ui()
        self.toast(
            f"« {device['name']} » : réglage {TRANSFER_PROFILES[profile_key]['label']}"
            + (" (automatique)." if choice == "auto" else " mémorisé.")
        )

    # -- Notification -------------------------------------------------------

    def _notify_finished(self, state):
        if self.is_active():
            return
        application = self.get_application()
        if application is None:
            return
        title = "Transfert Fret interrompu" if state == "error" else "Transfert Fret terminé"
        notification = Gio.Notification.new(title)
        application.send_notification("fret-transfer", notification)

    def _window_activity_changed(self, *_args):
        if self.is_active() and self.get_application() is not None:
            self.get_application().withdraw_notification("fret-transfer")

    # -- Supports amovibles et éjection ---------------------------------------

    def _setup_volume_monitor(self):
        self.volume_monitor = Gio.VolumeMonitor.get()
        self.volume_monitor.connect("mount-added", self._mounts_changed)
        self.volume_monitor.connect("mount-changed", self._mounts_changed)
        self.volume_monitor.connect("mount-removed", self._mount_removed)
        self._update_eject_button()

    def _ejectable_mounts(self):
        mounts = []
        if self.volume_monitor is None:
            return mounts
        for mount in self.volume_monitor.get_mounts():
            try:
                if mount.is_shadowed():
                    continue
                drive = mount.get_drive()
                if drive is None:
                    continue  # partages réseau, montages sans disque
                if mount.can_eject() or drive.can_eject() or drive.is_removable():
                    mounts.append(mount)
            except GLib.Error:
                continue
        return mounts

    def _mount_by_uri(self, uri):
        for mount in self._ejectable_mounts():
            if mount.get_root().get_uri() == uri:
                return mount
        return None

    def _mounts_changed(self, *_args):
        self._update_eject_button()
        self._update_profile_pill()

    def _mount_removed(self, _monitor, mount):
        root = mount.get_root()
        self._pending_ejects.discard(root.get_uri())
        home = Gio.File.new_for_path(os.path.expanduser("~"))
        for pane in getattr(self, "panes", []):
            if pane.location_file is not None and is_same_or_descendant(
                pane.location_file, root
            ):
                pane.load_location(file_object=home)
        self._mounts_changed()

    def _update_eject_button(self):
        mounts = self._ejectable_mounts()
        if not mounts:
            self.eject_button.set_visible(False)
            self.eject_menu_button.set_visible(False)
            return
        if len(mounts) == 1:
            mount = mounts[0]
            self.eject_button.set_action_name("win.eject")
            self.eject_button.set_action_target_value(
                GLib.Variant.new_string(mount.get_root().get_uri())
            )
            self.eject_button.set_tooltip_text(f"Éjecter « {mount.get_name()} »")
            self.eject_button.set_visible(True)
            self.eject_menu_button.set_visible(False)
            return
        menu = Gio.Menu()
        section = Gio.Menu()
        for mount in mounts:
            item = Gio.MenuItem.new(f"Éjecter « {mount.get_name()} »", None)
            item.set_action_and_target_value(
                "win.eject", GLib.Variant.new_string(mount.get_root().get_uri())
            )
            section.append_item(item)
        menu.append_section(None, section)
        self.eject_menu_button.set_menu_model(menu)
        self.eject_button.set_visible(False)
        self.eject_menu_button.set_visible(True)

    def _transfer_uses_root(self, root):
        jobs = list(self.transfer_queue)
        if self._job_is_active():
            jobs.append(self.active_job)
        for job in jobs:
            for location in (job.destination, *job.sources):
                if is_same_or_descendant(location, root):
                    return True
        return False

    def _eject_action(self, _action, parameter):
        uri = parameter.get_string()
        mount = self._mount_by_uri(uri)
        if mount is None:
            self.toast("Ce support n’est plus branché.")
            return
        name = mount.get_name()
        if self._transfer_uses_root(mount.get_root()):
            self._pending_ejects.add(uri)
            self.toast(f"« {name} » sera éjecté à la fin du transfert.")
            return
        self._eject_mount(mount)

    def _process_pending_ejects(self):
        for uri in list(self._pending_ejects):
            mount = self._mount_by_uri(uri)
            if mount is None:
                self._pending_ejects.discard(uri)
                continue
            if self._transfer_uses_root(mount.get_root()):
                continue
            self._pending_ejects.discard(uri)
            self._eject_mount(mount)

    def _eject_mount(self, mount):
        name = mount.get_name()
        root = mount.get_root()
        home = Gio.File.new_for_path(os.path.expanduser("~"))
        for pane in getattr(self, "panes", []):
            if pane.location_file is not None and is_same_or_descendant(
                pane.location_file, root
            ):
                pane.load_location(file_object=home)
        self.toast(f"Écriture des dernières données sur « {name} »…")
        operation = Gtk.MountOperation.new(self)
        flags = Gio.MountUnmountFlags.NONE
        if mount.can_eject():
            mount.eject_with_operation(
                flags, operation, None, self._eject_finished, ("eject", name)
            )
        else:
            mount.unmount_with_operation(
                flags, operation, None, self._eject_finished, ("unmount", name)
            )

    def _eject_finished(self, mount, result, data):
        how, name = data
        try:
            if how == "eject":
                mount.eject_with_operation_finish(result)
            else:
                mount.unmount_with_operation_finish(result)
        except GLib.Error as error:
            if error.matches(Gio.io_error_quark(), Gio.IOErrorEnum.FAILED_HANDLED):
                return
            self.toast(f"Impossible d’éjecter « {name} » : {error.message}")
            return
        self.toast(f"Tu peux retirer « {name} ».")

    def swap_panes(self):
        left_location = self.left_pane.location_file
        right_location = self.right_pane.location_file
        if left_location is not None and right_location is not None:
            self.left_pane.load_location(file_object=right_location)
            self.right_pane.load_location(file_object=left_location)
            self.toast("Emplacements permutés.")

    def _import_videos(self, *_args):
        if self._video_scan_busy:
            return

        settings = default_import_settings()
        settings.update(self.store.import_settings)
        try:
            source = self._local_import_path(
                settings.get("source"), str(Path.home() / VIDEO_SOURCE_DIR_NAME)
            )
            destination = self._local_import_path(
                settings.get("destination"),
                str(Path.home() / VIDEO_DESTINATION_DIR_NAME / ".DEV"),
            )
            extensions = self._parse_import_extensions(settings.get("extensions"))
        except TransferError as error:
            self.toast(f"Import videos impossible : {error_text(error)}")
            return

        source_text = os.path.abspath(str(source))
        destination_text = os.path.abspath(str(destination))
        if destination_text == source_text or destination_text.startswith(
            source_text + os.sep
        ):
            self.toast(
                "La destination ne peut pas être le dossier source ou l’un de ses sous-dossiers."
            )
            return

        mode = settings.get("mode") if settings.get("mode") in ("move", "copy") else "move"
        preserve = source / "VDH" if settings.get("preserve_vdh", True) else None
        cleanup_empty_dirs = bool(settings.get("cleanup_empty_dirs", True))
        if mode != "move":
            cleanup_empty_dirs = False

        self._video_scan_busy = True
        self._video_scan_details = f"Analyse de {source} vers {destination}…"
        self._refresh_transfer_ui()
        threading.Thread(
            target=self._scan_video_files_worker,
            args=(
                source,
                destination,
                mode,
                extensions,
                bool(settings.get("recursive", True)),
                cleanup_empty_dirs,
                preserve,
            ),
            name="fret-video-scan",
            daemon=True,
        ).start()

    def _scan_video_files_worker(
        self,
        source,
        destination,
        mode,
        extensions,
        recursive,
        cleanup_empty_dirs,
        preserve,
    ):
        try:
            if not source.is_dir():
                raise TransferError(f"Le dossier source n’existe pas : {source}")

            paths = []
            cleanup_dirs = set()

            def add_video(path):
                if path.suffix.casefold() not in extensions:
                    return
                if path.is_symlink() or not path.is_file():
                    return
                paths.append(str(path))
                cleanup_dirs.add(str(path.parent))

            if recursive:
                for root, dirs, filenames in os.walk(
                    source, topdown=True, followlinks=False
                ):
                    dirs[:] = sorted(
                        name
                        for name in dirs
                        if not os.path.islink(os.path.join(root, name))
                    )
                    for filename in sorted(filenames, key=str.casefold):
                        add_video(Path(root) / filename)
            else:
                entries = sorted(source.iterdir(), key=lambda path: path.name.casefold())
                for path in entries:
                    if path.is_file() or path.is_symlink():
                        add_video(path)

            paths.sort(key=str.casefold)
            if not cleanup_empty_dirs:
                cleanup_dirs.clear()

            GLib.idle_add(
                self._video_scan_finished,
                paths,
                str(source),
                str(destination),
                str(preserve) if preserve else "",
                sorted(cleanup_dirs),
                mode,
                "",
            )
        except Exception as error:  # noqa: BLE001 — affiché dans l’interface
            GLib.idle_add(
                self._video_scan_finished,
                [],
                str(source),
                str(destination),
                str(preserve) if preserve else "",
                [],
                mode,
                error_text(error),
            )

    def _video_scan_finished(
        self, paths, source, destination, preserve, cleanup_dirs, mode, error
    ):
        self._video_scan_busy = False
        self._video_scan_details = ""
        if error:
            self.active_job = None
            self._refresh_transfer_ui()
            self.toast(f"Import videos impossible : {error}")
            return False

        if not paths:
            self.active_job = None
            self._refresh_transfer_ui()
            self.toast(f"Aucune vidéo trouvée dans ~/{VIDEO_SOURCE_DIR_NAME}.")
            return False

        destination_path = Path(destination)
        try:
            destination_path.mkdir(parents=True, exist_ok=True)
        except OSError as mkdir_error:
            self.active_job = None
            self._refresh_transfer_ui()
            self.toast(f"Destination inaccessible : {error_text(mkdir_error)}")
            return False

        sources = [Gio.File.new_for_path(path) for path in paths]
        job = self._make_job(
            sources,
            Gio.File.new_for_path(destination),
            mode,
            cleanup_dirs=cleanup_dirs,
            cleanup_root=source if cleanup_dirs else None,
            preserve_dir=preserve or None,
            completion_message="Import videos terminé.",
            clear_clipboard=False,
        )
        self._submit_job(job)
        return False

    def _job_is_active(self):
        return self.active_job is not None and self.active_job.snapshot()["state"] in (
            "preparing",
            "running",
            "paused",
            "waiting",
            "stopping",
            "finalizing",
            "flushing",
        )

    def mark_transfer_sources_deleted(self, source_uris):
        job = self.active_job
        if job is not None and source_uris:
            job.mark_sources_deleted(source_uris)

    def _queue_transfer_refresh(self, pane):
        if pane._delete_busy or pane in self._queued_transfer_panes:
            return
        self._queued_transfer_panes.add(pane)
        GLib.timeout_add(120, self._flush_transfer_refresh, pane)

    def _flush_transfer_refresh(self, pane):
        self._queued_transfer_panes.discard(pane)
        if not pane._delete_busy and pane.location_file is not None:
            pane.refresh()
        return False

    def _transfer_item_changed(self, job, entry, _status):
        if job is not self.active_job:
            return False

        source_parent = entry.source.get_parent()
        target_parent = entry.target.get_parent()
        for pane in (self.left_pane, self.right_pane):
            if (
                source_parent is not None
                and same_location(pane.location_file, source_parent)
            ) or (
                target_parent is not None
                and same_location(pane.location_file, target_parent)
            ):
                self._queue_transfer_refresh(pane)
        return False

    def _ask_transfer_conflict(self, job, entry, request):
        if job is not self.active_job or job.stop_event.is_set():
            request["response"] = "cancel"
            request["event"].set()
            return False

        basename = entry.target.get_basename() or entry.source.get_basename() or "fichier"
        if request["conflict_kind"] == "file":
            title = "Un fichier existe déjà"
            body = f"« {basename} » existe déjà comme fichier dans la destination."
        elif request["conflict_kind"] == "directory":
            title = "Un dossier existe déjà"
            body = (
                f"« {basename} » existe déjà comme dossier dans la destination. "
                "Fusionner conserve le dossier existant; les éléments de même nom "
                "à l’intérieur feront l’objet de leur propre choix."
            )
        else:
            title = "Le type de destination est différent"
            source_type = "dossier" if request["source_is_dir"] else "fichier"
            target_type = (
                "dossier"
                if request["target_is_dir"]
                else "fichier"
                if request["target_is_file"]
                else "élément spécial"
            )
            body = (
                f"« {basename} » est un {target_type} dans la destination, "
                f"alors que la source est un {source_type}. "
                "Le remplacement est désactivé pour éviter de supprimer un contenu."
            )
        dialog = Adw.AlertDialog.new(title, body)
        dialog.add_response("cancel", "Annuler")
        dialog.add_response("rename", "Renommer")
        suggested = getattr(Adw.ResponseAppearance, "SUGGESTED", None)
        if "replace" in request["allowed_responses"]:
            dialog.add_response("replace", "Remplacer")
            if suggested is not None:
                dialog.set_response_appearance("replace", suggested)
        if "merge" in request["allowed_responses"]:
            dialog.add_response("merge", "Fusionner")
            if suggested is not None:
                dialog.set_response_appearance("merge", suggested)
        dialog.set_default_response(
            {
                "file": "replace",
                "directory": "merge",
            }.get(request["conflict_kind"], "cancel")
        )
        dialog.set_close_response("cancel")

        apply_all = Gtk.CheckButton(label="Appliquer à tous les fichiers et dossiers")
        apply_all.set_tooltip_text(
            "Le choix s’applique aux conflits où cette action est possible; "
            "les autres types nécessitent un choix distinct."
        )
        dialog.set_extra_child(apply_all)
        dialog.connect(
            "response",
            self._transfer_conflict_response,
            job,
            request,
            apply_all,
        )
        dialog.present(self)
        return False

    @staticmethod
    def _transfer_conflict_response(_dialog, response, job, request, apply_all):
        if job.stop_event.is_set():
            response = "cancel"
        if response not in request["allowed_responses"]:
            response = "cancel"
        request["response"] = response
        request["apply_all"] = (
            response in request["allowed_responses"] and apply_all.get_active()
        )
        request["event"].set()

    def paste_into(self, destination_pane):
        if not self.clipboard_items:
            self.toast("Rien à coller.")
            return
        if destination_pane.location_file is None or not destination_pane.location_ready:
            self.toast("L’emplacement de destination n’est pas disponible.")
            return

        destination = destination_pane.location_file
        for source in self.clipboard_items:
            parent = source.get_parent()
            if parent is not None and same_location(parent, destination):
                self.toast("La source et la destination sont identiques.")
                return
            if is_same_or_descendant(destination, source):
                self.toast("Impossible de transférer un dossier vers lui-même.")
                return

        self._start_transfer(list(self.clipboard_items), destination, self.clipboard_mode)

    def _pause_or_resume(self, *_args):
        job = self.active_job
        if job is None:
            return
        state = job.snapshot()["state"]
        if state == "running":
            job.request_pause()
        elif state == "paused":
            job.request_resume()
        elif state == "stopped":
            job.stop_event.clear()
            job.pause_event.set()
            job.set_state("running")
            threading.Thread(target=job.run, daemon=True).start()

    def _stop_transfer(self, *_args):
        if self.active_job is not None:
            self.active_job.request_stop()

    def _job_finished(self, job):
        if job is not self.active_job:
            return False

        state = job.snapshot()["state"]
        if state == "done":
            self.toast(job.completion_message)
            self.left_pane.refresh()
            self.right_pane.refresh()
            if job.mode == "move" and job.clear_clipboard:
                self.clipboard_items = []
                self.clipboard_source = None
                self._update_paste_buttons()
        elif state == "warning":
            self.toast(job.error or "Transfert terminé avec avertissement.")
            if job.failed_files or job.renamed_names:
                self._show_transfer_report(job)
            self.left_pane.refresh()
            self.right_pane.refresh()
            if job.mode == "move" and job.clear_clipboard and not job.move_errors and not job.failed_files:
                self.clipboard_items = []
                self.clipboard_source = None
                self._update_paste_buttons()
        elif state == "error":
            self.toast(f"Transfert interrompu : {job.error}" if job.error else "Transfert interrompu.")
            self.left_pane.refresh()
            self.right_pane.refresh()

        if state in ("done", "warning", "error"):
            if not self._start_next_queued():
                self._notify_finished(state)
            self._process_pending_ejects()
        self._rebuild_queue_ui()
        self._update_profile_pill()
        self._refresh_transfer_ui()
        return False

    def _show_transfer_report(self, job):
        """Liste, en fin de transfert, les éléments en échec et les noms adaptés."""

        sections = []
        skipped_children = getattr(job, "skipped_children", 0)
        if job.failed_files:
            lines = [f"• {name}\n   {message}" for name, message in job.failed_files]
            if skipped_children:
                lines.append(f"({skipped_children} fichier(s) ignoré(s) car leur dossier n’a pas pu être créé)")
            sections.append(
                f"Non copiés ({len(job.failed_files)})\n" + "\n".join(lines)
            )
        if job.renamed_names:
            lines = [f"• {item}" for item in job.renamed_names]
            sections.append(
                f"Noms adaptés à la destination ({len(job.renamed_names)})\n" + "\n".join(lines)
            )
        report = "\n\n".join(sections)

        title = (
            "Certains éléments n’ont pas pu être copiés"
            if job.failed_files
            else "Noms adaptés à la destination"
        )
        dialog = Adw.AlertDialog.new(title, None)

        label = Gtk.Label(label=report)
        label.set_selectable(True)
        label.set_wrap(True)
        label.set_xalign(0)
        label.set_margin_top(6)
        label.set_margin_bottom(6)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(160)
        scrolled.set_max_content_height(360)
        scrolled.set_min_content_width(420)
        scrolled.set_propagate_natural_height(True)
        scrolled.set_child(label)
        dialog.set_extra_child(scrolled)

        dialog.add_response("copy", "Copier la liste")
        dialog.add_response("close", "Fermer")
        dialog.set_default_response("close")
        dialog.set_close_response("close")

        def on_response(_dialog, response):
            if response == "copy":
                self.get_clipboard().set(report)

        dialog.connect("response", on_response)
        dialog.present(self)

    def _refresh_transfer_ui(self):
        self._update_action_buttons()
        self.transfer_file_row.set_visible(False)
        self.transfer_file_number_label.set_text("")
        self.transfer_filename_label.set_text("")
        self.transfer_filename_label.set_tooltip_text(None)
        if self._video_scan_busy:
            self.transfer_progress.set_fraction(0)
            self.transfer_progress_label.set_text("—")
            self.transfer_speed_label.set_text("—")
            self.transfer_eta_label.set_text("Temps restant total : —")
            self.transfer_bytes_label.set_text("Données transférées : — / —")
            self.transfer_status_label.set_text("Recherche des vidéos…")
            self.transfer_details_label.set_text(
                self._video_scan_details or f"Analyse de ~/{VIDEO_SOURCE_DIR_NAME}…"
            )
            self.transfer_pause_button.set_sensitive(False)
            self.transfer_stop_button.set_sensitive(False)
            self.import_videos_button.set_sensitive(False)
            return True

        job = self.active_job
        if job is None:
            self.transfer_progress.set_fraction(0)
            self.transfer_progress_label.set_text("—")
            self.transfer_speed_label.set_text("—")
            self.transfer_eta_label.set_text("Temps restant total : —")
            self.transfer_bytes_label.set_text("Données transférées : — / —")
            self.transfer_status_label.set_text("Aucun transfert en cours")
            self.transfer_details_label.set_text(
                "Sélectionner des fichiers, puis choisir Copier ou Déplacer vers l’autre panneau."
            )
            self.transfer_pause_button.set_sensitive(False)
            self.transfer_stop_button.set_sensitive(False)
            self.import_videos_button.set_sensitive(True)
            return True

        data = job.snapshot()
        state = data["state"]
        self.transfer_progress.set_fraction(data["fraction"])
        self.transfer_progress_label.set_text(f"{round(data['fraction'] * 100):d} %")
        self.transfer_speed_label.set_text(format_speed(data["speed"]))
        if data["remaining_seconds"] is None:
            eta = "Calcul…" if state == "running" and data["done_bytes"] < data["total_bytes"] else "—"
        else:
            eta = format_duration(data["remaining_seconds"])
        self.transfer_eta_label.set_text(f"Temps restant total : {eta}")
        self.transfer_bytes_label.set_text(
            "Données transférées : "
            f"{format_bytes(data['done_bytes'])} / {format_bytes(data['total_bytes'])}"
        )

        kind = "Déplacement" if job.mode == "move" else "Copie"
        state_labels = {
            "preparing": "Préparation du transfert…",
            "running": f"{kind} en cours",
            "paused": f"{kind} en pause",
            "waiting": "Choix requis pour un doublon",
            "stopping": "Arrêt du transfert…",
            "stopped": "Déplacement arrêté" if job.mode == "move" else "Copie arrêtée",
            "finalizing": "Finalisation du déplacement…",
            "flushing": (
                f"Écriture des données sur « {job.device.get('name', 'le support')} »…"
            ),
            "done": "Déplacement terminé" if job.mode == "move" else "Copie terminée",
            "warning": (
                "Déplacement terminé avec avertissement"
                if job.mode == "move"
                else "Copie terminée avec avertissement"
            ),
            "error": (
                "Déplacement interrompu"
                if job.mode == "move"
                else "Copie interrompue"
            ),
        }
        self.transfer_status_label.set_text(state_labels.get(state, "Transfert"))

        if state == "preparing":
            details = f"Analyse : {data['prepare_name']}"
        elif state == "flushing":
            details = "Les dernières données sont écrites sur le support. Plus que quelques instants."
        elif data["current_name"]:
            filename = os.path.basename(data["current_name"])
            self.transfer_file_number_label.set_text(
                f"{data['current_number']}/{data['total_files']} :"
            )
            self.transfer_filename_label.set_text(filename)
            self.transfer_filename_label.set_tooltip_text(filename)
            self.transfer_file_row.set_visible(True)
            remaining_bytes = max(0, data["current_size"] - data["current_done"])
            if state == "running" and data["speed"] > 0:
                file_eta = format_duration(remaining_bytes / data["speed"])
            elif state == "running" and remaining_bytes:
                file_eta = "Calcul…"
            else:
                file_eta = "—"
            details = (
                f"Temps restant pour ce fichier : {file_eta} · "
                f"{format_bytes(data['current_done'])} / {format_bytes(data['current_size'])} · "
                f"{data['remaining']} restant(s)"
            )
        elif data["total_files"]:
            details = (
                f"{data['current_number']}/{data['total_files']} fichier(s) traité(s) · "
                f"{data['remaining']} restant(s)"
            )
        else:
            details = "Aucun fichier à transférer"
        if state == "error" and data["error"]:
            details = data["error"]
        elif state == "warning" and data["error"]:
            details = data["error"]
            if data["missing_files"]:
                details += " · " + ", ".join(data["missing_files"][:2])
        if state == "stopped" and self.transfer_queue:
            waiting = len(self.transfer_queue)
            details += (
                f" · {waiting} en attente : reprends ce transfert "
                "ou passe au suivant depuis la file"
            )
        self.transfer_details_label.set_text(details)

        if state == "running":
            self.transfer_pause_button.set_icon_name("media-playback-pause-symbolic")
            self.transfer_pause_button.set_tooltip_text("Mettre en pause")
            self.transfer_pause_button.set_sensitive(True)
        elif state == "paused":
            self.transfer_pause_button.set_icon_name("media-playback-start-symbolic")
            self.transfer_pause_button.set_tooltip_text("Reprendre")
            self.transfer_pause_button.set_sensitive(True)
        elif state == "stopped":
            self.transfer_pause_button.set_icon_name("media-playback-start-symbolic")
            self.transfer_pause_button.set_tooltip_text("Reprendre")
            self.transfer_pause_button.set_sensitive(True)
        else:
            self.transfer_pause_button.set_icon_name("media-playback-pause-symbolic")
            self.transfer_pause_button.set_sensitive(False)

        self.transfer_stop_button.set_sensitive(
            state in ("preparing", "running", "paused", "waiting", "finalizing")
        )
        self.import_videos_button.set_sensitive(True)
        return True


class FretApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_startup(self):
        Adw.Application.do_startup(self)
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.quit())
        self.add_action(quit_action)
        for action, accels in (
            ("app.quit", ["<Control>q"]),
            ("win.configure-import", ["<Control>comma"]),
            ("win.show-help-overlay", ["<Control>question"]),
            ("win.toggle-privacy", ["<Control><Shift>h"]),
            ("win.show-hidden", ["<Control>h"]),
            ("win.swap-panes", ["<Control>t"]),
            ("win.import-videos", ["<Control>i"]),
            ("win.refresh", ["F5"]),
        ):
            self.set_accels_for_action(action, accels)

    def do_activate(self):
        window = self.props.active_window
        if window is None:
            window = FretWindow(self)
        window.present()


def main():
    application = FretApplication()
    return application.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
