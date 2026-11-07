import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import { ensureSessionsDirExists, getSessionFilePath } from '../utils/sessionStore.js';
import { Log } from '../utils/log.js';

const logger = Log.getDefault();

const SESSION_FORMAT_VERSION = 3;
const LAUNCH_STAGGER_MS = 80;
const RESTORE_WINDOW_MS = 12000;
const MATCH_RETRY_MS = 70;
const MATCH_RETRIES = 6;
const GEOMETRY_RETRIES = 5;
const AUTOSAVE_DEBOUNCE_MS = 1000;
const MULTI_WINDOW_SETTLE_MS = 650;
const MULTI_WINDOW_CONFIRM_MS = 350;
const NEW_WINDOW_STAGGER_MS = 90;

function normalizeId(value) {
    return typeof value === 'string'
        ? value.replace(/\.desktop$/i, '').trim().toLowerCase()
        : '';
}

function normalizeText(value) {
    return typeof value === 'string'
        ? value.trim().replace(/\s+/g, ' ').toLowerCase()
        : '';
}

function safeCall(object, method, fallback = null) {
    try {
        return typeof object?.[method] === 'function' ? object[method]() : fallback;
    }
    catch {
        return fallback;
    }
}

export class SessionManager {
    sessionsDir;
    extensionId;
    excludedApps;

    _windowCreatedHandler = 0;
    _restoreSources = new Set();
    _geometryCleanups = new Set();
    _pendingWindows = new WeakSet();
    _handledWindows = new WeakSet();
    _toRestore = [];
    _restoring = false;
    _destroyed = false;

    _autosaveEnabled = false;
    _autosaveWindowCreatedId = 0;
    _startupCompleteSignalId = 0;
    _trackedWindowSignals = new Map();
    _autosaveSourceId = 0;
    _autosaveCancellable = null;
    _autosaveGeneration = 0;
    _normalGeometry = new WeakMap();
    _multiWindowSources = new Map();
    _multiWindowAttempted = new Set();
    _expectedWindowsByApp = new Map();
    _startupPayload = null;
    _closing = false;
    _closingResetId = 0;
    _shutdownSubscriptionId = 0;

    constructor(extensionId, excludedApps = []) {
        this.excludedApps = excludedApps;
        this.extensionId = extensionId;
        this.sessionsDir = ensureSessionsDirExists(extensionId);
        // Capture l'état enregistré avant que l'auto-save de la nouvelle connexion puisse
        // modifier le fichier. Les restaurations de démarrage utilisent ce snapshot mémoire.
        this._startupPayload = this._loadValidatedPayload(true);
        this._startWindowTracking();
    }

    setExcludedApps(list) {
        this.excludedApps = Array.isArray(list) ? list : [];
        this._markSessionDirty();
    }

    setAutoSaveEnabled(enabled) {
        const wasEnabled = this._autosaveEnabled;
        this._autosaveEnabled = Boolean(enabled);
        if (!this._autosaveEnabled)
            this._cancelPendingAutosave();
        else if (!wasEnabled)
            this._markSessionDirty();

        if (this._autosaveEnabled)
            this._watchShutdown();
        else
            this._unwatchShutdown();
    }

    // Arrêt ou redémarrage lancé hors du dialogue GNOME (systemctl poweroff,
    // reboot depuis un terminal...) : logind prévient avant de fermer les sessions.
    _watchShutdown() {
        if (this._shutdownSubscriptionId || this._destroyed)
            return;

        try {
            this._shutdownSubscriptionId = Gio.DBus.system.signal_subscribe(
                'org.freedesktop.login1',
                'org.freedesktop.login1.Manager',
                'PrepareForShutdown',
                '/org/freedesktop/login1',
                null,
                Gio.DBusSignalFlags.NONE,
                (_connection, _sender, _path, _iface, _signal, parameters) => {
                    try {
                        const [starting] = parameters.deepUnpack();
                        if (starting)
                            this.flushOnClose();
                        else
                            this._endClosing();
                    }
                    catch (error) {
                        logger.error(error, 'Erreur lors de l’enregistrement avant arrêt');
                    }
                }
            );
        }
        catch (error) {
            logger.error(error, 'Abonnement à PrepareForShutdown impossible');
            this._shutdownSubscriptionId = 0;
        }
    }

    _unwatchShutdown() {
        if (!this._shutdownSubscriptionId)
            return;

        try { Gio.DBus.system.signal_unsubscribe(this._shutdownSubscriptionId); } catch {}
        this._shutdownSubscriptionId = 0;
    }

    // L'arrêt a été annulé : l'enregistrement continu reprend.
    _endClosing() {
        if (this._closingResetId) {
            try { GLib.source_remove(this._closingResetId); } catch {}
            this._closingResetId = 0;
        }
        this._closing = false;
    }

