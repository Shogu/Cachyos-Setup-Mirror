import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import { Log } from './log.js';

const logger = Log.getDefault();

const STATE_FILENAME = 'last_login_session';

export class LoginSessionTracker {
    static _currentSessionId() {
        try {
            const [ok, bytes] = Gio.File.new_for_path('/proc/self/cgroup').load_contents(null);
            if (ok) {
                const match = new TextDecoder().decode(bytes).match(/session-(\d+)\.scope/);
                if (match)
                    return match[0];
            }
        }
        catch (e) {
            logger.error(e, 'LoginSessionTracker : lecture de /proc/self/cgroup impossible');
        }

        try {
            const [ok, bytes] = Gio.File.new_for_path('/proc/self/stat').load_contents(null);
            if (ok) {
                const pid = parseInt(new TextDecoder().decode(bytes).split(' ')[0], 10) || 0;
                return `shell-pid-${pid}`;
            }
        }
        catch (e) {
            logger.error(e, 'LoginSessionTracker : lecture de /proc/self/stat impossible');
        }

        return null;
    }

    static _statePath(extensionId) {
        return GLib.build_filenamev([GLib.get_user_config_dir(), extensionId, STATE_FILENAME]);
    }

    static isFirstLogin(extensionId) {
        const cur = this._currentSessionId();
        if (!cur)
            return false;

        const path = this._statePath(extensionId);
        if (GLib.file_test(path, GLib.FileTest.EXISTS)) {
            try {
                const [ok, bytes] = Gio.File.new_for_path(path).load_contents(null);
                if (ok && new TextDecoder().decode(bytes).trim() === cur)
                    return false;
            }
            catch (e) {
                logger.error(e, 'LoginSessionTracker : lecture du fichier d’état impossible');
            }
        }

        const dir = GLib.path_get_dirname(path);
        GLib.mkdir_with_parents(dir, 0o700);
        try { GLib.chmod(dir, 0o700); } catch {}

        Gio.File.new_for_path(path).replace_contents(
            new TextEncoder().encode(cur),
            null,
            false,
            Gio.FileCreateFlags.REPLACE_DESTINATION,
            null
        );
        try { GLib.chmod(path, 0o600); } catch {}
        return true;
    }
}
