// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import St from 'gi://St';

import {buildEvent, eventDescription, openEvent} from './calendarEvent.js';
import {NoteRow} from './noteRow.js';
import {
    GRIMOIRE_ID, createNote, duplicateNote, listNotes, noteTitle, readNote, renameNote, showInFiles, trashNote,
    visibleFolders, writeTextFile,
} from './notesFolder.js';
import {bodyWithoutTitle, searchKey, toggleTask} from './noteText.js';

const UNDO_DELAY_S = 6;
const NOTE_KEYS = new Set(['hidden-folders', 'selected-folder', 'max-notes', 'pinned-notes', 'note-colors']);

function headerToggle(iconName, accessibleName) {
    return new St.Button({
        style_class: 'icon-button tcw-icon-button',
        child: new St.Icon({icon_name: iconName}),
        accessible_name: accessibleName,
        can_focus: true,
        toggle_mode: true,
        y_align: Clutter.ActorAlign.CENTER,
    });
}

function escapableEntry(hintText, onEscape) {
    const entry = new St.Entry({
        style_class: 'tcw-entry',
        hint_text: hintText,
        can_focus: true,
        visible: false,
    });
    entry.clutter_text.connect('key-press-event', (_actor, event) => {
        if (event.get_key_symbol() !== Clutter.KEY_Escape)
            return Clutter.EVENT_PROPAGATE;
        onEscape();
        return Clutter.EVENT_STOP;
    });
    return entry;
}

function basename(path) {
    return GLib.path_get_basename(path);
}