    destroy() {
        this._destroyed = true;
        this._autosaveEnabled = false;
        this._unwatchShutdown();
        this._cancelPendingAutosave();
        if (this._closingResetId) {
            try { GLib.source_remove(this._closingResetId); } catch {}
            this._closingResetId = 0;
        }
        this._stopWindowTracking();
        this._resetRestoreTracking();

        for (const cleanup of [...this._geometryCleanups]) {
            try { cleanup(); } catch {}
        }
        this._geometryCleanups.clear();
        this._toRestore = [];
    }

    saveSessionSync() {
        this._cancelPendingAutosave();
        const payload = this._buildPayload();
        this._writePayloadSync(payload);
        logger.info(`${payload.windows.length} fenêtre(s) enregistrée(s)`);
    }

    // Dernier enregistrement avant la fermeture de session. Les fenêtres qui se
    // ferment ensuite ne doivent plus déclencher d'enregistrement automatique,
    // sinon le fichier serait réécrit avec une session partielle.
    flushOnClose() {
        // Déjà fait (dialogue GNOME puis logind) : un second passage verrait
        // des fenêtres déjà fermées et écraserait la bonne sauvegarde.
        if (this._closing)
            return;

        this._closing = true;
        this._cancelPendingAutosave();

        if (this._closingResetId)
            GLib.source_remove(this._closingResetId);
        // Filet de sécurité : si GNOME n'a finalement pas quitté, l'enregistrement reprend.
        this._closingResetId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 60, () => {
            this._closingResetId = 0;
            this._closing = false;
            return GLib.SOURCE_REMOVE;
        });

