"""Collecte en lecture seule. Aucune commande ne passe par un shell.

Toutes les commandes tournent avec LC_ALL=C : on analyse des sorties
anglaises stables, l'interface se charge de la traduction.
"""
import datetime
import json
import os
import re
import shutil
import subprocess
from collections import deque
from dataclasses import dataclass

ENV = {**os.environ, "LC_ALL": "C", "LANG": "C", "SYSTEMD_COLORS": "0",
       "SYSTEMD_PAGER": "", "SYSTEMD_URLIFY": "0", "PAGER": "cat"}
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
PACMAN_LOG = "/var/log/pacman.log"

LEVELS = {0: "Urgence", 1: "Alerte", 2: "Critique", 3: "Erreur",
          4: "Avertissement", 5: "Notice", 6: "Info", 7: "Débogage"}
SHORT_LEVELS = {0: "URG", 1: "ALR", 2: "CRI", 3: "ERR", 4: "AVT", 5: "NOT", 6: "INF", 7: "DBG"}


@dataclass(frozen=True)
class Result:
    status: str            # ok, empty, missing, denied, failed, timeout, disabled, pending
    value: object = None
    detail: str = ""

    @property
    def ok(self):
        return self.status == "ok"


def read(path, encoding="utf-8"):
    with open(path, encoding=encoding, errors="replace") as handle:
        return handle.read()


