// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {QuickToggle, SystemIndicator} from 'resource:///org/gnome/shell/ui/quickSettings.js';

// Le script de mise à jour crée ce fichier au début et le supprime à la fin
// (même en cas d'erreur) : tant qu'il existe, la tuile est bleue.
const RUNNING_FILE = 'update-shelly.running';
const STALE_AFTER_S = 6 * 3600;

function upgradeIcon() {
    return Gio.ThemedIcon.new_from_names(['io.gitlab.shogu.Upgrade-symbolic', 'software-update-available-symbolic']);
}

const UpdateToggle = GObject.registerClass(
class UpdateToggle extends QuickToggle {
    _init(onLaunch) {
        super._init({title: 'Upgrade', subtitle: 'Lancer Shelly', gicon: upgradeIcon(), toggle_mode: false});
        this.connect('clicked', () => {
            if (!this.checked)
                onLaunch();
        });
    }

    setRunning(running) {
        this.checked = running;
        this.subtitle = running ? 'En cours…' : 'Lancer Shelly';
    }
});

// Tuile « Upgrade » de Quick Settings : un clic lance le script choisi dans
// les préférences ; elle reste bleue tant que le script tourne.
export const UpdateIndicator = GObject.registerClass(
class UpdateIndicator extends SystemIndicator {
    _init(command) {
        super._init();
        this._command = command;
        this._pollId = 0;
        this._runningFile = Gio.File.new_for_path(GLib.build_filenamev([GLib.get_user_runtime_dir(), RUNNING_FILE]));

        this._toggle = new UpdateToggle(() => this._launch());
        this.quickSettingsItems.push(this._toggle);

        this._monitor = Gio.File.new_for_path(GLib.get_user_runtime_dir())
            .monitor_directory(Gio.FileMonitorFlags.NONE, null);
        this._monitor.connect('changed', (_monitor, file) => {
            if (file.get_basename() === RUNNING_FILE)
                this._sync();
        });
        this._sync();
    }

    _sync() {
        let running = this._runningFile.query_exists(null);
        if (running) {
            // Témoin resté après un plantage ou une session tuée : périmé.
            try {
                const info = this._runningFile.query_info('time::modified', Gio.FileQueryInfoFlags.NONE, null);
                const age = GLib.DateTime.new_now_utc().difference(info.get_modification_date_time()) / GLib.USEC_PER_SEC;
                if (age > STALE_AFTER_S) {
                    this._runningFile.delete(null);
                    running = false;
                }
            } catch (_error) {
                // Fichier disparu entre-temps.
            }
        }
        this._toggle.setRunning(running);
    }

    _launch() {
        const command = this._command.replace(/^~(?=\/)/, GLib.get_home_dir());
        if (!GLib.file_test(command, GLib.FileTest.IS_EXECUTABLE)) {
            Main.notify('Upgrade', `Script introuvable ou non exécutable : ${command}`);
            return;
        }
        try {
            Gio.Subprocess.new([command], Gio.SubprocessFlags.NONE);
        } catch (error) {
            Main.notify('Upgrade', error.message);
            return;
        }
        // La tuile devient bleue sans attendre le fichier témoin ; elle
        // revient à l'état réel si celui-ci n'apparaît pas.
        this._toggle.setRunning(true);
        if (this._pollId)
            GLib.Source.remove(this._pollId);
        this._pollId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 10, () => {
            this._pollId = 0;
            this._sync();
            return GLib.SOURCE_REMOVE;
        });
        Main.panel.closeQuickSettings();
    }

    destroy() {
        if (this._pollId)
            GLib.Source.remove(this._pollId);
        this._pollId = 0;
        this._monitor.cancel();
        this.quickSettingsItems.forEach(item => item.destroy());
        this.quickSettingsItems.length = 0;
        super.destroy();
    }
});