        this.saveSessionSync();
    }

    _buildPayload() {
        return {
            formatVersion: SESSION_FORMAT_VERSION,
            created: new Date().toISOString(),
            windows: this.collectAllWindows(),
        };
    }

    _writePayloadSync(payload) {
        const filePath = getSessionFilePath(this.extensionId);
        const data = new TextEncoder().encode(JSON.stringify(payload));
        const file = Gio.File.new_for_path(filePath);
        const [ok] = file.replace_contents(
            data,
            null,
            false,
            Gio.FileCreateFlags.REPLACE_DESTINATION,
            null
        );

        if (!ok)
            throw new Error(`Impossible d’écrire ${filePath}`);

        try { GLib.chmod(filePath, 0o600); } catch {}
    }

    _writePayloadAsync(payload) {
        if (this._destroyed)
            return;

        const filePath = getSessionFilePath(this.extensionId);
        const file = Gio.File.new_for_path(filePath);
        const bytes = new GLib.Bytes(new TextEncoder().encode(JSON.stringify(payload)));
        const generation = ++this._autosaveGeneration;

        this._autosaveCancellable?.cancel();
        const cancellable = new Gio.Cancellable();
        this._autosaveCancellable = cancellable;

        file.replace_contents_bytes_async(
            bytes,
            null,
            false,
            Gio.FileCreateFlags.REPLACE_DESTINATION,
            cancellable,
            (fileObj, result) => {
                try {
                    fileObj.replace_contents_finish(result);
                    if (generation === this._autosaveGeneration) {
                        try { GLib.chmod(filePath, 0o600); } catch {}
                        logger.info(`${payload.windows.length} fenêtre(s) enregistrée(s) automatiquement`);
                    }
                }
                catch (error) {
                    if (!cancellable.is_cancelled())
                        logger.error(error, 'Échec de l’enregistrement automatique de la session');
                }
                finally {
                    if (this._autosaveCancellable === cancellable)
                        this._autosaveCancellable = null;
                }
            }
        );
    }

    restoreSession() {
        if (this._destroyed)
            return;

        // L'état enregistré au démarrage de GNOME prime tant qu'il n'a pas été
        // restauré : l'enregistrement continu a déjà pu réécrire le fichier.
        const payload = this._startupPayload ?? this._loadValidatedPayload();
        this._startupPayload = null;
        if (!payload)
            return;

        this._resetRestoreTracking();
        this._destroyed = false;

        let windows = payload.windows;
        if (this.excludedApps.length > 0) {
            const excluded = new Set(this.excludedApps.map(normalizeId));
            windows = windows.filter(info => !excluded.has(normalizeId(info.appId)));
        }

        if (windows.length === 0) {
            logger.info('Aucune fenêtre à restaurer');
            return;
        }

        this._expectedWindowsByApp.clear();
        for (const info of windows)
            this._expectedWindowsByApp.set(info.appId, (this._expectedWindowsByApp.get(info.appId) ?? 0) + 1);

        this._toRestore = windows.slice();
        this._pendingWindows = new WeakSet();
        this._handledWindows = new WeakSet();
        this._restoring = true;

        const display = global.display;
        this._windowCreatedHandler = display.connect('window-created', (_display, window) => {
            this._queueWindowMatch(window);
        });

        // Les applications déjà présentes sont traitées immédiatement : aucun délai.
        for (const actor of global.get_window_actors()) {
            const window = actor.get_meta_window();
            if (window)
                this._queueWindowMatch(window);
        }

        if (!this._restoring)
            return;

        const appSystem = Shell.AppSystem.get_default();
        const appIds = [...new Set(this._toRestore.map(info => info.appId).filter(Boolean))];
        let launchIndex = 0;

        for (const appId of appIds) {
            const app = appSystem.lookup_app(appId);
            if (!app) {
                logger.warning(`Application introuvable : ${appId}`);
                continue;
            }

            const delay = launchIndex * LAUNCH_STAGGER_MS;
            launchIndex++;

            if (!this._appIsRunning(app)) {
                if (delay === 0)
                    this._scheduleRestoreIdle(() => this._launchApp(app));
                else
                    this._scheduleRestoreTimeout(delay, () => this._launchApp(app));
            }

            this._scheduleMissingWindowCheck(appId, delay + MULTI_WINDOW_SETTLE_MS);
        }

        const deadline = RESTORE_WINDOW_MS + Math.max(0, (launchIndex - 1) * LAUNCH_STAGGER_MS);
        this._scheduleRestoreTimeout(deadline, () => {
            if (!this._restoring)
                return;

            const remaining = this._toRestore.length;
            this._finishRestore(remaining === 0);
            if (remaining > 0)
                logger.warning(`Fin de la fenêtre de restauration : ${remaining} fenêtre(s) non retrouvée(s)`);
        });
    }

    _launchApp(app) {
        if (!this._restoring)
            return;

        try {
            if (!this._appIsRunning(app)) {
                logger.info(`Lancement de ${app.get_id()}`);
                app.activate();
            }
        }
        catch (error) {
            logger.error(error, `Impossible de lancer ${app.get_id()}`);
        }
    }

    _scheduleRestoreTimeout(milliseconds, callback) {
        let id = 0;
        id = GLib.timeout_add(GLib.PRIORITY_DEFAULT, milliseconds, () => {
            this._restoreSources.delete(id);
            callback();
            return GLib.SOURCE_REMOVE;
        });
        this._restoreSources.add(id);
        return id;
    }

    _scheduleRestoreIdle(callback) {
        let id = 0;
        const wrapped = () => {
            this._restoreSources.delete(id);
            callback();
        };

        if (typeof GLib.idle_add_once === 'function') {
            id = GLib.idle_add_once(GLib.PRIORITY_DEFAULT_IDLE, wrapped);
        }
        else {
            id = GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, () => {
                wrapped();
                return GLib.SOURCE_REMOVE;
            });
        }

        this._restoreSources.add(id);
        return id;
    }

    _resetRestoreTracking() {
        this._restoring = false;

        if (this._windowCreatedHandler) {
            try { global.display.disconnect(this._windowCreatedHandler); } catch {}
            this._windowCreatedHandler = 0;
        }

        for (const id of this._restoreSources) {
            try { GLib.source_remove(id); } catch {}
        }
        this._restoreSources.clear();
        this._clearMultiWindowChecks();
        this._toRestore = [];
    }

    _finishRestore(complete = true) {
        if (!this._restoring)
            return;

        this._restoring = false;

        if (this._windowCreatedHandler) {
            try { global.display.disconnect(this._windowCreatedHandler); } catch {}
            this._windowCreatedHandler = 0;
        }

        for (const id of this._restoreSources) {
            try { GLib.source_remove(id); } catch {}
        }
        this._restoreSources.clear();
        this._clearMultiWindowChecks();
        this._toRestore = [];
        logger.info('Restauration des fenêtres terminée');

        // Ne remplace la sauvegarde source que si toutes les fenêtres ont réellement
        // été retrouvées. Une restauration partielle conserve ainsi le dernier état fiable.
        if (complete && this._autosaveEnabled)
            this._markSessionDirty();
    }

    _queueWindowMatch(window) {
        if (!this._restoring || !window || !this._isRestorableWindow(window) ||
            this._handledWindows.has(window) || this._pendingWindows.has(window))
            return;

        const liveAppId = this._windowIdentity(window).appId;
        if (liveAppId)
            this._scheduleMissingWindowCheck(liveAppId, MULTI_WINDOW_SETTLE_MS);

        this._pendingWindows.add(window);
        let attempts = 0;

        const tryMatch = () => {
            if (!this._restoring || !window || window.get_workspace?.() === null) {
                this._pendingWindows.delete(window);
                return;
            }

            if (this._tryMatchWindow(window)) {
                this._pendingWindows.delete(window);
                this._handledWindows.add(window);
                return;
            }

            attempts++;
            if (attempts >= MATCH_RETRIES) {
                this._pendingWindows.delete(window);
                return;
            }

            this._scheduleRestoreTimeout(MATCH_RETRY_MS, tryMatch);
        };

        tryMatch();
    }

    _tryMatchWindow(window) {
        if (this._toRestore.length === 0)
            return false;

        const live = this._windowIdentity(window);
        let bestIndex = -1;
        let bestScore = -Infinity;

        for (let i = 0; i < this._toRestore.length; i++) {
            const score = this._matchScore(this._toRestore[i], live);
            if (score > bestScore) {
                bestScore = score;
                bestIndex = i;
            }
        }

        const minimumScore = normalizeId(live.appId) ? 45 : 70;
        if (bestIndex < 0 || bestScore < minimumScore)
            return false;

        const info = this._toRestore.splice(bestIndex, 1)[0];
        logger.info(`Fenêtre reconnue : ${info.appId} / ${info.title || info.wmClass}`);
        this._applyGeometryWhenReady(window, info);

        if (this._toRestore.length === 0)
            this._finishRestore(true);

        return true;
    }

    _windowIdentity(window) {
        const tracker = Shell.WindowTracker.get_default();
        let app = null;
        try { app = tracker.get_window_app(window); } catch {}

        let appWindowIndex = -1;
        let creationRank = -1;
        if (app) {
            try {
                const appWindows = app.get_windows();
                appWindowIndex = appWindows.indexOf(window);
                const byCreation = [...appWindows]
                    .filter(w => this._isRestorableWindow(w))
                    .sort((a, b) => safeCall(a, 'get_stable_sequence', 0) - safeCall(b, 'get_stable_sequence', 0));
                creationRank = byCreation.indexOf(window);
            }
            catch {}
        }

        return {
            appId: app?.get_id?.() ?? null,
            wmClass: safeCall(window, 'get_wm_class', ''),
            wmClassInstance: safeCall(window, 'get_wm_class_instance', ''),
            gtkApplicationId: safeCall(window, 'get_gtk_application_id', ''),
            gtkWindowObjectPath: safeCall(window, 'get_gtk_window_object_path', ''),
            role: safeCall(window, 'get_role', ''),
            windowType: safeCall(window, 'get_window_type', -1),
            title: safeCall(window, 'get_title', ''),
            appWindowIndex,
            creationRank,
        };
    }

    _matchScore(saved, live) {
        const savedApp = normalizeId(saved.appId);
        const liveApp = normalizeId(live.appId);
        let score = 0;

        if (savedApp && liveApp) {
            if (savedApp !== liveApp)
                return -Infinity;
            score += 100;
        }

        const same = (a, b) => normalizeText(a) && normalizeText(a) === normalizeText(b);

        if (same(saved.wmClass, live.wmClass)) score += 45;
        if (same(saved.wmClassInstance, live.wmClassInstance)) score += 35;
        if (same(saved.gtkApplicationId, live.gtkApplicationId)) score += 45;
        // Le chemin GTK n’est pas toujours stable entre deux lancements : indice secondaire seulement.
        if (same(saved.gtkWindowObjectPath, live.gtkWindowObjectPath)) score += 15;
        if (same(saved.role, live.role)) score += 50;
        if (saved.windowType === live.windowType && saved.windowType !== undefined) score += 25;
        if (same(saved.title, live.title)) score += 60;
        if (Number.isInteger(saved.creationRank) && saved.creationRank === live.creationRank) score += 30;
        if (Number.isInteger(saved.appWindowIndex) && saved.appWindowIndex === live.appWindowIndex) score += 5;

        return score;
    }

    _applyGeometryWhenReady(window, info) {
        const signalHandles = [];
        const sourceIds = new Set();
        let cleaned = false;
        let geometryRetries = 0;
        let stableMatches = 0;
        let applyQueued = false;

        const disconnectHandle = ({ object, id }) => {
            try { object.disconnect(id); } catch {}
        };

        const cleanup = () => {
            if (cleaned)
                return;
            cleaned = true;

            for (const handle of signalHandles)
                disconnectHandle(handle);
            signalHandles.length = 0;

            for (const id of sourceIds) {
                try { GLib.source_remove(id); } catch {}
            }
            sourceIds.clear();
            this._geometryCleanups.delete(cleanup);
        };

        this._geometryCleanups.add(cleanup);

        const addSignal = (object, signal, callback) => {
            try {
                const id = object.connect(signal, callback);
                signalHandles.push({ object, id });
                return id;
            }
            catch {
                return 0;
            }
        };

        const addIdle = callback => {
            let id = 0;
            const wrapped = () => {
                sourceIds.delete(id);
                callback();
            };

            if (typeof GLib.idle_add_once === 'function')
                id = GLib.idle_add_once(GLib.PRIORITY_DEFAULT_IDLE, wrapped);
            else
                id = GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, () => { wrapped(); return GLib.SOURCE_REMOVE; });

            sourceIds.add(id);
            return id;
        };

        const addTimeout = (ms, callback) => {
            let id = 0;
            id = GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => {
                sourceIds.delete(id);
                callback();
                return GLib.SOURCE_REMOVE;
            });
            sourceIds.add(id);
            return id;
        };

        const queueApply = () => {
            if (applyQueued || cleaned)
                return;
            applyQueued = true;
            addIdle(() => {
                applyQueued = false;
                apply();
            });
        };

        const valid = () => {
            try { return window && window.get_workspace() !== null; }
            catch { return false; }
        };

        const apply = () => {
            if (!valid()) {
                cleanup();
                return;
            }

            try {
                this._normalGeometry.set(window, {
                    x: info.x,
                    y: info.y,
                    width: info.width,
                    height: info.height,
                });
                this._preparePlacement(window, info);

                const specialState = Boolean(
                    info.fullscreen ||
                    info.maximizedHorizontally ||
                    info.maximizedVertically
                );

                // Même pour une fenêtre maximisée/plein écran, positionner d’abord sa
                // géométrie normale permet à Mutter de retrouver la bonne taille après « Restaurer ».
                window.move_resize_frame(false, info.x, info.y, info.width, info.height);

                this._restoreStateFlags(window, info);

                if (specialState) {
                    cleanup();
                    return;
                }

                const rect = window.get_frame_rect();
                const matches = rect.x === info.x && rect.y === info.y &&
                    rect.width === info.width && rect.height === info.height;

                if (matches) {
                    stableMatches++;
                    if (stableMatches >= 2)
                        cleanup();
                    else
                        addTimeout(60, queueApply);
                }
                else if (geometryRetries++ < GEOMETRY_RETRIES) {
                    stableMatches = 0;
                    addTimeout(45, apply);
                }
                else {
                    cleanup();
                }
            }
            catch (error) {
                logger.warning(`Restauration de géométrie interrompue : ${error}`);
                cleanup();
            }
        };

        addSignal(window, 'unmanaged', cleanup);

        if (!info.fullscreen && !info.maximizedHorizontally && !info.maximizedVertically) {
            addSignal(window, 'position-changed', queueApply);
            addSignal(window, 'size-changed', queueApply);
        }

        const actor = safeCall(window, 'get_compositor_private', null);
        if (actor) {
            if (actor.mapped) {
                // Fenêtre déjà composée : application au prochain idle, sans délai fixe.
                queueApply();
            }
            else {
                let firstFrameId = 0;
                firstFrameId = addSignal(actor, 'first-frame', () => {
                    if (firstFrameId) {
                        const index = signalHandles.findIndex(h => h.object === actor && h.id === firstFrameId);
                        if (index >= 0) {
                            disconnectHandle(signalHandles[index]);
                            signalHandles.splice(index, 1);
                        }
                        firstFrameId = 0;
                    }
                    queueApply();
                });
                // Filet de sécurité court uniquement si first-frame n’arrive pas.
                addTimeout(140, queueApply);
            }
        }
        else {
            let shownId = 0;
            shownId = addSignal(window, 'shown', () => {
                if (shownId) {
                    const index = signalHandles.findIndex(h => h.object === window && h.id === shownId);
                    if (index >= 0) {
                        disconnectHandle(signalHandles[index]);
                        signalHandles.splice(index, 1);
                    }
                    shownId = 0;
                }

                const shownActor = safeCall(window, 'get_compositor_private', null);
                if (shownActor?.mapped) {
                    queueApply();
                }
                else if (shownActor) {
                    let ffId = 0;
                    ffId = addSignal(shownActor, 'first-frame', () => {
                        const index = signalHandles.findIndex(h => h.object === shownActor && h.id === ffId);
                        if (index >= 0) {
                            disconnectHandle(signalHandles[index]);
                            signalHandles.splice(index, 1);
                        }
                        queueApply();
                    });
                    addTimeout(140, queueApply);
                }
                else {
                    queueApply();
                }
            });

            // Fallback court si l’acteur apparaît sans émettre un signal observable ici.
            addTimeout(180, queueApply);
        }
    }

    _preparePlacement(window, info) {
        const workspace = this._ensureWorkspace(info.workspace);
        if (workspace && window.get_workspace() !== workspace)
            window.change_workspace(workspace);

        const monitorCount = Main.layoutManager.monitors?.length ?? 0;
        if (Number.isInteger(info.monitor) && info.monitor >= 0 && info.monitor < monitorCount &&
            safeCall(window, 'get_monitor', -1) !== info.monitor) {
            try { window.move_to_monitor(info.monitor); } catch {}
        }

        // On revient brièvement à un état normal afin que move_resize_frame()
        // définisse aussi la future taille « Restaurer », puis on remet l’état cible.
        if (safeCall(window, 'is_fullscreen', false)) {
            try { window.unmake_fullscreen(); } catch {}
        }

        if (safeCall(window, 'is_maximized', false)) {
            try {
                if (typeof window.set_unmaximize_flags === 'function')
                    window.set_unmaximize_flags(Meta.MaximizeFlags.BOTH);
                else
                    window.unmaximize();
            }
            catch {}
        }
    }

    _restoreStateFlags(window, info) {
        const hasMaximizeState = typeof info.maximizedHorizontally === 'boolean' ||
            typeof info.maximizedVertically === 'boolean';
        const wantsMaxH = Boolean(info.maximizedHorizontally);
        const wantsMaxV = Boolean(info.maximizedVertically);
        const wantsMax = wantsMaxH || wantsMaxV;

        if (typeof info.sticky === 'boolean' &&
            info.sticky !== Boolean(safeCall(window, 'is_on_all_workspaces', false))) {
            try { info.sticky ? window.stick() : window.unstick(); } catch {}
        }

        if (typeof info.above === 'boolean' &&
            info.above !== Boolean(safeCall(window, 'is_above', false))) {
            try { info.above ? window.make_above() : window.unmake_above(); } catch {}
        }

        if (hasMaximizeState && wantsMax) {
            let flags = 0;
            if (wantsMaxH) flags |= Meta.MaximizeFlags.HORIZONTAL;
            if (wantsMaxV) flags |= Meta.MaximizeFlags.VERTICAL;

            try {
                if (typeof window.set_maximize_flags === 'function')
                    window.set_maximize_flags(flags);
                else
                    window.maximize();
            }
            catch (error) {
                logger.warning(`Impossible de restaurer l’état maximisé : ${error}`);
            }
        }
        else if (hasMaximizeState && safeCall(window, 'is_maximized', false)) {
            try {
                if (typeof window.set_unmaximize_flags === 'function')
                    window.set_unmaximize_flags(Meta.MaximizeFlags.BOTH);
                else
                    window.unmaximize();
            }
            catch {}
        }

        const fullscreen = safeCall(window, 'is_fullscreen', false);
        if (Boolean(info.fullscreen) !== Boolean(fullscreen)) {
            try { info.fullscreen ? window.make_fullscreen() : window.unmake_fullscreen(); } catch {}
        }

        if (Boolean(info.minimized) !== Boolean(window.minimized)) {
            try { info.minimized ? window.minimize() : window.unminimize(); } catch {}
        }
    }

    _ensureWorkspace(index) {
        if (!Number.isInteger(index) || index < 0)
            return null;

        const manager = global.workspace_manager;
        while (manager.n_workspaces <= index) {
            const timestamp = global.display.get_current_time();
            manager.append_new_workspace(false, timestamp);
        }
        return manager.get_workspace_by_index(index);
    }

    _appIsRunning(app) {
        try {
            return Shell.AppSystem.get_default().get_running()
                .some(running => running.get_id() === app.get_id());
        }
        catch {
            return app.get_windows().length > 0;
        }
    }

    _isRestorableWindow(window) {
        if (!window)
            return false;

        try {
            return window.get_window_type() === Meta.WindowType.NORMAL &&
                !window.is_override_redirect();
        }
        catch {
            return false;
        }
    }

    _startWindowTracking() {
        if (this._autosaveWindowCreatedId || this._destroyed)
            return;

        if (Main.layoutManager._startingUp && !this._startupCompleteSignalId) {
            this._startupCompleteSignalId = Main.layoutManager.connect('startup-complete', () => {
                if (this._startupCompleteSignalId) {
                    try { Main.layoutManager.disconnect(this._startupCompleteSignalId); } catch {}
                    this._startupCompleteSignalId = 0;
                }
                this._markSessionDirty();
            });
        }

        for (const actor of global.get_window_actors()) {
            const window = actor.get_meta_window();
            if (window)
                this._trackWindow(window);
        }

        this._autosaveWindowCreatedId = global.display.connect('window-created', (_display, window) => {
            this._trackWindow(window);
            this._markSessionDirty();
        });
    }

    _stopWindowTracking() {
        if (this._startupCompleteSignalId) {
            try { Main.layoutManager.disconnect(this._startupCompleteSignalId); } catch {}
            this._startupCompleteSignalId = 0;
        }

        if (this._autosaveWindowCreatedId) {
            try { global.display.disconnect(this._autosaveWindowCreatedId); } catch {}
            this._autosaveWindowCreatedId = 0;
        }

        for (const [window, ids] of this._trackedWindowSignals) {
            for (const id of ids) {
                try { window.disconnect(id); } catch {}
            }
        }
        this._trackedWindowSignals.clear();
    }

    _trackWindow(window) {
        if (!this._isRestorableWindow(window) || this._trackedWindowSignals.has(window))
            return;

        this._rememberNormalGeometry(window);
        const ids = [];
        const connect = (signal, callback) => {
            try { ids.push(window.connect(signal, callback)); } catch {}
        };
        const geometryChanged = () => {
            this._rememberNormalGeometry(window);
            this._markSessionDirty();
        };
        const stateChanged = () => this._markSessionDirty();

        connect('position-changed', geometryChanged);
        connect('size-changed', geometryChanged);
        connect('workspace-changed', stateChanged);
        connect('notify::minimized', stateChanged);
        connect('notify::fullscreen', stateChanged);
        connect('notify::maximized-horizontally', stateChanged);
        connect('notify::maximized-vertically', stateChanged);
        connect('notify::on-all-workspaces', stateChanged);
        connect('notify::above', stateChanged);
        connect('unmanaged', () => {
            this._untrackWindow(window);
            this._markSessionDirty();
        });

        this._trackedWindowSignals.set(window, ids);
    }

    _untrackWindow(window) {
        const ids = this._trackedWindowSignals.get(window);
        if (!ids)
            return;

        for (const id of ids) {
            try { window.disconnect(id); } catch {}
        }
        this._trackedWindowSignals.delete(window);
        this._normalGeometry.delete(window);
    }

    _rememberNormalGeometry(window) {
        if (!this._isRestorableWindow(window))
            return;

        try {
            if (window.is_fullscreen() || window.maximized_horizontally || window.maximized_vertically)
                return;

            const rect = window.get_frame_rect();
            if (rect.width > 0 && rect.height > 0) {
                this._normalGeometry.set(window, {
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height,
                });
            }
        }
        catch {}
    }

    _markSessionDirty() {
        // Aucun I/O pendant le chemin critique du démarrage GNOME.
        if (!this._autosaveEnabled || this._destroyed || this._restoring || this._closing ||
            Main.layoutManager._startingUp)
            return;

        if (this._autosaveSourceId) {
            try { GLib.source_remove(this._autosaveSourceId); } catch {}
            this._autosaveSourceId = 0;
        }

        this._autosaveSourceId = GLib.timeout_add(
            GLib.PRIORITY_DEFAULT_IDLE,
            AUTOSAVE_DEBOUNCE_MS,
            () => {
                this._autosaveSourceId = 0;
                if (!this._autosaveEnabled || this._destroyed || this._restoring || this._closing)
                    return GLib.SOURCE_REMOVE;

                // Une liste vide (démarrage, applications pas encore ouvertes) ne remplace jamais
                // une session enregistrée ; seule la sauvegarde de fermeture peut l'écrire.
                const payload = this._buildPayload();
                if (payload.windows.length > 0)
                    this._writePayloadAsync(payload);
                return GLib.SOURCE_REMOVE;
            }
        );
    }

    _cancelPendingAutosave() {
        if (this._autosaveSourceId) {
            try { GLib.source_remove(this._autosaveSourceId); } catch {}
            this._autosaveSourceId = 0;
        }

        if (this._autosaveCancellable) {
            this._autosaveCancellable.cancel();
            this._autosaveCancellable = null;
        }
        this._autosaveGeneration++;
    }

    _scheduleMissingWindowCheck(appId, delay = MULTI_WINDOW_SETTLE_MS) {
        if (!this._restoring || this._multiWindowAttempted.has(appId))
            return;

        const previous = this._multiWindowSources.get(appId);
        if (previous) {
            try { GLib.source_remove(previous); } catch {}
            this._restoreSources.delete(previous);
        }

        const id = this._scheduleRestoreTimeout(delay, () => {
            this._multiWindowSources.delete(appId);
            this._confirmMissingWindows(appId);
        });
        this._multiWindowSources.set(appId, id);
    }

    _confirmMissingWindows(appId) {
        if (!this._restoring || this._multiWindowAttempted.has(appId))
            return;

        const app = Shell.AppSystem.get_default().lookup_app(appId);
        if (!app || !app.can_open_new_window?.()) {
            this._multiWindowAttempted.add(appId);
            return;
        }

        const totalExpected = this._expectedWindowsByApp.get(appId) ?? 0;
        if (totalExpected <= 1) {
            this._multiWindowAttempted.add(appId);
            return;
        }

        // Deuxième mesure après un court calme : évite de créer des doublons pour
        // les applications qui restaurent elles-mêmes plusieurs fenêtres.
        const id = this._scheduleRestoreTimeout(MULTI_WINDOW_CONFIRM_MS, () => {
            this._multiWindowSources.delete(appId);
            if (!this._restoring)
                return;

            const currentAgain = app.get_windows().filter(window => this._isRestorableWindow(window)).length;
            const missing = Math.max(0, totalExpected - currentAgain);
            this._multiWindowAttempted.add(appId);
            if (missing <= 0)
                return;

            const unmatched = this._toRestore
                .filter(info => info.appId === appId)
                .sort((a, b) => (a.creationRank ?? 0) - (b.creationRank ?? 0));

            for (let i = 0; i < Math.min(missing, unmatched.length); i++) {
                const info = unmatched[i];
                this._scheduleRestoreTimeout(i * NEW_WINDOW_STAGGER_MS, () => {
                    try {
                        app.open_new_window(Number.isInteger(info.workspace) ? info.workspace : -1);
                    }
                    catch (error) {
                        logger.warning(`Impossible d’ouvrir une fenêtre supplémentaire pour ${appId} : ${error}`);
                    }
                });
            }
        });
        this._multiWindowSources.set(appId, id);
    }

    _clearMultiWindowChecks() {
        for (const id of this._multiWindowSources.values()) {
            try { GLib.source_remove(id); } catch {}
            this._restoreSources.delete(id);
        }
        this._multiWindowSources.clear();
        this._multiWindowAttempted.clear();
        this._expectedWindowsByApp.clear();
    }

    collectAllWindows() {
        const appSystem = Shell.AppSystem.get_default();
        const runningApps = appSystem.get_running();
        const excluded = new Set(this.excludedApps.map(normalizeId));
        const result = [];

        for (const app of runningApps) {
            const appId = app.get_id();
            if (!appId || appId.startsWith('window:') || app.is_window_backed?.() || excluded.has(normalizeId(appId)))
                continue;

            const windows = app.get_windows().filter(window => this._isRestorableWindow(window));
            const byCreation = [...windows].sort((a, b) =>
                safeCall(a, 'get_stable_sequence', 0) - safeCall(b, 'get_stable_sequence', 0));

            for (let appWindowIndex = 0; appWindowIndex < windows.length; appWindowIndex++) {
                const window = windows[appWindowIndex];
                let currentFrame;
                try { currentFrame = window.get_frame_rect(); } catch { continue; }

                const workspaceObj = safeCall(window, 'get_workspace', null);
                const workspace = workspaceObj ? workspaceObj.index() : -1;
                const specialState = Boolean(
                    safeCall(window, 'is_fullscreen', false) ||
                    window.maximized_horizontally ||
                    window.maximized_vertically
                );
                const remembered = this._normalGeometry.get(window);
                const frame = specialState && remembered ? remembered : currentFrame;

                result.push({
                    windowId: `${appId}-${safeCall(window, 'get_id', appWindowIndex)}`,
                    appId,
                    appWindowIndex,
                    creationRank: byCreation.indexOf(window),
                    wmClass: safeCall(window, 'get_wm_class', '') ?? '',
                    wmClassInstance: safeCall(window, 'get_wm_class_instance', '') ?? '',
                    gtkApplicationId: safeCall(window, 'get_gtk_application_id', '') ?? '',
                    gtkWindowObjectPath: safeCall(window, 'get_gtk_window_object_path', '') ?? '',
                    role: safeCall(window, 'get_role', '') ?? '',
                    windowType: safeCall(window, 'get_window_type', -1),
                    title: safeCall(window, 'get_title', '') ?? '',
                    workspace,
                    monitor: safeCall(window, 'get_monitor', -1),
                    x: frame.x,
                    y: frame.y,
                    width: frame.width,
                    height: frame.height,
                    minimized: Boolean(window.minimized),
                    fullscreen: Boolean(safeCall(window, 'is_fullscreen', false)),
                    maximizedHorizontally: Boolean(window.maximized_horizontally),
                    maximizedVertically: Boolean(window.maximized_vertically),
                    sticky: Boolean(safeCall(window, 'is_on_all_workspaces', false)),
                    above: Boolean(safeCall(window, 'is_above', false)),
                });
            }
        }

        return result;
    }

    _loadValidatedPayload(quiet = false) {
        const sessionPath = getSessionFilePath(this.extensionId);
        if (!GLib.file_test(sessionPath, GLib.FileTest.EXISTS)) {
            if (!quiet)
                logger.warning(`Fichier de session introuvable : ${sessionPath}`);
            return null;
        }

        try {
            const [ok, contents] = Gio.File.new_for_path(sessionPath).load_contents(null);
            if (!ok)
                throw new Error('lecture impossible');

            const payload = JSON.parse(new TextDecoder().decode(contents));
            if (!payload || typeof payload !== 'object' || !Array.isArray(payload.windows))
                throw new Error('structure de session invalide');

            const version = payload.formatVersion ?? 1;
            if (version < 1 || version > SESSION_FORMAT_VERSION)
                throw new Error(`version de format non prise en charge : ${version}`);

            const sourceWindows = payload.windows.slice(0, 256);
            if (payload.windows.length > 256)
                logger.warning('Session anormalement grande : seules les 256 premières fenêtres seront examinées');

            const windows = sourceWindows.filter(window => this._isValidWindowInfo(window));
            if (windows.length !== sourceWindows.length)
                logger.warning(`${sourceWindows.length - windows.length} entrée(s) de fenêtre invalide(s) ignorée(s)`);

            return {
                formatVersion: version,
                created: typeof payload.created === 'string' ? payload.created : '',
                windows,
            };
        }
        catch (error) {
            logger.error(error, 'Fichier de session invalide');
            return null;
        }
    }

    _isValidWindowInfo(info) {
        if (!info || typeof info !== 'object' || typeof info.appId !== 'string' || !info.appId ||
            info.appId.startsWith('window:'))
            return false;

        if (Number.isInteger(info.windowType) && info.windowType !== Meta.WindowType.NORMAL)
            return false;

        for (const key of ['x', 'y', 'width', 'height']) {
            if (!Number.isFinite(info[key]))
                return false;
        }

        return info.width > 0 && info.height > 0 &&
            info.width <= 32768 && info.height <= 32768 &&
            Math.abs(info.x) <= 131072 && Math.abs(info.y) <= 131072;
    }

    hasStartupSession() {
        return Boolean(this._startupPayload?.windows?.length);
    }

    async deleteSession() {
        this._startupPayload = null;
        const sessionPath = getSessionFilePath(this.extensionId);
        if (!GLib.file_test(sessionPath, GLib.FileTest.EXISTS)) {
            logger.info('Le fichier de session n’existe pas : rien à supprimer');
            return;
        }

        const file = Gio.File.new_for_path(sessionPath);
        return new Promise((resolve, reject) => {
            file.delete_async(GLib.PRIORITY_DEFAULT, null, (fileObj, res) => {
                try {
                    fileObj.delete_finish(res);
                    logger.info('Fichier de session supprimé');
                    resolve();
                }
                catch (error) {
                    reject(error);
                }
            });
        });
    }
}
