"""Grimoire: GNOME Shell search provider for the notes of the pinned folders."""
from pathlib import Path

from gi.repository import Gio, GLib

import notes

PATH_SUFFIX = '/SearchProvider'
XML = '''<node>
  <interface name="org.gnome.Shell.SearchProvider2">
    <method name="GetInitialResultSet">
      <arg type="as" name="terms" direction="in"/>
      <arg type="as" name="results" direction="out"/>
    </method>
    <method name="GetSubsearchResultSet">
      <arg type="as" name="previous_results" direction="in"/>
      <arg type="as" name="terms" direction="in"/>
      <arg type="as" name="results" direction="out"/>
    </method>
    <method name="GetResultMetas">
      <arg type="as" name="identifiers" direction="in"/>
      <arg type="aa{sv}" name="metas" direction="out"/>
    </method>
    <method name="ActivateResult">
      <arg type="s" name="identifier" direction="in"/>
      <arg type="as" name="terms" direction="in"/>
      <arg type="u" name="timestamp" direction="in"/>
    </method>
    <method name="LaunchSearch">
      <arg type="as" name="terms" direction="in"/>
      <arg type="u" name="timestamp" direction="in"/>
    </method>
  </interface>
</node>'''


class SearchProvider:
    def __init__(self, app):
        self.app = app
        self.terms = []
        self.registration = 0

    def register(self, connection, object_path):
        info = Gio.DBusNodeInfo.new_for_xml(XML).interfaces[0]
        self.registration = connection.register_object(object_path + PATH_SUFFIX, info, self.call, None, None)

    def unregister(self, connection):
        if self.registration:
            connection.unregister_object(self.registration)
        self.registration = 0

    def folders(self):
        return [f for f in self.app.cfg.get_strv('pinned-folders') if Path(f).is_dir()]

    def call(self, _connection, _sender, _path, _interface, method, params, invocation):
        self.app.hold()
        try:
            args = params.unpack()
            if method == 'GetInitialResultSet':
                self.terms = args[0]
                invocation.return_value(GLib.Variant('(as)', (notes.search(self.folders(), self.terms),)))
            elif method == 'GetSubsearchResultSet':
                self.terms = args[1]
                invocation.return_value(GLib.Variant('(as)', (notes.search(self.folders(), self.terms),)))
            elif method == 'GetResultMetas':
                metas = [{
                    'id': GLib.Variant('s', path),
                    'name': GLib.Variant('s', Path(path).stem),
                    'description': GLib.Variant('s', f'{Path(path).parent.name} · {notes.snippet(path, self.terms)}'),
                    'gicon': GLib.Variant('s', 'text-markdown'),
                } for path in args[0]]
                invocation.return_value(GLib.Variant('(aa{sv})', (metas,)))
            elif method == 'ActivateResult':
                self.app.open_path(args[0])
                invocation.return_value(None)
            elif method == 'LaunchSearch':
                self.app.activate()
                invocation.return_value(None)
        except Exception as e:  # a failing search must answer GNOME Shell, not hang it
            invocation.return_error_literal(Gio.dbus_error_quark(), Gio.DBusError.FAILED, str(e))
        finally:
            self.app.release()
