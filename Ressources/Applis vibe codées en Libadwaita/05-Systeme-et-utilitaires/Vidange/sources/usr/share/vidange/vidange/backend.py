"""Vidange — logique sans interface : estimations, recherches, nettoyages.

Tout ce qui tourne ici s'exécute en utilisateur. Les opérations root
passent par run_helper(), qui appelle /usr/lib/vidange/vidange-helper
via pkexec. Aucune commande n'utilise de shell.
"""

import json
import os
from datetime import datetime
import re
import shutil
import subprocess
from pathlib import Path

APP_ID = "io.gitlab.shogu.Vidange"
HELPER = "/usr/lib/vidange/vidange-helper"
PKG_CACHE = Path("/var/cache/pacman/pkg")
FWUPD_CACHE = Path("/var/cache/fwupd")

HOME = Path.home()
XDG_CACHE = Path(os.environ.get("XDG_CACHE_HOME") or HOME / ".cache")
XDG_DATA = Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local/share")
XDG_CONFIG = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config")
SETTINGS_FILE = XDG_CONFIG / "vidange" / "settings.json"
CARGO_HOME = Path(os.environ.get("CARGO_HOME") or HOME / ".cargo")

C_ENV = {**os.environ, "LC_ALL": "C"}
MIB = 1024 * 1024

CATEGORIES = ["orphans", "pacman", "aur", "flatpak", "journal", "fwupd",
              "home", "webcache", "shaders", "dev", "containers", "browsers"]
LABELS = {
    "orphans": "Orphelins sûrs",
    "unneeded": "Orphelins à vérifier",
    "explicit": "Installés explicitement, à vérifier",
    "flatpak": "Flatpak inutilisés",
    "containers": "Conteneurs",
    "pacman": "Cache pacman",
    "aur": "Cache AUR",
    "journal": "Journaux systemd",
    "home": "Miniatures et corbeille",
    "dev": "Caches de développement",
    "browsers": "Navigateurs",
    "fwupd": "Cache des micrologiciels",
    "webcache": "Cache web des navigateurs",
    "shaders": "Caches de shaders",
    "configs": "Dossiers de configuration orphelins",
}
PACMAN_MODES = [
    ("keep2", "Garder 2 versions"),
    ("keep2-uninstalled", "Garder 2 versions, vider les désinstallés"),
    ("all", "Tout vider"),
]
PACMAN_HINTS = {
    "keep2": "paccache -rk2 · permet de revenir à la version précédente",
    "keep2-uninstalled": "paccache -rk2 puis -ruk0 · retire aussi les paquets "
                         "qui ne sont plus installés",
    "all": "pacman -Scc · plus aucun retour en arrière possible",
}


# --------------------------------------------------------------------------
# Outils
# --------------------------------------------------------------------------

def run(cmd, timeout=600, **kw):
    """subprocess.run sans shell ; renvoie None si la commande n'existe pas."""
    kw.setdefault("capture_output", True)
    kw.setdefault("text", True)
    kw.setdefault("env", C_ENV)
    if "input" not in kw:
        kw.setdefault("stdin", subprocess.DEVNULL)
    try:
        return subprocess.run(cmd, timeout=timeout, **kw)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def have(binary):
    return shutil.which(binary) is not None


def dir_size(path):
    """Taille totale d'un dossier, sans suivre les liens symboliques."""
    path = Path(path)
    if not path.exists():
        return 0
    total = 0
    stack = [path]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                        else:
                            total += entry.stat(follow_symlinks=False).st_size
                    except OSError:
                        pass
        except OSError:
            pass
    return total


def empty_dir(path):
    """Vide le contenu d'un dossier en conservant le dossier lui-même."""
    path = Path(path)
    if not path.is_dir():
        return
    for child in path.iterdir():
        try:
            if child.is_symlink() or not child.is_dir():
                child.unlink()
            else:
                shutil.rmtree(child)
        except OSError:
            # fichiers en lecture seule (cache Go, par exemple)
            for root, dirs, files in os.walk(child):
                for name in dirs + files:
                    try:
                        os.chmod(os.path.join(root, name), 0o700)
                    except OSError:
                        pass
            shutil.rmtree(child, ignore_errors=True)


