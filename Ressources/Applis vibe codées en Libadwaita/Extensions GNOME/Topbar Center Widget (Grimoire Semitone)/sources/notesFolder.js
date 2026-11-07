// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

Gio._promisify(Gio.File.prototype, 'enumerate_children_async');
Gio._promisify(Gio.FileEnumerator.prototype, 'next_files_async');
Gio._promisify(Gio.FileEnumerator.prototype, 'close_async');
Gio._promisify(Gio.File.prototype, 'load_contents_async');
Gio._promisify(Gio.File.prototype, 'replace_contents_bytes_async', 'replace_contents_finish');
Gio._promisify(Gio.File.prototype, 'create_async');
Gio._promisify(Gio.OutputStream.prototype, 'write_bytes_async');
Gio._promisify(Gio.OutputStream.prototype, 'close_async');
Gio._promisify(Gio.File.prototype, 'set_display_name_async');
Gio._promisify(Gio.File.prototype, 'trash_async');
Gio._promisify(Gio.File.prototype, 'delete_async');

export const GRIMOIRE_ID = 'io.github.shogu.Grimoire';

const MARKDOWN = /\.(md|markdown)$/i;
const ATTRIBUTES = 'standard::name,standard::type,standard::is-hidden,time::modified';
const encoder = new TextEncoder();

export function grimoireSettings() {
    const schema = Gio.SettingsSchemaSource.get_default().lookup(GRIMOIRE_ID, true);
    return schema ? new Gio.Settings({settings_schema: schema}) : null;
}

// Grimoire avant 0.2.0-19, ou pas encore relancé depuis, ne connaît que le
// dossier épinglé unique « pinned-folder ».
function pinnedFolders(grimoire) {
    const folders = grimoire.settings_schema.has_key('pinned-folders') ? grimoire.get_strv('pinned-folders') : [];
    const active = grimoire.get_string('pinned-folder');
    return folders.length || !active ? folders : [active];
}

// Catégories issues des dossiers épinglés : un dossier qui contient des
// sous-dossiers donne une catégorie par sous-dossier (et lui-même s'il contient
// directement des notes). Épingler « Notes » suffit donc à avoir AI, Lycée,
// Perso… sans les épingler un par un.
export function expandFolders(paths) {
    const result = [];
    for (const path of paths) {
        const subfolders = [];
        let hasNotes = false;
        try {
            const enumerator = Gio.File.new_for_path(path).enumerate_children(
                'standard::name,standard::type,standard::is-hidden', Gio.FileQueryInfoFlags.NONE, null);
            let info;
            while ((info = enumerator.next_file(null))) {
                if (info.get_is_hidden())
                    continue;
                if (info.get_file_type() === Gio.FileType.DIRECTORY)
                    subfolders.push(GLib.build_filenamev([path, info.get_name()]));
                else if (info.get_file_type() === Gio.FileType.REGULAR && MARKDOWN.test(info.get_name()))
                    hasNotes = true;
            }
            enumerator.close(null);
        } catch (_error) {
            // Dossier absent : il reste une catégorie, signalée « introuvable » à l'ouverture.
        }
        subfolders.sort((a, b) => GLib.path_get_basename(a).localeCompare(GLib.path_get_basename(b)));
        if (hasNotes || !subfolders.length)
            result.push(path);
        result.push(...subfolders);
    }
    return [...new Set(result)];
}

export function visibleFolders(settings, grimoire) {
    const hidden = new Set(settings.get_strv('hidden-folders'));
    return expandFolders(pinnedFolders(grimoire)).filter(path => !hidden.has(path));
}

const MAX_TITLE_LEN = 80;
function cleanTitle(title) {
    const cleaned = title.replace(/[/\\]/g, '-').replace(/\s+/g, ' ').trim().replace(/^\.+/, '');
    return cleaned.length > MAX_TITLE_LEN ? cleaned.slice(0, MAX_TITLE_LEN).trim() : cleaned;
}

export function noteTitle(name) {
    return name.replace(MARKDOWN, '');
}

