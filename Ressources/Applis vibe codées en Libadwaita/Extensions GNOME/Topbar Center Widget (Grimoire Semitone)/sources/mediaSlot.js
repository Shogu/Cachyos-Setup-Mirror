// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.
import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import St from 'gi://St';
import {MediaMessage} from 'resource:///org/gnome/shell/ui/messageList.js';

import {PlayerExtras, playerKey} from './playerExtras.js';

const STATUS_RANK = {Playing: 2, Paused: 1};

// Lecteur affiché au-dessus des notes : les cartes MediaMessage de GNOME,
// enrichies par PlayerExtras ; celles restées dans la liste des notifications
// (repliée) sont masquées.
export const MediaSlot = GObject.registerClass(
class MediaSlot extends St.BoxLayout {
    _init(messageView, settings) {
        super._init({
            style_class: `tcw-media tcw-cover-${settings.get_string('cover-size')}`,
            orientation: Clutter.Orientation.VERTICAL,
        });
        this._view = messageView;
        this._source = messageView._mediaSource;
        this._settings = settings;
        this._options = {
            roundedCover: settings.get_boolean('rounded-cover'),
            showProgress: settings.get_boolean('show-progress'),
            showShuffleRepeat: settings.get_boolean('show-shuffle-repeat'),
            scrollTitle: settings.get_boolean('scroll-title'),
            playerMenu: settings.get_boolean('player-menu'),
            showNext: settings.get_boolean('show-next'),
        };
        this._single = settings.get_boolean('single-player');
        this._cards = new Map();
        this._lastPlayed = new Map();

        this._addedId = this._source.connect('player-added', (_source, player) => this._addPlayer(player));
        this._removedId = this._source.connect('player-removed', (_source, player) => this._removePlayer(player));
        this._childId = messageView.connect('child-added', () => this._setNativeVisible(false));
        this._ignoredId = settings.connect('changed::ignored-players', () => this._syncPlayers());
        this._syncPlayers();
        this._setNativeVisible(false);
    }

    _isIgnored(player) {
        return this._settings.get_strv('ignored-players').includes(playerKey(player));
    }

    _syncPlayers() {
        for (const player of [...this._cards.keys()]) {
            if (this._isIgnored(player))
                this._removePlayer(player);
        }
        for (const player of this._source.players)
            this._addPlayer(player);
    }

    _addPlayer(player) {
        if (this._cards.has(player) || this._isIgnored(player))
            return;
        const message = new MediaMessage(player);
        const extras = new PlayerExtras(message, player, this._options);
        const changedId = player.connect('changed', () => {
            if (player.status === 'Playing')
                this._lastPlayed.set(player, GLib.get_monotonic_time());
            this._chooseVisible();
        });
        this._cards.set(player, {message, extras, changedId});
        this.add_child(message);
        this._chooseVisible();
    }

    _removePlayer(player) {
        const card = this._cards.get(player);
        if (!card)
            return;
        player.disconnect(card.changedId);
        card.extras.destroy();
        card.message.destroy();
        this._cards.delete(player);
        this._lastPlayed.delete(player);
        this._chooseVisible();
    }

    // Un seul lecteur : celui qui joue, sinon celui en pause, sinon le dernier
    // ayant joué.
    _chooseVisible() {
        if (!this._single)
            return;
        const score = player => [STATUS_RANK[player.status] ?? 0, this._lastPlayed.get(player) ?? 0];
        let best = null;
        for (const player of this._cards.keys()) {
            const [rank, time] = score(player);
            if (!best || rank > best.rank || (rank === best.rank && time > best.time))
                best = {player, rank, time};
        }
        for (const [player, card] of this._cards)
            card.message.visible = player === best?.player;
    }

    _setNativeVisible(visible) {
        for (const message of this._view.messages) {
            if (message instanceof MediaMessage)
                message.visible = visible;
        }
    }

    destroy() {
        this._source.disconnect(this._addedId);
        this._source.disconnect(this._removedId);
        this._view.disconnect(this._childId);
        this._settings.disconnect(this._ignoredId);
        this._setNativeVisible(true);
        for (const player of [...this._cards.keys()])
            this._removePlayer(player);
        this._view = null;
        this._source = null;
        this._settings = null;
        super.destroy();
    }
});