def fmt_size(n):
    if n is None:
        return "—"
    units = ["o", "Ko", "Mo", "Go", "To"]
    value = float(n)
    i = 0
    while value >= 1000 and i < len(units) - 1:
        value /= 1000
        i += 1
    text = f"{value:.0f}" if i == 0 or value >= 100 else f"{value:.1f}"
    return text.replace(".", ",") + " " + units[i]


_UNITS = {
    "B": 1, "": 1,
    "K": 1024, "KiB": 1024,
    "M": MIB, "MiB": MIB,
    "G": 1024 ** 3, "GiB": 1024 ** 3,
    "T": 1024 ** 4, "TiB": 1024 ** 4,
}


def parse_size(number, unit):
    try:
        return int(float(number) * _UNITS.get(unit, 1))
    except ValueError:
        return 0


# --------------------------------------------------------------------------
# Réglages
# --------------------------------------------------------------------------

DEFAULTS = {
    "enabled": {c: True for c in CATEGORIES},
    "pacman_mode": "keep2",
    "journal_mb": 200,
}


def load_settings():
    settings = json.loads(json.dumps(DEFAULTS))
    try:
        data = json.loads(SETTINGS_FILE.read_text())
        settings["enabled"].update(data.get("enabled", {}))
        if data.get("pacman_mode") in dict(PACMAN_MODES):
            settings["pacman_mode"] = data["pacman_mode"]
        settings["journal_mb"] = int(data.get("journal_mb", 200))
    except (OSError, ValueError, TypeError):
        pass
    return settings


def save_settings(settings):
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(settings, indent=2))
    except OSError:
        pass


# --------------------------------------------------------------------------
# Détection
# --------------------------------------------------------------------------

def shelly_cache():
    """Cache AUR de Shelly ($XDG_CACHE_HOME/Shelly)."""
    return XDG_CACHE / "Shelly"


def shelly_archives_size():
    """Taille des paquets construits et signatures dans le cache Shelly."""
    root = shelly_cache()
    total = 0
    if not root.is_dir():
        return 0
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if ".pkg.tar" in name:
                try:
                    total += os.lstat(os.path.join(dirpath, name)).st_size
                except OSError:
                    pass
    return total


def _go_dirs():
    gocache, gomod = XDG_CACHE / "go-build", HOME / "go" / "pkg" / "mod"
    if have("go"):
        r = run(["go", "env", "GOCACHE", "GOMODCACHE"], timeout=30)
        if r and r.returncode == 0:
            lines = r.stdout.splitlines()
            if len(lines) >= 2:
                gocache, gomod = Path(lines[0]), Path(lines[1])
    return [gocache, gomod]


def dev_dirs():
    """Caches de développement présents : {outil: [chemins]}."""
    candidates = {
        "pip": [XDG_CACHE / "pip"],
        "npm": [HOME / ".npm" / "_cacache"],
        "yarn": [XDG_CACHE / "yarn"],
        "Go": _go_dirs(),
        "Rust": [CARGO_HOME / "registry" / "cache", CARGO_HOME / "registry" / "src",
                 CARGO_HOME / "git" / "checkouts"],
        "Zig": [XDG_CACHE / "zig"],
        "ccache": [XDG_CACHE / "ccache", HOME / ".ccache"],
        "sccache": [XDG_CACHE / "sccache"],
        "uv": [XDG_CACHE / "uv"],
        "pnpm": [XDG_DATA / "pnpm" / "store"],
        "Bun": [HOME / ".bun" / "install" / "cache"],
        "Deno": [XDG_CACHE / "deno"],
        "Gradle": [HOME / ".gradle" / "caches"],
        "Electron": [XDG_CACHE / "electron"],
        "node-gyp": [XDG_CACHE / "node-gyp"],
    }
    return {tool: paths for tool, paths in candidates.items()
            if any(p.exists() for p in paths)}


