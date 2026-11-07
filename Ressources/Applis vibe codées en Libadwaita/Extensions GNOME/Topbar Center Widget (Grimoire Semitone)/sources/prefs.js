// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.
import Adw from 'gi://Adw';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import GObject from 'gi://GObject';
import Gtk from 'gi://Gtk';
import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

import {expandFolders, grimoireSettings} from './notesFolder.js';
import {PlayersGroup} from './prefs/playersGroup.js';

const POSITIONS = ['left', 'right'];
const COVER_SIZES = ['default', 'medium', 'large'];

function homeRelative(path) {
    const home = GLib.get_home_dir();
    return path.startsWith(`${home}/`) ? `~${path.slice(home.length)}` : path;
}

function positionGroup(settings) {
    const group = new Adw.PreferencesGroup({title: 'Emplacement'});
    const row = new Adw.ComboRow({
        title: 'Colonne des notes',
        model: Gtk.StringList.new(['À gauche, notifications repliées dessous', 'À droite du calendrier']),
        selected: POSITIONS.indexOf(settings.get_string('position')),
    });
    row.connect('notify::selected', () => settings.set_string('position', POSITIONS[row.selected]));
    group.add(row);
    const player = new Adw.SwitchRow({
        title: 'Lecteur au-dessus des notes',
        subtitle: 'Sinon il reste dans la liste des notifications',
    });
    settings.bind('player-above-notes', player, 'active', Gio.SettingsBindFlags.DEFAULT);
    row.bind_property_full('selected', player, 'sensitive', GObject.BindingFlags.SYNC_CREATE,
        (_binding, selected) => [true, selected === 0], null);
    group.add(player);
    return [group, player];
}

function playerGroup(settings, playerRow) {
    const group = new Adw.PreferencesGroup({title: 'Lecteur'});
    const cover = new Adw.ComboRow({
        title: 'Taille de la pochette',
        model: Gtk.StringList.new(['Par défaut', 'Moyenne', 'Grande']),
        selected: COVER_SIZES.indexOf(settings.get_string('cover-size')),
    });
    cover.connect('notify::selected', () => settings.set_string('cover-size', COVER_SIZES[cover.selected]));
    group.add(cover);
    for (const [key, title, subtitle] of [
        ['rounded-cover', 'Pochette arrondie', 'Rayon des coins de GNOME (8 px)'],
        ['show-progress', 'Barre de progression', 'Temps écoulé et durée ; cliquer ou glisser pour se déplacer'],
        ['show-shuffle-repeat', 'Aléatoire et Répéter', 'Pour les lecteurs qui les gèrent'],
        ['single-player', 'Un seul lecteur', 'Celui qui joue, sinon le dernier ayant joué'],
        ['scroll-title', 'Titre défilant', 'Fait défiler un titre trop long au lieu de le couper'],
        ['player-menu', 'Menu ⋯ du morceau', 'Ouvrir dans Disquaire, Afficher dans Fichiers, Copier Titre – Artiste'],
        ['show-next', 'Titre suivant', '« Titre suivant : … », si le lecteur publie sa file d’attente'],
    ]) {
        const row = new Adw.SwitchRow({title, subtitle});
        settings.bind(key, row, 'active', Gio.SettingsBindFlags.DEFAULT);
        group.add(row);
    }
    playerRow.bind_property('active', group, 'sensitive', GObject.BindingFlags.SYNC_CREATE);
    return group;
}

function foldersGroup(settings, grimoire) {
    const folders = grimoire ? expandFolders(grimoire.get_strv('pinned-folders')) : [];
    const group = new Adw.PreferencesGroup({
        title: 'Catégories',
        description: folders.length ? 'Chaque dossier épinglé dans Grimoire est une catégorie ; s’il contient des sous-dossiers, chacun devient une catégorie.'
            : 'Épinglez des dossiers dans Grimoire pour les voir ici.',
    });
    for (const path of folders) {
        const row = new Adw.SwitchRow({
            title: GLib.path_get_basename(path),
            subtitle: homeRelative(path),
            active: !settings.get_strv('hidden-folders').includes(path),
        });
        row.connect('notify::active', () => {
            const hidden = settings.get_strv('hidden-folders').filter(item => item !== path);
            settings.set_strv('hidden-folders', row.active ? hidden : [...hidden, path]);
        });
        group.add(row);
    }
    return group;
}

