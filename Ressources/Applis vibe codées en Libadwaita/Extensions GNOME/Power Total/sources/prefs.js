// SPDX-License-Identifier: GPL-3.0-only
import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import Gtk from 'gi://Gtk';
import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';
import {Endpoint, PROFILE_SERVICES, unpack} from './lib/dbus.js';

const PROFILE_IDS = ['performance', 'balanced', 'power-saver'];
const PROFILE_LABELS = ['Performance', 'Équilibré', 'Économie d’énergie'];

export default class PowerTotalPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();
        window.set_title('Power Total');
        window.set_default_size(700, 760);
        window.search_enabled = true;
        const signals = [];
        const watch = (key, callback) => signals.push(settings.connect(`changed::${key}`, callback));
        const enabled = (row, key) => settings.bind(key, row, 'sensitive', Gio.SettingsBindFlags.GET);
        const toggle = (group, title, key, subtitle = '') => {
            const row = new Adw.SwitchRow({title, subtitle});
            settings.bind(key, row, 'active', Gio.SettingsBindFlags.DEFAULT);
            group.add(row);
            return row;
        };
        const combo = (group, title, key, ids, labels, master) => {
            const row = new Adw.ComboRow({title, model: Gtk.StringList.new(labels)});
            const sync = () => { row.selected = Math.max(0, ids.indexOf(settings.get_string(key))); };
            sync();
            watch(key, sync);
            row.connect('notify::selected', () => {
                if (ids[row.selected] !== undefined && settings.get_string(key) !== ids[row.selected])
                    settings.set_string(key, ids[row.selected]);
            });
            if (master) enabled(row, master);
            group.add(row);
            return row;
        };
        const percent = (group, title, key, master, fractional) => {
            const row = new Adw.SpinRow({title, adjustment: new Gtk.Adjustment({lower: 0, upper: 100, step_increment: 5, page_increment: 10}), digits: 0});
            const read = () => fractional ? settings.get_double(key) * 100 : settings.get_int(key);
            row.value = read();
            watch(key, () => { row.value = read(); });
            row.connect('notify::value', () => {
                if (Math.abs(row.value - read()) < 0.001) return;
                if (fractional) settings.set_double(key, row.value / 100);
                else settings.set_int(key, Math.round(row.value));
            });
            enabled(row, master);
            group.add(row);
        };
        const page = new Adw.PreferencesPage({title: 'Alimentation', icon_name: 'battery-symbolic'});
        window.add(page);
        const profiles = new Adw.PreferencesGroup({title: 'Profils énergétiques', description: 'Un changement manuel reste en place jusqu’au prochain changement d’alimentation, d’application prioritaire ou de réglage.'});
        page.add(profiles);
        toggle(profiles, 'Changer automatiquement de profil', 'profiles-enabled');
        combo(profiles, 'Sur secteur', 'ac', PROFILE_IDS, PROFILE_LABELS, 'profiles-enabled');
        combo(profiles, 'Sur batterie', 'bat', PROFILE_IDS, PROFILE_LABELS, 'profiles-enabled');
        enabled(toggle(profiles, 'Mémoriser les changements manuels', 'remember-user-profile', 'Le profil choisi devient le réglage par défaut pour cette alimentation.'), 'profiles-enabled');
        enabled(toggle(profiles, 'Respecter l’économie à batterie faible', 'low-battery-saver', 'Si cette option est aussi activée dans GNOME, elle a priorité sur les profils par application.'), 'profiles-enabled');
        const availability = new Adw.ActionRow({title: 'Profils disponibles', subtitle: 'Détection du service…'});
        profiles.add(availability);
        let closed = false;
        let services = [];
        const syncAvailable = () => {
            if (closed) return;
            const service = services.find(endpoint => endpoint.ready && endpoint.get('ActiveProfile'));
            const available = service?.get('Profiles', []).map(p => unpack(p.Profile)) ?? [];
            availability.subtitle = available.length
                ? available.map(id => PROFILE_LABELS[PROFILE_IDS.indexOf(id)] ?? id).join(' · ')
                : 'Service de profils indisponible. Le thème et la luminosité restent indépendants.';
        };
        services = PROFILE_SERVICES.map(([name, path]) => new Endpoint(Gio.BusType.SYSTEM, name, path, name, syncAvailable, syncAvailable));

        const screen = new Adw.PreferencesGroup({title: 'Luminosité de l’écran', description: 'Pourcentage appliqué à la luminosité globale gérée par GNOME.'});
        page.add(screen);
        toggle(screen, 'Ajuster automatiquement l’écran', 'screen-enabled');
        percent(screen, 'Sur secteur (%)', 'power-brightness', 'screen-enabled', true);
        percent(screen, 'Sur batterie (%)', 'battery-brightness', 'screen-enabled', true);

        const theme = new Adw.PreferencesGroup({title: 'Apparence'});
        page.add(theme);
        toggle(theme, 'Changer automatiquement de thème', 'theme-enabled');
        for (const [title, key] of [['Sur secteur', 'power-theme'], ['Sur batterie', 'battery-theme']])
            combo(theme, title, key, ['default', 'prefer-dark', 'prefer-light'], ['Par défaut (clair)', 'Sombre', 'Préférer clair'], 'theme-enabled');

        const keyboard = new Adw.PreferencesGroup({title: 'Rétroéclairage du clavier', description: 'Pour les claviers reconnus par GNOME. 0 éteint le rétroéclairage ; 100 utilise le maximum.'});
        page.add(keyboard);
        toggle(keyboard, 'Ajuster automatiquement le clavier', 'keyboard-enabled');
        percent(keyboard, 'Sur secteur (%)', 'power-keyboard', 'keyboard-enabled', false);
        percent(keyboard, 'Sur batterie (%)', 'battery-keyboard', 'keyboard-enabled', false);

        const advanced = new Adw.PreferencesGroup({title: 'Options'});
        page.add(advanced);
        enabled(toggle(advanced, 'Protection contre un chargeur insuffisant', 'weak-adapter-protection', 'Après 30 secondes de décharge sur secteur, conserve l’économie d’énergie jusqu’au débranchement. Expérimental.'), 'profiles-enabled');
        toggle(advanced, 'Signaler les erreurs', 'notifications');

        const appsPage = new Adw.PreferencesPage({title: 'Applications', icon_name: 'application-x-executable-symbolic'});
        window.add(appsPage);
        const appConfig = new Adw.PreferencesGroup({title: 'Profils par application', description: 'Actif tant qu’une application sélectionnée possède au moins une fenêtre. Nécessite le changement automatique de profil.'});
        appsPage.add(appConfig);
        enabled(appConfig, 'profiles-enabled');
        toggle(appConfig, 'Activer les profils par application', 'apps-enabled');
        combo(appConfig, 'Sur secteur', 'performance-apps-ac', PROFILE_IDS, PROFILE_LABELS, 'apps-enabled');
        combo(appConfig, 'Sur batterie', 'performance-apps-bat', PROFILE_IDS, PROFILE_LABELS, 'apps-enabled');
        const appsGroup = new Adw.PreferencesGroup({title: 'Applications sélectionnées'});
        appsPage.add(appsGroup);
        const updateSensitive = () => { appsGroup.sensitive = settings.get_boolean('profiles-enabled') && settings.get_boolean('apps-enabled'); };
        watch('profiles-enabled', updateSensitive);
        watch('apps-enabled', updateSensitive);
        updateSensitive();
        const appMap = new Map(Gio.AppInfo.get_all().filter(app => app.should_show() && app.get_id()).map(app => [app.get_id(), app]));
        for (const id of settings.get_strv('performance-apps')) if (!appMap.has(id)) appMap.set(id, null);
        const selected = new Set(settings.get_strv('performance-apps'));
        const appRows = new Map();
        const entries = [...appMap.entries()].sort(([a, appA], [b, appB]) => Number(selected.has(b)) - Number(selected.has(a)) || (appA?.get_display_name() ?? a).localeCompare(appB?.get_display_name() ?? b));
        for (const [id, app] of entries) {
            const row = new Adw.SwitchRow({title: app?.get_display_name() ?? id, subtitle: id, active: selected.has(id), use_markup: false});
            if (app?.get_icon()) row.add_prefix(new Gtk.Image({gicon: app.get_icon(), pixel_size: 24}));
            row.connect('notify::active', () => {
                const ids = new Set(settings.get_strv('performance-apps'));
                if (ids.has(id) === row.active) return;
                if (row.active) ids.add(id); else ids.delete(id);
                settings.set_strv('performance-apps', [...ids]);
            });
            appsGroup.add(row);
            appRows.set(id, row);
        }
        watch('performance-apps', () => {
            const ids = new Set(settings.get_strv('performance-apps'));
            for (const [id, row] of appRows) row.active = ids.has(id);
        });
        window.connect('close-request', () => {
            closed = true;
            signals.forEach(id => settings.disconnect(id));
            services.forEach(service => service.destroy());
            return false;
        });
    }
}
