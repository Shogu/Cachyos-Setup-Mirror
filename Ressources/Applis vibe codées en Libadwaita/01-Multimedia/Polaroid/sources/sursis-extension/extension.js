// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.

import * as MessageTray from 'resource:///org/gnome/shell/ui/messageTray.js';
import {Extension, InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';

/** Icon of the notification source used for screenshots and screencasts */
const SCREEN_CAPTURE_ICON = 'screenshooter-symbolic';

/** Banner duration for screen capture notifications, in milliseconds (GNOME default: 4000) */
const SCREEN_CAPTURE_TIMEOUT = 15000;

export default class SursisExtension extends Extension {
    enable() {
        this._injections = new InjectionManager();
        this._injections.overrideMethod(MessageTray.MessageTray.prototype, '_showNotificationCompleted',
            original => function () {
                const notification = this._notification;
                if (notification.source.iconName === SCREEN_CAPTURE_ICON &&
                    notification.urgency !== MessageTray.Urgency.CRITICAL)
                    this._updateNotificationTimeout(SCREEN_CAPTURE_TIMEOUT);
                else
                    original.call(this);
            });
    }

    disable() {
        this._injections.clear();
        this._injections = null;
    }
}
