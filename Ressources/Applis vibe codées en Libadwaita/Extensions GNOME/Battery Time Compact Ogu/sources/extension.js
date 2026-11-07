import {
    Extension as BaseExtension,
    InjectionManager,
} from 'resource:///org/gnome/shell/extensions/extension.js';
import {panel} from 'resource:///org/gnome/shell/ui/main.js';
import {Indicator} from 'resource:///org/gnome/shell/ui/status/system.js';
import Gio from 'gi://Gio';
import UPower from 'gi://UPowerGlib';

function _formatTime(seconds) {
    if (!Number.isFinite(seconds) || seconds <= 0)
        return '…';

    const totalMinutes = Math.round(seconds / 60);
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    return `${hours}:${minutes.toString().padStart(2, '0')}`;
}

// Le proxy UPower de GNOME ne déclare pas `EnergyRate` : on lit la puissance
// avec un proxy dédié sur le même objet DisplayDevice.
function _formatWatts(watts) {
    const value = Number(watts);
    if (!Number.isFinite(value) || value === 0)
        return null;

    return `${Math.abs(value).toFixed(1)} W`;
}

function _batteryTexts(proxy, format, showWatts, energyRate) {
    if (!proxy?.IsPresent)
        return null;

    const percentage = `${Math.round(proxy.Percentage)}%`;
    let timeText = '…';

    switch (proxy.State) {
    case UPower.DeviceState.FULLY_CHARGED:
        timeText = '∞';
        break;
    case UPower.DeviceState.CHARGING:
        timeText = _formatTime(proxy.TimeToFull);
        break;
    case UPower.DeviceState.DISCHARGING:
        timeText = _formatTime(proxy.TimeToEmpty);
        break;
    default:
        break;
    }

    let panelText;
    switch (format) {
    case 'percent-time':
        panelText = `${percentage} - ${timeText}`;
        break;
    case 'time':
        panelText = timeText;
        break;
    case 'percent':
        panelText = percentage;
        break;
    default:
        panelText = `${timeText} - ${percentage}`;
    }

    const watts = showWatts ? _formatWatts(energyRate) : null;
    return {
        panel: panelText,
        quickSettings: watts ? `${timeText} - ${watts}` : timeText,
    };
}

function _system() {
    return panel.statusArea?.quickSettings?._system ?? null;
}

export default class BatteryTimePercentageOguExtension extends BaseExtension {
    // Pose les textes personnalisés juste après la mise à jour native de GNOME.
    _applyTexts(system) {
        const powerToggle = system?._systemItem?.powerToggle;
        const texts = _batteryTexts(
            powerToggle?._proxy,
            this._settings.get_string('panel-format'),
            this._settings.get_boolean('quick-show-watts'),
            this._rate?.get_cached_property('EnergyRate')?.unpack());
        if (!texts)
            return;

        // Le titre du bouton est lié au texte de l'étiquette de la barre : on
        // pose d'abord le titre, puis le texte de la barre.
        powerToggle.title = texts.quickSettings;
        system._percentageLabel.text = texts.panel;
        system._percentageLabel.visible = true;
    }

    _resync() {
        const system = _system();
        system?._systemItem?.powerToggle?._sync();
        system?._sync();
    }

    enable() {
        const powerToggle = _system()?._systemItem?.powerToggle;
        if (!powerToggle)
            return;

        this._settings = this.getSettings();
        this._settings.connectObject(
            'changed::panel-format', () => this._resync(),
            'changed::quick-show-watts', () => this._resync(),
            this);

        // Proxy dédié pour la puissance instantanée (EnergyRate).
        this._cancellable = new Gio.Cancellable();
        Gio.DBusProxy.new_for_bus(
            Gio.BusType.SYSTEM, Gio.DBusProxyFlags.NONE, null,
            'org.freedesktop.UPower',
            '/org/freedesktop/UPower/devices/DisplayDevice',
            'org.freedesktop.UPower.Device',
            this._cancellable,
            (_source, result) => {
                try {
                    this._rate = Gio.DBusProxy.new_for_bus_finish(result);
                } catch (e) {
                    if (!e.matches?.(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED))
                        console.error(`${this.uuid}: ${e.message}`);
                    return;
                }
                // Les propriétés de puissance changent à part du pourcentage :
                // on réapplique les textes à chaque changement.
                this._rate.connectObject(
                    'g-properties-changed', () => this._resync(), this);
                this._resync();
            });

        this._im = new InjectionManager();
        const ext = this;

        // PowerToggle._sync est appelé à chaque changement de propriété d'UPower
        // (pourcentage, durée restante) : les textes sont donc réappliqués à
        // chaque mise à jour.
        this._im.overrideMethod(Object.getPrototypeOf(powerToggle), '_sync', nativeSync => {
            return function (...args) {
                nativeSync.apply(this, args);
                ext._applyTexts(_system());
            };
        });

        // Indicator._sync repose la visibilité de l'étiquette selon le réglage GNOME.
        this._im.overrideMethod(Indicator.prototype, '_sync', nativeSync => {
            return function (...args) {
                nativeSync.apply(this, args);
                ext._applyTexts(this);
            };
        });

        powerToggle._sync();
    }

    disable() {
        this._cancellable?.cancel();
        this._cancellable = null;
        this._rate?.disconnectObject(this);
        this._rate = null;

        this._settings?.disconnectObject(this);
        this._settings = null;

        this._im?.clear();
        this._im = null;

        // Retour immédiat aux textes natifs.
        this._resync();
    }
}