async function children(folder, cancellable) {
    const enumerator = await folder.enumerate_children_async(
        ATTRIBUTES, Gio.FileQueryInfoFlags.NONE, GLib.PRIORITY_DEFAULT, cancellable);
    const infos = [];
    let batch;
    while ((batch = await enumerator.next_files_async(64, GLib.PRIORITY_DEFAULT, cancellable)).length > 0)
        infos.push(...batch);
    await enumerator.close_async(GLib.PRIORITY_DEFAULT, null);
    return infos;
}

export async function listNotes(folder, cancellable) {
    return (await children(folder, cancellable))
        .filter(info => !info.get_is_hidden() && info.get_file_type() === Gio.FileType.REGULAR &&
            MARKDOWN.test(info.get_name()))
        .map(info => ({
            file: folder.get_child(info.get_name()),
            name: info.get_name(),
            title: noteTitle(info.get_name()),
            folder: folder.get_path(),
            modified: info.get_modification_date_time(),
        }));
}

export async function readNote(file, cancellable = null) {
    const [contents] = await file.load_contents_async(cancellable);
    return new TextDecoder().decode(contents);
}

export function writeTextFile(file, text, flags = Gio.FileCreateFlags.NONE) {
    return file.replace_contents_bytes_async(new GLib.Bytes(encoder.encode(text)), null, false, flags, null);
}

export async function clearDirectory(directory) {
    for (const info of await children(directory, null))
        await directory.get_child(info.get_name()).delete_async(GLib.PRIORITY_DEFAULT, null);
}

async function writeNewNote(folder, base, text) {
    const data = new GLib.Bytes(encoder.encode(text));
    for (let n = 1; ; n++) {
        const file = folder.get_child(`${n === 1 ? base : `${base} ${n}`}.md`);
        try {
            const stream = await file.create_async(Gio.FileCreateFlags.NONE, GLib.PRIORITY_DEFAULT, null);
            await stream.write_bytes_async(data, GLib.PRIORITY_DEFAULT, null);
            await stream.close_async(GLib.PRIORITY_DEFAULT, null);
            return file;
        } catch (error) {
            if (!error.matches(Gio.IOErrorEnum, Gio.IOErrorEnum.EXISTS))
                throw error;
        }
    }
}

export function createNote(folder, title) {
    const base = cleanTitle(title) || 'Nouvelle note';
    return writeNewNote(folder, base, `# ${base}\n\n`);
}

export function duplicateNote(note) {
    return writeNewNote(note.file.get_parent(), `${note.title} (copie)`, note.text);
}

export async function renameNote(note, title) {
    const base = cleanTitle(title);
    if (!base)
        throw new Error('Nom de note vide');
    if (base === note.title)
        return note.file;
    try {
        const contents = await readNote(note.file);
        const lines = contents.split('\n');
        const firstIdx = lines.findIndex(line => line.trim() !== '');
        if (firstIdx >= 0 && /^#\s/.test(lines[firstIdx])) {
            const oldHeader = lines[firstIdx].replace(/^#\s*/, '').trim();
            if (oldHeader === note.title) {
                lines[firstIdx] = '# ' + base;
                await writeTextFile(note.file, lines.join('\n'), Gio.FileCreateFlags.REPLACE_DESTINATION);
            }
        }
    } catch (e) {
        console.error(`Grimoire: error resyncing H1 during rename: ${e}`);
    }
    return note.file.set_display_name_async(base + note.name.match(MARKDOWN)[0], GLib.PRIORITY_DEFAULT, null);
}

export function trashNote(note) {
    return note.file.trash_async(GLib.PRIORITY_DEFAULT, null);
}

export function showInFiles(file) {
    Gio.DBus.session.call(
        'org.freedesktop.FileManager1', '/org/freedesktop/FileManager1', 'org.freedesktop.FileManager1',
        'ShowItems', new GLib.Variant('(ass)', [[file.get_uri()], '']),
        null, Gio.DBusCallFlags.NONE, -1, null, null);
}

function sameDay(a, b) {
    return a.get_year() === b.get_year() && a.get_day_of_year() === b.get_day_of_year();
}

export function relativeDate(date) {
    const local = date.to_local();
    const now = GLib.DateTime.new_now_local();
    if (sameDay(local, now))
        return local.format('%H:%M');
    if (sameDay(local, now.add_days(-1)))
        return 'Hier';
    return local.format(local.get_year() === now.get_year() ? '%e %b' : '%e %b %Y').trim();
}
