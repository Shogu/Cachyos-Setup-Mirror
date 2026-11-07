// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.
import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import St from 'gi://St';
import {CheckBox} from 'resource:///org/gnome/shell/ui/checkBox.js';

import {relativeDate} from './notesFolder.js';
import {notePreview, noteTasks, taskProgress} from './noteText.js';

const COPIED_FEEDBACK_MS = 1500;

export const COLORS = {
    blue: ['Bleu', '#3584e4'],
    green: ['Vert', '#33d17a'],
    yellow: ['Jaune', '#f6d32d'],
    orange: ['Orange', '#ff7800'],
    red: ['Rouge', '#e01b24'],
    purple: ['Violet', '#9141ac'],
};

function iconButton(iconName, accessibleName, styleClass = 'tcw-icon-button') {
    return new St.Button({
        style_class: `icon-button ${styleClass}`,
        child: new St.Icon({icon_name: iconName}),
        accessible_name: accessibleName,
        can_focus: true,
        y_align: Clutter.ActorAlign.CENTER,
    });
}

function actionButton(iconName, text, callback) {
    const box = new St.BoxLayout({style_class: 'tcw-action-box', x_expand: true, x_align: Clutter.ActorAlign.START});
    box.add_child(new St.Icon({icon_name: iconName, style_class: 'tcw-action-icon'}));
    const label = new St.Label({text, y_align: Clutter.ActorAlign.CENTER});
    box.add_child(label);
    const button = new St.Button({style_class: 'tcw-action', child: box, can_focus: true, x_expand: true});
    button.connect('clicked', callback);
    button.label_actor = label;
    return button;
}

function colorDot(hex, styleClass = 'tcw-dot') {
    return new St.Widget({style_class: styleClass, style: `background-color: ${hex};`, y_align: Clutter.ActorAlign.CENTER});
}

function colorPicker(current, onPick) {
    const box = new St.BoxLayout({style_class: 'tcw-colors'});
    const none = new St.Button({
        style_class: 'tcw-color-button',
        child: new St.Icon({icon_name: 'action-unavailable-symbolic', style_class: 'tcw-color-none'}),
        accessible_name: 'Sans couleur',
        can_focus: true,
        checked: !current,
    });
    none.connect('clicked', () => onPick(null));
    box.add_child(none);
    for (const [name, [label, hex]] of Object.entries(COLORS)) {
        const button = new St.Button({
            style_class: 'tcw-color-button',
            child: colorDot(hex, 'tcw-color-swatch'),
            accessible_name: label,
            can_focus: true,
            checked: current === name,
        });
        button.connect('clicked', () => onPick(name));
        box.add_child(button);
    }
    return box;
}

