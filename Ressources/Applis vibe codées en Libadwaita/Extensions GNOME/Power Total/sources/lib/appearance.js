// SPDX-License-Identifier: GPL-3.0-only
// Adapted from Power Switching Manager, José Rui Barros (GPL-2.0-or-later).
import Gio from 'gi://Gio';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Endpoint} from './dbus.js';

export class Appearance {
    constructor(kind, settings, report) {
        Object.assign(this, {_kind: kind, _settings: settings, _report: report});
        this._alive = true;
        this._state = null;
        this._revision = 0;
        this._busy = false;
        this._settingsId = settings.connect('changed', (_settings, key) => {
            if ([`battery-${kind}`, `power-${kind}`].includes(key)) this.update(this._state, true);
        });
        if (kind === 'theme')
            this._interface = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'});
        if (kind === 'brightness') {
            this._manager = Main.brightnessManager;
            this._managerId = this._manager?.connect('changed', () => {
                if (this._scale !== this._manager.globalScale) this.update(this._state, true);
            });
        }
        if (kind === 'keyboard') {
            this._keyboard = new Endpoint(Gio.BusType.SESSION, 'org.gnome.SettingsDaemon.Power',
                '/org/gnome/SettingsDaemon/Power', 'org.gnome.SettingsDaemon.Power.Keyboard',
                () => {
                    const ready = this._keyboard?.ready && this._keyboard.get('Brightness', -1) >= 0;
                    const owner = this._keyboard?.proxy?.g_name_owner;
                    if (ready && (!this._ready || owner !== this._owner)) this.update(this._state, true);
                    this._ready = ready;
                    this._owner = owner;
                }, report);
        }
    }

    update(state, force = false) {
        if (!this._alive || !state) return;
        const transition = !this._state || this._state.onBattery !== state.onBattery;
        this._state = state;
        if (!transition && !force) return;
        this._revision++;
        this._apply();
    }

    async _apply() {
        if (!this._alive || !this._state || this._busy) return;
        const revision = this._revision;
        const key = `${this._state.onBattery ? 'battery' : 'power'}-${this._kind}`;
        this._busy = true;
        try {
            if (this._kind === 'theme') {
                const desired = this._settings.get_string(key);
                if (this._interface.get_string('color-scheme') !== desired)
                    this._interface.set_string('color-scheme', desired);
            } else if (this._kind === 'brightness') {
                this._scale = this._manager?.globalScale;
                const value = this._settings.get_double(key);
                if (this._scale && Math.abs(this._scale.value - value) > 0.001)
                    this._scale.value = value;
            } else if (this._keyboard?.ready) {
                const current = this._keyboard.get('Brightness', -1);
                const value = this._settings.get_int(key);
                if (current >= 0 && current !== value)
                    await this._keyboard.set('Brightness', 'i', value);
            }
        } catch (error) {
            if (this._alive) this._report(error);
        } finally {
            this._busy = false;
            if (this._alive && revision !== this._revision) this._apply();
        }
    }

    destroy() {
        this._alive = false;
        this._settings.disconnect(this._settingsId);
        if (this._managerId) this._manager.disconnect(this._managerId);
        this._keyboard?.destroy();
        this._manager = null;
        this._scale = null;
        this._interface = null;
    }
}
