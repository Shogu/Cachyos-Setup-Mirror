import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import Shell from 'gi://Shell';
import St from 'gi://St';

import * as SystemActions from 'resource:///org/gnome/shell/misc/systemActions.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as Volume from 'resource:///org/gnome/shell/ui/status/volume.js';
import * as EndSessionDialog from 'resource:///org/gnome/shell/ui/endSessionDialog.js';
import {Extension, InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';
import {QuickSettingsItem} from 'resource:///org/gnome/shell/ui/quickSettings.js';

import {ChargeLimitIndicator} from './chargeLimitToggle.js';
import {ProjectorIndicator} from './projectorToggle.js';
import {UpdateIndicator} from './updateToggle.js';

const SCREENSHOT_ICON = 'screenshooter-symbolic';
const LOCK_ICON = 'system-lock-screen-symbolic';
const SHUTDOWN_ICON = 'system-shutdown-symbolic';

const SETTINGS_FALLBACK_ICON = 'preferences-system-symbolic';
const TWEAKS_ICON = 'preferences-system-symbolic';
const DCONF_ICON = 'preferences-desktop-apps-symbolic';
const EXTENSIONS_ICON = 'com.mattjakeman.ExtensionManager-symbolic';

const ENERGY_TITLE = 'Énergie';
const POWER_SAVER_TITLE = 'Powersave';
const DARK_STYLE_TITLE = 'Thème Dark';
const DARK_STYLE_ICON = 'dark-mode-symbolic';
const LOGOUT_TITLE = 'Reconnexion';
const LOCK_TITLE = 'Verrouiller la session';
const LOGOUT_DIALOG_TYPE = 0; // DialogType.LOGOUT de endSessionDialog.js

const SETTINGS_APP_ID = 'org.gnome.Settings.desktop';
const TWEAKS_APP_ID = 'org.gnome.tweaks.desktop';
const DCONF_APP_ID = 'ca.desrt.dconf-editor.desktop';
const EXTENSIONS_APP_ID = 'com.mattjakeman.ExtensionManager.desktop';

const CompactSplitItem = GObject.registerClass(
class CompactSplitItem extends QuickSettingsItem {
    _init(params = {}) {
        const {
            iconName = null,
            gicon = null,
            accessibleName = '',
            menuAccessibleName = 'Ouvrir les options',
            onPrimary = null,
        } = params;

        super._init({
            hasMenu: true,
            reactive: false,
            can_focus: false,
            style_class: 'focus-buttons-split-item',
        });

        const box = new St.BoxLayout({
            style_class: 'focus-buttons-split-box',
        });
        this.set_child(box);

        const iconProps = {};
        if (gicon)
            iconProps.gicon = gicon;
        else if (iconName)
            iconProps.icon_name = iconName;

        this.primaryButton = new St.Button({
            style_class: 'icon-button focus-buttons-split-primary',
            can_focus: true,
            accessible_name: accessibleName,
            child: new St.Icon(iconProps),
        });
        box.add_child(this.primaryButton);

        this.menuButton = new St.Button({
            style_class: 'icon-button focus-buttons-split-menu',
            can_focus: true,
            accessible_name: menuAccessibleName,
            child: new St.Icon({icon_name: 'go-next-symbolic'}),
        });
        box.add_child(this.menuButton);

        if (onPrimary)
            this.primaryButton.connect('clicked', onPrimary);

        this.menuButton.connect('clicked', () => this.menu.open());
        this.menuButton.connect('popup-menu', () => this.menu.open());
    }
});

class HoverAutoCloseController {
    constructor(menu, closeCallback, delay) {
        this._menu = menu;
        this._actor = menu?.actor ?? null;
        this._closeCallback = closeCallback;
        this._delay = delay;

        this._timeoutId = 0;
        this._openStateId = 0;
        this._hoverId = 0;
        this._hasEnteredMenu = false;
        this._previousTrackHover = false;
        this._allocationId = 0;
        this._resizePos = null;
        this._resizeTime = 0;
        this._pollId = 0;
    }

    setDelay(delay) {
        this._delay = delay;
    }

    enable() {
        if (!this._menu || !this._actor)
            return false;

        this._previousTrackHover = this._actor.track_hover;
        this._actor.track_hover = true;

        this._hoverId = this._actor.connect('notify::hover', () => {
            this._onHoverChanged();
        });

        this._openStateId = this._menu.connect('open-state-changed', (_menu, isOpen) => {
            this._onOpenStateChanged(isOpen);
        });

        // Quand le menu change de taille (liste de rendez-vous ou de notes qui
        // rétrécit), le pointeur peut se retrouver dehors sans avoir bougé.
        this._allocationId = this._actor.connect('notify::height', () => {
            if (this._actor?.hover) {
                const [x, y] = global.get_pointer();
                this._resizePos = [x, y];
                this._resizeTime = GLib.get_monotonic_time();
            }
        });

        return true;
    }

    disable() {
        this._cancelClose();

        if (this._actor && this._allocationId)
            this._actor.disconnect(this._allocationId);
        this._allocationId = 0;

        if (this._actor && this._hoverId)
            this._actor.disconnect(this._hoverId);

        if (this._menu && this._openStateId)
            this._menu.disconnect(this._openStateId);

        if (this._actor)
            this._actor.track_hover = this._previousTrackHover;

        this._hoverId = 0;
        this._openStateId = 0;
        this._menu = null;
        this._actor = null;
        this._closeCallback = null;
    }

    _onOpenStateChanged(isOpen) {
        this._cancelClose();
        this._hasEnteredMenu = false;

        if (!isOpen)
            return;

        this._actor.sync_hover();
        if (this._actor.hover)
            this._hasEnteredMenu = true;
    }

    _onHoverChanged() {
        if (!this._menu?.isOpen)
            return;

        if (this._actor.hover) {
            this._hasEnteredMenu = true;
            this._cancelClose();
            return;
        }

        if (!this._hasEnteredMenu)
            return;

        // Perte de survol causée par un redimensionnement : tant que le
        // pointeur n'a pas bougé, ce n'est pas une sortie volontaire.
        if (this._resizePos &&
            GLib.get_monotonic_time() - this._resizeTime < 500000) {
            const [x, y] = global.get_pointer();
            if (x === this._resizePos[0] && y === this._resizePos[1]) {
                this._startPointerWatch();
                return;
            }
        }

        this._scheduleClose();
    }

    _startPointerWatch() {
        if (this._pollId)
            return;

        this._pollId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 120, () => {
            if (!this._menu?.isOpen || !this._actor) {
                this._pollId = 0;
                return GLib.SOURCE_REMOVE;
            }

            this._actor.sync_hover();
            if (this._actor.hover) {
                this._pollId = 0;
                return GLib.SOURCE_REMOVE;
            }

            const [x, y] = global.get_pointer();
            if (x !== this._resizePos?.[0] || y !== this._resizePos?.[1]) {
                this._resizePos = null;
                this._pollId = 0;
                this._scheduleClose();
                return GLib.SOURCE_REMOVE;
            }
            return GLib.SOURCE_CONTINUE;
        });
    }

    _scheduleClose(delay = this._delay) {
        this._cancelClose();

        this._timeoutId = GLib.timeout_add(
            GLib.PRIORITY_DEFAULT,
            delay,
            () => {
                this._timeoutId = 0;

                if (!this._menu?.isOpen)
                    return GLib.SOURCE_REMOVE;

                this._actor.sync_hover();
                if (this._actor.hover || this._isTyping())
                    return GLib.SOURCE_REMOVE;

                const [, , modifiers] = global.get_pointer();
                const buttonMask =
                    Clutter.ModifierType.BUTTON1_MASK |
                    Clutter.ModifierType.BUTTON2_MASK |
                    Clutter.ModifierType.BUTTON3_MASK;

                if (modifiers & buttonMask) {
                    this._scheduleClose(120);
                    return GLib.SOURCE_REMOVE;
                }

                this._closeCallback?.();
                return GLib.SOURCE_REMOVE;
            }
        );
    }

    // Saisie en cours dans un champ du menu (titre de note, mot de passe Wi-Fi…) :
    // le menu reste ouvert même si le pointeur est sorti.
    _isTyping() {
        const focus = global.stage.get_key_focus();
        return focus instanceof Clutter.Text && focus.editable && this._actor.contains(focus);
    }

    _cancelClose() {
        if (this._pollId) {
            GLib.source_remove(this._pollId);
            this._pollId = 0;
        }
        this._resizePos = null;

        if (!this._timeoutId)
            return;

        GLib.source_remove(this._timeoutId);
        this._timeoutId = 0;
    }
}

