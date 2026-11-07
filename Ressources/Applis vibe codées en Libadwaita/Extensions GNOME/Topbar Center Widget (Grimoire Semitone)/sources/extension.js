// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {CalendarFeatures} from './calendarFeatures.js';
import {ColumnPlacement} from './columnPlacement.js';
import {MediaIndicatorHost} from './mediaIndicator.js';
import {NotesColumn} from './notesColumn.js';
import {grimoireSettings} from './notesFolder.js';

export default class TopbarCenterWidgetExtension extends Extension {
    enable() {
        const dateMenu = Main.panel.statusArea.dateMenu;
        const settings = this.getSettings();
        this._column = new NotesColumn(settings, grimoireSettings(), dateMenu.menu, dateMenu._calendar);
        this._placement = new ColumnPlacement(dateMenu, this._column, settings);
        this._calendar = new CalendarFeatures(dateMenu, settings, this.path);
        this._mediaIndicator = new MediaIndicatorHost(dateMenu._messageList._messageView._mediaSource, settings);
        Main.wm.addKeybinding('new-note-shortcut', settings, Meta.KeyBindingFlags.IGNORE_AUTOREPEAT,
            Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW, () => this._column.startNewNote());
    }

    disable() {
        Main.wm.removeKeybinding('new-note-shortcut');
        this._mediaIndicator.destroy();
        this._mediaIndicator = null;
        this._calendar.destroy();
        this._calendar = null;
        this._placement.destroy();
        this._placement = null;
        this._column.destroy();
        this._column = null;
    }
}
