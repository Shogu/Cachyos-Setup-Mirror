import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

const BOOT_ID_FILE = '/proc/sys/kernel/random/boot_id';
const STATE_FILENAME = 'last_boot_id';

export class BootTracker {
    static readBootId() {
        try {
            const file = Gio.File.new_for_path(BOOT_ID_FILE);
            const [ok, bytes] = file.load_contents(null);
            if (!ok)
                return null;
            return new TextDecoder().decode(bytes).trim();
        }
        catch {
            return null;
        }
    }

    static statePath(uuid) {
        const cfg = GLib.get_user_config_dir();
        return GLib.build_filenamev([cfg, uuid, STATE_FILENAME]);
    }

    static isFirstBoot(uuid) {
        const cur = this.readBootId();
        if (!cur)
            return false;

        const path = this.statePath(uuid);
        if (GLib.file_test(path, GLib.FileTest.EXISTS)) {
            try {
                const [ok, bytes] = Gio.File.new_for_path(path).load_contents(null);
                if (ok && new TextDecoder().decode(bytes).trim() === cur)
                    return false;
            }
            catch {
                // On réécrit simplement l’état ci-dessous.
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