# lettres reconnues par profile-cleaner
_BROWSERS = [
    ("v", "Vivaldi", [XDG_CONFIG / "vivaldi"]),
    ("f", "Firefox", [HOME / ".mozilla" / "firefox", XDG_CONFIG / "mozilla" / "firefox"]),
    ("c", "Chromium", [XDG_CONFIG / "chromium"]),
    ("gc", "Chrome", [XDG_CONFIG / "google-chrome"]),
]


def browsers():
    """Navigateurs dont un profil existe : (lettre, nom, chemins)."""
    return [(key, name, [p for p in paths if p.exists()])
            for key, name, paths in _BROWSERS
            if any(p.exists() for p in paths)]


# cache web : (nom, processus, dossier)
_WEB_CACHES = [
    ("Vivaldi", ["vivaldi-bin"], XDG_CACHE / "vivaldi"),
    ("Firefox", ["firefox"], XDG_CACHE / "mozilla" / "firefox"),
    ("Chromium", ["chromium"], XDG_CACHE / "chromium"),
    ("Chrome", ["chrome"], XDG_CACHE / "google-chrome"),
]


def web_caches():
    return [(n, procs, p) for n, procs, p in _WEB_CACHES if p.is_dir()]


def is_running(procs):
    for proc in procs:
        r = run(["pgrep", "-x", "-u", str(os.getuid()), proc], timeout=10)
        if r and r.returncode == 0:
            return True
    return False


_SHADER_DIRS = [
    ("Mesa", XDG_CACHE / "mesa_shader_cache"),
    ("Mesa", XDG_CACHE / "mesa_shader_cache_db"),
    ("RADV", XDG_CACHE / "radv_builtin_shaders"),
    ("NVIDIA", XDG_CACHE / "nvidia" / "GLCache"),
    ("NVIDIA", HOME / ".nv" / "GLCache"),
]


def shader_dirs():
    return [(n, p) for n, p in _SHADER_DIRS if p.is_dir()]


def trash_dir():
    return XDG_DATA / "Trash"


def thumbnails_dir():
    return XDG_CACHE / "thumbnails"


# --------------------------------------------------------------------------
# Mesures et estimations
# --------------------------------------------------------------------------

def journal_usage():
    r = run(["journalctl", "--disk-usage"], timeout=60)
    if not r:
        return 0
    m = re.search(r"take up ([\d.]+)([KMGT]?)", r.stdout + r.stderr)
    return parse_size(*m.groups()) if m else 0


def _paccache_dry(args):
    r = run(["paccache", "-d", *args], timeout=120)
    if not r:
        return 0
    m = re.search(r"disk space saved: ([\d.]+) (\w+)", r.stdout + r.stderr)
    return parse_size(*m.groups()) if m else 0


def pacman_estimate(mode):
    if mode == "all":
        return dir_size(PKG_CACHE)
    total = _paccache_dry(["-k2"])
    if mode == "keep2-uninstalled":
        # -uk0 compte aussi ce que -k2 retire déjà : on soustrait le recouvrement
        total += _paccache_dry(["-uk0"]) - _paccache_dry(["-uk2"])
    return max(0, total)


def measure(cid):
    """Place occupée actuellement par une catégorie (None si non mesurable)."""
    if cid == "pacman":
        return dir_size(PKG_CACHE)
    if cid == "journal":
        return journal_usage()
    if cid == "aur":
        return dir_size(shelly_cache())
    if cid == "home":
        return dir_size(thumbnails_dir()) + dir_size(trash_dir())
    if cid == "dev":
        return sum(dir_size(p) for paths in dev_dirs().values() for p in paths)
    if cid == "browsers":
        return sum(dir_size(p) for _, _, paths in browsers() for p in paths)
    if cid == "fwupd":
        return dir_size(FWUPD_CACHE)
    if cid == "webcache":
        return sum(dir_size(p) for _, _, p in web_caches())
    if cid == "shaders":
        return sum(dir_size(p) for _, p in shader_dirs())
    return None


