"""Grimoire: note and folder operations shared with the Topbar Center Widget.

Everything here is independent from GTK windows so it can run from a window
menu, from the D-Bus action used by the widget, or from the search provider.
"""
import functools
import os
from pathlib import Path
import re
import shutil
import uuid
from datetime import date, datetime, timedelta, timezone

from gi.repository import Gio, GLib
from core import atomic_write, retitle

MARKDOWN = ('.md', '.markdown')
WIDGET_UUID = 'topbar-center-widget@ogu'
WIDGET_SCHEMA = 'org.gnome.shell.extensions.topbar-center-widget'


def check_name(name):
    name = name.strip()
    if not name or '/' in name or '\\' in name or name in ('.', '..'):
        raise ValueError('Choisissez un nom sans séparateur de dossier.')
    return name


def link_rename(source, target):
    """Rename without overwriting: hard links are created no-clobber."""
    if target.exists():
        raise FileExistsError(f'« {target.name} » existe déjà.')
    os.link(source, target)
    source.unlink()


def rename_note(path, name):
    name = check_name(name)
    if not name.lower().endswith(MARKDOWN):
        name += '.md'
    target = path.with_name(name)
    if target != path:
        # Keep the leading H1 title in sync with the new file name when they match.
        try:
            old_text = Path(path).read_text(encoding='utf-8', errors='replace')
        except OSError:
            old_text = ''
        new_text = retitle(old_text, Path(path).stem, target.stem)
        if new_text != old_text:
            atomic_write(path, new_text.encode('utf-8'))
        link_rename(path, target)
    return target


def free_name(folder, stem, suffix):
    candidate = folder/f'{stem}{suffix}'
    n = 2
    while candidate.exists():
        candidate = folder/f'{stem} {n}{suffix}'
        n += 1
    return candidate


def duplicate_note(path):
    target = free_name(path.parent, f'{path.stem} (copie)', path.suffix)
    shutil.copy2(path, target)
    return target


def move_note(path, folder):
    target = Path(folder)/path.name
    if target == path:
        return path
    if target.exists():
        raise FileExistsError(f'« {path.name} » existe déjà dans « {Path(folder).name} ».')
    shutil.move(str(path), str(target))
    return target


def trash(path):
    Gio.File.new_for_path(str(path)).trash(None)


def notes_in(folder):
    try:
        return [p for p in Path(folder).iterdir()
                if p.is_file() and p.suffix.lower() in MARKDOWN and not p.name.startswith('.')]
    except OSError:
        return []


# ------------------------------------------------------------- widget link

@functools.cache
def widget_settings():
    """Settings of the Topbar Center Widget extension, if it is installed."""
    for base in (Path(GLib.get_user_data_dir()), *map(Path, GLib.get_system_data_dirs())):
        schemas = base/'gnome-shell'/'extensions'/WIDGET_UUID/'schemas'
        if not (schemas/'gschemas.compiled').exists():
            continue
        try:
            source = Gio.SettingsSchemaSource.new_from_directory(
                str(schemas), Gio.SettingsSchemaSource.get_default(), False)
        except GLib.Error:
            continue
        schema = source.lookup(WIDGET_SCHEMA, False)
        if schema:
            return Gio.Settings.new_full(schema, None, None)
    return None


def _moved(value, old, new):
    """New path for `value` if it is `old` or lies inside it, else None."""
    if value == old:
        return new
    if value.startswith(old + '/'):
        return new + value[len(old):]
    return None


def remap_paths(old, new, grimoire=None):
    """Keep the widget (and Grimoire's pins) pointing at a renamed note or folder."""
    old, new = str(old), str(new)
    if grimoire is not None:
        grimoire.set_strv('pinned-folders', [_moved(f, old, new) or f for f in grimoire.get_strv('pinned-folders')])
        current = grimoire.get_string('pinned-folder')
        if _moved(current, old, new):
            grimoire.set_string('pinned-folder', _moved(current, old, new))
    widget = widget_settings()
    if widget is None:
        return
    for key in ('hidden-folders', 'pinned-notes'):
        widget.set_strv(key, [_moved(p, old, new) or p for p in widget.get_strv(key)])
    selected = widget.get_string('selected-folder')
    if _moved(selected, old, new):
        widget.set_string('selected-folder', _moved(selected, old, new))
    colors = widget.get_value('note-colors').unpack()
    widget.set_value('note-colors', GLib.Variant('a{ss}', {_moved(p, old, new) or p: c for p, c in colors.items()}))


def forget_path(path):
    """Drop a trashed note from the widget's pins and colours."""
    widget = widget_settings()
    if widget is None:
        return
    path = str(path)
    widget.set_strv('pinned-notes', [p for p in widget.get_strv('pinned-notes') if p != path])
    colors = widget.get_value('note-colors').unpack()
    colors.pop(path, None)
    widget.set_value('note-colors', GLib.Variant('a{ss}', colors))


