import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

const SESSION_FILE_NAME = 'session-default.json';

export function getSessionFilePath(extensionId) {
    const dataDir = GLib.get_user_config_dir();
    const sessionsDir = GLib.build_filenamev([dataDir, extensionId, 'sessions']);
    return GLib.build_filenamev([sessionsDir, SESSION_FILE_NAME]);
}

export function ensureSessionsDirExists(extensionId) {
    const dataDir = GLib.get_user_config_dir();
    const sessionsDir = GLib.build_filenamev([dataDir, extensionId, 'sessions']);
    GLib.mkdir_with_parents(sessionsDir, 0o700);
    try {
        GLib.chmod(sessionsDir, 0o700);
    }
    catch {
        // chmod peut échouer sur certains systèmes de fichiers non POSIX.
    }
    return sessionsDir;
}

export function loadSessionData(extensionId) {
    const sessionPath = getSessionFilePath(extensionId);
    if (!GLib.file_test(sessionPath, GLib.FileTest.EXISTS))
        return [];

    try {
        const file = Gio.File.new_for_path(sessionPath);
        const [ok, contents] = file.load_contents(null);
        if (!ok)
            return [];

        const payload = JSON.parse(new TextDecoder().decode(contents));
        return Array.isArray(payload?.windows) ? payload.windows : [];
    }
    catch {
        return [];
    }
}
