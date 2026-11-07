// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.
import Gio from 'gi://Gio';
import GObject from 'gi://GObject';

import {QuickToggle, SystemIndicator} from 'resource:///org/gnome/shell/ui/quickSettings.js';

Gio._promisify(Gio.DBusConnection.prototype, 'call');

const UPOWER = 'org.freedesktop.UPower';
const BATTERY_TYPE = 2;

const DeviceProxy = Gio.DBusProxy.makeProxyWrapper(`
<node>
  <interface name="org.freedesktop.UPower.Device">
    <method name="EnableChargeThreshold"><arg type="b" direction="in"/></method>
    <property name="Type" type="u" access="read"/>
    <property name="PowerSupply" type="b" access="read"/>
    <property name="ChargeThresholdSupported" type="b" access="read"/>
    <property name="ChargeThresholdEnabled" type="b" access="read"/>
    <property name="ChargeEndThreshold" type="u" access="read"/>
  </interface>
</node>`);

function deviceProxy(path, cancellable) {
    return new Promise((resolve, reject) => {
        new DeviceProxy(Gio.DBus.system, UPOWER, path,
            (proxy, error) => (error ? reject(error) : resolve(proxy)), cancellable);
    });
}

const ChargeLimitToggle = GObject.registerClass(
class ChargeLimitToggle extends QuickToggle {
    _init(device) {
        super._init({title: 'Charge batterie', iconName: 'battery-level-80-symbolic', toggle_mode: false});
        this._device = device;
        this.connect('clicked', () => this._device.EnableChargeThresholdAsync(!this.checked).catch(logError));
        this._propertiesId = device.connect('g-properties-changed', () => this._sync());
        this._sync();
    }

    _sync() {
        const end = this._device.ChargeEndThreshold;
        this.checked = this._device.ChargeThresholdEnabled;
        this.subtitle = this.checked && end <= 100 ? `Jusqu’à ${end} %` : 'Charge complète';
    }

    destroy() {
        this._device.disconnect(this._propertiesId);
        this._device = null;
        super.destroy();
    }
});

// Pilule « Charge batterie » : le même réglage que « Préserver la santé de la
// batterie » dans Paramètres (UPower) ; absente si la batterie ne le gère pas.
export const ChargeLimitIndicator = GObject.registerClass(
class ChargeLimitIndicator extends SystemIndicator {
    _init(quickSettings) {
        super._init();
        this._quickSettings = quickSettings;
        this._cancellable = new Gio.Cancellable();
        this._findBattery();
    }

    async _findBattery() {
        try {
            const reply = await Gio.DBus.system.call(UPOWER, '/org/freedesktop/UPower', UPOWER, 'EnumerateDevices',
                null, null, Gio.DBusCallFlags.NONE, -1, this._cancellable);
            for (const path of reply.deepUnpack()[0]) {
                const device = await deviceProxy(path, this._cancellable);
                if (device.Type === BATTERY_TYPE && device.PowerSupply && device.ChargeThresholdSupported) {
                    this.quickSettingsItems.push(new ChargeLimitToggle(device));
                    this._quickSettings.addExternalIndicator(this);
                    return;
                }
            }
        } catch (error) {
            if (!error.matches(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED))
                console.warn(`Focus & Boutons : limite de charge indisponible — ${error.message}`);
        }
    }

    destroy() {
        this._cancellable.cancel();
        this.quickSettingsItems.forEach(item => item.destroy());
        this.quickSettingsItems.length = 0;
        this._quickSettings = null;
        super.destroy();
    }
});