def estimate(cid, settings):
    """Place que le nettoyage devrait libérer (None si inconnue à l'avance)."""
    if cid == "pacman":
        return pacman_estimate(settings["pacman_mode"])
    if cid == "journal":
        return max(0, journal_usage() - settings["journal_mb"] * MIB)
    if cid == "browsers":
        return None  # profile-cleaner compacte des bases : gain non prévisible
    if cid == "aur":
        # estimation prudente : paquets construits et signatures
        # (le README de Shelly dit que --aur-cache vide tout le cache,
        # sa référence CLI dit seulement les archives ; le récapitulatif mesure)
        return shelly_archives_size()
    return measure(cid)


# --------------------------------------------------------------------------
# Paquets
# --------------------------------------------------------------------------

def _lines(r):
    if not r:
        return []
    return [line.strip() for line in r.stdout.splitlines() if line.strip()]


def list_orphans():
    return _lines(run(["pacman", "-Qtdq"]))


def list_unneeded():
    """Dépendances retirables sans rien casser, hors orphelins simples.

    Reprend orphans+ : pacman -Qdq, puis simulation pacman -Rsu --print.
    Trouve en plus les dépendances qui ne servent qu'entre elles ou
    seulement comme dépendances optionnelles.
    """
    deps = _lines(run(["pacman", "-Qdq"]))
    if not deps:
        return []
    r = run(["pacman", "-Rsu", "--print", "--print-format", "%n", "--", *deps])
    names = [n for n in _lines(r)
             if re.fullmatch(r"[A-Za-z0-9@_+][A-Za-z0-9@._+-]*", n)]
    orphans = set(list_orphans())
    return sorted(set(names) - orphans)


def list_explicit_unused():
    return _lines(run(["pacman", "-Qetq"]))


def pkg_info(names):
    """Essentiel de pacman -Qi pour chaque paquet."""
    if not names:
        return {}
    r = run(["pacman", "-Qi", "--", *names])
    info = {}
    if not r:
        return info
    for block in r.stdout.split("\n\n"):
        fields, key = {}, None
        for line in block.splitlines():
            if line and not line[0].isspace() and " : " in line:
                key, value = line.split(" : ", 1)
                key = key.strip()
                fields[key] = value.strip()
            elif key:
                fields[key] += " " + line.strip()
        name = fields.get("Name")
        if not name:
            continue
        m = re.match(r"([\d.]+)\s*(\w+)", fields.get("Installed Size", ""))

        def clean(value):
            return "" if not value or value == "None" else value

        info[name] = {
            "name": name,
            "version": fields.get("Version", ""),
            "desc": clean(fields.get("Description")),
            "required": clean(fields.get("Required By")),
            "optional": clean(fields.get("Optional For")),
            "date": clean(fields.get("Install Date")),
            "size": parse_size(*m.groups()) if m else 0,
        }
    return info


def search(kind):
    """Recherche d'un niveau d'orphelins ; renvoie une liste de dicts."""
    if kind == "configs":
        return list_config_orphans()
    names = {"orphans": list_orphans,
             "unneeded": list_unneeded,
             "explicit": list_explicit_unused}[kind]()
    info = pkg_info(names)
    return [info.get(n, {"name": n, "version": "", "desc": "", "required": "",
                         "optional": "", "date": "", "size": 0})
            for n in names]


# --------------------------------------------------------------------------
# Helper root
# --------------------------------------------------------------------------

def helper_error(rc):
    if rc == 126:
        return "Authentification annulée"
    if rc == 127:
        return "Autorisation refusée"
    if rc is None:
        return "pkexec est introuvable"
    return f"Le helper a échoué (code {rc})"


def run_helper(steps, on_line=None):
    """Lance toutes les étapes root en un seul appel pkexec.

    Renvoie (code_retour, {id: (ok, message)}).
    """
    try:
        proc = subprocess.Popen(["pkexec", HELPER], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True)
    except FileNotFoundError:
        return None, {}
    proc.stdin.write(json.dumps(steps))
    proc.stdin.close()
    results = {}
    for line in proc.stdout:
        try:
            item = json.loads(line)
        except ValueError:
            continue
        results[item.get("id")] = (bool(item.get("ok")), item.get("message", ""))
        if on_line:
            on_line(item)
    proc.stderr.read()
    proc.wait()
    return proc.returncode, results