export default class FocusButtonsExtension extends Extension {
    enable() {
        this._settings = this.getSettings();
        this._settingsChangedId = this._settings.connect('changed', (_settings, key) => {
            // Le délai ne demande pas de tout reconstruire à chaque cran du spinner.
            if (key === 'close-delay-ms') {
                const delay = this._settings.get_uint('close-delay-ms');
                this._quickSettingsAutoClose?.setDelay(delay);
                this._calendarAutoClose?.setDelay(delay);
                return;
            }
            this._refreshFeatures();
        });

        this._quickSettings = Main.panel.statusArea.quickSettings;
        this._quickSettingsMenu = this._quickSettings?.menu ?? null;
        this._quickSettingsActor = this._quickSettingsMenu?.actor ?? null;
        this._dateMenu = Main.panel.statusArea.dateMenu ?? null;
        this._calendarMenu = this._dateMenu?.menu ?? null;
        this._systemActions = SystemActions.getDefault();
        this._systemItem = this._quickSettings?._system?._systemItem ?? null;
        this._nativeSystemMenu = this._systemItem?.menu ?? null;

        this._resetFeatureState();
        this._applyFeatures();
    }

    disable() {
        if (this._settings && this._settingsChangedId)
            this._settings.disconnect(this._settingsChangedId);

        this._settingsChangedId = 0;
        this._clearFeatures();

        this._settings = null;
        this._systemActions = null;
        this._calendarMenu = null;
        this._dateMenu = null;
        this._quickSettingsActor = null;
        this._quickSettingsMenu = null;
        this._quickSettings = null;
        this._nativeSystemMenu = null;
        this._systemItem = null;
    }

