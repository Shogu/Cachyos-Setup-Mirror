// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.

import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as QuickSettings from 'resource:///org/gnome/shell/ui/quickSettings.js';

const APP_ID = 'fr.ogu.Chihiro';
const APP_PATH = '/fr/ogu/Chihiro';

const ChihiroToggle = GObject.registerClass(
class ChihiroToggle extends QuickSettings.QuickToggle {
    constructor(gicon) {
        super({title: 'Chihiro', gicon, toggleMode: false});
        this._running = false;
        this._watchId = Gio.bus_watch_name(Gio.BusType.SESSION, APP_ID, Gio.BusNameWatcherFlags.NONE,
            () => this._setRunning(true), () => this._setRunning(false));
        this.connect('clicked', () => this._toggle());
    }

    _setRunning(running) {
        this._running = running;
        this.checked = running;
    }

    _toggle() {
        if (this._running)
            this._quit();
        else
            this._launch();
    }

    _launch() {
        const app = Gio.DesktopAppInfo.new(`${APP_ID}.desktop`);
        if (app === null) {
            Main.notifyError('Chihiro', "L'application Chihiro n'est pas installée.");
            return;
        }
        app.launch([], global.create_app_launch_context(0, -1));
    }

    _quit() {
        Gio.DBus.session.call(APP_ID, APP_PATH, 'org.gtk.Actions', 'Activate',
            new GLib.Variant('(sava{sv})', ['quit', [], {}]), null, Gio.DBusCallFlags.NONE, -1, null,
            (connection, result) => {
                try {
                    connection.call_finish(result);
                } catch (error) {
                    console.warn(`[Chihiro] Fermeture impossible : ${error.message}`);
                }
            });
    }

    destroy() {
        Gio.bus_unwatch_name(this._watchId);
        super.destroy();
    }
});

const ChihiroIndicator = GObject.registerClass(
class ChihiroIndicator extends QuickSettings.SystemIndicator {
    constructor(gicon) {
        super();
        this.quickSettingsItems.push(new ChihiroToggle(gicon));
    }

    destroy() {
        for (const item of this.quickSettingsItems)
            item.destroy();
        super.destroy();
    }
});

export default class ChihiroQuickSettingsLaunchToggleExtension extends Extension {
    enable() {
        const gicon = new Gio.FileIcon({file: this.dir.resolve_relative_path('icons/chihiro-symbolic.svg')});
        this._indicator = new ChihiroIndicator(gicon);
        Main.panel.statusArea.quickSettings.addExternalIndicator(this._indicator);
    }

    disable() {
        this._indicator.destroy();
        this._indicator = null;
    }
}
