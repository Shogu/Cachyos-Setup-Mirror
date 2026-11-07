// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.
import Clutter from 'gi://Clutter';
import St from 'gi://St';

import {MediaSlot} from './mediaSlot.js';
import {NotificationsDrawer} from './notificationsDrawer.js';

export class ColumnPlacement {
    constructor(dateMenu, column, settings) {
        this._calendarArea = dateMenu._calendar.get_parent().get_parent();
        this._messageList = dateMenu._messageList;
        this._menu = dateMenu.menu;
        this._column = column;
        this._settings = settings;
        this._stack = null;
        this._media = null;
        this._drawer = null;
        this._signals = ['position', 'player-above-notes', 'cover-size', 'single-player', 'rounded-cover',
            'show-progress', 'show-shuffle-repeat', 'scroll-title', 'player-menu', 'show-next'].map(key => `changed::${key}`)
            .map(signal => settings.connect(signal, () => this._place()));
        this._place();
    }

    _place() {
        this._unplace();
        const left = this._settings.get_string('position') === 'left';
        this._column.setSide(left);
        if (!left) {
            this._calendarArea.add_child(this._column);
            return;
        }
        this._stack = new St.BoxLayout({
            style_class: 'tcw-stack',
            orientation: Clutter.Orientation.VERTICAL,
            y_expand: true,
        });
        const index = this._calendarArea.get_children().indexOf(this._messageList);
        this._calendarArea.remove_child(this._messageList);
        this._calendarArea.insert_child_at_index(this._stack, index);
        if (this._settings.get_boolean('player-above-notes')) {
            this._media = new MediaSlot(this._messageList._messageView, this._settings);
            this._stack.add_child(this._media);
        }
        this._stack.add_child(this._column);
        this._drawer = new NotificationsDrawer(this._messageList, this._menu);
        this._stack.add_child(this._drawer);
    }

    _unplace() {
        if (!this._stack) {
            if (this._column.get_parent())
                this._calendarArea.remove_child(this._column);
            return;
        }
        this._media?.destroy();
        this._media = null;
        this._stack.remove_child(this._column);
        const messageList = this._drawer.release();
        this._drawer.destroy();
        this._drawer = null;
        const index = this._calendarArea.get_children().indexOf(this._stack);
        this._stack.destroy();
        this._stack = null;
        this._calendarArea.insert_child_at_index(messageList, index);
    }

    destroy() {
        for (const id of this._signals)
            this._settings.disconnect(id);
        this._unplace();
        this._calendarArea = null;
        this._messageList = null;
        this._menu = null;
        this._column = null;
        this._settings = null;
    }
}