    _resetFeatureState() {
        this._quickSettingsAutoClose = null;
        this._calendarAutoClose = null;

        this._screenshotButton = null;
        this._screenshotWasVisible = false;
        this._nativeSettingsButton = null;
        this._nativeSettingsWasVisible = false;
        this._nativeLockButton = null;
        this._nativeLockWasVisible = false;
        this._nativeShutdownButton = null;
        this._nativeShutdownWasVisible = false;

        this._settingsSplitItem = null;
        this._powerSplitItem = null;
        this._nestedMenus = new Map();
        this._powerBindings = [];

        this._powerProfileToggle = null;
        this._powerProfileOriginalTitle = null;
        this._powerSaverName = null;
        this._powerSaverIds = [];
        this._darkStyleToggle = null;
        this._darkStyleOriginalTitle = null;

        this._outputSlider = null;
        this._outputMenuId = 0;

        this._volumeMixer = null;
        this._volumeMixerIds = [];
        this._volumeSink = null;
        this._volumeSinkIds = [];

        this._endSessionInjections = null;

        this._chargeLimitIndicator = null;
        this._projectorIndicator = null;
        this._updateIndicator = null;
    }

    _refreshFeatures() {
        this._clearFeatures();
        this._resetFeatureState();
        this._applyFeatures();
    }

    _applyFeatures() {
        const settings = this._settings;
        const delay = settings.get_uint('close-delay-ms');

        if (settings.get_boolean('auto-close-quick-settings') && this._quickSettingsMenu) {
            this._applyStep('fermeture automatique de Quick Settings', () => {
                this._quickSettingsAutoClose = new HoverAutoCloseController(
                    this._quickSettingsMenu,
                    () => Main.panel.closeQuickSettings(),
                    delay
                );
                this._quickSettingsAutoClose.enable();
            });
        }

        if (settings.get_boolean('auto-close-calendar') && this._calendarMenu) {
            this._applyStep('fermeture automatique du calendrier', () => {
                this._calendarAutoClose = new HoverAutoCloseController(
                    this._calendarMenu,
                    () => Main.panel.closeCalendar(),
                    delay
                );
                this._calendarAutoClose.enable();
            });
        }

        if (settings.get_boolean('restart-session-dialog'))
            this._applyStep('fenêtre « Reconnexion »', () => this._relabelLogoutDialog());

        // Tout ce qui suit habille Quick Settings : sans lui, rien à faire.
        if (!this._quickSettingsMenu || !this._quickSettingsActor)
            return;

        this._applyStep('rangée système', () => this._configureSystemRow());

        if (settings.get_boolean('charge-limit-toggle')) {
            this._applyStep('pilule Charge batterie', () => {
                this._chargeLimitIndicator = new ChargeLimitIndicator(this._quickSettings);
            });
        }

        if (settings.get_boolean('projector-toggle')) {
            this._applyStep('pilule Projecteur', () => {
                this._projectorIndicator = new ProjectorIndicator();
                this._quickSettings.addExternalIndicator(this._projectorIndicator);
            });
        }

        if (settings.get_boolean('update-toggle')) {
            this._applyStep('tuile Upgrade', () => {
                this._updateIndicator = new UpdateIndicator(settings.get_string('update-command'));
                this._quickSettings.addExternalIndicator(this._updateIndicator);
            });
        }

        if (settings.get_boolean('rename-power-profile'))
            this._applyStep('libellé « Énergie »', () => this._renamePowerProfile());

        if (settings.get_boolean('rename-dark-style'))
            this._applyStep('libellé « Thème Dark »', () => this._renameDarkStyle());

        if (settings.get_boolean('hide-audio-outputs'))
            this._applyStep('masquage des sorties audio', () => this._hideAudioOutputs());

        if (settings.get_boolean('slider-osd'))
            this._applyStep('OSD du volume', () => this._enableVolumeOsd());
    }