# --------------------------------------------------------------------------
# Nettoyages en utilisateur
# --------------------------------------------------------------------------

def _tail(r):
    if r is None:
        return "commande introuvable ou trop longue"
    return (r.stderr or r.stdout).strip()[-300:]


def clean_browsers():
    found = browsers()
    if not found:
        return True, "Aucun profil de navigateur trouvé"
    if not have("profile-cleaner"):
        return False, "profile-cleaner n'est pas installé"
    errors = []
    for key, name, _ in found:
        r = run(["profile-cleaner", key], env=os.environ, timeout=900)
        if r is None or r.returncode != 0:
            errors.append(f"{name} : {_tail(r)}")
    names = ", ".join(n for _, n, _ in found)
    return (not errors), ("; ".join(errors) if errors else names)


SHELLY_AUR = ["shelly", "purify", "standard", "--aur-cache"]
# Le vrai nettoyage passe par le helper (action shelly-aur-cache) : Shelly
# appelle sudo en interne et échoue sans terminal s'il tourne en utilisateur.


def aur_precheck():
    """(ok, message) si le cache AUR n'a pas besoin du helper, sinon None."""
    if not shelly_cache().is_dir():
        return True, "Aucun cache Shelly"
    if not have("shelly"):
        return False, "Shelly n'est pas installé"
    return None


def clean_home():
    empty_dir(thumbnails_dir())
    r = run(["gio", "trash", "--empty"], env=os.environ) if have("gio") else None
    if r is None or r.returncode != 0:
        empty_dir(trash_dir() / "files")
        empty_dir(trash_dir() / "info")
    return True, "Miniatures et corbeille vidées"


def clean_dev():
    found = dev_dirs()
    if not found:
        return True, "Aucun cache trouvé"
    commands = {
        "pip": ["pip", "cache", "purge"],
        "npm": ["npm", "cache", "clean", "--force"],
        "yarn": ["yarn", "cache", "clean"],
        "Go": ["go", "clean", "-cache", "-modcache"],
        "ccache": ["ccache", "-C"],
        "uv": ["uv", "cache", "clean"],
        "pnpm": ["pnpm", "store", "prune"],
        "Bun": ["bun", "pm", "cache", "rm"],
        "Deno": ["deno", "clean"],
        # Rust, Zig, sccache, Gradle, Electron, node-gyp : pas de commande
        # de nettoyage stable, les dossiers de cache sont vidés
    }
    for tool, paths in found.items():
        cmd = commands.get(tool)
        r = run(cmd, env=os.environ, timeout=900) if cmd and have(cmd[0]) else None
        if r is None or r.returncode != 0:
            for p in paths:
                empty_dir(p)
    return True, ", ".join(found)


def clean_webcache():
    found = web_caches()
    if not found:
        return True, "Aucun cache web trouvé"
    done, skipped = [], []
    for name, procs, path in found:
        if is_running(procs):
            skipped.append(name)
            continue
        empty_dir(path)
        done.append(name)
    if skipped:
        return False, (f"Fermez {', '.join(skipped)} puis relancez"
                       + (f" (vidé : {', '.join(done)})" if done else ""))
    return True, ", ".join(done)


def clean_shaders():
    found = shader_dirs()
    for _, path in found:
        empty_dir(path)
    return True, ", ".join(sorted({n for n, _ in found})) or "Aucun cache trouvé"


def _reclaimed(text):
    """« Total reclaimed space: 1.2GB » → octets (docker)."""
    m = re.search(r"reclaimed space:\s*([\d.]+)\s*([kKMGT]?)i?B", text or "")
    if not m:
        return 0
    unit = {"": 1, "k": 1000, "K": 1000, "M": 1000 ** 2, "G": 1000 ** 3, "T": 1000 ** 4}
    return int(float(m.group(1)) * unit[m.group(2)])


CONTAINER_COMMANDS = {
    # uniquement le cache de build et les images orphelines (<none>) :
    # jamais les conteneurs, les volumes ni les images utilisées
    "Docker": [["docker", "builder", "prune", "-f"], ["docker", "image", "prune", "-f"]],
    "Podman": [["podman", "image", "prune", "-f"]],
}


