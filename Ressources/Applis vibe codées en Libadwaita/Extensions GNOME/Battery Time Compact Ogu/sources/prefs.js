import Adw from 'gi://Adw';
import Gtk from 'gi://Gtk';

import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

const PANEL_FORMATS = [
    ['time-percent', 'Temps - pourcentage (2:30 - 85%)'],
    ['percent-time', 'Pourcentage - temps (85% - 2:30)'],
    ['time', 'Temps seul (sans pourcentage)'],
    ['percent', 'Pourcentage seul'],
];

export default class BatteryTimePreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();

        const page = new Adw.PreferencesPage({
            title: 'Batterie',
            icon_name: 'battery-symbolic',
        });
        window.add(page);

        const panelGroup = new Adw.PreferencesGroup({title: 'Barre du haut'});
        page.add(panelGroup);

        const model = new Gtk.StringList();
        for (const [, label] of PANEL_FORMATS)
            model.append(label);

        const formatRow = new Adw.ComboRow({
            title: 'Affichage',
            subtitle: 'Ce qui est écrit à côté de l’icône de batterie.',
            model,
        });
        const current = settings.get_string('panel-format');
        formatRow.selected = Math.max(0, PANEL_FORMATS.findIndex(([nick]) => nick === current));
        formatRow.connect('notify::selected', () => {
            settings.set_string('panel-format', PANEL_FORMATS[formatRow.selected][0]);
        });
        panelGroup.add(formatRow);

        const quickGroup = new Adw.PreferencesGroup({title: 'Quick Settings'});
        page.add(quickGroup);

        const wattsRow = new Adw.SwitchRow({
            title: 'Afficher la puissance',
            subtitle: 'Ajoute la consommation instantanée (W) après le temps restant dans le bouton batterie.',
        });
        settings.bind('quick-show-watts', wattsRow, 'active', 0);
        quickGroup.add(wattsRow);
    }
}
