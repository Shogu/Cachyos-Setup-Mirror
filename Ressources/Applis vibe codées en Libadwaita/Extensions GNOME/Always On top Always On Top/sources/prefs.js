import Adw from 'gi://Adw';
import Gio from 'gi://Gio';

import {ExtensionPreferences, gettext as _} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

export default class AlwaysOnTopAlwaysOnTopPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();
        // Garde l'objet GSettings en vie aussi longtemps que la fenêtre.
        window._settings = settings;

        const page = new Adw.PreferencesPage({
            title: _('General'),
            icon_name: 'preferences-system-symbolic',
        });
        window.add(page);

        const group = new Adw.PreferencesGroup({
            title: _('Keyboard shortcut'),
        });
        page.add(group);

        const row = new Adw.SwitchRow({
            title: _('Enable the Super+T shortcut'),
            subtitle: _('Toggles Always on Top on the focused window, like the top bar button. Does nothing on a maximized window.'),
        });
        group.add(row);

        settings.bind('shortcut-enabled', row, 'active', Gio.SettingsBindFlags.DEFAULT);
    }
}
