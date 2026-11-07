"""Analyse des fichiers fish, sans dépendance à GTK.

- alias et abbr définis dans un fichier ;
- fichiers inclus par « source » (suivis récursivement) ;
- description d'une fonction ;
- vérification de syntaxe (fish -n) et reformatage (fish_indent).
"""

import os
import re
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Shortcut:
    kind: str  # "alias" ou "abbr"
    name: str
    value: str
    line: int  # numéro de ligne, à partir de 1
    text: str  # ligne d'origine, telle quelle


# Options d'abbr qui consomment l'argument suivant.
_ABBR_OPTS_WITH_VALUE = {
    "-p", "--position", "-r", "--regex", "-f", "--function",
    "-c", "--command",
}
# Sous-commandes d'abbr qui ne définissent rien.
_ABBR_NON_DEFINING = {
    "-e", "--erase", "-l", "--list", "-s", "--show", "-q", "--query",
    "--rename", "-h", "--help",
}


def _split(line: str) -> list[str] | None:
    try:
        return shlex.split(line, comments=True)
    except ValueError:
        return None


def _parse_segment(head: str, number: int, raw: str) -> Shortcut | None:
    words = head.split()
    if not words or words[0] not in ("alias", "abbr"):
        return None
    tokens = _split(head)
    if not tokens or len(tokens) < 2:
        return None
    if words[0] == "alias":
        args = [t for t in tokens[1:] if t not in ("-s", "--save")]
        if not args or args[0].startswith("-"):
            return None
        if "=" in args[0]:
            name, value = args[0].split("=", 1)
            if args[1:]:
                value = " ".join([value, *args[1:]]).strip()
        else:
            name, value = args[0], " ".join(args[1:])
        return Shortcut("alias", name, value, number, raw) if name else None
    args = tokens[1:]
    if any(a in _ABBR_NON_DEFINING for a in args):
        return None
    positional: list[str] = []
    function = None
    options_done = False
    i = 0
    while i < len(args):
        a = args[i]
        if options_done:
            positional.append(a)
            i += 1
            continue
        if a == "--":
            options_done = True
            i += 1
            continue
        if a in ("-f", "--function") and i + 1 < len(args):
            function = args[i + 1]
            i += 2
            continue
        if a.startswith("--function="):
            function = a.split("=", 1)[1]
            i += 1
            continue
        if a in _ABBR_OPTS_WITH_VALUE:
            i += 2
            continue
        if a.startswith("-"):
            i += 1
            continue
        positional.append(a)
        i += 1
    if not positional:
        return None
    value = " ".join(positional[1:])
    if not value and function:
        value = f"→ fonction {function}"
    return Shortcut("abbr", positional[0], value, number, raw)


def parse_shortcuts(text: str) -> list[Shortcut]:
    """Repère les définitions « alias … » et « abbr … » d'un fichier."""
    found: list[Shortcut] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for segment in stripped.split(";"):
            item = _parse_segment(segment.strip(), number, raw)
            if item is not None:
                found.append(item)
    return found


_SOURCE_RE = re.compile(r"^\s*(?:source|\.)\s+(.+?)\s*(?:;.*)?$")


def _expand(path_text: str, base: Path) -> Path | None:
    tokens = _split(path_text)
    if not tokens:
        return None
    token = tokens[0]
    if token.startswith("("):
        return None  # substitution de commande : impossible à résoudre ici
    cfg = str(base)
    for var in ("$__fish_config_dir", "{$__fish_config_dir}"):
        token = token.replace(var, cfg)
    token = token.replace("$HOME", str(Path.home())).replace("{$HOME}", str(Path.home()))
    xdg = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    token = token.replace("$XDG_CONFIG_HOME", xdg).replace("{$XDG_CONFIG_HOME}", xdg)
    if "$" in token or "*" in token:
        return None
    path = Path(os.path.expanduser(token))
    if not path.is_absolute():
        path = base / path
    return path


def find_sources(path: Path, base: Path, exclude: set[Path], depth: int = 3) -> list[Path]:
    """Fichiers chargés par « source » depuis `path`, récursivement (sans doublon)."""
    result: list[Path] = []
    seen = {p.resolve() for p in exclude if p.exists()}

    def walk(current: Path, level: int):
        if level < 0:
            return
        try:
            text = current.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        for raw in text.splitlines():
            line = raw.strip()
            if line.startswith("#"):
                continue
            match = _SOURCE_RE.match(line)
            if not match:
                continue
            target = _expand(match.group(1), base)
            if target is None or not target.is_file():
                continue
            real = target.resolve()
            if real in seen:
                continue
            seen.add(real)
            result.append(target)
            walk(target, level - 1)

    seen.add(path.resolve())
    walk(path, depth)
    return result


_FUNC_LINE_RE = re.compile(r"^\s*function\s+(.*)$")


def function_description(text: str, name: str) -> str | None:
    """Valeur de --description/-d sur la ligne « function <name> … »."""
    fallback = None
    for raw in text.splitlines():
        match = _FUNC_LINE_RE.match(raw)
        if not match:
            continue
        tokens = _split(match.group(1))
        if not tokens:
            continue
        desc = None
        for i, tok in enumerate(tokens):
            if tok in ("-d", "--description") and i + 1 < len(tokens):
                desc = tokens[i + 1]
                break
            if tok.startswith("--description="):
                desc = tok.split("=", 1)[1]
                break
        if tokens[0] == name:
            return desc or None
        if fallback is None and desc:
            fallback = desc
    return fallback


_ERR_RE = re.compile(r"\(line (\d+)\):\s*(.*)")


def check_syntax(text: str) -> tuple[int, str] | None:
    """Renvoie (ligne, message) si fish -n trouve une erreur, sinon None.

    Renvoie aussi None si fish n'est pas installé.
    """
    fd, tmp = tempfile.mkstemp(suffix=".fish", prefix="fisherman-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        try:
            proc = subprocess.run(
                ["fish", "--no-config", "-n", tmp],
                capture_output=True, text=True, timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if proc.returncode == 0:
            return None
        for line in proc.stderr.splitlines():
            match = _ERR_RE.search(line)
            if match:
                return int(match.group(1)), match.group(2).strip()
        lines = [l for l in proc.stderr.splitlines() if l.strip()]
        return 1, (lines[0] if lines else "erreur de syntaxe")
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def indent(text: str) -> str | None:
    """Texte reformaté par fish_indent, ou None si indisponible / en erreur."""
    try:
        proc = subprocess.run(
            ["fish_indent"], input=text, capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def first_match_line(text: str, query: str) -> tuple[int, str] | None:
    """Première ligne contenant `query` (insensible à la casse)."""
    q = query.casefold()
    for number, raw in enumerate(text.splitlines(), start=1):
        if q in raw.casefold():
            return number, raw.strip()
    return None

