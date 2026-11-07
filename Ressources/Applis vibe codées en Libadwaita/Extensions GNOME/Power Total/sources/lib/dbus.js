// SPDX-License-Identifier: GPL-3.0-only
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

export function unpack(value) {
    return value?.deepUnpack?.() ?? value?.deep_unpack?.() ?? value;
}

// All proxy creation and writes share a cancellable owned by this endpoint.
export class Endpoint {
    constructor(bus, name, path, iface, changed, report) {
        Object.assign(this, {name, path, iface, changed, report});
        this._alive = true;
        this._signals = [];
        this._cancel = new Gio.Cancellable();
        Gio.DBusProxy.new_for_bus(bus, Gio.DBusProxyFlags.NONE, null,
            name, path, iface, this._cancel, (_source, result) => {
                let proxy;
                try {
                    proxy = Gio.DBusProxy.new_for_bus_finish(result);
                } catch (error) {
                    if (this._alive) this.report(error);
                    return;
                }
                if (!this._alive) {
                    proxy.run_dispose();
                    return;
                }
                this.proxy = proxy;
                this._signals.push(proxy.connect('g-properties-changed', () => this.changed()));
                this._signals.push(proxy.connect('notify::g-name-owner', () => this.changed()));
                this.changed();
            });
    }

    get ready() {
        return this._alive && Boolean(this.proxy?.g_name_owner);
    }

    get(property, fallback = null) {
        if (!this.ready) return fallback;
        return unpack(this.proxy.get_cached_property(property)) ?? fallback;
    }

    async set(property, type, value) {
        if (!this.ready) throw new Error(`Service indisponible : ${this.name}`);
        const proxy = this.proxy;
        return new Promise((resolve, reject) => {
            proxy.call('org.freedesktop.DBus.Properties.Set',
                new GLib.Variant('(ssv)', [this.iface, property, new GLib.Variant(type, value)]),
                Gio.DBusCallFlags.NONE, 5000, this._cancel, (source, result) => {
                    try {
                        source.call_finish(result);
                        resolve();
                    } catch (error) {
                        reject(error);
                    }
                });
        });
    }

    destroy() {
        this._alive = false;
        this._cancel.cancel();
        for (const id of this._signals) this.proxy?.disconnect(id);
        this._signals = [];
        this.proxy?.run_dispose();
        this.proxy = null;
        this.changed = () => {};
    }
}

export const PROFILE_SERVICES = [
    ['org.freedesktop.UPower.PowerProfiles', '/org/freedesktop/UPower/PowerProfiles'],
    ['net.hadess.PowerProfiles', '/net/hadess/PowerProfiles'],
];
