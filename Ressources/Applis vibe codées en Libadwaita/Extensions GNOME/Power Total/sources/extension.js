// SPDX-License-Identifier: GPL-3.0-only
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {PowerState} from './lib/powerState.js';
import {Profiles} from './lib/profiles.js';
import {Appearance} from './lib/appearance.js';

export default class PowerTotal extends Extension {
    enable() {
        this._settings = this.getSettings();
        this._modules = new Map();
        this._reported = new Set();
        this._state = null;
        this._sensor = new PowerState(state => {
            this._state = state;
            for (const module of this._modules.values()) module.update(state);
        }, error => this._report('Alimentation', error));
        this._settingsId = this._settings.connect('changed', (_settings, key) => {
            if (['profiles-enabled', 'screen-enabled', 'theme-enabled', 'keyboard-enabled'].includes(key)) this._syncModules();
        });
        this._syncModules();
    }

    _report(name, error) {
        if (!this._settings) return;
        const message = `${name} : ${error.message ?? error}`;
        if (this._reported.has(message)) return;
        this._reported.add(message);
        console.warn(`[Power Total] ${message}`);
        if (this._settings.get_boolean('notifications')) Main.notify('Power Total', message);
    }

    _syncModules() {
        const definitions = [
            ['profiles-enabled', 'Profils', () => new Profiles(this._settings, error => this._report('Profils', error))],
            ['screen-enabled', 'Écran', () => new Appearance('brightness', this._settings, error => this._report('Écran', error))],
            ['theme-enabled', 'Thème', () => new Appearance('theme', this._settings, error => this._report('Thème', error))],
            ['keyboard-enabled', 'Clavier', () => new Appearance('keyboard', this._settings, error => this._report('Clavier', error))],
        ];
        for (const [key, name, create] of definitions) {
            if (!this._settings.get_boolean(key)) {
                this._modules.get(key)?.destroy();
                this._modules.delete(key);
            } else if (!this._modules.has(key)) {
                try {
                    const module = create();
                    this._modules.set(key, module);
                    module.update(this._state);
                } catch (error) {
                    this._report(name, error);
                }
            }
        }
    }

    disable() {
        if (this._settingsId) this._settings.disconnect(this._settingsId);
        this._settingsId = 0;
        this._sensor?.destroy();
        this._sensor = null;
        for (const module of this._modules?.values() ?? []) module.destroy();
        this._modules?.clear();
        this._modules = null;
        this._state = null;
        this._settings = null;
        this._reported = null;
    }
}
