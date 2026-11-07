import Adw from 'gi://Adw';
import Gtk from 'gi://Gtk';
import { gettext as _ } from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';
export function createDebugPage(settings) {
    const debugPage = new Adw.PreferencesPage({
        title: _('Débogage'),
        iconName: 'applications-engineering-symbolic',
    });
    const debugGroup = new Adw.PreferencesGroup({
        title: _('Actions sur la session'),
        description: _('Enregistrer ou restaurer manuellement votre session'),
    });
    debugPage.add(debugGroup);
    const saveBtn = new Gtk.Button({ label: _('Enregistrer la session actuelle') });
    saveBtn.set_hexpand(true);
    saveBtn.set_halign(Gtk.Align.FILL);
    saveBtn.set_margin_bottom(12);
    saveBtn.get_style_context().add_class('suggested-action');
    saveBtn.connect('clicked', () => {
        settings.set_boolean('save-session-trigger', !settings.get_boolean('save-session-trigger'));
    });
    debugGroup.add(saveBtn);
    const restoreBtn = new Gtk.Button({ label: _('Restaurer la session') });
    restoreBtn.set_hexpand(true);
    restoreBtn.set_halign(Gtk.Align.FILL);
    restoreBtn.set_margin_top(12);
    restoreBtn.connect('clicked', () => {
        settings.set_boolean('restore-session-trigger', !settings.get_boolean('restore-session-trigger'));
    });
    debugGroup.add(restoreBtn);
    const showNotificationBtn = new Gtk.Button({ label: _('Afficher une notification') });
    showNotificationBtn.set_hexpand(true);
    showNotificationBtn.set_halign(Gtk.Align.FILL);
    showNotificationBtn.set_margin_top(12);
    showNotificationBtn.connect('clicked', () => {
        settings.set_boolean('show-notification-trigger', !settings.get_boolean('show-notification-trigger'));
    });
    debugGroup.add(showNotificationBtn);
    return debugPage;
}
