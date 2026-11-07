import GLib from 'gi://GLib';
import GObject from 'gi://GObject';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import * as QuickSettings from 'resource:///org/gnome/shell/ui/quickSettings.js';
import { gettext as _ } from 'resource:///org/gnome/shell/extensions/extension.js';

import { RestoreSessionMode } from '../models/sessionModes.js';

const MODE_LABELS = () => ({
    [RestoreSessionMode.NEVER]: _('Désactivée'),
    [RestoreSessionMode.LOGIN]: _('À la connexion'),
    [RestoreSessionMode.BOOT]: _('Au démarrage'),
    [RestoreSessionMode.NOTIFICATION]: _('Notification'),
});

// Modes proposés dans le menu. « Au démarrage » reste réglable dans les
// préférences ; il s'affiche dans le sous-titre quand il est actif.
const MENU_MODES = [
    RestoreSessionMode.LOGIN,
    RestoreSessionMode.NOTIFICATION,
    RestoreSessionMode.NEVER,
];

const SessionToggle = GObject.registerClass(
class SessionToggle extends QuickSettings.QuickMenuToggle {
    _init(settings) {
        super._init({
            title: _('Session'),
            iconName: 'view-restore-symbolic',
            toggleMode: false,
        });

        this._settings = settings;
        this._items = new Map();

        this.menu.setHeader('view-restore-symbolic', _('Restauration de la session'));

        const section = new PopupMenu.PopupMenuSection();
        for (const mode of MENU_MODES) {
            const item = new PopupMenu.PopupMenuItem(MODE_LABELS()[mode]);
            item.connect('activate', () => this._setMode(mode));
            section.addMenuItem(item);
            this._items.set(mode, item);
        }
        this.menu.addMenuItem(section);

        // Un clic sur le bouton bascule entre « Désactivée » et le dernier mode actif.
        this.connect('clicked', () => this._onClicked());

        this._changedId = this._settings.connect('changed::restore-session-mode', () => this._sync());
        this._sync();
    }

    _mode() {
        return this._settings.get_uint('restore-session-mode');
    }

    _setMode(mode) {
        if (mode !== RestoreSessionMode.NEVER)
            this._settings.set_uint('last-restore-mode', mode);
        this._settings.set_uint('restore-session-mode', mode);
    }

    _onClicked() {
        const mode = this._mode();
        if (mode === RestoreSessionMode.NEVER) {
            const last = this._settings.get_uint('last-restore-mode');
            this._setMode(last >= RestoreSessionMode.LOGIN ? last : RestoreSessionMode.LOGIN);
        } else {
            this._settings.set_uint('last-restore-mode', mode);
            this._settings.set_uint('restore-session-mode', RestoreSessionMode.NEVER);
        }
    }

    _sync() {
        const mode = this._mode();
        this.checked = mode !== RestoreSessionMode.NEVER;
        this.subtitle = MODE_LABELS()[mode] ?? '';
        for (const [itemMode, item] of this._items)
            item.setOrnament(itemMode === mode ? PopupMenu.Ornament.CHECK : PopupMenu.Ornament.NONE);
    }

    destroy() {
        if (this._changedId) {
            this._settings.disconnect(this._changedId);
            this._changedId = 0;
        }
        super.destroy();
    }
});

const SessionIndicator = GObject.registerClass(
class SessionIndicator extends QuickSettings.SystemIndicator {
    _init(settings) {
        super._init();
        this.quickSettingsItems.push(new SessionToggle(settings));
    }

    destroy() {
        this.quickSettingsItems.forEach(item => item.destroy());
        this.quickSettingsItems = [];
        super.destroy();
    }
});

let indicator = null;
let gridSignalId = 0;
let placeSourceId = 0;

function grid() {
    return Main.panel.statusArea.quickSettings?.menu?._grid ?? null;
}

// Place le bouton juste après le dernier bouton à bascule existant (par exemple
// Caféine), donc dans la même rangée, au lieu d'une rangée seule sous le lecteur.
function placeNextToToggles() {
    const container = grid();
    const toggle = indicator?.quickSettingsItems?.[0];
    if (!container || !toggle)
        return;

    const children = container.get_children();
    let last = null;
    for (const child of children) {
        if (child !== toggle && child instanceof QuickSettings.QuickToggle && child.visible)
            last = child;
    }
    if (!last)
        return;

    const index = children.indexOf(last);
    if (children[index + 1] === toggle)
        return;
    container.set_child_above_sibling(toggle, last);
}

function queuePlacement() {
    if (placeSourceId)
        return;
    placeSourceId = GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, () => {
        placeSourceId = 0;
        try {
            placeNextToToggles();
        } catch (_error) {
            // Mise en page non critique.
        }
        return GLib.SOURCE_REMOVE;
    });
}

export function initQuickToggle(settings) {
    if (indicator)
        return;
    indicator = new SessionIndicator(settings);
    Main.panel.statusArea.quickSettings.addExternalIndicator(indicator);

    // D'autres extensions ajoutent leurs boutons après le nôtre : on se replace.
    const container = grid();
    if (container)
        gridSignalId = container.connect('child-added', queuePlacement);
    queuePlacement();
}

export function destroyQuickToggle() {
    if (placeSourceId) {
        GLib.source_remove(placeSourceId);
        placeSourceId = 0;
    }
    if (gridSignalId) {
        try {
            grid()?.disconnect(gridSignalId);
        } catch (_error) {
            // Conteneur déjà détruit.
        }
        gridSignalId = 0;
    }
    indicator?.destroy();
    indicator = null;
}
