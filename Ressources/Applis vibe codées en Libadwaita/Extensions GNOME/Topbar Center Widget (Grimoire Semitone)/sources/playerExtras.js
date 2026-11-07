// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Pango from 'gi://Pango';
import St from 'gi://St';
import {Slider} from 'resource:///org/gnome/shell/ui/slider.js';

import {NextTrack} from './nextTrack.js';
import {PlayerMenu} from './playerMenu.js';
import {RoundedCover} from './roundedCover.js';

const MPRIS_PREFIX = 'org.mpris.MediaPlayer2.';
const MPRIS_PATH = '/org/mpris/MediaPlayer2';
const PLAYER_IFACE = 'org.mpris.MediaPlayer2.Player';
const POSITION_POLL_MS = 1000;
const SCROLL_SPEED_PX_S = 30;
const SCROLL_PAUSE_MS = 1500;
const SCROLL_RETURN_SPEEDUP = 4;
const SCROLL_END_PAUSE_MS = 600;
// En dessous, le titre « dépasse » d'à peine quelques pixels : on le laisse fixe.
const SCROLL_MIN_OVERFLOW_PX = 4;

// Ce que le lecteur de GNOME ne lit pas : position, saut, aléatoire, répétition.
const PlayerProxy = Gio.DBusProxy.makeProxyWrapper(`
<node>
  <interface name="${PLAYER_IFACE}">
    <method name="SetPosition">
      <arg direction="in" type="o" name="TrackId"/>
      <arg direction="in" type="x" name="Position"/>
    </method>
    <method name="Seek">
      <arg direction="in" type="x" name="Offset"/>
    </method>
    <signal name="Seeked"><arg type="x" name="Position"/></signal>
    <property name="Metadata" type="a{sv}" access="read"/>
    <property name="PlaybackStatus" type="s" access="read"/>
    <property name="CanSeek" type="b" access="read"/>
    <property name="Shuffle" type="b" access="readwrite"/>
    <property name="LoopStatus" type="s" access="readwrite"/>
  </interface>
</node>`);

const LOOP_NEXT = {None: 'Playlist', Playlist: 'Track', Track: 'None'};

// Nom stable d'un lecteur : « org.mpris.MediaPlayer2.vivaldi.instance1234 » → « vivaldi ».
export function playerKey(player) {
    return player._busName.slice(MPRIS_PREFIX.length).replace(/\.instance[^.]*$/, '');
}

function formatTime(microseconds) {
    const seconds = Math.max(0, Math.floor(microseconds / GLib.USEC_PER_SEC));
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor(seconds / 60) % 60;
    const rest = String(seconds % 60).padStart(2, '0');
    return hours ? `${hours}:${String(minutes).padStart(2, '0')}:${rest}` : `${minutes}:${rest}`;
}

// Ajouts à une carte MediaMessage native : barre de progression, aléatoire et
// répétition, pochette arrondie, titre défilant. La carte reste celle de GNOME.
export class PlayerExtras {
    constructor(message, player, options) {
        this._message = message;
        this._player = player;
        this._options = options;
        this._proxy = null;
        this._cancellable = new Gio.Cancellable();
        this._pollId = 0;
        this._scrollId = 0;
        this._dragging = false;
        this._length = 0;
        this._trackId = null;
        this._position = 0;
        this._menu = null;
        this._next = null;

        this._cover = options.roundedCover ? new RoundedCover(message, player) : null;
        // Le bouton « déplier » de GNOME ne sert à rien pour un lecteur : il
        // n'affiche que l'artiste sur plusieurs lignes.
        this._expandButton = message._header.expandButton;
        this._expandButton.visible = false;
        this._moveControlsBelow();
        if (options.scrollTitle)
            this._setupTitleScroll();

        new PlayerProxy(Gio.DBus.session, player._busName, MPRIS_PATH, (proxy, error) => {
            if (error) {
                if (!error.matches(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED))
                    console.warn(`Topbar Center Widget : ${player._busName} — ${error.message}`);
                return;
            }
            this._proxy = proxy;
            this._setupControls();
        }, this._cancellable);
    }

    // Les boutons passent sous la barre de temps : le titre et l'artiste
    // prennent toute la largeur à droite de la pochette.
    _moveControlsBelow() {
        const controls = this._message._mediaControls;
        this._controlsHome = controls.get_parent();
        this._controlsHome.remove_child(controls);
        const messageBox = this._message.titleLabel.get_parent().get_parent();
        this._message.child.insert_child_above(controls, messageBox);
        controls.x_align = Clutter.ActorAlign.CENTER;
        controls.add_style_class_name('tcw-media-controls');
    }