def container_tools():
    return [name for name, cmds in CONTAINER_COMMANDS.items() if have(cmds[0][0])]


def clean_containers():
    tools = container_tools()
    if not tools:
        return True, "Ni Docker ni Podman", 0
    errors, freed = [], 0
    for name in tools:
        for cmd in CONTAINER_COMMANDS[name]:
            r = run(cmd, env=os.environ, timeout=900)
            if r is None or r.returncode != 0:
                errors.append(f"{name} : {_tail(r)}")
            else:
                freed += _reclaimed(r.stdout)
    return (not errors), ("; ".join(errors) if errors else ", ".join(tools)), freed


FLATPAK_UNUSED = ["flatpak", "uninstall", "--unused", "-y", "--noninteractive"]


def clean_flatpak():
    if not have("flatpak"):
        return True, "Flatpak n'est pas installé"
    r = run(FLATPAK_UNUSED, env=os.environ, timeout=1800)
    if r is None or r.returncode != 0:
        return False, f"flatpak a échoué : {_tail(r)}"
    return True, "flatpak uninstall --unused"


USER_CLEANERS = {
    "containers": clean_containers,
    "flatpak": clean_flatpak,
    "webcache": clean_webcache,
    "shaders": clean_shaders,
    "browsers": clean_browsers,
    "home": clean_home,
    "dev": clean_dev,
}


# --------------------------------------------------------------------------
# Simulation : rien n'est supprimé, tout tourne en utilisateur
# --------------------------------------------------------------------------

def _count(n, word):
    return f"{n} {word}{'s' if n > 1 else ''}"


def simulate(cid, settings, packages=None):
    """Renvoie (ok, message, octets) sans rien modifier."""
    if cid == "orphans":
        if not packages:
            return True, "Aucun paquet sélectionné", 0
        r = run(["pacman", "-Rns", "--print", "--print-format", "%n", "--", *packages])
        if r is None or r.returncode != 0:
            return False, f"pacman refuserait : {_tail(r)}", 0
        names = _lines(r)
        info = pkg_info(names)
        size = sum(p["size"] for p in info.values())
        return True, f"{_count(len(names), 'paquet')} supprimés : " + ", ".join(names[:12]) \
            + (" …" if len(names) > 12 else ""), size
    if cid == "pacman":
        mode = settings["pacman_mode"]
        size = pacman_estimate(mode)
        commands = {"keep2": "paccache -rk2",
                    "keep2-uninstalled": "paccache -rk2 puis paccache -ruk0",
                    "all": "pacman -Scc (tout le cache)"}
        return True, commands[mode], size
    if cid == "journal":
        keep = settings["journal_mb"]
        return True, f"journalctl --vacuum-size={keep}M (journaux archivés seulement)", \
            max(0, journal_usage() - keep * MIB)
    if cid == "aur":
        if not shelly_cache().is_dir():
            return True, "Aucun cache Shelly", 0
        if not have("shelly"):
            return False, "Shelly n'est pas installé", 0
        r = run([*SHELLY_AUR, "--dry-run"], env=os.environ, timeout=300,
                input="n\n" * 2000)
        if r is not None and "terminal is required" in (r.stderr + r.stdout):
            return True, ("Shelly demande les droits root même à blanc : "
                          "estimation sur les paquets construits"), shelly_archives_size()
        if r is None or r.returncode != 0:
            return False, f"Shelly --dry-run a échoué : {_tail(r)}", 0
        return True, "Plan de Shelly : " + (_tail(r) or "rien à faire"), shelly_archives_size()
    if cid == "home":
        return True, "~/.cache/thumbnails et gio trash --empty", measure("home")
    if cid == "dev":
        found = dev_dirs()
        return True, ", ".join(found) if found else "Aucun cache trouvé", measure("dev")
    if cid == "browsers":
        found = [name for _, name, _ in browsers()]
        if not have("profile-cleaner"):
            return False, "profile-cleaner n'est pas installé", 0
        return True, "profile-cleaner : " + (", ".join(found) or "aucun profil"), 0
    if cid == "fwupd":
        return True, "Vide /var/cache/fwupd (métadonnées et micrologiciels téléchargés)", \
            measure("fwupd")
    if cid == "webcache":
        found = web_caches()
        running = [n for n, procs, _ in found if is_running(procs)]
        msg = ", ".join(n for n, _, _ in found) or "Aucun cache web trouvé"
        if running:
            msg += f" — à fermer avant : {', '.join(running)}"
        return True, msg, measure("webcache")
    if cid == "shaders":
        names = sorted({n for n, _ in shader_dirs()})
        return True, ", ".join(names) or "Aucun cache trouvé", measure("shaders")
    if cid == "containers":
        tools = container_tools()
        if not tools:
            return True, "Ni Docker ni Podman", 0
        cmds = "; ".join(" ".join(c) for t in tools for c in CONTAINER_COMMANDS[t])
        return True, cmds + " (cache de build et images orphelines seulement)", 0
    if cid == "flatpak":
        if not have("flatpak"):
            return True, "Flatpak n'est pas installé", 0
        r = run(["flatpak", "uninstall", "--unused"], env=os.environ, timeout=300,
                input="n\n")
        refs = [ln.split()[1] for ln in (r.stdout if r else "").splitlines()
                if re.match(r"\s*\d+\.\s", ln) and len(ln.split()) > 1]
        if not refs:
            return True, "Aucun runtime inutilisé", 0
        return True, f"{_count(len(refs), 'runtime')} : " + ", ".join(refs[:10]), 0
    return False, "Catégorie inconnue", 0