function listGroup(settings) {
    const group = new Adw.PreferencesGroup({title: 'Liste'});
    const maxRow = new Adw.SpinRow({
        title: 'Notes par catégorie',
        subtitle: '0 pour toutes les afficher',
        adjustment: new Gtk.Adjustment({lower: 0, upper: 1000, step_increment: 1, page_increment: 10}),
    });
    settings.bind('max-notes', maxRow, 'value', Gio.SettingsBindFlags.DEFAULT);
    group.add(maxRow);

    const shortcutRow = new Adw.ActionRow({
        title: 'Nouvelle note',
        subtitle: 'Ouvre le calendrier sur le champ de saisie',
    });
    shortcutRow.add_suffix(new Gtk.ShortcutLabel({
        accelerator: settings.get_strv('new-note-shortcut')[0] ?? '',
        valign: Gtk.Align.CENTER,
    }));
    group.add(shortcutRow);
    return group;
}

export default class TopbarCenterWidgetPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();
        const playerPage = new Adw.PreferencesPage({title: 'Lecteur', icon_name: 'audio-x-generic-symbolic'});
        const [position, playerRow] = positionGroup(settings);
        playerPage.add(position);
        playerPage.add(playerGroup(settings, playerRow));
        const players = new PlayersGroup(settings);
        playerRow.bind_property('active', players, 'sensitive', GObject.BindingFlags.SYNC_CREATE);
        playerPage.add(players);
        const icon = new Adw.SwitchRow({
            title: 'Icône animée dans la barre du haut',
            subtitle: 'Tout à gauche des icônes système, tant qu’un lecteur joue ou est en pause',
        });
        settings.bind('media-indicator', icon, 'active', Gio.SettingsBindFlags.DEFAULT);
        const iconGroup = new Adw.PreferencesGroup({title: 'Barre du haut'});
        iconGroup.add(icon);
        playerPage.add(iconGroup);
        window.add(playerPage);

        const notesPage = new Adw.PreferencesPage({title: 'Notes', icon_name: 'document-edit-symbolic'});
        notesPage.add(foldersGroup(settings, grimoireSettings()));
        notesPage.add(listGroup(settings));
        window.add(notesPage);

        const calendarPage = new Adw.PreferencesPage({title: 'Calendrier', icon_name: 'x-office-calendar-symbolic'});
        const events = new Adw.PreferencesGroup({title: 'Rendez-vous'});
        const style = new Adw.SwitchRow({
            title: 'Rendez-vous distincts par agenda',
            subtitle: 'Point à la couleur de l’agenda, cartouche gris aplati, rendez-vous passés atténués, « en cours »',
        });
        settings.bind('calendar-event-style', style, 'active', Gio.SettingsBindFlags.DEFAULT);
        events.add(style);
        const countdown = new Adw.SwitchRow({
            title: 'Temps restant',
            subtitle: '« dans 25 min », « reste 40 min », « encore 6 jours » avec une fine barre, « demain »',
        });
        settings.bind('calendar-countdown', countdown, 'active', Gio.SettingsBindFlags.DEFAULT);
        style.bind_property('active', countdown, 'sensitive', GObject.BindingFlags.SYNC_CREATE);
        events.add(countdown);
        for (const [key, title, subtitle] of [
            ['quick-event', 'Bouton + Nouveau rendez-vous', 'À droite de « Aujourd’hui », pour le jour sélectionné, sans ouvrir Agenda'],
            ['hide-today-date', 'Masquer la date sous le calendrier', 'Elle répète la date de la barre du haut'],
        ]) {
            const row = new Adw.SwitchRow({title, subtitle});
            settings.bind(key, row, 'active', Gio.SettingsBindFlags.DEFAULT);
            events.add(row);
        }
        calendarPage.add(events);
        window.add(calendarPage);
    }
}
