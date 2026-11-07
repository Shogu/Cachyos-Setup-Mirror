// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.
import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import Gtk from 'gi://Gtk';

Gio._promisify(Gio.DBusConnection.prototype, 'call');

const MPRIS_PREFIX = 'org.mpris.MediaPlayer2.';

function dbusCall(name, path, iface, method, args, type) {
    return Gio.DBus.session.call(name, path, iface, method, args, new GLib.VariantType(type),
        Gio.DBusCallFlags.NONE, -1, null);
}

async function runningPlayers() {
    const [names] = (await dbusCall('org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus',
        'ListNames', null, '(as)')).deepUnpack();
    const players = new Map();
    for (const name of names.filter(item => item.startsWith(MPRIS_PREFIX))) {
        const key = name.slice(MPRIS_PREFIX.length).replace(/\.instance[^.]*$/, '');
        try {
            const [identity] = (await dbusCall(name, '/org/mpris/MediaPlayer2', 'org.freedesktop.DBus.Properties',
                'Get', new GLib.Variant('(ss)', ['org.mpris.MediaPlayer2', 'Identity']), '(v)')).deepUnpack();
            players.set(key, identity.deepUnpack());
        } catch {
            players.set(key, key);
        }
    }
    return players;
}

// Lecteurs MPRIS ouverts en ce moment, plus ceux déjà ignorés : un interrupteur
// par lecteur pour le laisser afficher ou non au-dessus des notes.
export const PlayersGroup = GObject.registerClass(
class PlayersGroup extends Adw.PreferencesGroup {
    _init(settings) {
        super._init({
            title: 'Lecteurs pris en charge',
            description: 'Audio ou vidéo : tout logiciel qui se déclare lecteur à GNOME (MPRIS). '
                + 'Ouvrez un lecteur puis actualisez pour le voir ici.',
        });
        this._settings = settings;
        this._rows = [];
        const refresh = new Gtk.Button({
            icon_name: 'view-refresh-symbolic',
            tooltip_text: 'Actualiser',
            valign: Gtk.Align.CENTER,
            css_classes: ['flat'],
        });
        refresh.connect('clicked', () => this._fill());
        this.set_header_suffix(refresh);
        this._fill();
    }

    async _fill() {
        const players = await runningPlayers().catch(() => new Map());
        for (const key of this._settings.get_strv('ignored-players')) {
            if (!players.has(key))
                players.set(key, key);
        }
        for (const row of this._rows)
            this.remove(row);
        this._rows = [...players].sort(([, a], [, b]) => a.localeCompare(b)).map(([key, identity]) => {
            const row = new Adw.SwitchRow({
                title: identity,
                subtitle: key,
                active: !this._settings.get_strv('ignored-players').includes(key),
            });
            row.connect('notify::active', () => {
                const ignored = this._settings.get_strv('ignored-players').filter(item => item !== key);
                this._settings.set_strv('ignored-players', row.active ? ignored : [...ignored, key]);
            });
            this.add(row);
            return row;
        });
    }
});
