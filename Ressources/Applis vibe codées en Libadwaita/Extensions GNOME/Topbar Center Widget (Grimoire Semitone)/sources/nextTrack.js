// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';

Gio._promisify(Gio.DBusConnection.prototype, 'call');

const MPRIS_PATH = '/org/mpris/MediaPlayer2';

const TrackListProxy = Gio.DBusProxy.makeProxyWrapper(`
<node>
  <interface name="org.mpris.MediaPlayer2.TrackList">
    <method name="GetTracksMetadata">
      <arg direction="in" type="ao" name="TrackIds"/>
      <arg direction="out" type="aa{sv}" name="Metadata"/>
    </method>
    <signal name="TrackListReplaced">
      <arg type="ao" name="Tracks"/>
      <arg type="o" name="CurrentTrack"/>
    </signal>
    <property name="Tracks" type="ao" access="read"/>
  </interface>
</node>`);

// « Titre suivant : Titre — Artiste » sous l'artiste, seulement pour les lecteurs qui
// publient leur file d'attente (MPRIS TrackList, HasTrackList = true).
export class NextTrack {
    constructor(message, busName, cancellable) {
        this._busName = busName;
        this._cancellable = cancellable;
        this._proxy = null;
        this._trackId = null;
        this._label = new St.Label({style_class: 'tcw-next-track', visible: false});
        message.titleLabel.get_parent().add_child(this._label);
        this._connect();
    }

    async _connect() {
        try {
            const reply = await Gio.DBus.session.call(this._busName, MPRIS_PATH, 'org.freedesktop.DBus.Properties',
                'Get', new GLib.Variant('(ss)', ['org.mpris.MediaPlayer2', 'HasTrackList']),
                new GLib.VariantType('(v)'), Gio.DBusCallFlags.NONE, -1, this._cancellable);
            if (!reply.deepUnpack()[0].deepUnpack())
                return;
            this._proxy = await new Promise((resolve, reject) => {
                new TrackListProxy(Gio.DBus.session, this._busName, MPRIS_PATH,
                    (proxy, error) => (error ? reject(error) : resolve(proxy)), this._cancellable);
            });
        } catch (error) {
            if (!error.matches(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED))
                this._label.hide();
            return;
        }
        this._propertiesId = this._proxy.connect('g-properties-changed', () => this._update());
        this._replacedId = this._proxy.connectSignal('TrackListReplaced', (_proxy, _sender, [tracks]) => this._update(tracks));
        this._update();
    }

    setTrack(trackId) {
        this._trackId = trackId;
        this._update();
    }

    async _update(tracks = this._proxy?.Tracks ?? []) {
        const index = tracks.indexOf(this._trackId);
        const next = index >= 0 ? tracks[index + 1] : undefined;
        if (!next) {
            this._label.hide();
            return;
        }
        try {
            const [[metadata]] = await this._proxy.GetTracksMetadataAsync([next]);
            const title = metadata['xesam:title']?.deepUnpack() ?? '';
            const artists = metadata['xesam:artist']?.deepUnpack()?.join(', ') ?? '';
            this._label.text = `Titre suivant : ${artists ? `${title} — ${artists}` : title}`;
            this._label.visible = Boolean(title);
        } catch {
            this._label.hide();
        }
    }

    destroy() {
        if (this._proxy) {
            this._proxy.disconnect(this._propertiesId);
            this._proxy.disconnectSignal(this._replacedId);
        }
        this._proxy = null;
        this._cancellable = null;
    }
}
