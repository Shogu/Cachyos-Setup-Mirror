import Adw from 'gi://Adw';
import Gtk from 'gi://Gtk';

import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

export default class FocusButtonsPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();

        const page = new Adw.PreferencesPage({
            title: 'Focus & Boutons',
            icon_name: 'preferences-system-symbolic',
        });
        window.add(page);

        const focusGroup = new Adw.PreferencesGroup({
            title: 'Focus',
            description: 'Fermeture automatique des panneaux quand le pointeur en sort.',
        });
        page.add(focusGroup);

        this._addSwitchRow(
            focusGroup,
            settings,
            'auto-close-quick-settings',
            'Quick Settings',
            'Fermer automatiquement Quick Settings.'
        );
        this._addSwitchRow(
            focusGroup,
            settings,
            'auto-close-calendar',
            'Calendrier et notifications',
            'Fermer automatiquement le panneau central.'
        );

        const delayRow = new Adw.ActionRow({
            title: 'Délai de fermeture',
            subtitle: '100 à 2000 ms — 350 ms par défaut',
        });
        const adjustment = new Gtk.Adjustment({
            lower: 100,
            upper: 2000,
            step_increment: 50,
            page_increment: 100,
            value: settings.get_uint('close-delay-ms'),
        });
        const spin = new Gtk.SpinButton({
            adjustment,
            numeric: true,
            valign: Gtk.Align.CENTER,
        });
        spin.connect('value-changed', widget => {
            settings.set_uint('close-delay-ms', widget.get_value_as_int());
        });
        delayRow.add_suffix(spin);
        delayRow.activatable_widget = spin;
        focusGroup.add(delayRow);

        const quickGroup = new Adw.PreferencesGroup({
            title: 'Quick Settings',
            description: 'Simplifier la rangée système et le curseur de volume.',
        });
        page.add(quickGroup);

        this._addSwitchRow(
            quickGroup,
            settings,
            'hide-screenshot',
            'Masquer Capture d’écran',
            'La capture reste disponible avec les raccourcis GNOME.'
        );
        this._addSwitchRow(
            quickGroup,
            settings,
            'split-settings-button',
            'Bouton Réglages scindé',
            'Clic sur la roue dentée : Paramètres. Chevron : Ajustements, dconf et Extensions.'
        );
        this._addSwitchRow(
            quickGroup,
            settings,
            'rename-power-profile',
            'Libellé « Énergie »',
            'Remplacer le titre du profil de puissance par « Énergie », et « Économie d’énergie » par « Powersave ».'
        );
        this._addSwitchRow(
            quickGroup,
            settings,
            'rename-dark-style',
            'Libellé « Thème Dark »',
            'Remplacer le titre « Style sombre » par « Thème Dark ».'
        );
        this._addSwitchRow(
            quickGroup,
            settings,
            'hide-audio-outputs',
            'Masquer les sorties audio',
            'Retirer le chevron du volume : seule la sortie par défaut est utilisée, les autres ne sont plus listées.'
        );
        this._addSwitchRow(
            quickGroup,
            settings,
            'restart-session-dialog',
            'Fenêtre « Reconnexion »',
            'Dans la fenêtre de confirmation de GNOME, afficher « Reconnexion » à la place de « Fermer la session » (titre et bouton).'
        );
        this._addSwitchRow(
            quickGroup,
            settings,
            'split-power-button',
            'Bouton Power scindé',
            'Clic principal : Éteindre. Chevron : Suspendre, Redémarrer, Reconnexion et Verrouiller.'
        );

        this._addSwitchRow(
            quickGroup,
            settings,
            'charge-limit-toggle',
            'Pilule Charge batterie',
            'Le réglage « Préserver la santé de la batterie » de Paramètres, en un clic.'
        );
        this._addSwitchRow(
            quickGroup,
            settings,
            'projector-toggle',
            'Pilule Projecteur',
            'Dupliquer, Étendre ou un seul écran, quand un deuxième écran est branché.'
        );
        this._addSwitchRow(
            quickGroup,
            settings,
            'update-toggle',
            'Tuile Upgrade',
            'Un clic lance le script ci-dessous ; la tuile reste bleue tant qu’il tourne.'
        );
        const commandRow = new Adw.EntryRow({
            title: 'Script de mise à jour',
            text: settings.get_string('update-command'),
            show_apply_button: true,
        });
        commandRow.connect('apply', row => settings.set_string('update-command', row.text));
        quickGroup.add(commandRow);
        this._addSwitchRow(
            quickGroup,
            settings,
            'slider-osd',
            'OSD du volume',
            'Afficher l’OSD de GNOME quand on déplace le curseur de volume de Quick Settings, comme pour la luminosité.'
        );
    }

    _addSwitchRow(group, settings, key, title, subtitle) {
        const row = new Adw.SwitchRow({
            title,
            subtitle,
        });
        settings.bind(key, row, 'active', 0);
        group.add(row);
    }
}