def simulate_pkg_action(kind, packages):
    """Simulation des actions des pages de paquets."""
    if kind == "configs":
        shown = "\n".join(_home_display(p) for p in packages[:30])
        return True, (f"{_count(len(packages), 'dossier')} iraient à la corbeille :\n"
                      + shown + ("\n…" if len(packages) > 30 else ""))
    if kind == "explicit":
        return True, f"pacman -D --asdeps marquerait {_count(len(packages), 'paquet')}"
    ok, message, size = simulate("orphans", {}, packages)
    return ok, message + (f" ({fmt_size(size)})" if ok and size else "")


# --------------------------------------------------------------------------
# Configurations orphelines : dossiers dont l'appli semble désinstallée
# --------------------------------------------------------------------------

CONFIG_ROOTS = [XDG_CONFIG, XDG_DATA, XDG_CACHE]

# Dossiers partagés, système ou gérés ailleurs dans Vidange : jamais proposés
_CONFIG_KEEP_RAW = [
    "autostart", "dconf", "environment.d", "systemd", "gtk-2.0", "gtk-3.0", "gtk-4.0",
    "pulse", "pipewire", "wireplumber", "menus", "fontconfig", "fonts", "icons", "themes",
    "applications", "desktop-directories", "mime", "sounds", "backgrounds", "ibus",
    "enchant", "gnome-session", "gnome-shell", "gnome-settings-daemon", "goa-1.0",
    "keyrings", "Trash", "recently-used", "xdg-desktop-portal", "gvfs-metadata",
    "tracker3", "evolution", "folks", "geoclue", "glib-2.0", "dbus-1", "session",
    "flatpak", "vidange", "user-dirs", "gstreamer-1.0", "webkitgtk", "webkitgtk-6.0",
    "qt5ct", "qt6ct", "Kvantum", "kdeglobals", "configstore", "pki", "nautilus",
    # caches traités par d'autres catégories
    "thumbnails", "mesa_shader_cache", "mesa_shader_cache_db", "radv_builtin_shaders",
    "nvidia", "Shelly", "pip", "yarn", "zig", "go-build", "ccache", "vivaldi",
    "mozilla", "chromium", "google-chrome", "sccache", "uv", "deno", "electron",
    "node-gyp",
]


def _norm(text):
    return re.sub(r"\d+$", "", re.sub(r"[^a-z0-9]", "", text.lower()))


_CONFIG_KEEP = {_norm(n) for n in _CONFIG_KEEP_RAW}