def run(args, timeout=20, ok_codes=(0,)):
    if not shutil.which(args[0]):
        return Result("missing", detail=f"{args[0]} n’est pas installé")
    try:
        proc = subprocess.run(args, capture_output=True, text=True, errors="replace",
                              timeout=timeout, env=ENV, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return Result("timeout", detail=f"{args[0]} : délai dépassé")
    except OSError as exc:
        return Result("failed", detail=str(exc))
    if proc.returncode not in ok_codes:
        detail = (proc.stderr or proc.stdout).strip() or f"code de sortie {proc.returncode}"
        low = detail.lower()
        denied = any(x in low for x in ("permission denied", "access denied", "not authorized",
                                        "operation not permitted"))
        return Result("denied" if denied else "failed", proc.stdout, detail)
    return Result("ok" if proc.stdout.strip() else "empty", proc.stdout, proc.stderr.strip())


# --------------------------------------------------------------------------- durées

_DUR = re.compile(r"(\d+(?:\.\d+)?)(h|min|ms|us|µs|s)\b")
_DUR_UNITS = {"h": 3600, "min": 60, "s": 1, "ms": 1e-3, "us": 1e-6, "µs": 1e-6}


def seconds(text):
    """« 1min 2.345s » → 62.345"""
    return sum(float(v) * _DUR_UNITS[u] for v, u in _DUR.findall(text or ""))


def human(sec):
    if sec >= 60:
        return f"{int(sec // 60)} min {sec % 60:04.1f} s"
    if sec >= 1:
        return f"{sec:.2f} s".replace(".", ",")
    return f"{sec * 1000:.0f} ms"


def size(value):
    value = float(value or 0)
    for unit in ("o", "Kio", "Mio", "Gio", "Tio"):
        if value < 1024 or unit == "Tio":
            return f"{value:.0f} {unit}" if unit in ("o", "Kio") else f"{value:.1f} {unit}".replace(".", ",")
        value /= 1024


# --------------------------------------------------------------------------- événements

@dataclass(frozen=True)
class Event:
    priority: int
    message: str
    unit: str
    timestamp: int          # microsecondes depuis l’époque
    source: str = "journal"  # journal, kernel, user, pacman
    pid: str = ""
    boot: str = ""
    transport: str = ""

    @property
    def dt(self):
        if not self.timestamp:
            return None
        return datetime.datetime.fromtimestamp(self.timestamp / 1e6)

    def clock(self, with_date=False):
        dt = self.dt
        if dt is None:
            return "--:--:--"
        return dt.strftime("%d/%m %H:%M" if with_date else "%H:%M:%S")

    @property
    def full_date(self):
        dt = self.dt
        return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "date inconnue"


def _text(value):
    if isinstance(value, list):            # MESSAGE binaire : liste d’octets
        try:
            return bytes(value).decode("utf-8", "replace")
        except (TypeError, ValueError):
            return " ".join(map(str, value))
    if value is None:
        return ""
    return value if isinstance(value, str) else str(value)


def unit_of(data):
    if _text(data.get("_TRANSPORT")) == "kernel":
        return "kernel"
    user_unit = _text(data.get("_SYSTEMD_USER_UNIT"))
    if user_unit and user_unit != "init.scope":
        return user_unit.removesuffix(".service")
    unit = _text(data.get("_SYSTEMD_UNIT"))
    if unit and not unit.startswith("user@") and not unit.endswith(".scope"):
        return unit.removesuffix(".service")
    ident = _text(data.get("SYSLOG_IDENTIFIER"))
    if ident.endswith("]") and "[" not in ident:      # « gdm-password] » : défaut connu de PAM
        ident = ident[:-1]
    return ident or _text(data.get("_COMM")) or unit.removesuffix(".service") or "système"


def parse_journal(output, source="journal"):
    events = []
    for line in output.splitlines():
        if not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = _text(data.get("MESSAGE")).rstrip()
        if not message:
            continue
        try:
            priority = int(_text(data.get("PRIORITY")) or 6)
        except ValueError:
            priority = 6
        priority = priority if 0 <= priority <= 7 else 6
        try:
            ts = int(_text(data.get("__REALTIME_TIMESTAMP")) or 0)
        except ValueError:
            ts = 0
        transport = _text(data.get("_TRANSPORT"))
        events.append(Event(priority, message, unit_of(data), ts,
                            "kernel" if transport == "kernel" else source,
                            _text(data.get("_PID")), _text(data.get("_BOOT_ID")), transport))
    return events


FIELDS = ("MESSAGE,PRIORITY,_SYSTEMD_UNIT,_SYSTEMD_USER_UNIT,SYSLOG_IDENTIFIER,"
          "_COMM,_PID,_TRANSPORT,_BOOT_ID")
PARTIAL_HINT = "not seeing messages from other users and the system"


def journal(boot="0", scope="all", priority=(0, 3), limit=20000, unit=None, since=None, until=None):
    """scope : all | system | user | kernel"""
    args = ["journalctl", "--no-pager", "-o", "json", f"--output-fields={FIELDS}"]
    if scope == "kernel":
        args.append("-k")
    args += ["-b", str(boot)]
    if scope == "system":
        args.append("--system")
    elif scope == "user":
        args.append("--user")
    if priority:
        args += ["-p", f"{priority[0]}..{priority[1]}"]
    if since is not None:
        args += ["--since", f"@{since}"]
    if until is not None:
        args += ["--until", f"@{until}"]
    if limit:
        args += ["-n", str(limit)]
    result = run(args, timeout=40)
    if result.status == "failed" and "no journal boot entry" in result.detail.lower():
        return Result("empty", [], "Ce démarrage n’est plus dans le journal")
    if result.status not in ("ok", "empty"):
        return result
    events = parse_journal(result.value or "", "user" if scope == "user" else "journal")
    if unit:
        events = [e for e in events if e.unit == unit]
    hint = "partial" if PARTIAL_HINT in (result.detail or "") else ""
    return Result("ok" if events else "empty", events, hint)


CLEAN_END = ("journal stopped", "reached target system shutdown", "reached target power-off",
             "reached target system power off", "reached target system reboot", "reached target final step",
             "system is powering down", "system is rebooting", "system is halting")


def previous_shutdown():
    """Le démarrage précédent s’est-il terminé par un arrêt propre ?

    Un arrêt normal laisse « Journal stopped » ou « Reached target System
    Shutdown » dans les dernières lignes ; un plantage ou une coupure, non.
    """
    result = run(["journalctl", "--no-pager", "-b", "-1", "-n", "120", "-o", "json",
                  f"--output-fields={FIELDS}"], timeout=20)
    if result.status == "failed" and "no journal boot entry" in result.detail.lower():
        return Result("empty", None, "Pas de démarrage précédent dans le journal")
    if result.status not in ("ok", "empty"):
        return result
    events = parse_journal(result.value or "")
    if not events:
        return Result("empty", None, "Pas de démarrage précédent dans le journal")
    last = max(events, key=lambda e: e.timestamp)
    clean = any(any(k in e.message.lower() for k in CLEAN_END) for e in events)
    return Result("ok", {"clean": clean, "last": last})


def boots():
    result = run(["journalctl", "--list-boots", "--no-pager", "-o", "json"], timeout=20)
    entries = []
    if result.ok:
        try:
            for item in json.loads(result.value):
                entries.append({"index": int(item.get("index", 0)), "id": item.get("boot_id", ""),
                                "first": int(item.get("first_entry") or 0),
                                "last": int(item.get("last_entry") or 0)})
        except (ValueError, TypeError, AttributeError):
            entries = []
    if not entries:                      # ancien systemd : sortie texte
        result = run(["journalctl", "--list-boots", "--no-pager"], timeout=20)
        if result.ok:
            for line in result.value.splitlines():
                m = re.match(r"\s*(-?\d+)\s+([0-9a-f]{32})\s+\w+\s+(\S+ \S+)", line)
                if m:
                    try:
                        first = datetime.datetime.strptime(m.group(3), "%Y-%m-%d %H:%M:%S")
                        first = int(first.timestamp() * 1e6)
                    except ValueError:
                        first = 0
                    entries.append({"index": int(m.group(1)), "id": m.group(2), "first": first, "last": 0})
    if not entries:
        return Result(result.status if result.status != "ok" else "empty", [], result.detail)
    entries.sort(key=lambda e: e["index"], reverse=True)
    return Result("ok", entries[:20])


def signature(message):
    text = re.sub(r"\b(?:[0-9a-f]{8}-){4}[0-9a-f]{12}\b|\b[0-9a-f]{32}\b", "<id>", message, flags=re.I)
    text = re.sub(r"\b0x[0-9a-f]+\b|\b\d+(?:\.\d+)*\b", "#", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip().lower()[:240]


def group(events):
    """Regroupe des événements semblables ; renvoie [(représentant, nombre)] triés."""
    groups = {}
    for event in events:
        key = (event.unit, signature(event.message))
        groups.setdefault(key, []).append(event)
    ordered = sorted(groups.values(), key=lambda items: (min(e.priority for e in items),
                                                        -len(items), -max(e.timestamp for e in items)))
    return [(max(items, key=lambda e: e.timestamp), len(items)) for items in ordered]


# --------------------------------------------------------------------------- pacman

_PAC = re.compile(r"^\[(?P<ts>[^\]]+)\] \[(?P<src>[^\]]+)\] (?P<msg>.*)$")


def _pacman_time(stamp):
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.datetime.strptime(stamp, fmt)
            return int(dt.timestamp() * 1e6)
        except ValueError:
            continue
    return 0


def pacman_priority(source, message):
    low = message.lower().lstrip("=> ").strip()
    if low.startswith(("error", "erreur")) or "failed" in low or "could not" in low:
        return 3
    if low.startswith(("warning", "avertissement")):
        return 4
    if source == "ALPM" and low.startswith(("upgraded", "installed", "removed", "downgraded", "reinstalled")):
        return 5
    return 6


def parse_pacman(lines):
    events = []
    for line in lines:
        m = _PAC.match(line.rstrip("\n"))
        if not m:
            continue
        src, msg = m.group("src"), m.group("msg").strip()
        if not msg:
            continue
        unit = {"ALPM": "alpm", "PACMAN": "pacman", "ALPM-SCRIPTLET": "scriptlet"}.get(src, src.lower())
        events.append(Event(pacman_priority(src, msg), msg, unit, _pacman_time(m.group("ts")), "pacman"))
    return events


def pacman_log(path=PACMAN_LOG, keep=8000):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            lines = deque(handle, maxlen=keep)
    except FileNotFoundError:
        return Result("missing", [], f"{path} est absent")
    except PermissionError:
        return Result("denied", [], f"Lecture de {path} refusée")
    events = parse_pacman(lines)
    return Result("ok" if events else "empty", events)


# --------------------------------------------------------------------------- systemd

def system_state():
    result = run(["systemctl", "is-system-running"], timeout=8, ok_codes=(0, 1))
    state = (result.value or "").strip() or result.detail.strip()
    return Result("ok" if state else "failed", state, result.detail)


def parse_failed_plain(text):
    units = []
    for line in text.splitlines():
        parts = line.replace("●", " ").split(None, 4)
        if len(parts) >= 4 and "." in parts[0]:
            units.append({"unit": parts[0], "load": parts[1], "active": parts[2], "sub": parts[3],
                          "description": parts[4] if len(parts) > 4 else ""})
    return units


def failed_units(user=False):
    base = ["systemctl"] + (["--user"] if user else []) + ["list-units", "--failed", "--all", "--no-pager"]
    result = run(base + ["--output=json"], timeout=10)
    units = None
    if result.ok:
        try:
            units = [{"unit": u.get("unit", ""), "load": u.get("load", ""), "active": u.get("active", ""),
                      "sub": u.get("sub", ""), "description": u.get("description", "")}
                     for u in json.loads(result.value)]
        except (ValueError, AttributeError):
            units = None
    elif result.status == "empty":
        units = []
    if units is None:
        result = run(base + ["--plain", "--no-legend"], timeout=10)
        if result.status not in ("ok", "empty"):
            return result
        units = parse_failed_plain(result.value or "")
    return Result("ok", units)


def parse_analyze(text):
    """Sortie de « systemd-analyze time » → (étapes, total, cible)."""
    stages = []
    lines = text.strip().splitlines()
    first = lines[0] if lines else ""
    for m in re.finditer(r"((?:\d+(?:\.\d+)?(?:h|min|ms|us|µs|s)\s?)+)\((\w+)\)", first):
        stages.append((m.group(2), seconds(m.group(1))))
    total = re.search(r"=\s*((?:\d+(?:\.\d+)?(?:h|min|ms|us|µs|s)\s?)+)", first)
    target = ""
    for line in lines[1:]:
        m = re.match(r"\s*(\S+) reached after (.+?) in userspace", line)
        if m:
            target = f"{m.group(1)} atteint après {human(seconds(m.group(2)))}"
    return stages, (seconds(total.group(1)) if total else sum(s for _, s in stages)), target


def analyze(user=False):
    result = run(["systemd-analyze"] + (["--user"] if user else []) + ["time"], timeout=15)
    if result.status != "ok":
        low = result.detail.lower()
        if "not yet finished" in low or "bootup is not yet" in low:
            return Result("pending", detail="Le démarrage n’est pas encore terminé")
        return result
    stages, total, target = parse_analyze(result.value)
    return Result("ok", {"stages": stages, "total": total, "target": target})


def parse_blame(text):
    rows = []
    for line in text.splitlines():
        m = re.match(r"^\s*((?:\d+(?:\.\d+)?(?:h|min|ms|us|µs|s)\s)+)(\S.*)$", line)
        if m:
            rows.append((m.group(2).strip(), seconds(m.group(1))))
    return rows


def blame(user=False):
    result = run(["systemd-analyze"] + (["--user"] if user else []) + ["blame", "--no-pager"], timeout=15)
    if result.status != "ok":
        return result
    rows = parse_blame(result.value)
    return Result("ok" if rows else "empty", rows)


def critical_chain(user=False):
    result = run(["systemd-analyze"] + (["--user"] if user else []) + ["critical-chain", "--no-pager"],
                 timeout=15)
    if result.status != "ok":
        return result
    lines = [ANSI.sub("", l) for l in result.value.splitlines()]
    lines = [l for l in lines if l.strip() and not l.startswith(("The time when", "The time the"))]
    return Result("ok", "\n".join(lines))


# --------------------------------------------------------------------------- noyau

TAINTS = {
    0: ("P", "module propriétaire chargé", False), 1: ("F", "module chargé de force", True),
    2: ("S", "processeur hors spécification", True), 3: ("R", "module retiré de force", True),
    4: ("M", "erreur machine (MCE)", True), 5: ("B", "mauvaise page mémoire", True),
    6: ("U", "marqué par l’utilisateur", False), 7: ("D", "le noyau a planté (oops)", True),
    8: ("A", "table ACPI remplacée", False), 9: ("W", "avertissement du noyau émis", True),
    10: ("C", "pilote « staging » chargé", False), 11: ("I", "contournement de micrologiciel", False),
    12: ("O", "module hors arbre chargé", False), 13: ("E", "module non signé chargé", False),
    14: ("L", "blocage logiciel (soft lockup)", True), 15: ("K", "noyau corrigé à chaud", False),
    16: ("X", "taint auxiliaire", False), 17: ("T", "compilé avec randstruct", False),
    18: ("N", "module de test chargé", False),
}


def taint(path="/proc/sys/kernel/tainted"):
    try:
        value = int(read(path).strip() or 0)
    except (OSError, ValueError) as exc:
        return Result("failed", detail=str(exc))
    flags = [(TAINTS[b][0], TAINTS[b][1], TAINTS[b][2]) for b in TAINTS if value >> b & 1]
    return Result("ok", {"value": value, "flags": flags})


_PARAM = re.compile(r"unknown kernel command line parameters?|unknown (?:boot|kernel) parameter|"
                    r"\b(?:parameter|option)\b.{0,70}\b(?:unknown|invalid|ignored|unrecognized)\b|"
                    r"\b(?:unknown|invalid|ignored|unrecognized)\b.{0,70}\b(?:parameter|option)\b", re.I)


def kernel_parameters(boot="0"):
    try:
        cmdline = read("/proc/cmdline").strip()
    except OSError:
        cmdline = ""
    # tout le journal noyau de ce démarrage : ces messages arrivent à t = 0
    result = journal(boot, "kernel", priority=None, limit=0)
    if result.status not in ("ok", "empty"):
        return Result(result.status, (cmdline, []), result.detail)
    reports = [e for e in (result.value or []) if _PARAM.search(e.message)]
    return Result("ok", (cmdline, reports))


def os_identity():
    name = "Linux"
    try:
        for line in read("/etc/os-release").splitlines():
            if line.startswith("PRETTY_NAME="):
                name = line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return f"{name} · noyau {os.uname().release}"


# --------------------------------------------------------------------------- plantages

def coredump_state():
    result = run(["systemctl", "is-enabled", "systemd-coredump.socket"], timeout=8, ok_codes=(0, 1))
    state = (result.value or "").strip()
    try:
        pattern = read("/proc/sys/kernel/core_pattern").strip()
    except OSError:
        pattern = ""
    return state, pattern


def coredumps(days=30):
    state, pattern = coredump_state()
    if state.startswith("masked"):
        return Result("disabled", [], "systemd-coredump est masqué : les plantages ne sont pas enregistrés")
    if pattern and "systemd-coredump" not in pattern:
        return Result("disabled", [], f"core_pattern ne passe pas par systemd-coredump ({pattern})")
    result = run(["coredumpctl", "list", "--json=short", "--no-pager", f"--since=-{days}d"],
                 timeout=20, ok_codes=(0, 1))
    if result.status not in ("ok", "empty"):
        return result
    if not (result.value or "").strip():
        return Result("empty", [])
    try:
        items = json.loads(result.value)
    except ValueError:
        return Result("failed", [], "Sortie de coredumpctl illisible")
    dumps = [{"time": int(i.get("time") or 0), "pid": i.get("pid"), "sig": i.get("sig"),
              "exe": i.get("exe") or "?", "present": i.get("corefile", "") in ("present", "journal")}
             for i in items]
    dumps.sort(key=lambda d: d["time"], reverse=True)
    return Result("ok" if dumps else "empty", dumps)


SIGNALS = {4: "SIGILL", 5: "SIGTRAP", 6: "SIGABRT", 7: "SIGBUS", 8: "SIGFPE", 11: "SIGSEGV", 31: "SIGSYS"}


# --------------------------------------------------------------------------- espace

def space():
    rows = []
    seen = set()
    result = run(["findmnt", "-J", "-n", "-o", "TARGET,SOURCE,FSTYPE",
                  "-t", "btrfs,ext4,xfs,vfat,f2fs,bcachefs"], timeout=8)
    targets = []
    if result.ok:
        try:
            def walk(nodes):
                for node in nodes:
                    targets.append((node.get("target"), node.get("source"), node.get("fstype")))
                    walk(node.get("children", []))
            walk(json.loads(result.value).get("filesystems", []))
        except (ValueError, AttributeError):
            targets = []
    wanted = ("/", "/boot", "/efi", "/boot/efi", "/home")
    for target, source, fstype in targets:
        if target not in wanted:
            continue
        try:
            st = os.statvfs(target)
        except OSError:
            continue
        key = (st.f_fsid, st.f_blocks)
        if key in seen and target != "/":
            continue
        seen.add(key)
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        if total:
            rows.append({"target": target, "source": (source or "").split("[")[0], "fstype": fstype,
                         "total": total, "free": free, "used_ratio": 1 - free / total})
    rows.sort(key=lambda r: wanted.index(r["target"]))
    return Result("ok" if rows else "empty", rows)


# --------------------------------------------------------------------------- matériel (root)

HELPER = os.environ.get("SISMOGRAPHE_HELPER", "/usr/lib/sismographe/sismographe-helper")


def hardware():
    """Lance l’assistant root via pkexec (SMART, btrfs, FAT). Lecture seule."""
    if not os.path.exists(HELPER):
        return Result("missing", detail=f"Assistant introuvable : {HELPER}")
    if not shutil.which("pkexec"):
        return Result("missing", detail="pkexec n’est pas installé (paquet polkit)")
    try:
        proc = subprocess.run(["pkexec", HELPER, "all"], capture_output=True, text=True,
                              errors="replace", timeout=300, env=ENV, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return Result("timeout", detail="La vérification a dépassé 5 minutes")
    except OSError as exc:
        return Result("failed", detail=str(exc))
    if proc.returncode in (126, 127):
        return Result("denied", detail="Authentification annulée ou refusée")
    if proc.returncode != 0:
        return Result("failed", detail=proc.stderr.strip() or f"code de sortie {proc.returncode}")
    try:
        return Result("ok", json.loads(proc.stdout))
    except ValueError:
        return Result("failed", detail="Réponse de l’assistant illisible")
