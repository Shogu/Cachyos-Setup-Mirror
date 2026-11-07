"""Accès direct au serveur OpenCode 2.x : flux d'événements et infos de session.

Les requêtes réutilisent le cookie de la session appairée, lu dans le
gestionnaire de cookies de WebKit. Un seul abonnement au flux, quel que soit
l'état de l'interface.
"""

import json

from gi.repository import Gio, GLib, GObject, Soup

from config import BASE_URL
from journal import log

EVENT_PATH = "/api/event"
RETRY_MIN_SECONDS = 2
RETRY_MAX_SECONDS = 60


def is_cancelled(error):
    return error.matches(Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED)


class Server(GObject.Object):
    __gsignals__ = {
        "event": (GObject.SignalFlags.RUN_FIRST, None, (str, object)),
    }

    def __init__(self, network_session):
        super().__init__()
        self._cookie_manager = network_session.get_cookie_manager()
        self._soup = Soup.Session(timeout=0)
        self._cancellable = Gio.Cancellable()
        self._cookie_header = ""
        self._cookies_loaded = False
        self._pending = []
        self._retry_id = 0
        self._retry_delay = RETRY_MIN_SECONDS
        self._sessions = {}
        self._waiting = {}

    def start(self):
        if self._cookies_loaded:
            return
        self._subscribe()

    def destroy(self):
        if self._retry_id:
            GLib.Source.remove(self._retry_id)
            self._retry_id = 0
        self._cancellable.cancel()
        self._soup.abort()

    def _subscribe(self):
        self._cookie_manager.get_cookies(BASE_URL, self._cancellable, self._on_cookies)

    def _retry_later(self):
        log("flux : nouvelle tentative dans %d s" % self._retry_delay)
        self._retry_id = GLib.timeout_add_seconds(self._retry_delay, self._on_retry)
        self._retry_delay = min(self._retry_delay * 2, RETRY_MAX_SECONDS)

    def _on_retry(self):
        self._retry_id = 0
        self._subscribe()
        return GLib.SOURCE_REMOVE

    def _message(self, path, method="GET", body=None):
        message = Soup.Message.new(method, BASE_URL + path)
        if self._cookie_header:
            message.get_request_headers().append("Cookie", self._cookie_header)
        if body is not None:
            message.set_request_body_from_bytes("application/json", GLib.Bytes.new(json.dumps(body).encode("utf-8")))
        return message

    def _on_cookies(self, manager, result):
        try:
            cookies = manager.get_cookies_finish(result)
        except GLib.Error as error:
            if not is_cancelled(error):
                log("flux : cookies illisibles (%s)" % error.message)
                self._retry_later()
            return
        self._cookie_header = Soup.cookies_to_cookie_header(cookies)
        self._cookies_loaded = True
        for session_id in self._waiting:
            self._request_session(session_id)
        pending, self._pending = self._pending, []
        for request in pending:
            self.request_json(*request)

        message = self._message(EVENT_PATH + "?cursor=now")
        self._soup.send_async(
            message, GLib.PRIORITY_DEFAULT, self._cancellable, self._on_subscribed, message
        )

    def _on_subscribed(self, soup, result, message):
        try:
            stream = soup.send_finish(result)
        except GLib.Error as error:
            if not is_cancelled(error):
                log("flux : connexion impossible (%s)" % error.message)
                self._retry_later()
            return
        content_type = message.get_response_headers().get_content_type()[0]
        if message.get_status() != Soup.Status.OK or content_type != "text/event-stream":
            log("flux : réponse inattendue %d %s" % (message.get_status(), content_type))
            stream.close_async(GLib.PRIORITY_DEFAULT, None, None)
            self._retry_later()
            return
        log("flux : abonné à " + EVENT_PATH)
        self._retry_delay = RETRY_MIN_SECONDS
        self._read_line(Gio.DataInputStream.new(stream), [])

    def _read_line(self, lines, data):
        lines.read_line_async(GLib.PRIORITY_DEFAULT, self._cancellable, self._on_line, data)

    def _on_line(self, lines, result, data):
        try:
            line = lines.read_line_finish_utf8(result)[0]
        except GLib.Error as error:
            if not is_cancelled(error):
                log("flux : lecture interrompue (%s)" % error.message)
                self._retry_later()
            return
        if line is None:
            log("flux : fermé par le serveur")
            self._retry_later()
            return
        if line.startswith("data:"):
            data.append(line[6:] if line.startswith("data: ") else line[5:])
        elif not line and data:
            self._dispatch("\n".join(data))
            data.clear()
        self._read_line(lines, data)

    def _dispatch(self, payload):
        try:
            event = json.loads(payload)
        except ValueError:
            log("flux : événement illisible " + payload[:120])
            return
        kind = event.get("type", "")
        data = event.get("data") or {}
        self._update_sessions(kind, data)
        self.emit("event", kind, data)

    def _update_sessions(self, kind, data):
        if kind == "session.created":
            self._sessions[data["sessionID"]] = {
                "id": data["sessionID"],
                "parentID": data.get("parentID"),
                "title": data.get("title", ""),
            }
        elif kind == "session.renamed" and data["sessionID"] in self._sessions:
            self._sessions[data["sessionID"]]["title"] = data["title"]
        elif kind == "session.deleted":
            self._sessions.pop(data["sessionID"], None)

    def get_session(self, session_id, callback):
        """callback(info) avec le dict Session.Info d'OpenCode, ou None en cas d'échec."""
        if session_id in self._sessions:
            callback(self._sessions[session_id])
            return
        waiting = self._waiting.setdefault(session_id, [])
        waiting.append(callback)
        if len(waiting) == 1 and self._cookie_header:
            self._request_session(session_id)

    def _request_session(self, session_id):
        message = self._message("/api/session/" + GLib.Uri.escape_string(session_id, None, False))
        self._soup.send_and_read_async(
            message, GLib.PRIORITY_DEFAULT, self._cancellable, self._on_session, (session_id, message)
        )

    def _on_session(self, soup, result, request):
        session_id, message = request
        info = None
        try:
            body = soup.send_and_read_finish(result)
        except GLib.Error as error:
            if is_cancelled(error):
                return
            log("session %s : %s" % (session_id, error.message))
        else:
            if message.get_status() == Soup.Status.OK:
                info = json.loads(body.get_data())["data"]
                self._sessions[session_id] = info
            else:
                log("session %s : réponse %d" % (session_id, message.get_status()))
        for callback in self._waiting.pop(session_id, []):
            callback(info)

    def request_json(self, method, path, body, callback):
        """callback(data) avec le champ « data » de la réponse JSON, ou None en cas d'échec.

        Mise en attente tant que le cookie d'appairage n'a pas été lu.
        """
        if not self._cookies_loaded:
            self._pending.append((method, path, body, callback))
            return
        message = self._message(path, method, body)
        self._soup.send_and_read_async(
            message, GLib.PRIORITY_DEFAULT, self._cancellable, self._on_json, (message, callback)
        )

    def _on_json(self, soup, result, request):
        message, callback = request
        try:
            body = soup.send_and_read_finish(result)
        except GLib.Error as error:
            if is_cancelled(error):
                return
            log("requête %s : %s" % (message.get_uri().get_path(), error.message))
            callback(None)
            return
        status = message.get_status()
        if not 200 <= status < 300:
            log("requête %s : réponse %d" % (message.get_uri().get_path(), status))
            callback(None)
            return
        raw = body.get_data()
        data = json.loads(raw) if raw else {}
        callback(data.get("data", data) if isinstance(data, dict) else data)
