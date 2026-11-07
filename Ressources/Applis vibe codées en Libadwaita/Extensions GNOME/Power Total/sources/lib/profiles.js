// SPDX-License-Identifier: GPL-3.0-only
// Profile selection and app tracking adapted from Auto Power Profile, dmy3k.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {Endpoint, PROFILE_SERVICES, unpack} from './dbus.js';
import {PerformanceAppTracker} from './performanceAppTracker.js';
import {chooseProfile, supportedProfile, canRemember} from './policy.js';

export class Profiles {
    constructor(settings, report) {
        this._settings = settings;
        this._report = report;
        this._alive = true;
        this._state = null;
        this._weak = false;
        this._weakTimer = 0;
        this._signature = null;
        this._busy = false;
        this._expected = null;
        this._lastActive = null;
        this._services = PROFILE_SERVICES.map(([name, path]) =>
            new Endpoint(Gio.BusType.SYSTEM, name, path, name,
                () => this._serviceChanged(), error => report(error)));
        this._settingsId = settings.connect('changed', (_settings, key) => {
            if (!['ac', 'bat', 'remember-user-profile', 'performance-apps', 'performance-apps-ac',
                'performance-apps-bat', 'apps-enabled', 'weak-adapter-protection', 'low-battery-saver'].includes(key)) return;
            this._signature = null;
            if (['performance-apps', 'apps-enabled'].includes(key)) this._syncTracker();
            if (!settings.get_boolean('weak-adapter-protection')) this._resetWeak();
            this.update(this._state);
        });
        const schema = Gio.SettingsSchemaSource.get_default().lookup('org.gnome.settings-daemon.plugins.power', true);
        if (schema?.has_key('power-saver-profile-on-low-battery')) {
            this._gnome = new Gio.Settings({settings_schema: schema});
            this._gnomeId = this._gnome.connect('changed::power-saver-profile-on-low-battery', () => {
                this._signature = null;
                this._apply();
            });
        }
        this._syncTracker();
    }

    _syncTracker() {
        this._tracker?.destroy();
        this._tracker = null;
        if (this._settings.get_boolean('apps-enabled') && this._settings.get_strv('performance-apps').length) {
            this._tracker = new PerformanceAppTracker();
            this._tracker.initialize(() => this._apply());
            this._tracker.setPerformanceApps(this._settings.get_strv('performance-apps'));
        }
    }

    get _endpoint() {
        return this._services?.find(service => service.ready && service.get('ActiveProfile'));
    }

    _config() {
        const s = this._settings;
        return {
            ac: s.get_string('ac'), battery: s.get_string('bat'),
            appsAC: s.get_string('performance-apps-ac'), appsBattery: s.get_string('performance-apps-bat'),
            remember: s.get_boolean('remember-user-profile'),
            lowBatterySaver: s.get_boolean('low-battery-saver') && (this._gnome?.get_boolean('power-saver-profile-on-low-battery') ?? true),
        };
    }

    update(state) {
        if (!this._alive) return;
        this._state = state;
        if (!state || state.onBattery || !this._settings.get_boolean('weak-adapter-protection')) {
            this._resetWeak();
        } else if (!state.weakAdapterSuspected) {
            // Once confirmed, keep protection until unplugged.
            if (this._weakTimer) GLib.Source.remove(this._weakTimer);
            this._weakTimer = 0;
        } else if (!this._weak && !this._weakTimer) {
            this._weakTimer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 30, () => {
                this._weakTimer = 0;
                if (this._alive && this._state?.weakAdapterSuspected && !this._state.onBattery) {
                    this._weak = true;
                    this._apply();
                }
                return GLib.SOURCE_REMOVE;
            });
        }
        this._apply();
    }

    _resetWeak() {
        if (this._weakTimer) GLib.Source.remove(this._weakTimer);
        this._weakTimer = 0;
        this._weak = false;
    }

    _serviceChanged() {
        if (!this._alive) return;
        const endpoint = this._endpoint;
        const owner = endpoint?.proxy?.g_name_owner;
        if (endpoint !== this._lastEndpoint || owner !== this._owner) {
            this._lastEndpoint = endpoint;
            this._owner = owner;
            this._lastActive = null;
            this._signature = null;
            this._expected = null;
        }
        const active = endpoint?.get('ActiveProfile');
        const previous = this._lastActive;
        this._lastActive = active;
        if (active === this._expected) {
            this._expected = null;
        } else if (previous && active && active !== previous && !this._busy && this._state) {
            const config = this._config();
            if (canRemember(this._state, config, Boolean(this._tracker?.hasActiveApps), this._weak)) {
                const key = this._state.onBattery ? 'bat' : 'ac';
                if (['performance', 'balanced', 'power-saver'].includes(active))
                    this._settings.set_string(key, active);
            }
            // A manual change is left in place until a power/app/config transition.
        }
        this._apply();
    }

    async _apply() {
        if (!this._alive || !this._state || !this._endpoint || this._busy) return;
        const endpoint = this._endpoint;
        const config = this._config();
        const apps = Boolean(this._tracker?.hasActiveApps);
        const profiles = endpoint.get('Profiles', []).map(p => unpack(p.Profile));
        const requested = chooseProfile(this._state, config, apps, this._weak);
        const target = supportedProfile(requested, profiles);
        if (!target) return;
        const signature = JSON.stringify([this._state.onBattery, this._state.lowBattery, apps, this._weak, target]);
        if (signature === this._signature) return;
        this._signature = signature;
        if (endpoint.get('ActiveProfile') === target) return;
        this._expected = target;
        this._busy = true;
        try {
            await endpoint.set('ActiveProfile', 's', target);
        } catch (error) {
            if (this._alive) this._report(error);
            this._expected = null;
        } finally {
            this._busy = false;
            // If power state changed while a D-Bus write was pending, apply the
            // latest state after completion, never an obsolete queued value.
            if (this._alive) this._apply();
        }
    }

    destroy() {
        this._alive = false;
        this._settings.disconnect(this._settingsId);
        if (this._gnomeId) this._gnome.disconnect(this._gnomeId);
        this._resetWeak();
        this._tracker?.destroy();
        this._services.forEach(service => service.destroy());
        this._services = [];
        // Keep the current profile; disabling the module is not a request for Balanced.
    }
}
