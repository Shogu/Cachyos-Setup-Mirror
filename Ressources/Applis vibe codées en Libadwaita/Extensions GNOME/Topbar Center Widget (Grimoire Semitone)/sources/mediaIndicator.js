// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.
import Cairo from 'cairo';
import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {SystemIndicator} from 'resource:///org/gnome/shell/ui/quickSettings.js';

import {playerKey} from './playerExtras.js';

// Barres reprises de Now Playing Card (style « rounded ») : trois traits
// arrondis à la couleur du texte du panneau, animés tant qu'un lecteur joue.
const BAR_WIDTH = 3;
const BAR_GAP = 2;
const FRAME_MS = 33;
const SPEEDS = [7.1, 9.7, 5.3];
const PHASES = [0, 2.1, 4.2];
const REST_LEVELS = [0.35, 0.7, 0.5];

function scaleFactor() {
    return St.ThemeContext.get_for_stage(global.stage).scale_factor;
}

const EqualizerBars = GObject.registerClass(
class EqualizerBars extends St.DrawingArea {
    _init() {
        super._init({style_class: 'tcw-equalizer', y_align: Clutter.ActorAlign.CENTER});
        this._levels = [...REST_LEVELS];
        this._playing = false;
        this._timerId = 0;
        this._start = GLib.get_monotonic_time();
        this.connect('notify::mapped', () => this._syncTimer());
        this._animationsId = St.Settings.get().connect('notify::enable-animations', () => this._syncTimer());
    }

    vfunc_get_preferred_width(_forHeight) {
        const width = (REST_LEVELS.length * (BAR_WIDTH + BAR_GAP) - BAR_GAP) * scaleFactor();
        return [width, width];
    }

    set playing(playing) {
        this._playing = playing;
        this._syncTimer();
    }

    _syncTimer() {
        const running = this._playing && this.mapped && St.Settings.get().enable_animations;
        if (running && !this._timerId) {
            this._timerId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, FRAME_MS, () => {
                const t = (GLib.get_monotonic_time() - this._start) / GLib.USEC_PER_SEC;
                this._levels = SPEEDS.map((speed, i) => (Math.sin(t * speed + PHASES[i]) + 1) / 2);
                this.queue_repaint();
                return GLib.SOURCE_CONTINUE;
            });
        } else if (!running && this._timerId) {
            GLib.Source.remove(this._timerId);
            this._timerId = 0;
            this._levels = [...REST_LEVELS];
            this.queue_repaint();
        }
    }

    vfunc_repaint() {
        const cr = this.get_context();
        const [, height] = this.get_surface_size();
        const color = this.get_theme_node().get_foreground_color();
        const barWidth = BAR_WIDTH * scaleFactor();
        const gap = BAR_GAP * scaleFactor();
        const minHeight = Math.max(Math.round(height * 0.25), barWidth);
        const maxHeight = Math.round(height * 0.85);

        cr.setLineWidth(barWidth);
        cr.setLineCap(Cairo.LineCap.ROUND);
        cr.setSourceRGBA(color.red / 255, color.green / 255, color.blue / 255, color.alpha / 255);
        this._levels.forEach((level, i) => {
            const barHeight = minHeight + (maxHeight - minHeight) * level;
            const middle = i * (barWidth + gap) + barWidth / 2;
            const bottom = (height + barHeight) / 2;
            cr.moveTo(middle, bottom - barHeight + barWidth / 2);
            cr.lineTo(middle, bottom - barWidth / 2);
            cr.stroke();
        });
        cr.$dispose();
    }

    destroy() {
        if (this._timerId)
            GLib.Source.remove(this._timerId);
        this._timerId = 0;
        St.Settings.get().disconnect(this._animationsId);
        super.destroy();
    }
});

// Icône de la rangée de Quick Settings : visible tant qu'un lecteur joue ou est
// en pause, animée seulement pendant la lecture. Les lecteurs ignorés
// (préférences, page Lecteur) le sont aussi ici.
// Les lecteurs viennent de la source MPRIS que GNOME tient déjà pour la liste
// des notifications : aucune connexion D-Bus en plus.
export const MediaIndicator = GObject.registerClass(
class MediaIndicator extends SystemIndicator {
    _init(mediaSource, settings) {
        super._init();
        this._source = mediaSource;
        this._settings = settings;
        this._ignoredId = settings.connect('changed::ignored-players', () => this._sync());
        this._players = new Map();
        this._bars = new EqualizerBars();
        this.add_child(this._bars);

        this._addedId = mediaSource.connect('player-added', (_source, player) => this._watch(player));
        this._removedId = mediaSource.connect('player-removed', (_source, player) => this._unwatch(player));
        for (const player of mediaSource.players)
            this._watch(player);
        this._sync();
    }

    _watch(player) {
        if (this._players.has(player))
            return;
        this._players.set(player, player.connect('changed', () => this._sync()));
        this._sync();
    }

    _unwatch(player) {
        if (!this._players.has(player))
            return;
        player.disconnect(this._players.get(player));
        this._players.delete(player);
        this._sync();
    }

    _sync() {
        const ignored = this._settings.get_strv('ignored-players');
        const statuses = [...this._players.keys()]
            .filter(player => !ignored.includes(playerKey(player)))
            .map(player => player.status);
        this.visible = statuses.some(status => status === 'Playing' || status === 'Paused');
        this._bars.playing = statuses.includes('Playing');
    }

    destroy() {
        this._settings.disconnect(this._ignoredId);
        this._settings = null;
        this._source.disconnect(this._addedId);
        this._source.disconnect(this._removedId);
        for (const [player, id] of this._players)
            player.disconnect(id);
        this._players.clear();
        this._source = null;
        super.destroy();
    }
});

// Ajoute l'icône tout à gauche de la rangée de Quick Settings, ou la retire,
// selon le réglage « media-indicator ».
export class MediaIndicatorHost {
    constructor(mediaSource, settings) {
        this._source = mediaSource;
        this._settings = settings;
        this._indicator = null;
        this._settingsId = settings.connect('changed::media-indicator', () => this._sync());
        this._sync();
    }

    _sync() {
        this._indicator?.destroy();
        this._indicator = null;
        if (!this._settings.get_boolean('media-indicator'))
            return;
        const quickSettings = Main.panel.statusArea.quickSettings;
        this._indicator = new MediaIndicator(this._source, this._settings);
        quickSettings.addExternalIndicator(this._indicator);
        quickSettings._indicators.set_child_at_index(this._indicator, 0);
    }

    destroy() {
        this._settings.disconnect(this._settingsId);
        this._indicator?.destroy();
        this._indicator = null;
        this._source = null;
        this._settings = null;
    }
}
