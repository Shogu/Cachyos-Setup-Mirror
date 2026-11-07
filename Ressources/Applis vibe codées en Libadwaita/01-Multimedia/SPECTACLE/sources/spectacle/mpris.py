"""Interface MPRIS 2 : Spectacle apparaît comme lecteur dans GNOME (notifications, extensions de lecteurs)."""

from gi.repository import Gio, GLib

BUS_NAME = "org.mpris.MediaPlayer2.spectacle_ogu"
PATH = "/org/mpris/MediaPlayer2"
ROOT = "org.mpris.MediaPlayer2"
PLAYER = "org.mpris.MediaPlayer2.Player"
XML = f"""<node>
  <interface name="{ROOT}">
    <method name="Raise"/><method name="Quit"/>
    <property name="CanQuit" type="b" access="read"/><property name="CanRaise" type="b" access="read"/>
    <property name="HasTrackList" type="b" access="read"/><property name="Identity" type="s" access="read"/>
    <property name="DesktopEntry" type="s" access="read"/>
    <property name="SupportedUriSchemes" type="as" access="read"/><property name="SupportedMimeTypes" type="as" access="read"/>
  </interface>
  <interface name="{PLAYER}">
    <method name="Next"/><method name="Previous"/><method name="Pause"/><method name="PlayPause"/>
    <method name="Stop"/><method name="Play"/>
    <method name="Seek"><arg direction="in" name="Offset" type="x"/></method>
    <method name="SetPosition"><arg direction="in" name="TrackId" type="o"/><arg direction="in" name="Position" type="x"/></method>
    <method name="OpenUri"><arg direction="in" name="Uri" type="s"/></method>
    <signal name="Seeked"><arg name="Position" type="x"/></signal>
    <property name="PlaybackStatus" type="s" access="read"/><property name="Rate" type="d" access="read"/>
    <property name="Metadata" type="a{{sv}}" access="read"/><property name="Volume" type="d" access="read"/>
    <property name="Position" type="x" access="read"/><property name="MinimumRate" type="d" access="read"/>
    <property name="MaximumRate" type="d" access="read"/><property name="CanGoNext" type="b" access="read"/>
    <property name="CanGoPrevious" type="b" access="read"/><property name="CanPlay" type="b" access="read"/>
    <property name="CanPause" type="b" access="read"/><property name="CanSeek" type="b" access="read"/>
    <property name="CanControl" type="b" access="read"/>
  </interface>
</node>"""
US = 1_000_000


class Mpris:
    """« player » fournit : play, pause, play_pause, stop, next, previous, seek_to(s), open_url(url), present(), quit(),
    et les attributs status, metadata(), position(), volume, can_next, can_previous, can_seek, has_media."""

    def __init__(self, connection, player):
        self._connection = connection
        self._player = player
        self._track = 0
        info = Gio.DBusNodeInfo.new_for_xml(XML)
        self._ids = [connection.register_object(PATH, iface, self._on_call, self._on_get, None) for iface in info.interfaces]
        self._owner = Gio.bus_own_name_on_connection(connection, BUS_NAME, Gio.BusNameOwnerFlags.NONE, None, None)

    def destroy(self):
        Gio.bus_unown_name(self._owner)
        for registration in self._ids:
            self._connection.unregister_object(registration)

    def new_track(self):
        self._track += 1
        self.changed("Metadata", "CanGoNext", "CanGoPrevious", "CanSeek", "CanPlay", "CanPause")

    def changed(self, *names):
        values = {name: self._value(name) for name in names}
        self._connection.emit_signal(None, PATH, "org.freedesktop.DBus.Properties", "PropertiesChanged",
                                     GLib.Variant("(sa{sv}as)", (PLAYER, values, [])))

    def seeked(self, seconds):
        self._connection.emit_signal(None, PATH, PLAYER, "Seeked", GLib.Variant("(x)", (int(seconds * US),)))

    def _track_path(self):
        return f"/io/gitlab/shogu/Spectacle/track/{self._track}"

    def _metadata(self):
        data = self._player.metadata()
        if not data:
            return {"mpris:trackid": GLib.Variant("o", "/org/mpris/MediaPlayer2/TrackList/NoTrack")}
        meta = {
            "mpris:trackid": GLib.Variant("o", self._track_path()),
            "xesam:title": GLib.Variant("s", data["title"]),
            "xesam:artist": GLib.Variant("as", [data["channel"]] if data["channel"] else []),
            "xesam:url": GLib.Variant("s", data["url"]),
        }
        if data.get("thumbnail"):
            meta["mpris:artUrl"] = GLib.Variant("s", data["thumbnail"])
        if data.get("duration"):
            meta["mpris:length"] = GLib.Variant("x", int(data["duration"] * US))
        return meta

    def _value(self, name):
        p = self._player
        values = {
            "CanQuit": ("b", True), "CanRaise": ("b", True), "HasTrackList": ("b", False),
            "Identity": ("s", "Spectacle"), "DesktopEntry": ("s", "io.gitlab.shogu.Spectacle"),
            "SupportedUriSchemes": ("as", ["https"]), "SupportedMimeTypes": ("as", []),
            "PlaybackStatus": ("s", p.status), "Rate": ("d", 1.0), "MinimumRate": ("d", 1.0), "MaximumRate": ("d", 1.0),
            "Volume": ("d", p.volume), "Position": ("x", int(p.position() * US)),
            "CanGoNext": ("b", p.can_next), "CanGoPrevious": ("b", p.can_previous),
            "CanPlay": ("b", p.has_media), "CanPause": ("b", p.has_media), "CanSeek": ("b", p.can_seek),
            "CanControl": ("b", True),
        }
        if name == "Metadata":
            return GLib.Variant("a{sv}", self._metadata())
        return GLib.Variant(*values[name])

    def _on_get(self, _connection, _sender, _path, _interface, name):
        return self._value(name)

    def _on_call(self, _connection, _sender, _path, _interface, method, params, invocation):
        p = self._player
        args = params.unpack()
        simple = {"Raise": p.present, "Quit": p.quit, "Next": p.next, "Previous": p.previous, "Pause": p.pause,
                  "PlayPause": p.play_pause, "Stop": p.stop, "Play": p.play}
        if method in simple:
            simple[method]()
        elif method == "Seek" and p.can_seek:
            p.seek_to(max(0.0, p.position() + args[0] / US))
        elif method == "SetPosition" and p.can_seek and args[0] == self._track_path():
            p.seek_to(args[1] / US)
        elif method == "OpenUri":
            p.open_url(args[0])
        invocation.return_value(None)