    /**
     * Applique un réglage et journalise son échec sans interrompre les autres.
     *
     * Les réglages sont indépendants : sans cette isolation, une exception dans
     * l'un d'eux sautait silencieusement les suivants (c'est ainsi qu'un défaut
     * du style des rendez-vous avait désactivé le masquage des sorties audio).
     *
     * @param {string} what libellé du réglage, pour le journal
     * @param {Function} apply
     */
    _applyStep(what, apply) {
        try {
            apply();
        } catch (error) {
            console.error(`Focus & Boutons : ${what} — ${error.message}`, error);
        }
    }

    _clearFeatures() {
        this._restoreNativeSystemMenu();

        this._quickSettingsAutoClose?.disable();
        this._calendarAutoClose?.disable();
        this._quickSettingsAutoClose = null;
        this._calendarAutoClose = null;

        this._chargeLimitIndicator?.destroy();
        this._chargeLimitIndicator = null;
        this._projectorIndicator?.destroy();
        this._projectorIndicator = null;
        this._updateIndicator?.destroy();
        this._updateIndicator = null;

        for (const binding of this._powerBindings)
            binding.unbind();
        this._powerBindings = [];

        this._destroySplitItem(this._settingsSplitItem);
        this._destroySplitItem(this._powerSplitItem);
        this._settingsSplitItem = null;
        this._powerSplitItem = null;

        if (this._screenshotButton)
            this._screenshotButton.visible = this._screenshotWasVisible;
        if (this._nativeSettingsButton)
            this._nativeSettingsButton.visible = this._nativeSettingsWasVisible;
        if (this._nativeLockButton)
            this._nativeLockButton.visible = this._nativeLockWasVisible;
        if (this._nativeShutdownButton)
            this._nativeShutdownButton.visible = this._nativeShutdownWasVisible;

        this._restorePowerSaver();
        if (this._powerProfileToggle && this._powerProfileOriginalTitle !== null)
            this._powerProfileToggle.title = this._powerProfileOriginalTitle;
        if (this._darkStyleToggle && this._darkStyleOriginalTitle !== null)
            this._darkStyleToggle.title = this._darkStyleOriginalTitle;
        this._darkStyleToggle = null;
        this._darkStyleOriginalTitle = null;

        this._restoreAudioOutputs();
        this._disableVolumeOsd();

        this._endSessionInjections?.clear();
        this._endSessionInjections = null;
    }

    _configureSystemRow() {
        const root = this._quickSettings?._system?._systemItem?.child ?? this._quickSettingsActor;
        const screenshotButton = this._findButtonByIcon(root, SCREENSHOT_ICON);
        const lockButton = this._findButtonByIcon(root, LOCK_ICON);
        const shutdownButton = this._findButtonByIcon(root, SHUTDOWN_ICON);

        if (!screenshotButton)
            return false;

        const parent = screenshotButton.get_parent();
        if (!parent || typeof parent.insert_child_at_index !== 'function')
            return false;

        const settingsButton = this._findNativeSettingsButton(parent, screenshotButton);

        this._screenshotButton = screenshotButton;
        this._screenshotWasVisible = screenshotButton.visible;
        if (this._settings.get_boolean('hide-screenshot'))
            screenshotButton.hide();

        if (settingsButton && this._settings.get_boolean('split-settings-button'))
            this._installSettingsSplitButton(parent, settingsButton);

        if (lockButton && shutdownButton && this._settings.get_boolean('split-power-button'))
            this._installPowerSplitButton(parent, lockButton, shutdownButton);

        return true;
    }

    _findNativeSettingsButton(parent, screenshotButton) {
        const settingsApp = Shell.AppSystem.get_default().lookup_app(SETTINGS_APP_ID);
        const expectedName = settingsApp?.get_name() ?? null;
        const children = parent.get_children();

        if (expectedName) {
            const byName = children.find(child =>
                child instanceof St.Button && child.accessible_name === expectedName);
            if (byName)
                return byName;
        }

        const screenshotIndex = children.indexOf(screenshotButton);
        if (screenshotIndex >= 0) {
            const candidate = children[screenshotIndex + 1];
            if (candidate instanceof St.Button)
                return candidate;
        }

        return null;
    }

