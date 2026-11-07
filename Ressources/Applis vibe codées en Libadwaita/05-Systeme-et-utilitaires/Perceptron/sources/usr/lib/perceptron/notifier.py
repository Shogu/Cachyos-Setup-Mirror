"""Notifications GNOME à partir des événements d'OpenCode 2.x.

- permission.asked / permission.replied : demande d'autorisation et sa réponse ;
- form.created / form.replied / form.cancelled : question posée par l'agent ;
- session.execution.succeeded / failed / interrupted : fin d'une réponse,
  hors sessions de sous-agents.

OpenCode n'émet pas d'événement `session.status` (busy → idle) sur le flux
`/api/event` : la fin d'un tour y est signalée par les événements terminaux
`session.execution.*`.
"""

from gi.repository import Gio, GLib

from config import APP_ID

ATTENTION = {
    "permission": ("Autorisation requise", "OpenCode attend ta validation", Gio.NotificationPriority.HIGH),
    "question": ("Question d’OpenCode", "OpenCode attend ta réponse", Gio.NotificationPriority.HIGH),
    "idle": ("Réponse terminée", "OpenCode a fini de répondre", Gio.NotificationPriority.NORMAL),
}

TERMINAL = (
    "session.execution.succeeded",
    "session.execution.failed",
    "session.execution.interrupted",
)


def describe_permission(data):
    return data.get("message") or " · ".join(filter(None, (data["action"], " ".join(data.get("resources", [])))))


class Notifier:
    def __init__(self, window, server):
        self._window = window
        self._server = server
        self._shown = set()
        self._event_id = server.connect("event", self._on_event)

    def _on_event(self, _server, kind, data):
        if kind == "permission.asked":
            self._send("permission-" + data["id"], "permission", data["sessionID"], describe_permission(data))
        elif kind == "permission.replied":
            self._withdraw("permission-" + data["requestID"])
        elif kind == "form.created":
            form = data["form"]
            self._send("form-" + form["id"], "question", form["sessionID"], form["title"])
        elif kind in ("form.replied", "form.cancelled"):
            self._withdraw("form-" + data["id"])
        elif kind in TERMINAL:
            session_id = data["sessionID"]
            self._server.get_session(session_id, lambda info, sid=session_id: self._on_idle(sid, info))

    def _on_idle(self, session_id, info):
        if info is not None and info.get("parentID"):
            return
        self._send("idle-" + session_id, "idle", session_id, (info or {}).get("title", ""))

    def _send(self, key, kind, session_id, detail):
        if self._window.is_active():
            return
        title, body, priority = ATTENTION[kind]
        notification = Gio.Notification.new(title)
        notification.set_body(body + (" : " + detail if detail else "."))
        notification.set_priority(priority)
        notification.set_icon(Gio.ThemedIcon.new(APP_ID))
        notification.set_default_action_and_target("app.show-session", GLib.Variant.new_string(session_id))
        self._shown.add(key)
        self._window.get_application().send_notification(key, notification)

    def _withdraw(self, key):
        if key in self._shown:
            self._shown.discard(key)
            self._window.get_application().withdraw_notification(key)

    def withdraw_all(self):
        app = self._window.get_application()
        for key in self._shown:
            app.withdraw_notification(key)
        self._shown.clear()

    def destroy(self):
        self._server.disconnect(self._event_id)
