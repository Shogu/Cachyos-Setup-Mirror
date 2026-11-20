#!/usr/bin/env python3
"""Contrôle en direct du mod WebPanel Auto-Discard sur votre vrai Vivaldi.

Affiche l'état de chaque web panel : affiché, caché (avec le compte à rebours
avant déchargement), exclu, ou déchargé.

  python3 vivaldi-webpanel-status.py           # un relevé
  python3 vivaldi-webpanel-status.py --watch   # rafraîchi toutes les 5 s (Ctrl+C pour quitter)

Le script a besoin que Vivaldi tourne avec le port de débogage 9222. Sinon, il
propose de fermer puis relancer Vivaldi avec ce port (la session est restaurée).
"""
import argparse, base64, json, os, re, shutil, socket, struct, subprocess, sys, time
import urllib.parse, urllib.request
from pathlib import Path

PORT = 9222
VIVALDI_UI = 'mpognobbkildjkofajifpdfhcoklimli/window.html'
MOD_JS = Path('/usr/share/vivaldi-webpanel-auto-discard/webpanel-auto-discard.js')


# --- Client WebSocket / CDP minimal -------------------------------------------

class CDP:
    def __init__(self, ws_url):
        u = urllib.parse.urlparse(ws_url)
        self.sock = socket.create_connection((u.hostname, u.port), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f'GET {u.path} HTTP/1.1\r\nHost: {u.hostname}:{u.port}\r\n'
                           'Upgrade: websocket\r\nConnection: Upgrade\r\n'
                           f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
        resp = b''
        while b'\r\n\r\n' not in resp:
            resp += self.sock.recv(4096)
        if b' 101 ' not in resp.split(b'\r\n')[0]:
            raise RuntimeError(f'Handshake WebSocket refusé : {resp[:200]!r}')
        self.buf = resp.split(b'\r\n\r\n', 1)[1]
        self.next_id = 0

    def _recv_exact(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError('WebSocket fermé')
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def _recv_msg(self):
        data = b''
        while True:
            b1, b2 = self._recv_exact(2)
            length = b2 & 0x7F
            if length == 126:
                length = struct.unpack('>H', self._recv_exact(2))[0]
            elif length == 127:
                length = struct.unpack('>Q', self._recv_exact(8))[0]
            payload = self._recv_exact(length)
            opcode = b1 & 0x0F
            if opcode == 8:
                raise ConnectionError('WebSocket fermé par le navigateur')
            if opcode in (0, 1, 2):
                data += payload
                if b1 & 0x80:
                    return json.loads(data)

    def _send(self, obj):
        payload = json.dumps(obj).encode()
        header = bytearray([0x81])
        n = len(payload)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header += bytes([0x80 | 126]) + struct.pack('>H', n)
        else:
            header += bytes([0x80 | 127]) + struct.pack('>Q', n)
        mask = os.urandom(4)
        self.sock.sendall(bytes(header) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def call(self, method, params=None, session=None):
        self.next_id += 1
        msg = {'id': self.next_id, 'method': method, 'params': params or {}}
        if session:
            msg['sessionId'] = session
        self._send(msg)
        while True:
            r = self._recv_msg()
            if r.get('id') == self.next_id:
                if 'error' in r:
                    raise RuntimeError(f"{method}: {r['error'].get('message')}")
                return r.get('result', {})

    def attach(self, target_id):
        return self.call('Target.attachToTarget', {'targetId': target_id, 'flatten': True})['sessionId']

    def eval(self, session, expr):
        r = self.call('Runtime.evaluate', {'expression': expr, 'awaitPromise': True,
                                           'returnByValue': True}, session)
        if 'exceptionDetails' in r:
            raise RuntimeError(r['exceptionDetails'].get('exception', {}).get('description')
                               or r['exceptionDetails'].get('text'))
        return r['result'].get('value')

    def targets(self):
        return self.call('Target.getTargets')['targetInfos']


# --- Connexion à Vivaldi ------------------------------------------------------

def version():
    try:
        return json.load(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/version', timeout=2))
    except Exception:
        return None


def vivaldi_running():
    return subprocess.run(['pgrep', '-x', 'vivaldi-bin'], stdout=subprocess.DEVNULL).returncode == 0


def relaunch_with_port():
    binary = shutil.which('vivaldi') or shutil.which('vivaldi-stable')
    if not binary:
        sys.exit('Vivaldi introuvable.')
    if vivaldi_running():
        rep = input("Vivaldi tourne sans port de débogage. Le fermer et le relancer avec ?\n"
                    "(vos onglets sont restaurés si Vivaldi rouvre la dernière session) [o/N] ")
        if rep.strip().lower() not in ('o', 'oui', 'y'):
            sys.exit('Abandon.')
        subprocess.run(['pkill', '-TERM', '-x', 'vivaldi-bin'])
        for _ in range(30):
            if not vivaldi_running():
                break
            time.sleep(0.5)
        else:
            sys.exit("Vivaldi ne s'est pas fermé, réessayez.")
    subprocess.Popen([binary, f'--remote-debugging-port={PORT}'], start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        if version():
            return
        time.sleep(0.5)
    sys.exit("Vivaldi relancé, mais le port de débogage ne répond pas.")


def connect():
    v = version()
    if not v:
        relaunch_with_port()
        v = version()
    cdp = CDP(v['webSocketDebuggerUrl'])
    for _ in range(40):
        ui = next((t for t in cdp.targets() if VIVALDI_UI in t['url']), None)
        if ui:
            break
        time.sleep(0.5)
    else:
        sys.exit("Interface de Vivaldi introuvable.")
    session = cdp.attach(ui['targetId'])
    for _ in range(40):
        if cdp.eval(session, 'typeof window.__wpad') == 'object':
            return cdp, session
        time.sleep(0.5)
    sys.exit("Le mod n'est pas chargé dans Vivaldi.\n"
             "→ sudo vivaldi-webpanel-auto-discard install, puis redémarrer Vivaldi.")


# --- Affichage ----------------------------------------------------------------

def excluded_domains():
    try:
        m = re.search(r'const EXCLUDE = \[(.*?)\];', MOD_JS.read_text())
        return re.findall(r"['\"]([^'\"]+)['\"]", m.group(1)) if m else []
    except OSError:
        return []


def duration(ms):
    s = max(0, int(ms / 1000))
    return f'{s // 60} min {s % 60:02d} s' if s >= 60 else f'{s} s'


def render(d, exclude):
    now = time.time() * 1000
    lines = [f"Délai de déchargement : {duration(d['delay'])}"
             + (f"   ·   exclus : {', '.join(exclude)}" if exclude else ''), '']
    panels = [t for t in d['tabs'] if t['panelId']]
    if not panels:
        lines.append("Aucun web panel chargé pour l'instant (ils se chargent à la première ouverture).")
    for t in panels:
        host = urllib.parse.urlparse(t['url']).hostname or t['url'] or '?'
        is_excl = any(host == e or host.endswith('.' + e) for e in exclude)
        since = d['hiddenSince'].get(str(t['id']))
        if t['discarded']:
            state = '○ déchargé ✔'
        elif t['shown']:
            state = '● affiché'
        elif is_excl:
            state = '◌ caché, exclu (jamais déchargé)'
        elif t['audible']:
            state = '♪ caché mais joue du son (attend la fin)'
        elif since is not None:
            left = d['delay'] - (now - since)
            state = f"◐ caché depuis {duration(now - since)} → déchargement dans ~{duration(left)}"
        else:
            state = '◐ caché (pris en compte au prochain passage, ≤ 5 s)'
        lines.append(f'  {host:<32} {state}')
    if d['lastErrors']:
        lines += ['', 'Erreurs récentes :'] + [f"  {e.get('message')}" for e in d['lastErrors'][-5:]]
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--watch', action='store_true', help='rafraîchir toutes les 5 s')
    args = ap.parse_args()
    cdp, session = connect()
    exclude = excluded_domains()
    try:
        while True:
            out = render(cdp.eval(session, '__wpad.diag()'), exclude)
            if args.watch:
                print('\033[2J\033[H' + time.strftime('%H:%M:%S') + '  (Ctrl+C pour quitter)\n')
            print(out, flush=True)
            if not args.watch:
                break
            time.sleep(5)
    except KeyboardInterrupt:
        print()


if __name__ == '__main__':
    main()