    _installSettingsSplitButton(parent, settingsButton) {
        const app = Shell.AppSystem.get_default().lookup_app(SETTINGS_APP_ID);
        if (!app)
            return false;

        const index = parent.get_children().indexOf(settingsButton);
        if (index < 0)
            return false;

        this._nativeSettingsButton = settingsButton;
        this._nativeSettingsWasVisible = settingsButton.visible;
        settingsButton.hide();

        this._settingsSplitItem = new CompactSplitItem({
            gicon: app.get_icon(),
            iconName: SETTINGS_FALLBACK_ICON,
            accessibleName: 'Paramètres',
            menuAccessibleName: 'Autres réglages GNOME',
            onPrimary: () => this._launchApp(SETTINGS_APP_ID),
        });
        this._settingsSplitItem.menu.setHeader(app.get_icon() ?? SETTINGS_FALLBACK_ICON, 'Réglages');

        this._addAppMenuAction(this._settingsSplitItem.menu, 'Ajustements', TWEAKS_APP_ID, TWEAKS_ICON);
        this._addAppMenuAction(this._settingsSplitItem.menu, 'Éditeur dconf', DCONF_APP_ID, DCONF_ICON);
        this._addAppMenuAction(this._settingsSplitItem.menu, 'Extensions', EXTENSIONS_APP_ID, EXTENSIONS_ICON);

        parent.insert_child_at_index(this._settingsSplitItem, index);
        this._attachNestedMenu(this._settingsSplitItem);
        return true;
    }

    _installPowerSplitButton(parent, lockButton, shutdownButton) {
        const index = parent.get_children().indexOf(shutdownButton);
        if (index < 0)
            return false;

        this._nativeLockButton = lockButton;
        this._nativeLockWasVisible = lockButton.visible;
        this._nativeShutdownButton = shutdownButton;
        this._nativeShutdownWasVisible = shutdownButton.visible;
        lockButton.hide();
        shutdownButton.hide();

        this._powerSplitItem = new CompactSplitItem({
            iconName: SHUTDOWN_ICON,
            accessibleName: 'Éteindre',
            menuAccessibleName: 'Options d’alimentation et de session',
            onPrimary: () => {
                this._systemActions.activatePowerOff();
                Main.panel.closeQuickSettings();
            },
        });
        this._powerSplitItem.menu.setHeader(SHUTDOWN_ICON, 'Alimentation');

        this._addBoundSystemAction(
            this._powerSplitItem.menu,
            'Suspendre',
            'can-suspend',
            'media-playback-pause-symbolic',
            () => this._systemActions.activateSuspend()
        );
        this._addBoundSystemAction(
            this._powerSplitItem.menu,
            'Redémarrer…',
            'can-restart',
            'system-reboot-symbolic',
            () => this._systemActions.activateRestart()
        );
        this._addBoundSystemAction(
            this._powerSplitItem.menu,
            LOGOUT_TITLE,
            'can-logout',
            'system-log-out-symbolic',
            () => this._logoutSession()
        );
        this._addBoundSystemAction(
            this._powerSplitItem.menu,
            LOCK_TITLE,
            'can-lock-screen',
            LOCK_ICON,
            () => this._systemActions.activateLockScreen()
        );

        const powerOffBinding = this._systemActions.bind_property(
            'can-power-off',
            this._powerSplitItem.primaryButton,
            'reactive',
            GObject.BindingFlags.DEFAULT | GObject.BindingFlags.SYNC_CREATE
        );
        this._powerBindings.push(powerOffBinding);

        parent.insert_child_at_index(this._powerSplitItem, index);
        this._attachNestedMenu(this._powerSplitItem);
        return true;
    }

    _addAppMenuAction(menu, label, appId, fallbackIcon) {
        const app = Shell.AppSystem.get_default().lookup_app(appId);
        if (!app)
            return null;

        return menu.addAction(
            label,
            () => this._launchApp(appId),
            app.get_icon() ?? fallbackIcon
        );
    }

    _addBoundSystemAction(menu, label, propertyName, iconName, callback) {
        const item = menu.addAction(label, () => {
            callback();
            Main.panel.closeQuickSettings();
        }, iconName);

        const binding = this._systemActions.bind_property(
            propertyName,
            item,
            'visible',
            GObject.BindingFlags.DEFAULT | GObject.BindingFlags.SYNC_CREATE
        );
        this._powerBindings.push(binding);
        return item;
    }

    _launchApp(appId) {
        const app = Shell.AppSystem.get_default().lookup_app(appId);
        if (!app) {
            console.warn(`Focus & Boutons: application introuvable: ${appId}`);
            return;
        }

        Main.overview.hide();
        Main.panel.closeQuickSettings();
        app.activate();
    }