    _restoreControls() {
        const controls = this._message._mediaControls;
        controls.get_parent().remove_child(controls);
        controls.x_align = Clutter.ActorAlign.FILL;
        controls.remove_style_class_name('tcw-media-controls');
        this._controlsHome.add_child(controls);
        this._controlsHome = null;
    }

    _setupControls() {
        this._propertiesId = this._proxy.connect('g-properties-changed', () => this._sync());
        if (this._options.showProgress)
            this._buildProgress();
        if (this._options.showShuffleRepeat)
            this._buildShuffleRepeat();
        if (this._options.playerMenu)
            this._menu = new PlayerMenu(this._message, this._player, () => this._proxy.Metadata ?? {});
        if (this._options.showNext)
            this._next = new NextTrack(this._message, this._player._busName, this._cancellable);
        this._sync();
    }

    _buildProgress() {
        this._elapsed = new St.Label({style_class: 'tcw-progress-time', y_align: Clutter.ActorAlign.CENTER});
        this._total = new St.Label({style_class: 'tcw-progress-time', y_align: Clutter.ActorAlign.CENTER});
        this._slider = new Slider(0);
        this._slider.add_style_class_name('tcw-progress-slider');
        this._slider.x_expand = true;
        this._slider.accessible_name = 'Position dans le morceau';
        this._slider.connect('drag-begin', () => (this._dragging = true));
        this._slider.connect('drag-end', () => {
            this._dragging = false;
            this._seek(this._slider.value);
        });
        this._slider.connect('notify::value', () => {
            if (this._dragging)
                this._elapsed.text = formatTime(this._slider.value * this._length);
        });

        this._progress = new St.BoxLayout({style_class: 'tcw-progress'});
        this._progress.add_child(this._elapsed);
        this._progress.add_child(this._slider);
        this._progress.add_child(this._total);
        // Sous la rangée pochette + titre + boutons, dans la carte elle-même.
        const messageBox = this._message.titleLabel.get_parent().get_parent();
        this._message.child.insert_child_above(this._progress, messageBox);

        this._seekedId = this._proxy.connectSignal('Seeked', (_proxy, _sender, [position]) => {
            this._showPosition(position);
        });
        this._progress.connect('notify::mapped', () => this._syncPolling());
    }

    _buildShuffleRepeat() {
        this._shuffle = this._message.addMediaControl('media-playlist-shuffle-symbolic', () => {
            this._proxy.Shuffle = !this._proxy.Shuffle;
        });
        this._shuffle.accessible_name = 'Lecture aléatoire';
        this._shuffle.get_parent().set_child_at_index(this._shuffle, 0);
        this._repeat = this._message.addMediaControl('media-playlist-repeat-symbolic', () => {
            this._proxy.LoopStatus = LOOP_NEXT[this._proxy.LoopStatus] ?? 'None';
        });
        this._repeat.accessible_name = 'Répéter';
    }

    _sync() {
        const metadata = this._proxy.Metadata ?? {};
        this._length = metadata['mpris:length']?.deepUnpack() ?? 0;
        const trackId = metadata['mpris:trackid']?.deepUnpack() ?? null;
        this._trackId = trackId && GLib.Variant.is_object_path(trackId) ? trackId : null;
        this._next?.setTrack(this._trackId);

        if (this._progress) {
            this._progress.visible = this._length > 0;
            this._slider.reactive = Boolean(this._proxy.CanSeek);
            this._total.text = formatTime(this._length);
            this._syncPolling();
        }
        if (this._shuffle) {
            this._shuffle.visible = this._proxy.Shuffle !== null;
            this._shuffle.checked = this._proxy.Shuffle === true;
            this._repeat.visible = this._proxy.LoopStatus !== null;
            this._repeat.checked = this._proxy.LoopStatus === 'Playlist' || this._proxy.LoopStatus === 'Track';
            this._repeat.icon_name = this._proxy.LoopStatus === 'Track'
                ? 'media-playlist-repeat-song-symbolic' : 'media-playlist-repeat-symbolic';
        }
        this._restartTitleScroll();
    }

