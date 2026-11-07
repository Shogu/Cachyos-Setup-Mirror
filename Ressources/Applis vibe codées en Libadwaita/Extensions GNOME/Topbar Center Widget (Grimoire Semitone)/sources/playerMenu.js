// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const TAG_EDITOR_NAME = 'Disquaire';
const SHOW_ITEMS_DELAY_MS = 150;

function localFile(url) {
    return url?.startsWith('file://') ? Gio.File.new_for_uri(url) : null;
}

function tagEditor() {
    return Gio.AppInfo.get_all().find(app => app.get_name() === TAG_EDITOR_NAME) ?? null;
}

// Demande au gestionnaire de fichiers d'ouvrir le dossier avec le fichier
// sélectionné. L'appel part une fois le menu refermé, avec un jeton
// d'activation : lancé pendant que le menu tient le clavier, Fichiers ouvrait
// bien le dossier mais sans sélectionner le morceau.
function showInFiles(file, done) {
    const nautilus = Gio.DesktopAppInfo.new('org.gnome.Nautilus.desktop');
    const token = nautilus
        ? global.create_app_launch_context(0, -1).get_startup_notify_id(nautilus, [file]) ?? '' : '';
    return GLib.timeout_add(GLib.PRIORITY_DEFAULT, SHOW_ITEMS_DELAY_MS, () => {
        Gio.DBus.session.call('org.freedesktop.FileManager1', '/org/freedesktop/FileManager1',
            'org.freedesktop.FileManager1', 'ShowItems', new GLib.Variant('(ass)', [[file.get_uri()], token]),
            null, Gio.DBusCallFlags.NONE, -1, null, null);
        done();
        return GLib.SOURCE_REMOVE;
    });
}

function actionButton(iconName, text, callback) {
    // Contenu calé à gauche : sinon le bouton centre chaque ligne et les icônes ne s'alignent pas.
    const box = new St.BoxLayout({style_class: 'tcw-action-box', x_expand: true, x_align: Clutter.ActorAlign.START});
    box.add_child(new St.Icon({icon_name: iconName, style_class: 'tcw-action-icon'}));
    box.add_child(new St.Label({text, y_align: Clutter.ActorAlign.CENTER}));
    const button = new St.Button({style_class: 'tcw-action', child: box, can_focus: true, x_expand: true});
    button.connect('clicked', callback);
    return button;
}

// Bouton ⋯ dans l'en-tête de la carte du lecteur, à côté du nom de l'appli, et
// actions dépliées sous la carte (même présentation que les notes).
export class PlayerMenu {
    constructor(message, player, metadata) {
        this._player = player;
        this._metadata = metadata;
        this._showId = 0;
        this._more = new St.Button({
            style_class: 'icon-button tcw-player-more',
            child: new St.Icon({icon_name: 'view-more-symbolic'}),
            accessible_name: 'Actions sur le morceau',
            can_focus: true,
            toggle_mode: true,
            y_align: Clutter.ActorAlign.CENTER,
        });
        this._more.connect('notify::checked', () => this._toggle());
        message.child.get_first_child().add_child(this._more);

        this._actions = new St.BoxLayout({
            style_class: 'tcw-actions tcw-player-actions',
            orientation: Clutter.Orientation.VERTICAL,
            visible: false,
        });
        message.child.add_child(this._actions);
    }

    _toggle() {
        this._actions.destroy_all_children();
        this._actions.visible = this._more.checked;
        if (!this._more.checked)
            return;

        const file = localFile(this._metadata()['xesam:url']?.deepUnpack());
        const editor = file ? tagEditor() : null;
        if (editor) {
            this._actions.add_child(actionButton('document-edit-symbolic', `Ouvrir dans ${TAG_EDITOR_NAME}`, () => {
                editor.launch([file], global.create_app_launch_context(0, -1));
                Main.panel.closeCalendar();
            }));
        }
        if (file) {
            this._actions.add_child(actionButton('folder-open-symbolic', 'Afficher dans Fichiers', () => {
                Main.panel.closeCalendar();
                if (this._showId)
                    GLib.Source.remove(this._showId);
                this._showId = showInFiles(file, () => (this._showId = 0));
            }));
        }
        this._actions.add_child(actionButton('edit-copy-symbolic', 'Copier « Titre – Artiste »', () => {
            const artists = this._player.trackArtists?.join(', ');
            const text = artists ? `${this._player.trackTitle} – ${artists}` : this._player.trackTitle;
            St.Clipboard.get_default().set_text(St.ClipboardType.CLIPBOARD, text);
            this._more.checked = false;
        }));
    }

    destroy() {
        if (this._showId)
            GLib.Source.remove(this._showId);
        this._showId = 0;
        this._player = null;
        this._metadata = null;
    }
}