export const NoteRow = GObject.registerClass(
class NoteRow extends St.BoxLayout {
    _init(note, state, column) {
        super._init({style_class: 'tcw-row', orientation: Clutter.Orientation.VERTICAL});
        this.note = note;
        this._column = column;
        this._copiedId = 0;

        const line = new St.BoxLayout({style_class: 'tcw-line'});
        this.add_child(line);

        this._buildButtons();
        this._card = new St.Button({
            style_class: 'events-button tcw-card',
            child: this._cardContent(state),
            accessible_name: `Ouvrir ${note.title} dans Grimoire`,
            can_focus: true,
            x_expand: true,
        });
        this._card.connect('clicked', () => column.openNote(note));
        line.add_child(this._card);

        this._renameEntry = new St.Entry({
            style_class: 'tcw-entry',
            text: note.title,
            can_focus: true,
            x_expand: true,
            visible: false,
        });
        this._renameEntry.clutter_text.connect('activate', () => column.renameNote(note, this._renameEntry.get_text()));
        this._renameEntry.clutter_text.connect('key-press-event', (_actor, event) => {
            if (event.get_key_symbol() !== Clutter.KEY_Escape)
                return Clutter.EVENT_PROPAGATE;
            this.stopRenaming();
            return Clutter.EVENT_STOP;
        });
        line.add_child(this._renameEntry);


        this._tasks = new St.BoxLayout({
            style_class: 'tcw-tasklist',
            orientation: Clutter.Orientation.VERTICAL,
            visible: false,
        });
        this.add_child(this._tasks);
        this.add_child(this._buildActions(state));
        this.updateText(note.text);
    }

    // Copier et ⋮ sont dans la carte, en bas à droite : le titre a toute la
    // ligne du haut. Un clic sur ces boutons n'ouvre pas la note.
    _buildButtons() {
        this._buttons = new St.BoxLayout({style_class: 'tcw-card-buttons', y_align: Clutter.ActorAlign.END});
        this._tasksButton = iconButton('checkbox-checked-symbolic', 'Afficher les tâches', 'tcw-card-button');
        this._tasksButton.toggle_mode = true;
        this._tasksButton.connect('notify::checked', () => this._showTasks(this._tasksButton.checked));
        this._buttons.add_child(this._tasksButton);
        const copy = iconButton('edit-copy-symbolic', 'Copier le contenu de la note', 'tcw-card-button');
        this._copyIcon = copy.child;
        copy.connect('clicked', () => this._column.copyNote(this));
        this._buttons.add_child(copy);
        this._more = iconButton('view-more-symbolic', 'Actions sur la note', 'tcw-card-button');
        this._more.toggle_mode = true;
        this._more.connect('notify::checked', () => this._column.setExpanded(this, this._more.checked));
        this._buttons.add_child(this._more);
    }

    _cardContent(state) {
        const content = new St.BoxLayout({orientation: Clutter.Orientation.VERTICAL, x_expand: true});
        const heading = new St.BoxLayout({style_class: 'tcw-heading'});
        if (state.color)
            heading.add_child(colorDot(COLORS[state.color][1]));
        if (state.pinned)
            heading.add_child(new St.Icon({icon_name: 'view-pin-symbolic', style_class: 'tcw-pin-icon'}));
        heading.add_child(new St.Label({text: this.note.title, style_class: 'tcw-title', x_expand: true}));
        if (state.showDate !== false)
            heading.add_child(new St.Label({text: relativeDate(this.note.modified), style_class: 'tcw-date'}));
        content.add_child(heading);

        const bottom = new St.BoxLayout({style_class: 'tcw-card-bottom'});
        const details = new St.BoxLayout({orientation: Clutter.Orientation.VERTICAL, x_expand: true,
            y_align: Clutter.ActorAlign.CENTER});
        this._preview = new St.Label({style_class: 'tcw-preview'});
        details.add_child(this._preview);
        this._progress = new St.BoxLayout({style_class: 'tcw-tasks'});
        this._progress.add_child(new St.Icon({icon_name: 'object-select-symbolic', style_class: 'tcw-tasks-icon'}));
        this._progressLabel = new St.Label();
        this._progress.add_child(this._progressLabel);
        details.add_child(this._progress);
        bottom.add_child(details);
        bottom.add_child(this._buttons);
        content.add_child(bottom);
        return content;
    }

    _buildActions(state) {
        const column = this._column;
        const note = this.note;
        this._actions = new St.BoxLayout({
            style_class: 'tcw-actions',
            orientation: Clutter.Orientation.VERTICAL,
            visible: false,
        });
        this._actions.add_child(colorPicker(state.color, color => column.setColor(note, color)));
        this._actions.add_child(actionButton('view-pin-symbolic', state.pinned ? 'Ne plus épingler' : 'Épingler en haut',
            () => column.togglePinned(note)));
        this._actions.add_child(actionButton('document-edit-symbolic', 'Renommer', () => this._startRenaming()));
        this._actions.add_child(actionButton('document-new-symbolic', 'Dupliquer', () => column.duplicateNote(note)));
        this._eventButton = actionButton('x-office-calendar-symbolic', '', () => column.createEvent(note));
        this._actions.add_child(this._eventButton);
        this._actions.add_child(actionButton('folder-open-symbolic', 'Afficher dans Fichiers',
            () => column.showNote(note)));
        this._actions.add_child(new St.Widget({style_class: 'tcw-separator'}));
        const trash = actionButton('user-trash-symbolic', 'Mettre à la corbeille', () => column.trashNote(note));
        trash.add_style_class_name('tcw-destructive');
        this._actions.add_child(trash);
        return this._actions;
    }

    updateText(text) {
        this.note.text = text;
        this._preview.text = notePreview(text);
        this._preview.visible = Boolean(this._preview.text);
        const progress = taskProgress(text);
        this._progress.visible = Boolean(progress);
        this._tasksButton.visible = Boolean(progress);
        if (progress)
            this._progressLabel.text = `${progress.done}/${progress.total}`;
        else
            this._tasksButton.checked = false;
        if (this._tasks.visible)
            this._fillTasks();
    }

    _fillTasks() {
        this._tasks.destroy_all_children();
        for (const task of noteTasks(this.note.text)) {
            const box = new CheckBox(task.label);
            box.add_style_class_name('tcw-task');
            box.checked = task.done;
            box.connect('clicked', () => this._column.toggleTask(this, task.line));
            this._tasks.add_child(box);
        }
    }

    _showTasks(visible) {
        this._tasks.visible = visible;
        if (visible)
            this._fillTasks();
    }

    setEventDay(description) {
        this._eventButton.label_actor.text = `Créer un rendez-vous ${description}`;
    }

    setExpanded(expanded) {
        this._actions.visible = expanded;
        this._more.checked = expanded;
        if (!expanded)
            this.stopRenaming();
    }

    _startRenaming() {
        this._actions.hide();
        this._card.hide();
        this._renameEntry.show();
        this._renameEntry.grab_key_focus();
        this._renameEntry.clutter_text.set_selection(0, -1);
    }

    stopRenaming() {
        this._renameEntry.hide();
        this._renameEntry.set_text(this.note.title);
        this._card.show();
    }

    showCopied() {
        if (this._copiedId)
            GLib.Source.remove(this._copiedId);
        this._copyIcon.icon_name = 'object-select-symbolic';
        this._copiedId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, COPIED_FEEDBACK_MS, () => {
            this._copyIcon.icon_name = 'edit-copy-symbolic';
            this._copiedId = 0;
            return GLib.SOURCE_REMOVE;
        });
    }

    destroy() {
        if (this._copiedId)
            GLib.Source.remove(this._copiedId);
        this._copiedId = 0;
        this._column = null;
        super.destroy();
    }
});
