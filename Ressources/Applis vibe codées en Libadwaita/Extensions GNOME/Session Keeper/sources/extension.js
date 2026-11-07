import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import GLib from 'gi://GLib';

import { SessionManager } from './services/sessionManager.js';
import { Log } from './utils/log.js';
import { initSessionOnClose, restoreSessionOnClose } from './ui/sessionOnClose.js';
import { BootTracker } from './utils/bootTracker.js';
import { LoginSessionTracker } from './utils/loginSessionTracker.js';
import { SaveSessionMode, RestoreSessionMode } from './models/sessionModes.js';
import { NotificationService } from './services/notificationService.js';
import { initQuickToggle, destroyQuickToggle } from './ui/quickToggle.js';

const logger = Log.getDefault();

export default class SessionKeeperExtension extends Extension {
    gsettings;
    sessionMgr;

    _settingsSignalIds = [];
    _startupSignalId = 0;
    _startupSourceId = 0;

    enable() {
        this.gsettings = this.getSettings();
        this.sessionMgr = new SessionManager(this.gsettings.schemaId);

        Log.setDebugEnabled(this.gsettings.get_boolean('debug-mode'));

        // Version optimisée : 0 s est le comportement par défaut. On ne remplace
        // jamais un délai explicitement choisi par l’utilisateur.
        if (this.gsettings.get_user_value('autostart-delay') === null)
            this.gsettings.set_int('autostart-delay', 0);

        const updateExclusions = () => {
            const enabled = this.gsettings.get_boolean('exclude-enabled');
            const list = enabled ? this.gsettings.get_strv('excluded-apps') : [];
            this.sessionMgr.setExcludedApps(list);
        };
        updateExclusions();

        this._connectSetting('changed::exclude-enabled', updateExclusions);
        this._connectSetting('changed::excluded-apps', updateExclusions);
        this._connectSetting('changed::save-session-trigger', () => this._onSaveSession());
        this._connectSetting('changed::restore-session-trigger', () => this._onRestoreSession());
        this._connectSetting('changed::delete-session-trigger', () => this._onDeleteSession());
        this._connectSetting('changed::save-session-mode', () => this._onSaveModeChanged());
        this._connectSetting('changed::show-notification-trigger', () => this._onShowNotification());
        this._connectSetting('changed::debug-mode', () => {
            Log.setDebugEnabled(this.gsettings.get_boolean('debug-mode'));
        });

        this._applySaveMode();
        this._scheduleConfiguredStartupAction();

        try {
            initQuickToggle(this.gsettings);
        }
        catch (error) {
            logger.error(error, 'Échec de l’ajout du bouton Quick Settings');
        }
    }

    disable() {
        destroyQuickToggle();
        restoreSessionOnClose();
        this._cancelStartupAction();

        if (this.gsettings) {
            for (const id of this._settingsSignalIds) {
                try {
                    this.gsettings.disconnect(id);
                }
                catch {
                    // Le signal a déjà pu disparaître avec l’objet GSettings.
                }
            }
        }
        this._settingsSignalIds = [];

        this.sessionMgr?.destroy();
        this.sessionMgr = null;
        this.gsettings = null;
    }

    _connectSetting(signal, callback) {
        this._settingsSignalIds.push(this.gsettings.connect(signal, callback));
    }

    _applySaveMode() {
        const saveMode = this.gsettings.get_uint('save-session-mode');
        if (saveMode === SaveSessionMode.AUTO) {
            this.sessionMgr.setAutoSaveEnabled(true);
            initSessionOnClose(this.sessionMgr);
            logger.info('Mode d’enregistrement automatique continu activé');
        }
        else {
            this.sessionMgr.setAutoSaveEnabled(false);
            restoreSessionOnClose();
            logger.info('Mode d’enregistrement manuel activé');
        }
    }

    _onSaveModeChanged() {
        this._applySaveMode();
    }

    _scheduleConfiguredStartupAction() {
        const restoreMode = this.gsettings.get_uint('restore-session-mode');
        let action = null;

        if (restoreMode === RestoreSessionMode.LOGIN &&
            LoginSessionTracker.isFirstLogin(this.gsettings.schemaId)) {
            action = () => this._onRestoreSession();
        }
        else if (restoreMode === RestoreSessionMode.BOOT &&
            BootTracker.isFirstBoot(this.uuid)) {
            action = () => this._onRestoreSession();
        }
        else if (restoreMode === RestoreSessionMode.NOTIFICATION) {
            action = () => this._checkAndShowRestoreNotification();
        }

        if (action)
            this._runAfterShellStartup(action);
    }

    _runAfterShellStartup(action) {
        this._cancelStartupAction();

        const queueAction = () => {
            if (!this.gsettings || !this.sessionMgr)
                return;

            const delay = Math.max(0, this.gsettings.get_int('autostart-delay'));
            if (delay > 0) {
                this._startupSourceId = GLib.timeout_add_seconds(
                    GLib.PRIORITY_DEFAULT,
                    delay,
                    () => {
                        this._startupSourceId = 0;
                        action();
                        return GLib.SOURCE_REMOVE;
                    }
                );
            }
            else {
                const run = () => {
                    this._startupSourceId = 0;
                    action();
                };

                if (typeof GLib.idle_add_once === 'function') {
                    this._startupSourceId = GLib.idle_add_once(GLib.PRIORITY_DEFAULT_IDLE, run);
                }
                else {
                    this._startupSourceId = GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, () => {
                        run();
                        return GLib.SOURCE_REMOVE;
                    });
                }
            }
        };

        // _startingUp est la propriété utilisée par GNOME Shell lui-même et par
        // de nombreuses extensions pour savoir si startup-complete est encore à venir.
        if (Main.layoutManager._startingUp) {
            this._startupSignalId = Main.layoutManager.connect('startup-complete', () => {
                if (this._startupSignalId) {
                    Main.layoutManager.disconnect(this._startupSignalId);
                    this._startupSignalId = 0;
                }
                queueAction();
            });
        }
        else {
            queueAction();
        }
    }

    _cancelStartupAction() {
        if (this._startupSignalId) {
            try {
                Main.layoutManager.disconnect(this._startupSignalId);
            }
            catch {
                // Déjà déconnecté.
            }
            this._startupSignalId = 0;
        }

        if (this._startupSourceId) {
            GLib.source_remove(this._startupSourceId);
            this._startupSourceId = 0;
        }
    }

    _onSaveSession() {
        try {
            this.sessionMgr.saveSessionSync();
        }
        catch (e) {
            logger.error(e, 'Échec de l’enregistrement de la session');
        }
    }

    _onRestoreSession() {
        try {
            this.sessionMgr.restoreSession();
        }
        catch (e) {
            logger.error(e, 'Échec de la restauration de la session');
        }
    }

    _onDeleteSession() {
        this.sessionMgr.deleteSession()
            .catch(e => logger.error(e, 'Échec de la suppression de la session'));
    }

    _onShowNotification() {
        NotificationService.showRestoreNotification(() => this._onRestoreSession());
    }

    _checkAndShowRestoreNotification() {
        try {
            if (this.sessionMgr.hasStartupSession())
                this._onShowNotification();
            else
                logger.info('Aucune session enregistrée trouvée : notification non affichée');
        }
        catch (error) {
            logger.error(error, 'Échec de la vérification de la session enregistrée');
        }
    }
}