def _home_display(path):
    path = str(path)
    home = str(HOME)
    return "~" + path[len(home):] if path.startswith(home) else path


def _known_tokens():
    """Noms connus du système : paquets, applis, exécutables, Flatpak."""
    raw = set(_lines(run(["pacman", "-Qq"])))
    desktop_dirs = [Path("/usr/share/applications"), XDG_DATA / "applications",
                    Path("/var/lib/flatpak/exports/share/applications"),
                    XDG_DATA / "flatpak" / "exports" / "share" / "applications"]
    for folder in desktop_dirs:
        if not folder.is_dir():
            continue
        for f in folder.glob("*.desktop"):
            raw.add(f.stem)
            raw.update(f.stem.split("."))
            try:
                text = f.read_text(errors="ignore")
            except OSError:
                continue
            for line in text.splitlines():
                if line.startswith(("Exec=", "StartupWMClass=", "Name=")):
                    value = line.split("=", 1)[1].strip()
                    if line.startswith("Exec=") and value:
                        value = os.path.basename(value.split()[0])
                    raw.add(value)
    try:
        raw.update(os.listdir("/usr/bin"))
    except OSError:
        pass
    raw.update(flatpak_apps())
    return {t for t in (_norm(x) for x in raw) if len(t) >= 3}


def flatpak_apps():
    r = run(["flatpak", "list", "--app", "--columns=application"], timeout=60) \
        if have("flatpak") else None
    return set(_lines(r)) if r and r.returncode == 0 else set()


def _matches(name, tokens):
    """Le dossier correspond-il clairement à quelque chose d'installé ?

    Volontairement strict : seul un nom identique (le dossier entier ou un
    de ses morceaux) compte. Mieux vaut proposer trop de dossiers et laisser
    l'utilisateur trier que d'en cacher.
    """
    n = _norm(name)
    if len(n) < 3 or n in _CONFIG_KEEP or n in tokens:
        return True
    generic = {"org", "com", "io", "net", "gnome", "github", "gitlab", "freedesktop",
               "app", "apps", "config", "data", "cache", "desktop", "linux", "kde"}
    for part in re.split(r"[^A-Za-z0-9]+", name):
        p = _norm(part)
        if len(p) >= 4 and p not in generic and p in tokens:
            return True
    return False


def _entry(path):
    try:
        mtime = path.stat().st_mtime
        date = datetime.fromtimestamp(mtime).strftime("%d/%m/%Y")
    except OSError:
        date = ""
    return {"name": str(path), "display": _home_display(path),
            "size": dir_size(path), "date": date}


def list_config_orphans():
    """Dossiers de config, de données ou de cache sans appli correspondante.

    Correspondance devinée d'après les noms : une vue de vérification,
    rien n'est coché par défaut, et les dossiers partent à la corbeille.
    """
    tokens = _known_tokens()
    found = []
    for root in CONFIG_ROOTS:
        if not root.is_dir():
            continue
        for entry in sorted(root.iterdir()):
            if entry.name.startswith(".") or entry.is_symlink() or not entry.is_dir():
                continue
            if not _matches(entry.name, tokens):
                found.append(_entry(entry))
    var_app = HOME / ".var" / "app"
    if var_app.is_dir():
        installed = flatpak_apps()
        for entry in sorted(var_app.iterdir()):
            if entry.is_dir() and entry.name not in installed:
                found.append(_entry(entry))
    return sorted(found, key=lambda e: -e["size"])


def trash_paths(paths):
    """Met les dossiers à la corbeille (récupérables) avec gio."""
    allowed = [str(r) for r in CONFIG_ROOTS] + [str(HOME / ".var" / "app")]
    for p in paths:
        parent = os.path.dirname(os.path.abspath(p))
        if parent not in allowed:
            return False, f"Chemin refusé : {p}"
    if not have("gio"):
        return False, "gio est introuvable"
    r = run(["gio", "trash", "--", *paths], env=os.environ, timeout=300)
    if r is None or r.returncode != 0:
        return False, f"gio trash a échoué : {_tail(r)}"
    return True, f"{_count(len(paths), 'dossier')} à la corbeille"
