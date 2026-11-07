// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.
import GObject from 'gi://GObject';
import Meta from 'gi://Meta';

import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import {QuickMenuToggle, SystemIndicator} from 'resource:///org/gnome/shell/ui/quickSettings.js';

const Config = Meta.MonitorSwitchConfigType;
const MODES = [
    [Config.ALL_MIRROR, 'Dupliquer', false],
    [Config.ALL_LINEAR, 'Étendre', false],
    [Config.EXTERNAL, 'Écran externe seul', true],
    [Config.BUILTIN, 'Écran intégré seul', true],
];

function monitorManager() {
    return global.backend.get_monitor_manager();
}

// Pilule « Projecteur » : les choix du raccourci Super+P, visibles dès qu'un
// deuxième écran est branché. Clic principal : Dupliquer ⇄ Étendre.
const ProjectorToggle = GObject.registerClass(
class ProjectorToggle extends QuickMenuToggle {
    _init() {
        super._init({title: 'Projecteur', iconName: 'video-display-symbolic', toggle_mode: false});
        this.menu.setHeader('video-display-symbolic', 'Projecteur');
        this._items = new Map();
        const builtin = monitorManager().has_builtin_panel;
        for (const [type, label, needsBuiltin] of MODES) {
            if (needsBuiltin && !builtin)
                continue;
            this._items.set(type, this.menu.addAction(label, () => monitorManager().switch_config(type)));
        }
        this.connect('clicked', () => {
            monitorManager().switch_config(this.checked ? Config.ALL_LINEAR : Config.ALL_MIRROR);
        });
    }

    sync() {
        const current = monitorManager().get_switch_config();
        this.checked = current === Config.ALL_MIRROR;
        this.subtitle = MODES.find(([type]) => type === current)?.[1] ?? 'Personnalisé';
        for (const [type, item] of this._items) {
            item.setOrnament(type === current ? PopupMenu.Ornament.CHECK : PopupMenu.Ornament.NONE);
        }
    }
});

export const ProjectorIndicator = GObject.registerClass(
class ProjectorIndicator extends SystemIndicator {
    _init() {
        super._init();
        this._toggle = new ProjectorToggle();
        this.quickSettingsItems.push(this._toggle);
        this._monitorsId = monitorManager().connect('monitors-changed', () => this._sync());
        this._sync();
    }

    _sync() {
        this._toggle.visible = global.display.get_n_monitors() > 1 && monitorManager().can_switch_config();
        this._toggle.sync();
    }

    destroy() {
        monitorManager().disconnect(this._monitorsId);
        this.quickSettingsItems.forEach(item => item.destroy());
        this.quickSettingsItems.length = 0;
        super.destroy();
    }
});