export const NotesColumn = GObject.registerClass(
class NotesColumn extends St.BoxLayout {
    _init(settings, grimoire, menu, calendar) {
        super._init({
            style_class: 'tcw-column',
            orientation: Clutter.Orientation.VERTICAL,
            y_expand: true,
        });
        this._settings = settings;
        this._grimoire = grimoire;
        this._menu = menu;
        this._calendar = calendar;
        this._cancellable = null;
        this._expandedRow = null;
        this._folders = [];
        this._notes = [];
        this._texts = new Map();
        this._pendingTrash = null;
        this._monitors = [];
        this._watchKey = '';
        this._refreshId = 0;
        this._selectedDay = GLib.DateTime.new_now_local();

        this._buildHeader();
        this._buildBody();
        this._applyCollapsed();

        this._menuSignal = menu.connect('open-state-changed', (_menu, open) => this._menuToggled(open));
        this._calendarSignal = calendar.connect('selected-date-changed', (_calendar, day) => this._dayChanged(day));
        this._settingsSignal = settings.connect('changed', (_settings, key) => {
            if (key === 'notes-collapsed')
                this._applyCollapsed();
            if (NOTE_KEYS.has(key))
                this._refreshIfOpen();
        });
        this._grimoireSignal = grimoire
            ? grimoire.connect('changed', () => this._refreshIfOpen()) : 0;
    }

    _buildHeader() {
        const header = new St.BoxLayout({style_class: 'tcw-header'});
        header.add_child(new St.Icon({
            gicon: Gio.ThemedIcon.new_from_names([`${GRIMOIRE_ID}-symbolic`, 'accessories-text-editor-symbolic']),
            style_class: 'tcw-header-icon',
            y_align: Clutter.ActorAlign.CENTER,
        }));
        header.add_child(new St.Label({
            text: 'Notes',
            style_class: 'tcw-header-title',
            x_expand: true,
            y_align: Clutter.ActorAlign.CENTER,
        }));

        this._searchButton = headerToggle('edit-find-symbolic', 'Rechercher dans les notes');
        this._searchButton.connect('notify::checked', () => this._toggleEntry(this._searchEntry, this._searchButton));
        const buttons = new St.BoxLayout({style_class: 'tcw-button-pair', y_align: Clutter.ActorAlign.CENTER});
        // Replier les notes : le lecteur et les notifications reprennent la place.
        this._collapseButton = headerToggle('pan-up-symbolic', 'Replier les notes');
        this._collapseButton.toggle_mode = false;
        this._collapseButton.connect('clicked', () =>
            this._settings.set_boolean('notes-collapsed', !this._settings.get_boolean('notes-collapsed')));
        buttons.add_child(this._collapseButton);
        buttons.add_child(this._searchButton);
        this._addButton = headerToggle('list-add-symbolic', 'Nouvelle note');
        this._addButton.connect('notify::checked', () => this._toggleEntry(this._newEntry, this._addButton));
        buttons.add_child(this._addButton);
        header.add_child(buttons);
        this.add_child(header);

        this._categories = new St.BoxLayout({style_class: 'tcw-categories'});
        this._categoriesScroll = new St.ScrollView({
            style_class: 'tcw-categories-scroll hfade',
            child: this._categories,
            vscrollbar_policy: St.PolicyType.NEVER,
            hscrollbar_policy: St.PolicyType.EXTERNAL,
            overlay_scrollbars: true,
            visible: false,
        });
        this.add_child(this._categoriesScroll);

        this._searchEntry = escapableEntry('Rechercher dans les notes', () => (this._searchButton.checked = false));
        this._searchEntry.set_primary_icon(new St.Icon({icon_name: 'edit-find-symbolic', style_class: 'search-entry-icon'}));
        this._searchEntry.clutter_text.connect('text-changed', () => this._render());
        this.add_child(this._searchEntry);

        this._newEntry = escapableEntry('', () => (this._addButton.checked = false));
        this._newEntry.clutter_text.connect('activate', () => this._createNote(this._newEntry.get_text()));
        this.add_child(this._newEntry);
    }

    _buildBody() {
        this._error = new St.Label({style_class: 'tcw-error', visible: false});
        this._error.clutter_text.line_wrap = true;
        this.add_child(this._error);

        this._hint = new St.Label({style_class: 'tcw-hint', visible: false});
        this.add_child(this._hint);

        this._list = new St.BoxLayout({orientation: Clutter.Orientation.VERTICAL, style_class: 'tcw-list'});
        this._scroll = new St.ScrollView({
            style_class: 'tcw-scroll vfade',
            child: this._list,
            hscrollbar_policy: St.PolicyType.NEVER,
            overlay_scrollbars: true,
            y_expand: true,
        });
        this.add_child(this._scroll);

        this._undoBar = new St.BoxLayout({style_class: 'tcw-undo', visible: false});
        this._undoLabel = new St.Label({x_expand: true, y_align: Clutter.ActorAlign.CENTER});
        this._undoBar.add_child(this._undoLabel);
        const undo = new St.Button({style_class: 'button tcw-undo-button', label: 'Annuler', can_focus: true});
        undo.connect('clicked', () => this._undoTrash());
        this._undoBar.add_child(undo);
        this.add_child(this._undoBar);
    }

    setSide(left) {
        if (left) {
            this.add_style_class_name('tcw-left');
            this.remove_style_class_name('tcw-right');
        } else {
            this.add_style_class_name('tcw-right');
            this.remove_style_class_name('tcw-left');
        }
    }

    startNewNote() {
        if (!this._menu.isOpen)
            this._menu.toggle();
        if (this._addButton.checked)
            this._newEntry.grab_key_focus();
        else
            this._addButton.checked = true;
    }

    // Replié, la colonne se réduit à son en-tête. _refresh() ne tourne pas dans
    // cet état : rien ne peut rendre visible ce qui vient d'être masqué.
    _applyCollapsed() {
        const collapsed = this._settings.get_boolean('notes-collapsed');
        this.y_expand = !collapsed;
        this._searchButton.visible = !collapsed;
        this._addButton.visible = !collapsed;
        this._collapseButton.child.icon_name = collapsed ? 'pan-down-symbolic' : 'pan-up-symbolic';
        this._collapseButton.accessible_name = collapsed ? 'Déplier les notes' : 'Replier les notes';
        if (collapsed) {
            this._searchButton.checked = false;
            this._addButton.checked = false;
            this.setExpanded(this._expandedRow, false);
            for (const child of [this._categoriesScroll, this._searchEntry, this._newEntry,
                this._error, this._hint, this._scroll, this._undoBar])
                child.visible = false;
        } else {
            this._scroll.visible = true;
            this._refreshIfOpen();
        }
    }

    _toggleEntry(entry, button) {
        entry.visible = button.checked;
        entry.set_text('');
        if (button.checked)
            entry.grab_key_focus();
    }

    _menuToggled(open) {
        if (open) {
            this._refresh();
            return;
        }
        this._searchButton.checked = false;
        this._addButton.checked = false;
        this.setExpanded(this._expandedRow, false);
        this._commitTrash();
    }

    _dayChanged(day) {
        this._selectedDay = day;
        this._expandedRow?.setEventDay(eventDescription(day));
    }

    _refreshIfOpen() {
        if (this._menu.isOpen)
            this._refresh();
    }

    _selectedFolder() {
        const selected = this._settings.get_string('selected-folder');
        if (this._folders.length === 1)
            return this._folders[0];
        return this._folders.includes(selected) ? selected : '';
    }

    _targetFolder() {
        const active = this._grimoire.get_string('pinned-folder');
        return this._selectedFolder() || (this._folders.includes(active) ? active : this._folders[0]);
    }

    _showError(text) {
        this._error.text = text ?? '';
        this._error.visible = Boolean(text);
    }

    _showHint(text) {
        this._hint.text = text ?? '';
        this._hint.visible = Boolean(text);
    }

    _clearRows() {
        this._expandedRow = null;
        for (const child of this._list.get_children())
            child.destroy();
    }

    _showUnavailable() {
        this._notes = [];
        this._clearRows();
        this._categoriesScroll.hide();
        this._searchButton.reactive = false;
        this._addButton.reactive = false;
        this._showHint(null);
    }

    _fillCategories() {
        this._categories.destroy_all_children();
        this._categoriesScroll.visible = this._folders.length > 1;
        const selected = this._selectedFolder();
        for (const path of ['', ...this._folders]) {
            const chip = new St.Button({
                style_class: 'button tcw-chip',
                label: path ? basename(path) : 'Toutes',
                can_focus: true,
                checked: path === selected,
            });
            chip.connect('clicked', () => this._settings.set_string('selected-folder', path));
            this._categories.add_child(chip);
        }
    }

    async _noteText(note, cancellable) {
        const path = note.file.get_path();
        const stamp = note.modified.format_iso8601();
        const cached = this._texts.get(path);
        if (cached?.stamp === stamp)
            return cached.text;
        const text = await readNote(note.file, cancellable);
        this._texts.set(path, {stamp, text});
        return text;
    }

    async _loadFolder(path, cancellable) {
        try {
            const notes = await listNotes(Gio.File.new_for_path(path), cancellable);
            await Promise.all(notes.map(async note => {
                note.text = await this._noteText(note, cancellable).catch(() => '');
            }));
            return notes;
        } catch (error) {
            if (error.matches(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED))
                throw error;
            this._showError(`Dossier introuvable : ${path}`);
            return [];
        }
    }

    async _refresh() {
        if (this._settings.get_boolean('notes-collapsed'))
            return;
        this._cancellable?.cancel();
        this._showError(null);
        this._folders = this._grimoire ? visibleFolders(this._settings, this._grimoire) : [];
        if (!this._folders.length) {
            this._showUnavailable();
            return;
        }
        this._watchFolders();
        this._fillCategories();
        this._searchButton.reactive = true;
        this._addButton.reactive = true;
        this._newEntry.hint_text = `Nouvelle note dans ${basename(this._targetFolder())}`;

        const cancellable = new Gio.Cancellable();
        this._cancellable = cancellable;
        const selected = this._selectedFolder();
        let notes;
        try {
            notes = (await Promise.all((selected ? [selected] : this._folders)
                .map(path => this._loadFolder(path, cancellable)))).flat();
        } catch {
            return;
        }
        if (cancellable.is_cancelled())
            return;

        for (const note of notes)
            note.key = searchKey(`${note.title}\n${note.text}`);
        const paths = new Set(notes.map(note => note.file.get_path()));
        for (const path of this._texts.keys()) {
            if (!paths.has(path))
                this._texts.delete(path);
        }
        this._notes = notes;
        this._render();
    }

    // Notes ajoutées, supprimées ou modifiées pendant que le menu est ouvert.
    _watchFolders() {
        const key = this._folders.join('\n');
        if (key === this._watchKey)
            return;
        this._unwatchFolders();
        this._watchKey = key;
        for (const path of this._folders) {
            try {
                const monitor = Gio.File.new_for_path(path).monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, null);
                monitor.connect('changed', () => this._queueRefresh());
                this._monitors.push(monitor);
            } catch (error) {
                console.warn(`Topbar Center Widget : surveillance impossible de ${path} — ${error.message}`);
            }
        }
    }

    _unwatchFolders() {
        for (const monitor of this._monitors)
            monitor.cancel();
        this._monitors = [];
        this._watchKey = '';
    }

    _queueRefresh() {
        if (!this._menu?.isOpen)
            return;
        if (this._refreshId)
            GLib.Source.remove(this._refreshId);
        this._refreshId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 600, () => {
            this._refreshId = 0;
            this._refreshIfOpen();
            return GLib.SOURCE_REMOVE;
        });
    }

    _noteState(note, pinned, colors) {
        const path = note.file.get_path();
        return {pinned: pinned.has(path), color: colors[path] ?? null};
    }

    _render() {
        const query = searchKey(this._searchEntry.get_text().trim());
        const pinned = new Set(this._settings.get_strv('pinned-notes'));
        const colors = this._settings.get_value('note-colors').deepUnpack();
        const max = this._settings.get_int('max-notes');
        const pending = this._pendingTrash?.note.file.get_path();
        const visible = this._notes.filter(note => note.file.get_path() !== pending &&
            (!query || note.key.includes(query)));
        const grouped = !this._selectedFolder();

        this._clearRows();
        for (const folder of this._folders) {
            const notes = visible
                .filter(note => note.folder === folder)
                .sort((a, b) =>
                    pinned.has(b.file.get_path()) - pinned.has(a.file.get_path()) || b.modified.compare(a.modified));
            if (!notes.length)
                continue;
            if (grouped)
                this._list.add_child(new St.Label({text: basename(folder), style_class: 'tcw-section'}));
            for (const note of max > 0 ? notes.slice(0, max) : notes)
                this._list.add_child(new NoteRow(note, this._noteState(note, pinned, colors), this));
        }

        this._showHint(query && !visible.length ? 'Aucune note ne correspond.' : null);
    }

    _openFile(file) {
        Gio.DesktopAppInfo.new(`${GRIMOIRE_ID}.desktop`)
            .launch([file], global.create_app_launch_context(0, -1));
        this._menu.close();
    }

    async _createNote(title) {
        try {
            this._openFile(await createNote(Gio.File.new_for_path(this._targetFolder()), title));
        } catch (error) {
            this._showError(`Impossible de créer la note : ${error.message}`);
        }
    }

    _moveNoteSettings(oldPath, newPath) {
        const pinned = this._settings.get_strv('pinned-notes');
        if (pinned.includes(oldPath)) {
            this._settings.set_strv('pinned-notes',
                pinned.filter(path => path !== oldPath).concat(newPath ? [newPath] : []));
        }
        const colors = this._settings.get_value('note-colors').deepUnpack();
        if (oldPath in colors) {
            if (newPath)
                colors[newPath] = colors[oldPath];
            delete colors[oldPath];
            this._settings.set_value('note-colors', new GLib.Variant('a{ss}', colors));
        }
    }

    setExpanded(row, expanded) {
        if (!row)
            return;
        if (expanded && this._expandedRow && this._expandedRow !== row)
            this._expandedRow.setExpanded(false);
        if (expanded)
            row.setEventDay(eventDescription(this._selectedDay));
        row.setExpanded(expanded);
        this._expandedRow = expanded ? row : null;
    }

    openNote(note) {
        this._openFile(note.file);
    }

    async copyNote(row) {
        try {
            St.Clipboard.get_default().set_text(St.ClipboardType.CLIPBOARD, await readNote(row.note.file));
            row.showCopied();
        } catch (error) {
            this._showError(`Impossible de lire la note : ${error.message}`);
        }
    }

    async toggleTask(row, lineIndex) {
        try {
            const text = toggleTask(await readNote(row.note.file), lineIndex);
            await writeTextFile(row.note.file, text);
            row.updateText(text);
        } catch (error) {
            this._showError(`Impossible d’enregistrer la tâche : ${error.message}`);
        }
    }

    togglePinned(note) {
        const path = note.file.get_path();
        const pinned = this._settings.get_strv('pinned-notes');
        this._settings.set_strv('pinned-notes',
            pinned.includes(path) ? pinned.filter(item => item !== path) : [...pinned, path]);
    }

    setColor(note, color) {
        const colors = this._settings.get_value('note-colors').deepUnpack();
        if (color)
            colors[note.file.get_path()] = color;
        else
            delete colors[note.file.get_path()];
        this._settings.set_value('note-colors', new GLib.Variant('a{ss}', colors));
    }

    async renameNote(note, title) {
        try {
            const renamed = await renameNote(note, title);
            this._moveNoteSettings(note.file.get_path(), renamed.get_path());
            this._refresh();
        } catch (error) {
            const exists = error instanceof GLib.Error && error.matches(Gio.IOErrorEnum, Gio.IOErrorEnum.EXISTS);
            this._showError(exists ? `Une note « ${noteTitle(title.trim())} » existe déjà.`
                : `Impossible de renommer la note : ${error.message}`);
        }
    }

    async duplicateNote(note) {
        try {
            await duplicateNote(note);
            this._refresh();
        } catch (error) {
            this._showError(`Impossible de dupliquer la note : ${error.message}`);
        }
    }

    async createEvent(note) {
        try {
            const ics = buildEvent(note.title, bodyWithoutTitle(note.text, note.title), this._selectedDay);
            await openEvent(ics, global.create_app_launch_context(0, -1));
            this._menu.close();
        } catch (error) {
            this._showError(`Impossible de créer le rendez-vous : ${error.message}`);
        }
    }

    showNote(note) {
        showInFiles(note.file);
        this._menu.close();
    }

    trashNote(note) {
        this._commitTrash();
        const id = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, UNDO_DELAY_S, () => {
            this._pendingTrash.id = 0;
            this._commitTrash();
            return GLib.SOURCE_REMOVE;
        });
        this._pendingTrash = {note, id};
        this._undoLabel.text = `« ${note.title} » mise à la corbeille`;
        this._undoBar.show();
        this._render();
    }

    _undoTrash() {
        GLib.Source.remove(this._pendingTrash.id);
        this._pendingTrash = null;
        this._undoBar.hide();
        this._render();
    }

    async _commitTrash() {
        if (!this._pendingTrash)
            return;
        const {note, id} = this._pendingTrash;
        if (id)
            GLib.Source.remove(id);
        this._pendingTrash = null;
        this._undoBar.hide();
        try {
            await trashNote(note);
            this._moveNoteSettings(note.file.get_path(), null);
        } catch (error) {
            this._showError(`Impossible de mettre la note à la corbeille : ${error.message}`);
        }
        this._refreshIfOpen();
    }

    destroy() {
        if (this._pendingTrash?.id)
            GLib.Source.remove(this._pendingTrash.id);
        if (this._pendingTrash)
            trashNote(this._pendingTrash.note).catch(logError);
        this._pendingTrash = null;
        this._cancellable?.cancel();
        if (this._refreshId)
            GLib.Source.remove(this._refreshId);
        this._refreshId = 0;
        this._unwatchFolders();
        this._menu.disconnect(this._menuSignal);
        this._calendar.disconnect(this._calendarSignal);
        this._settings.disconnect(this._settingsSignal);
        if (this._grimoireSignal)
            this._grimoire.disconnect(this._grimoireSignal);
        this._clearRows();
        this._texts.clear();
        this._settings = null;
        this._grimoire = null;
        this._menu = null;
        this._calendar = null;
        super.destroy();
    }
});
