// SPDX-License-Identifier: GPL-3.0-only
import Gio from 'gi://Gio';
import UPower from 'gi://UPowerGlib';
import {Endpoint} from './dbus.js';

export class PowerState {
    constructor(changed, report) {
        this._changed = changed;
        const update = () => this._changed(this.state);
        this._root = new Endpoint(Gio.BusType.SYSTEM, 'org.freedesktop.UPower',
            '/org/freedesktop/UPower', 'org.freedesktop.UPower', update, report);
        this._battery = new Endpoint(Gio.BusType.SYSTEM, 'org.freedesktop.UPower',
            '/org/freedesktop/UPower/devices/DisplayDevice',
            'org.freedesktop.UPower.Device', update, report);
    }

    get state() {
        const onBattery = this._root?.get('OnBattery');
        if (typeof onBattery !== 'boolean') return null;
        const warning = this._battery?.get('WarningLevel', UPower.DeviceLevel.NONE);
        const state = this._battery?.get('State');
        const discharging = [UPower.DeviceState.DISCHARGING, UPower.DeviceState.PENDING_DISCHARGE].includes(state);
        return {
            onBattery,
            lowBattery: onBattery && [UPower.DeviceLevel.LOW, UPower.DeviceLevel.CRITICAL, UPower.DeviceLevel.ACTION].includes(warning),
            weakAdapterSuspected: !onBattery && discharging && Math.abs(this._battery?.get('EnergyRate', 0)) > 1,
        };
    }

    destroy() {
        this._root.destroy();
        this._battery.destroy();
        this._changed = () => {};
    }
}
