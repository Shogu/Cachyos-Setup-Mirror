import { ExtensionPreferences } from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';
import { createGeneralPage } from './ui/prefs/generalPage.js';
import { createDebugPage } from './ui/prefs/debugPage.js';
export default class SessionKeeperPreferences extends ExtensionPreferences {
    _settings;
    async fillPreferencesWindow(window) {
        this._settings = this.getSettings();
        // Augmente la taille par défaut de la fenêtre des préférences
        window.set_default_size(700, 900);
        const { page: generalPage, debugSwitch } = createGeneralPage(this._settings);
        window.add(generalPage);
        const debugPage = createDebugPage(this._settings);
        const updateVisibility = () => {
            const active = this._settings.get_boolean('debug-mode');
            if (active) {
                if (!debugPage.get_parent())
                    window.add(debugPage);
            }
            else if (debugPage.get_parent()) {
                window.remove(debugPage);
            }
        };
        updateVisibility();
        debugSwitch.connect('notify::active', updateVisibility);
    }
}