    _attachNestedMenu(item) {
        const menu = item?.menu;
        const overlay = this._quickSettingsMenu?._overlay;
        if (!menu || !overlay)
            return false;

        overlay.add_child(menu.actor);
        const openStateId = menu.connect('open-state-changed', (_menu, isOpen) => {
            if (isOpen) {
                item.add_style_class_name('focus-buttons-split-open');
                const activeMenu = this._quickSettingsMenu?._activeMenu;
                if (activeMenu && activeMenu !== menu)
                    activeMenu.close();

                // SystemItem is the direct child of the Quick Settings grid. Its
                // `menu` property is what the native layout watches to reserve
                // vertical space for an opened submenu. Temporarily expose our
                // nested split-button menu there so it expands the panel instead
                // of painting over the rows below it.
                if (this._systemItem)
                    this._systemItem.menu = menu;

                this._queueQuickSettingsRelayout();

                if (this._quickSettingsMenu) {
                    this._quickSettingsMenu._activeMenu = menu;
                    this._quickSettingsMenu._setDimmed?.(true);
                }
            } else {
                item.remove_style_class_name('focus-buttons-split-open');

                if (this._systemItem?.menu === menu)
                    this._systemItem.menu = this._nativeSystemMenu;

                this._queueQuickSettingsRelayout();

                if (this._quickSettingsMenu?._activeMenu === menu) {
                    this._quickSettingsMenu._activeMenu = null;
                    this._quickSettingsMenu._setDimmed?.(false);
                }
            }
        });

        this._nestedMenus.set(item, {menu, openStateId});
        return true;
    }

    _queueQuickSettingsRelayout() {
        this._systemItem?.queue_relayout?.();
        this._quickSettingsMenu?._grid?.queue_relayout?.();
        this._quickSettingsActor?.queue_relayout?.();
    }

    _restoreNativeSystemMenu() {
        if (!this._systemItem)
            return;

        this._systemItem.menu = this._nativeSystemMenu;
        this._queueQuickSettingsRelayout();
    }

    _destroySplitItem(item) {
        if (!item)
            return;

        item.remove_style_class_name?.('focus-buttons-split-open');

        const registration = this._nestedMenus.get(item);
        if (registration) {
            const {menu, openStateId} = registration;

            if (this._systemItem?.menu === menu) {
                this._systemItem.menu = this._nativeSystemMenu;
                this._queueQuickSettingsRelayout();
            }

            if (this._quickSettingsMenu?._activeMenu === menu) {
                this._quickSettingsMenu._activeMenu = null;
                this._quickSettingsMenu._setDimmed?.(false);
            }
            if (openStateId)
                menu.disconnect(openStateId);
            menu.destroy();
            this._nestedMenus.delete(item);
        }

        item.destroy();
    }

    // Le curseur de volume n'ouvre son sélecteur de sortie que si `menuEnabled`
    // est vrai ; GNOME le recalcule à chaque ajout/retrait de périphérique
    // (`_sync`), donc on le force à faux à chaque changement.
    // Dans la fenêtre de confirmation de GNOME (type « Fermer la session »),
    // remplace le titre et le bouton par « Reconnexion ».
    _relabelLogoutDialog() {
        const proto = EndSessionDialog.EndSessionDialog?.prototype;
        if (!proto?._sync || !proto?._updateButtons)
            return;

        this._endSessionInjections = new InjectionManager();

        this._endSessionInjections.overrideMethod(proto, '_sync', nativeSync => {
            return function (...args) {
                nativeSync.apply(this, args);
                if (this._type === LOGOUT_DIALOG_TYPE && this._messageDialogContent)
                    this._messageDialogContent.title = LOGOUT_TITLE;
            };
        });

        this._endSessionInjections.overrideMethod(proto, '_updateButtons', nativeUpdate => {
            return function (...args) {
                nativeUpdate.apply(this, args);
                if (this._type !== LOGOUT_DIALOG_TYPE)
                    return;
                // Le bouton de confirmation est le dernier (après « Annuler »).
                const buttons = this.buttonLayout?.get_children() ?? [];
                const confirm = buttons.at(-1);
                if (confirm && buttons.length > 1)
                    confirm.label = LOGOUT_TITLE;
            };
        });
    }

    _hideAudioOutputs() {
        const slider = this._quickSettings?._volumeOutput?._output;
        if (!slider)
            return;

        this._outputSlider = slider;
        this._outputMenuId = slider.connect('notify::menu-enabled', () => {
            if (slider.menuEnabled)
                slider.menuEnabled = false;
        });
        slider.menu?.close?.(false);
        slider.menuEnabled = false;
    }

