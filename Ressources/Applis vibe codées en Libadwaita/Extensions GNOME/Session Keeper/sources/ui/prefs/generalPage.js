import Gtk from 'gi://Gtk';
import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import { gettext as _ } from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';
import { loadSessionData } from '../../utils/sessionStore.js';
import { SaveSessionMode, RestoreSessionMode } from '../../models/sessionModes.js';
export function createGeneralPage(settings) {
    const page = new Adw.PreferencesPage({
        title: _('Général'),
        iconName: 'applications-system-symbolic',
    });
    const sessionSaveGroup = new Adw.PreferencesGroup({
        title: _('Enregistrement de la session'),
        description: _('Choisissez comment enregistrer la session'),
    });
    page.add(sessionSaveGroup);
    const autoSaveRow = new Adw.ActionRow({
        title: _('Automatiquement et en continu'),
        subtitle: _('Les changements de fenêtres sont enregistrés après un court délai, avec un flush final avant la déconnexion'),
    });
    const manualSaveRow = new Adw.ActionRow({
        title: _('Manuellement'),
        subtitle: _('Pour enregistrer une session, cliquez manuellement sur « Enregistrer la session actuelle »'),
    });
    sessionSaveGroup.add(autoSaveRow);
    sessionSaveGroup.add(manualSaveRow);
    const autoSaveRadio = new Gtk.CheckButton();
    const manualSaveRadio = new Gtk.CheckButton();
    autoSaveRow.add_suffix(autoSaveRadio);
    manualSaveRow.add_suffix(manualSaveRadio);
    autoSaveRow.set_activatable_widget(autoSaveRadio);
    manualSaveRow.set_activatable_widget(manualSaveRadio);
    const radioGroup = new Gtk.CheckButton();
    autoSaveRadio.set_group(radioGroup);
    manualSaveRadio.set_group(radioGroup);
    const currentSaveMode = settings.get_uint('save-session-mode');
    if (currentSaveMode === SaveSessionMode.AUTO) {
        autoSaveRadio.set_active(true);
    }
    else {
        manualSaveRadio.set_active(true);
    }
    autoSaveRadio.connect('toggled', () => {
        if (autoSaveRadio.get_active()) {
            settings.set_uint('save-session-mode', SaveSessionMode.AUTO);
        }
    });
    manualSaveRadio.connect('toggled', () => {
        if (manualSaveRadio.get_active()) {
            settings.set_uint('save-session-mode', SaveSessionMode.MANUAL);
        }
    });
    const sessionRestoreGroup = new Adw.PreferencesGroup({
        title: _('Restauration de la session'),
        description: _('Choisissez quand restaurer la session enregistrée'),
    });
    const restoreLoginRow = new Adw.ActionRow({
        title: _('À la connexion'),
        subtitle: _('Restaurer à chaque connexion au système'),
    });
    const restoreBootRow = new Adw.ActionRow({
        title: _('Au démarrage'),
        subtitle: _('Restaurer uniquement après le démarrage de l’ordinateur'),
    });
    const restoreNeverRow = new Adw.ActionRow({
        title: _('Jamais'),
        subtitle: _('La session n’est restaurée que manuellement via le mode débogage ou D-Bus'),
    });
    const restoreNotificationRow = new Adw.ActionRow({
        title: _('Afficher une notification'),
        subtitle: _('Afficher une notification avec un bouton de restauration'),
    });
    const restoreLoginBtn = new Gtk.CheckButton();
    const restoreBootBtn = new Gtk.CheckButton();
    const restoreGroupBtn = new Gtk.CheckButton();
    const restoreNeverBtn = new Gtk.CheckButton();
    const restoreNotificationBtn = new Gtk.CheckButton();
    restoreLoginBtn.set_group(restoreGroupBtn);
    restoreBootBtn.set_group(restoreGroupBtn);
    restoreNotificationBtn.set_group(restoreGroupBtn);
    restoreNeverBtn.set_group(restoreGroupBtn);
    restoreLoginRow.add_suffix(restoreLoginBtn);
    restoreBootRow.add_suffix(restoreBootBtn);
    restoreNotificationRow.add_suffix(restoreNotificationBtn);
    restoreNeverRow.add_suffix(restoreNeverBtn);
    restoreLoginRow.set_activatable_widget(restoreLoginBtn);
    restoreBootRow.set_activatable_widget(restoreBootBtn);
    restoreNotificationRow.set_activatable_widget(restoreNotificationBtn);
    restoreNeverRow.set_activatable_widget(restoreNeverBtn);
    sessionRestoreGroup.add(restoreLoginRow);
    sessionRestoreGroup.add(restoreBootRow);
    sessionRestoreGroup.add(restoreNotificationRow);
    sessionRestoreGroup.add(restoreNeverRow);
    const restoreBtn = new Gtk.Button({ label: _('Restaurer la session') });
    restoreBtn.set_hexpand(true);
    restoreBtn.set_halign(Gtk.Align.FILL);
    restoreBtn.set_margin_top(12);
    restoreBtn.set_margin_bottom(12);
    restoreBtn.connect('clicked', () => {
        settings.set_boolean('restore-session-trigger', !settings.get_boolean('restore-session-trigger'));
    });
    sessionRestoreGroup.add(restoreBtn);
    const restoreMode = settings.get_uint('restore-session-mode');
    if (restoreMode === RestoreSessionMode.NEVER)
        restoreNeverBtn.set_active(true);
    else if (restoreMode === RestoreSessionMode.LOGIN)
        restoreLoginBtn.set_active(true);
    else if (restoreMode === RestoreSessionMode.BOOT)
        restoreBootBtn.set_active(true);
    else if (restoreMode === RestoreSessionMode.NOTIFICATION)
        restoreNotificationBtn.set_active(true);
    const updateRestoreButtonVisibility = () => {
        const isManualRestore = settings.get_uint('restore-session-mode') === RestoreSessionMode.NEVER;
        restoreBtn.set_visible(isManualRestore);
    };
    updateRestoreButtonVisibility();
    restoreNeverBtn.connect('toggled', () => {
        if (restoreNeverBtn.get_active()) {
            settings.set_uint('restore-session-mode', RestoreSessionMode.NEVER);
            updateRestoreButtonVisibility();
        }
    });
    restoreLoginBtn.connect('toggled', () => {
        if (restoreLoginBtn.get_active()) {
            settings.set_uint('restore-session-mode', RestoreSessionMode.LOGIN);
            updateRestoreButtonVisibility();
        }
    });
    restoreBootBtn.connect('toggled', () => {
        if (restoreBootBtn.get_active()) {
            settings.set_uint('restore-session-mode', RestoreSessionMode.BOOT);
            updateRestoreButtonVisibility();
        }
    });
    restoreNotificationBtn.connect('toggled', () => {
        if (restoreNotificationBtn.get_active()) {
            settings.set_uint('restore-session-mode', RestoreSessionMode.NOTIFICATION);
            updateRestoreButtonVisibility();
        }
    });
    const delayAdjustment = new Gtk.Adjustment({
        lower: 0,
        upper: 15,
        step_increment: 1,
        page_increment: 1,
        value: settings.get_int('autostart-delay'),
    });
    const delayRow = new Adw.SpinRow({
        title: _('Délai avant la restauration'),
        subtitle: _('Délai supplémentaire après le démarrage de GNOME (0 = immédiat, recommandé)'),
        adjustment: delayAdjustment,
        digits: 0,
        wrap: false,
    });
    sessionRestoreGroup.add(delayRow);
    settings.bind('autostart-delay', delayRow, 'value', Gio.SettingsBindFlags.DEFAULT);
    const appsGroup = new Adw.PreferencesGroup({
        title: _('Applications de la session'),
        description: _('Applications de la dernière session enregistrée'),
    });
    const appsList = new Gtk.ListBox();
    appsList.set_selection_mode(Gtk.SelectionMode.NONE);
    appsList.set_show_separators(true);
    appsList.get_style_context().add_class('view');
    appsList.set_margin_bottom(6);
    const scrolledWindow = new Gtk.ScrolledWindow({
        vexpand: false,
        max_content_height: 800,
        min_content_height: 200,
    });
    scrolledWindow.set_child(appsList);
    scrolledWindow.set_margin_top(6);
    scrolledWindow.set_margin_bottom(6);
    const updateAppsList = () => {
        let child = appsList.get_first_child();
        while (child) {
            appsList.remove(child);
            child = appsList.get_first_child();
        }
        const sessionData = loadSessionData(settings.schemaId);
        if (sessionData.length === 0) {
            const noDataRow = new Adw.ActionRow({
                title: _('Aucune session enregistrée n’a été trouvée'),
                subtitle: _('Enregistrez d’abord une session pour afficher les applications'),
            });
            appsList.append(noDataRow);
            return;
        }
        const appGroups = new Map();
        for (const windowInfo of sessionData) {
            if (!appGroups.has(windowInfo.appId)) {
                appGroups.set(windowInfo.appId, {
                    appId: windowInfo.appId,
                    title: windowInfo.title,
                    windows: [],
                });
            }
            appGroups.get(windowInfo.appId).windows.push(windowInfo);
        }
        for (const [appId, appData] of appGroups) {
            const row = new Adw.ActionRow({
                title: appId,
                subtitle: appData.windows.length > 1
                    ? `${appData.windows.length} fenêtres`
                    : appData.windows[0]?.title || '',
            });
            appsList.append(row);
        }
    };
    appsGroup.add(scrolledWindow);
    const buttonsBox = new Gtk.Box({ orientation: Gtk.Orientation.HORIZONTAL, spacing: 12 });
    buttonsBox.set_margin_top(6);
    appsGroup.add(buttonsBox);
    page.add(appsGroup);
    page.add(sessionRestoreGroup);
    const saveSessionBtn = new Gtk.Button({ label: _('Enregistrer la session actuelle'), hexpand: true });
    saveSessionBtn.get_style_context().add_class('suggested-action');
    saveSessionBtn.connect('clicked', () => {
        settings.set_boolean('save-session-trigger', !settings.get_boolean('save-session-trigger'));
    });
    buttonsBox.append(saveSessionBtn);
    const clearSessionBtn = new Gtk.Button({ label: _('Tout effacer'), hexpand: true });
    clearSessionBtn.get_style_context().add_class('destructive-action');
    clearSessionBtn.connect('clicked', () => {
        settings.set_boolean('delete-session-trigger', !settings.get_boolean('delete-session-trigger'));
    });
    buttonsBox.append(clearSessionBtn);
    const updateAppsVisibility = () => {
        const isManualMode = settings.get_uint('save-session-mode') === SaveSessionMode.MANUAL;
        appsGroup.set_visible(isManualMode);
        if (isManualMode) {
            updateAppsList();
        }
    };
    updateAppsVisibility();
    autoSaveRadio.connect('toggled', () => {
        updateAppsVisibility();
    });
    manualSaveRadio.connect('toggled', () => {
        updateAppsVisibility();
    });
    settings.connect('changed::save-session-trigger', () => {
        GLib.timeout_add(GLib.PRIORITY_DEFAULT, 500, () => {
            updateAppsList();
            return GLib.SOURCE_REMOVE;
        });
    });
    settings.connect('changed::delete-session-trigger', () => {
        GLib.timeout_add(GLib.PRIORITY_DEFAULT, 500, () => {
            updateAppsList();
            return GLib.SOURCE_REMOVE;
        });
    });
    const generalGroup = new Adw.PreferencesGroup({ title: _('Mode débogage') });
    const debugSwitch = new Adw.SwitchRow({
        title: _('Activer le débogage'),
        subtitle: _('Active le mode débogage pour afficher les boutons d’enregistrement et de restauration de la session'),
    });
    generalGroup.add(debugSwitch);
    settings.bind('debug-mode', debugSwitch, 'active', Gio.SettingsBindFlags.DEFAULT);
    /* ---------- Groupe des applications exclues ---------- */
    const excludeGroup = new Adw.PreferencesGroup({
        title: _('Applications exclues'),
        description: _('Applications qui ne seront pas restaurées'),
    });
    const excludeSwitch = new Adw.SwitchRow({
        title: _('Activer les exclusions'),
        subtitle: _('Ignorer les applications sélectionnées lors de l’enregistrement et de la restauration'),
    });
    excludeGroup.add(excludeSwitch);
    settings.bind('exclude-enabled', excludeSwitch, 'active', Gio.SettingsBindFlags.DEFAULT);
    /* Liste des applications exclues */
    const excludedList = new Gtk.ListBox();
    excludedList.set_selection_mode(Gtk.SelectionMode.NONE);
    excludedList.set_show_separators(true);
    excludedList.add_css_class?.('view');
    excludedList.set_margin_top(6);
    excludeGroup.add(excludedList);
    /* Bouton Ajouter */
    const addBtn = new Gtk.Button({ label: _('Ajouter') });
    addBtn.set_tooltip_text(_('Ajouter une application à la liste d’exclusion'));
    addBtn.get_style_context().add_class('suggested-action');
    addBtn.set_margin_top(8);
    excludeGroup.add(addBtn);
    page.add(excludeGroup);
    page.add(generalGroup);
    const buildRow = (appId) => {
        const row = new Gtk.ListBoxRow();
        const box = new Gtk.Box({
            orientation: Gtk.Orientation.HORIZONTAL,
            spacing: 12,
            margin_start: 12,
            margin_end: 12
        });
        row.set_child(box);
        const appInfo = Gio.DesktopAppInfo.new(appId);
        let icon = null;
        let name = appId;
        if (appInfo) {
            icon = appInfo.get_icon();
            name = appInfo.get_display_name();
        }
        let image;
        if (icon) {
            image = new Gtk.Image({ gicon: icon, pixel_size: 24 });
        }
        else {
            image = new Gtk.Image({ icon_name: 'application-x-unknown-symbolic', pixel_size: 24 });
        }
        box.append(image);
        const label = new Gtk.Label({ label: name, xalign: 0 });
        label.set_hexpand(true);
        box.append(label);
        const removeBtn = new Gtk.Button({ icon_name: 'user-trash-symbolic' });
        removeBtn.get_style_context().add_class('flat');
        box.append(removeBtn);
        removeBtn.connect('clicked', () => {
            const arr = settings.get_strv('excluded-apps');
            const idx = arr.indexOf(appId);
            if (idx >= 0) {
                arr.splice(idx, 1);
                settings.set_strv('excluded-apps', arr);
            }
        });
        return row;
    };
    const refreshExcludedList = () => {
        // Efface la liste
        let child = excludedList.get_first_child();
        while (child) {
            excludedList.remove(child);
            child = excludedList.get_first_child();
        }
        const arr = settings.get_strv('excluded-apps');
        for (const id of arr) {
            excludedList.append(buildRow(id));
        }
    };
    refreshExcludedList();
    settings.connect('changed::excluded-apps', refreshExcludedList);
    addBtn.connect('clicked', () => {
        const dialog = new Gtk.AppChooserDialog({
            transient_for: page.get_root() ?? null,
            modal: true,
        });
        dialog.set_default_size(800, 600);
        const chooser = dialog.get_widget();
        chooser.set_show_all(true);
        chooser.set_show_default(true);
        dialog.connect('response', (_dlg, resp) => {
            if (resp === Gtk.ResponseType.OK) {
                const info = dialog.get_app_info();
                if (info) {
                    const id = info.get_id();
                    if (id) {
                        const arr = settings.get_strv('excluded-apps');
                        if (!arr.includes(id)) {
                            arr.push(id);
                            settings.set_strv('excluded-apps', arr);
                        }
                    }
                }
            }
            dialog.destroy();
        });
        dialog.show();
    });
    const updateExcludeVisibility = () => {
        const active = settings.get_boolean('exclude-enabled');
        excludedList.set_visible(active);
        addBtn.set_visible(active);
    };
    updateExcludeVisibility();
    excludeSwitch.connect('notify::active', updateExcludeVisibility);
    settings.connect('changed::exclude-enabled', updateExcludeVisibility);
    return { page, debugSwitch };
}
