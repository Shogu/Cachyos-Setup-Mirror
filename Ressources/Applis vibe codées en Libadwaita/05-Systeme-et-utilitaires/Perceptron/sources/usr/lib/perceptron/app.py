from gi.repository import Adw, Gio, GLib

from config import APP_ID
from window import MainWindow

ACCELERATORS = {
    "app.quit": ["<Control>q"],
    "win.new-session": ["<Control>t"],
    "win.reload": ["<Control>r", "F5"],
    "win.reconnect": ["<Alt>Home"],
    "win.zoom-in": ["<Control>plus", "<Control>equal"],
    "win.zoom-out": ["<Control>minus"],
    "win.zoom-reset": ["<Control>0"],
    "win.fullscreen": ["F11"],
    "win.shortcuts": ["<Control>question"],
}


class PerceptronApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.add_main_option("prompt", 0, GLib.OptionFlags.NONE, GLib.OptionArg.STRING,
                             "Texte à envoyer dans une nouvelle session", "TEXTE")
        self.add_main_option("title", 0, GLib.OptionFlags.NONE, GLib.OptionArg.STRING,
                             "Titre de la nouvelle session", "TITRE")
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.quit())
        self.add_action(quit_action)

        show_session = Gio.SimpleAction.new("show-session", GLib.VariantType.new("s"))
        show_session.connect("activate", self.on_show_session)
        self.add_action(show_session)

        for action, accels in ACCELERATORS.items():
            self.set_accels_for_action(action, accels)

    def window(self):
        return self.props.active_window or MainWindow(self)

    def do_activate(self):
        self.window().present()

    def do_command_line(self, command_line):
        options = command_line.get_options_dict().end().unpack()
        window = self.window()
        window.present()
        if options.get("prompt"):
            window.send_to_new_session(options.get("title", ""), options["prompt"])
        return 0

    def on_show_session(self, _action, parameter):
        self.window().show_session(parameter.get_string())