    _restoreAudioOutputs() {
        const slider = this._outputSlider;
        if (!slider)
            return;

        if (this._outputMenuId)
            slider.disconnect(this._outputMenuId);
        this._outputMenuId = 0;
        this._outputSlider = null;
        slider._sync?.();
    }

    // OSD natif du volume : GNOME affiche déjà son OSD pour la luminosité et pour
    // les touches du clavier, mais pas quand on déplace le curseur de volume de
    // Quick Settings. On écoute directement le volume de la sortie par défaut
    // (PulseAudio/PipeWire via Gvc) plutôt que le widget du curseur, dont la
    // structure interne change d'une version de GNOME à l'autre.
    _enableVolumeOsd() {
        let mixer = null;
        try {
            mixer = Volume.getMixerControl?.() ?? null;
        } catch (error) {
            console.warn(`Focus & Boutons: getMixerControl: ${error.message}`);
        }
        mixer ??= this._quickSettings?._volumeOutput?._output?._control ?? null;
        if (!mixer) {
            console.warn('Focus & Boutons: mixeur audio introuvable, OSD du volume inactif');
            return;
        }

        this._volumeMixer = mixer;
        this._osdVariant = undefined;
        this._osdErrorLogged = false;
        this._logOsdSignature();
        this._volumeSinkIds = [];
        this._volumeSink = null;

        const attachSink = () => {
            this._detachVolumeSink();
            const sink = mixer.get_default_sink();
            if (!sink)
                return;
            this._volumeSink = sink;
            const onChange = () => this._onVolumeChanged();
            this._volumeSinkIds = [
                sink.connect('notify::volume', onChange),
                sink.connect('notify::is-muted', onChange),
            ];
            console.log(`Focus & Boutons: OSD du volume actif (${sink.name ?? 'sortie par défaut'})`);
        };

        this._volumeMixerIds = [
            mixer.connect('default-sink-changed', attachSink),
            mixer.connect('state-changed', attachSink),
        ];
        attachSink();
    }

    // La signature de osdWindowManager.show() a changé selon les versions de
    // GNOME Shell (niveau seul ou liste de niveaux) : on essaie les formes
    // connues et on retient celle qui passe.
    _showOsd(icon, label, level, maxLevel) {
        const monitor = Main.layoutManager.primaryIndex;
        const manager = Main.osdWindowManager;
        const variants = [
            () => manager.showOne(monitor, icon, label, level, maxLevel),
            () => manager.show(icon, label, {[monitor]: {level, maxLevel}}),
            () => manager.show(monitor, icon, label, level, maxLevel),
        ];

        const order = this._osdVariant !== undefined
            ? [this._osdVariant]
            : variants.map((_v, index) => index);

        let lastError = null;
        for (const index of order) {
            try {
                variants[index]();
                if (this._osdVariant === undefined) {
                    this._osdVariant = index;
                    console.log(`Focus & Boutons: OSD du volume : forme d'appel ${index + 1} retenue`);
                }
                return;
            } catch (error) {
                lastError = error;
            }
        }
        if (!this._osdErrorLogged) {
            this._osdErrorLogged = true;
            console.error(`Focus & Boutons: OSD du volume: ${lastError?.message}`);
        }
    }

    _logOsdSignature() {
        try {
            console.log(`Focus & Boutons: osdWindowManager.show = ${String(Main.osdWindowManager.show).slice(0, 700)}`);
        } catch (error) {
            console.log(`Focus & Boutons: signature OSD illisible: ${error.message}`);
        }
    }

    _detachVolumeSink() {
        if (this._volumeSink) {
            for (const id of this._volumeSinkIds ?? []) {
                try {
                    this._volumeSink.disconnect(id);
                } catch (_error) {
                    // Flux déjà détruit.
                }
            }
        }
        this._volumeSinkIds = [];
        this._volumeSink = null;
    }

    _onVolumeChanged() {
        try {
            // Seulement quand on agit depuis Quick Settings : le clavier a déjà son OSD.
            if (!this._quickSettingsMenu?.isOpen)
                return;

            const sink = this._volumeSink;
            const mixer = this._volumeMixer;
            if (!sink || !mixer)
                return;

            const norm = mixer.get_vol_max_norm();
            const level = norm > 0 ? Math.max(0, sink.volume / norm) : 0;
            const muted = sink.is_muted;

            let iconName;
            if (muted || level === 0)
                iconName = 'audio-volume-muted-symbolic';
            else if (level < 0.34)
                iconName = 'audio-volume-low-symbolic';
            else if (level < 0.67)
                iconName = 'audio-volume-medium-symbolic';
            else
                iconName = 'audio-volume-high-symbolic';

            this._showOsd(
                new Gio.ThemedIcon({name: iconName}),
                `${Math.round(level * 100)} %`,
                muted ? 0 : level,
                Math.max(1, level)
            );
        } catch (error) {
            console.error(`Focus & Boutons: OSD du volume: ${error.message}`);
        }
    }