    _syncPolling() {
        const polling = this._progress.mapped && this._length > 0;
        if (polling && !this._pollId) {
            this._queryPosition();
            this._pollId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, POSITION_POLL_MS, () => {
                if (this._proxy.PlaybackStatus === 'Playing')
                    this._queryPosition();
                return GLib.SOURCE_CONTINUE;
            });
        } else if (!polling && this._pollId) {
            GLib.Source.remove(this._pollId);
            this._pollId = 0;
        }
    }

    // Position n'est jamais annoncée par PropertiesChanged : il faut la demander.
    _queryPosition() {
        this._proxy.g_connection.call(this._player._busName, MPRIS_PATH, 'org.freedesktop.DBus.Properties', 'Get',
            new GLib.Variant('(ss)', [PLAYER_IFACE, 'Position']), new GLib.VariantType('(v)'),
            Gio.DBusCallFlags.NONE, -1, this._cancellable, (connection, result) => {
                try {
                    const [position] = connection.call_finish(result).deepUnpack();
                    this._showPosition(position.deepUnpack());
                } catch (error) {
                    if (!error.matches(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED))
                        this._elapsed.text = '';
                }
            });
    }

    _showPosition(position) {
        if (this._dragging || !this._length)
            return;
        this._position = position;
        this._slider.value = Math.min(1, position / this._length);
        this._elapsed.text = formatTime(position);
    }

    // SetPosition exige l'identifiant du morceau ; sans lui (Semitone, Gapless),
    // on se déplace par rapport à la dernière position connue avec Seek.
    _seek(fraction) {
        const target = Math.round(fraction * this._length);
        if (this._trackId)
            this._proxy.SetPositionRemote(this._trackId, target);
        else
            this._proxy.SeekRemote(target - this._position);
        this._position = target;
    }

    _setupTitleScroll() {
        const label = this._message.titleLabel;
        label.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;
        // Sans « … », le titre réclamerait toute sa longueur et pousserait les
        // boutons hors de la carte : il prend la place disponible, le reste
        // défile et est découpé par sa boîte.
        label.min_width = 0;
        label.natural_width = 0;
        label.x_expand = true;
        label.get_parent().clip_to_allocation = true;
        this._titleAllocationId = label.get_parent().connect('notify::allocation', () => this._restartTitleScroll());
    }

    // Défilement aller-retour, avec une pause à chaque bout, seulement si le
    // titre dépasse et que la carte est affichée.
    _restartTitleScroll() {
        if (!this._options.scrollTitle)
            return;
        const label = this._message.titleLabel;
        if (this._scrollId)
            GLib.Source.remove(this._scrollId);
        this._scrollId = 0;
        label.remove_transition('translation-x');
        label.translation_x = 0;

        // Place réellement disponible : la boîte du titre, pas l'étiquette, dont
        // la largeur n'est pas encore à jour quand la boîte vient d'être placée.
        const box = label.get_parent();
        const available = box.get_theme_node().get_content_box(box.get_allocation_box()).get_width();
        const [, natural] = label.clutter_text.get_preferred_width(-1);
        const overflow = natural - available;
        if (overflow <= SCROLL_MIN_OVERFLOW_PX || !label.mapped || !St.Settings.get().enable_animations)
            return;

        // Aller à vitesse de lecture, retour rapide.
        const duration = Math.round(overflow / SCROLL_SPEED_PX_S * 1000);
        let forward = true;
        const step = () => {
            this._scrollId = 0;
            label.ease({
                translation_x: forward ? -overflow : 0,
                duration: forward ? duration : Math.round(duration / SCROLL_RETURN_SPEEDUP),
                mode: Clutter.AnimationMode.LINEAR,
                onStopped: finished => {
                    if (!finished)
                        return;
                    forward = !forward;
                    const pause = forward ? SCROLL_PAUSE_MS : SCROLL_END_PAUSE_MS;
                    this._scrollId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, pause, () => {
                        step();
                        return GLib.SOURCE_REMOVE;
                    });
                },
            });
        };
        this._scrollId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, SCROLL_PAUSE_MS, () => {
            step();
            return GLib.SOURCE_REMOVE;
        });
    }

    destroy() {
        this._cover?.destroy();
        this._cover = null;
        this._expandButton.visible = true;
        this._expandButton = null;
        this._restoreControls();
        this._menu?.destroy();
        this._menu = null;
        this._next?.destroy();
        this._next = null;
        if (this._pollId)
            GLib.Source.remove(this._pollId);
        this._pollId = 0;
        if (this._scrollId)
            GLib.Source.remove(this._scrollId);
        this._scrollId = 0;
        this._cancellable.cancel();
        if (this._proxy) {
            this._proxy.disconnect(this._propertiesId);
            if (this._seekedId)
                this._proxy.disconnectSignal(this._seekedId);
        }
        if (this._titleAllocationId)
            this._message.titleLabel.get_parent().disconnect(this._titleAllocationId);
        this._message.titleLabel.remove_transition('translation-x');
        this._proxy = null;
        this._message = null;
        this._player = null;
    }
}