def widget_pinned(path):
    widget = widget_settings()
    return widget is not None and str(path) in widget.get_strv('pinned-notes')


def toggle_widget_pin(path):
    widget = widget_settings()
    if widget is None:
        raise ValueError('Topbar Center Widget n’est pas installé.')
    pins = widget.get_strv('pinned-notes')
    path = str(path)
    pinned = path not in pins
    widget.set_strv('pinned-notes', pins + [path] if pinned else [p for p in pins if p != path])
    return pinned


def rename_folder(folder, name, grimoire):
    """Rename a pinned folder on disk and update every reference to it."""
    folder = Path(folder)
    if not folder.is_dir():
        raise FileNotFoundError(f'Dossier introuvable : {folder}')
    target = folder.with_name(check_name(name))
    if target == folder:
        return folder
    if target.exists():
        raise FileExistsError(f'« {target.name} » existe déjà.')
    folder.rename(target)
    remap_paths(folder, target, grimoire)
    return target


# --------------------------------------------------------------- calendar

HOUR = re.compile(r'\b([01]?\d|2[0-3])\s*[h:]\s*([0-5]\d)?\b', re.IGNORECASE)


def _escape(text):
    return text.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')


def _fold(line):
    data, parts = line.encode(), []
    while len(data) > 75:
        cut = 75 if not parts else 74
        while cut and (data[cut] & 0xC0) == 0x80:
            cut -= 1
        parts.append(data[:cut])
        data = data[cut:]
    parts.append(data)
    return '\r\n '.join(p.decode() for p in parts)


def event_ics(title, description, day=None):
    """One VEVENT for today: at the hour written in the title, else all day."""
    day = day or date.today()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Grimoire//FR', 'BEGIN:VEVENT',
             f'UID:{uuid.uuid4()}@grimoire', f'DTSTAMP:{stamp}', f'SUMMARY:{_escape(title)}']
    match = HOUR.search(title)
    if match:
        start = datetime(day.year, day.month, day.day, int(match[1]), int(match[2] or 0))
        end = start + timedelta(hours=1)
        lines += [f'DTSTART:{start:%Y%m%dT%H%M%S}', f'DTEND:{end:%Y%m%dT%H%M%S}']
    else:
        lines += [f'DTSTART;VALUE=DATE:{day:%Y%m%d}', f'DTEND;VALUE=DATE:{day + timedelta(days=1):%Y%m%d}']
    if description.strip():
        lines.append(f'DESCRIPTION:{_escape(description.strip())}')
    lines += ['END:VEVENT', 'END:VCALENDAR']
    return '\r\n'.join(_fold(line) for line in lines) + '\r\n'


def event_file(path):
    """Write the note as an .ics in the runtime dir and return it."""
    directory = Path(GLib.get_user_runtime_dir())/'grimoire'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    for old in directory.glob('*.ics'):
        old.unlink(missing_ok=True)
    target = directory/f'{uuid.uuid4()}.ics'
    target.write_text(event_ics(Path(path).stem, Path(path).read_text(encoding='utf-8', errors='replace')))
    return target


# ----------------------------------------------------------------- search

def _fold_text(text):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', text.casefold()) if unicodedata.category(c) != 'Mn')


def search(folders, terms, limit=10):
    """Notes of the pinned folders containing every term, title matches first."""
    terms = [_fold_text(t) for t in terms if t.strip()]
    if not terms:
        return []
    hits = []
    for folder in folders:
        for path in notes_in(folder):
            title = _fold_text(path.stem)
            if all(t in title for t in terms):
                hits.append((0, -path.stat().st_mtime, str(path)))
                continue
            try:
                body = _fold_text(path.read_text(encoding='utf-8', errors='replace'))
            except OSError:
                continue
            if all(t in title or t in body for t in terms):
                hits.append((1, -path.stat().st_mtime, str(path)))
    return [p for *_, p in sorted(hits)[:limit]]


def snippet(path, terms, width=90):
    try:
        text = Path(path).read_text(encoding='utf-8', errors='replace')
    except OSError:
        return ''
    flat = ' '.join(re.sub(r'^\[[ xX]\]\s*', '', line.strip(' #>*-')) for line in text.splitlines() if line.strip())
    folded = _fold_text(flat)
    at = min((folded.find(_fold_text(t)) for t in terms if _fold_text(t) in folded), default=0)
    start = 0 if at < 40 else at - 20
    return ('…' if start else '') + flat[start:start + width].strip() + ('…' if len(flat) > start + width else '')