    _disableVolumeOsd() {
        this._detachVolumeSink();
        if (this._volumeMixer) {
            for (const id of this._volumeMixerIds ?? []) {
                try {
                    this._volumeMixer.disconnect(id);
                } catch (_error) {
                    // Mixeur déjà détruit.
                }
            }
        }
        this._volumeMixerIds = [];
        this._volumeMixer = null;
    }

    _renamePowerProfile() {
        const toggle = this._findPowerProfileToggle(this._quickSettingsActor);
        if (!toggle)
            return false;

        this._powerProfileToggle = toggle;
        this._powerProfileOriginalTitle = toggle.title;
        toggle.title = ENERGY_TITLE;

        // « Économie d'énergie » devient « Powersave », dans le sous-titre et dans le menu.
        this._powerSaverName = toggle._profileItems?.get('power-saver')?.label.text ?? null;
        this._powerSaverIds = [
            [toggle, toggle.connect('notify::subtitle', () => this._relabelPowerSaver())],
            [toggle.menu, toggle.menu.connect('open-state-changed', () => this._relabelPowerSaver())],
        ];
        this._relabelPowerSaver();
        return true;
    }

    _relabelPowerSaver() {
        const toggle = this._powerProfileToggle;
        const item = toggle._profileItems?.get('power-saver');
        if (item)
            item.label.text = POWER_SAVER_TITLE;
        if (this._powerSaverName && toggle.subtitle === this._powerSaverName)
            toggle.subtitle = POWER_SAVER_TITLE;
    }

    _restorePowerSaver() {
        for (const [object, id] of this._powerSaverIds)
            object.disconnect(id);
        this._powerSaverIds = [];
        const toggle = this._powerProfileToggle;
        if (toggle && this._powerSaverName) {
            const item = toggle._profileItems?.get('power-saver');
            if (item)
                item.label.text = this._powerSaverName;
            if (toggle.subtitle === POWER_SAVER_TITLE)
                toggle.subtitle = this._powerSaverName;
        }
        this._powerSaverName = null;
    }

    _renameDarkStyle() {
        const toggle = this._findToggleByIcon(this._quickSettingsActor, DARK_STYLE_ICON);
        if (!toggle)
            return false;

        this._darkStyleToggle = toggle;
        this._darkStyleOriginalTitle = toggle.title;
        toggle.title = DARK_STYLE_TITLE;
        return true;
    }

    _findToggleByIcon(actor, iconName) {
        if (!actor)
            return null;

        if (typeof actor.title === 'string' && actor.icon_name === iconName)
            return actor;

        if (typeof actor.get_children !== 'function')
            return null;

        for (const child of actor.get_children()) {
            const found = this._findToggleByIcon(child, iconName);
            if (found)
                return found;
        }

        return null;
    }

    _logoutSession() {
        if (this._systemActions?.canLogout) {
            this._systemActions.activateLogout();
            return;
        }

        Gio.DBus.session.call(
            'org.gnome.SessionManager',
            '/org/gnome/SessionManager',
            'org.gnome.SessionManager',
            'Logout',
            new GLib.Variant('(u)', [0]),
            null,
            Gio.DBusCallFlags.NONE,
            -1,
            null,
            (connection, result) => {
                try {
                    connection.call_finish(result);
                } catch (error) {
                    console.error(`Focus & Boutons: échec de la fermeture de session: ${error.message}`);
                }
            }
        );
    }

    _findButtonByIcon(actor, iconName) {
        if (!actor)
            return null;

        if (actor instanceof St.Button && actor.icon_name === iconName)
            return actor;

        if (typeof actor.get_children !== 'function')
            return null;

        for (const child of actor.get_children()) {
            const found = this._findButtonByIcon(child, iconName);
            if (found)
                return found;
        }

        return null;
    }

    _findPowerProfileToggle(actor) {
        if (!actor)
            return null;

        const iconName = actor.icon_name ?? '';
        const headerIconName = actor.menu?._headerIcon?.icon_name ?? '';

        if (typeof actor.title === 'string' &&
            (iconName.startsWith('power-profile-') ||
             headerIconName === 'power-profile-balanced-symbolic'))
            return actor;

        if (typeof actor.get_children !== 'function')
            return null;

        for (const child of actor.get_children()) {
            const found = this._findPowerProfileToggle(child);
            if (found)
                return found;
        }

        return null;
    }
}
