"""Grimoire: document operations independent from GTK."""
import hashlib
import html
import json
import os
from pathlib import Path
import re
import tempfile


class ConflictError(OSError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data):
    path = Path(path)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    fd, tmp = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


class Document:
    def __init__(self):
        self.path = None
        self.text = ''
        self.saved = ''
        self.fingerprint = None
        self.newline = '\n'
        self.bom = False

    @property
    def dirty(self):
        return self.text != self.saved

    def load(self, path):
        path = Path(path).expanduser().resolve()
        data = path.read_bytes()
        text = data.decode('utf-8-sig')
        self.path, self.fingerprint = path, digest(data)
        self.newline = '\r\n' if b'\r\n' in data else '\n'
        self.bom = data.startswith(b'\xef\xbb\xbf')
        self.text = self.saved = text.replace('\r\n', '\n')

    def save(self, target=None):
        path = Path(target).expanduser().absolute() if target else self.path
        if path is None:
            raise ValueError('Choisissez un fichier.')
        if self.path and path.resolve() == self.path.resolve():
            if not path.exists() or digest(path.read_bytes()) != self.fingerprint:
                raise ConflictError('Le fichier a changé sur le disque. Enregistrez une copie ou rechargez-le.')
        elif path.exists():
            raise FileExistsError('Ce fichier existe déjà. Choisissez un autre nom pour préserver son contenu.')
        data = self.text.replace('\n', self.newline).encode('utf-8')
        if self.bom:
            data = b'\xef\xbb\xbf' + data
        atomic_write(path, data)
        self.path, self.fingerprint, self.saved = path.resolve(), digest(data), self.text

    def rename(self, name):
        if not self.path:
            raise ValueError('Enregistrez le document avant de le renommer.')
        name = name.strip()
        if not name or '/' in name or '\\' in name or name in ('.', '..'):
            raise ValueError('Choisissez un nom de fichier sans séparateur de dossier.')
        if not name.lower().endswith(('.md', '.markdown')):
            name += '.md'
        target = self.path.with_name(name)
        if target == self.path:
            return
        if target.exists():
            raise FileExistsError('Un fichier porte déjà ce nom.')
        self.save()
        # Hard-link creation is no-clobber, unlike a POSIX rename.
        os.link(self.path, target)
        self.path.unlink()
        self.path = target


def headings(text):
    result, fence = [], None
    lines = text.splitlines()
    for i, line in enumerate(lines):
        match = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if match:
            token, rest = match.groups()
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence) and not rest.strip():
                fence = None
            continue
        if fence:
            continue
        m = re.match(r'^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$', line)
        if m:
            result.append((i, len(m[1]), m[2]))
        elif i and re.fullmatch(r' {0,3}(=+|-+)\s*', line) and lines[i-1].strip():
            if not re.match(r'^\s*(#|[-*+]\s)', lines[i-1]):
                result.append((i-1, 1 if '=' in line else 2, lines[i-1].strip()))
    return result


def code_block(text='', language='fish'):
    fence = '`' * max(3, max((len(x) + 1 for x in re.findall(r'`+', text)), default=3))
    return '\n' + fence + language + '\n' + text + ('\n' if not text.endswith('\n') else '') + fence + '\n'


def state_dir():
    p = Path(os.environ.get('XDG_STATE_HOME', Path.home()/'.local/state'))/'grimoire'
    p.mkdir(parents=True, exist_ok=True, mode=0o700)
    return p


def css_family(name, generic):
    """CSS font stack starting with the system family, then the generic fallback."""
    name = re.sub(r'[^\w .+-]', '', name or '').strip()
    return f'"{name}",{generic}' if name else generic


def render(text, dark=False, accent='#3584e4', sans='', mono=''):
    import markdown
    import bleach
    from pygments.formatters import HtmlFormatter
    body = markdown.markdown(text, extensions=['fenced_code', 'tables', 'sane_lists', 'codehilite'],
                             extension_configs={'codehilite': {'guess_lang': False}})
    body = bleach.clean(body,
                        tags=['p', 'div', 'span', 'pre', 'code', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                              'blockquote', 'ul', 'ol', 'li', 'strong', 'em', 'del', 's', 'a', 'img',
                              'table', 'thead', 'tbody', 'tr', 'td', 'th', 'hr', 'br'],
                        attributes={'*': ['class'], 'a': ['href', 'title'], 'img': ['src', 'alt', 'title'],
                                    'ol': ['start'], 'td': ['align'], 'th': ['align']},
                        protocols=['http', 'https', 'mailto', 'file', 'data'], strip=True)
    # Values of the libadwaita view_bg_color / view_fg_color / secondary background named colours.
    bg, fg, panel = ('#1d1d20', '#ffffff', '#28282c') if dark else ('#ffffff', '#000000', '#f3f3f5')
    scheme = 'dark' if dark else 'light'
    # Scripts, frames, forms and remote images are blocked by CSP, independently of Markdown HTML.
    return '''<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src file: data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<meta name="viewport" content="width=device-width, initial-scale=1"><style>''' + f'''
:root {{color-scheme:{scheme}}}
body {{background:{bg};color:{fg};font:17px/1.65 {css_family(sans, 'system-ui,sans-serif')};margin:0;padding:32px;overflow-wrap:anywhere}}
main {{max-width:820px;margin:auto}} h1,h2,h3 {{line-height:1.25}} h1 {{font-size:2em}} h2 {{border-bottom:1px solid #8884;padding-bottom:8px}}
a {{color:{accent}}} pre,code {{font-family:{css_family(mono, 'monospace')}}} pre {{overflow:auto;padding:18px;background:{panel};border-radius:10px}}
code {{background:{panel};padding:2px 4px;border-radius:4px}} pre code {{padding:0}} img {{max-width:100%;height:auto}}
blockquote {{border-left:4px solid {accent};margin-left:0;padding:4px 20px;background:{panel}}}
table {{border-collapse:collapse;width:100%}} td,th {{border:1px solid #8885;padding:8px 12px}} hr {{border:0;border-top:1px solid #8885}}
''' + HtmlFormatter(style='native' if dark else 'friendly').get_style_defs('.codehilite') + '</style></head><body><main>' + body + '</main></body></html>'
