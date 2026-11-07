// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Pango from 'gi://Pango';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {buildIcs} from './calendarEvent.js';

Gio._promisify(Gio.Subprocess.prototype, 'communicate_utf8_async');

const CALENDAR_APP = 'org.gnome.Calendar.desktop';
const TIME = /^([01]?\d|2[0-3])\s*[:h]\s*([0-5]\d)?$/i;

function parseTime(text) {
    const match = text.trim().match(TIME);
    return match ? {hour: Number(match[1]), minute: Number(match[2] ?? 0)} : null;
}

// Dernière ligne utile de la sortie d'erreur, sans le préfixe « (gjs:1234): Gjs-CRITICAL **: 12:00:00.000: ».
function helperError(stderr) {
    const lines = stderr.split('\n').map(line => line.replace(/^\(gjs:\d+\): [\w-]+ \*\*: [\d:.]+: /, '').trim())
        .filter(line => line && !line.startsWith('JS ERROR') && !line.startsWith('@'));
    return lines.at(-1) ?? 'erreur inconnue';
}

function pill(label, styleClass) {
    return new St.Button({style_class: `button ${styleClass}`, label, can_focus: true});
}

// Bouton + à droite de « Aujourd'hui » et petit formulaire sous la liste des
// rendez-vous : titre, heures ou journée entière, agenda. L'écriture passe par
// l'assistant helpers/edsCalendar.js (processus séparé) ; en cas d'échec,
// « Ouvrir Agenda » reste proposé.
export class QuickEvent {
    constructor(dateMenu, settings, extensionPath) {
        this._settings = settings;
        this._helper = GLib.build_filenamev([extensionPath, 'helpers', 'edsCalendar.js']);
        this._cancellable = new Gio.Cancellable();
        this._calendars = null;
        this._calendarIndex = 0;
        this._day = GLib.DateTime.new_now_local();
        this._eventsItem = dateMenu._eventsItem;
        this._calendar = dateMenu._calendar;
        this._menu = dateMenu.menu;

        this._title = this._eventsItem._title;
        this._header = new St.BoxLayout({style_class: 'tcw-events-header'});
        this._title.get_parent().replace_child(this._title, this._header);
        this._title.x_expand = true;
        this._header.add_child(this._title);
        this._addButton = new St.Button({
            style_class: 'icon-button tcw-icon-button tcw-events-add',
            child: new St.Icon({icon_name: 'list-add-symbolic'}),
            accessible_name: 'Nouveau rendez-vous',
            can_focus: true,
            toggle_mode: true,
            y_align: Clutter.ActorAlign.CENTER,
        });
        this._addButton.connect('notify::checked', () => this._showForm(this._addButton.checked));
        this._header.add_child(this._addButton);

        this._buildForm();
        this._eventsItem.get_parent().insert_child_above(this._form, this._eventsItem);

        this._dayId = this._calendar.connect('selected-date-changed', (_calendar, day) => {
            this._day = day;
            this._syncDay();
        });
        this._menuId = this._menu.connect('open-state-changed', (_menu, open) => {
            if (!open)
                this._addButton.checked = false;
        });
    }

    _buildForm() {
        this._form = new St.BoxLayout({
            style_class: 'tcw-quick-event',
            orientation: Clutter.Orientation.VERTICAL,
            visible: false,
        });
        this._titleEntry = new St.Entry({style_class: 'tcw-entry', hint_text: 'Titre du rendez-vous', can_focus: true});
        this._titleEntry.clutter_text.connect('activate', () => this._create());
        this._titleEntry.clutter_text.connect('key-press-event', (_actor, event) => {
            if (event.get_key_symbol() !== Clutter.KEY_Escape)
                return Clutter.EVENT_PROPAGATE;
            this._addButton.checked = false;
            return Clutter.EVENT_STOP;
        });
        this._form.add_child(this._titleEntry);

        const when = new St.BoxLayout({style_class: 'tcw-quick-event-row'});
        this._dayLabel = new St.Label({style_class: 'tcw-quick-event-day', x_expand: true, y_align: Clutter.ActorAlign.CENTER});
        when.add_child(this._dayLabel);
        this._allDay = pill('Journée entière', 'tcw-chip');
        this._allDay.toggle_mode = true;
        this._allDay.connect('notify::checked', () => (this._times.visible = !this._allDay.checked));
        when.add_child(this._allDay);
        this._form.add_child(when);

        this._times = new St.BoxLayout({style_class: 'tcw-quick-event-row'});
        this._startEntry = new St.Entry({style_class: 'tcw-entry tcw-time-entry', can_focus: true});
        this._endEntry = new St.Entry({style_class: 'tcw-entry tcw-time-entry', can_focus: true});
        this._times.add_child(new St.Label({text: 'De', style_class: 'tcw-quick-event-label', y_align: Clutter.ActorAlign.CENTER}));
        this._times.add_child(this._startEntry);
        this._times.add_child(new St.Label({text: 'à', style_class: 'tcw-quick-event-label', y_align: Clutter.ActorAlign.CENTER}));
        this._times.add_child(this._endEntry);
        this._form.add_child(this._times);

        this._calendarButton = new St.Button({style_class: 'button tcw-chip tcw-calendar-chip', can_focus: true, x_align: Clutter.ActorAlign.START});
        const calendarBox = new St.BoxLayout({style_class: 'tcw-calendar-chip-box'});
        this._calendarDot = new St.Widget({style_class: 'tcw-dot', y_align: Clutter.ActorAlign.CENTER});
        this._calendarName = new St.Label({y_align: Clutter.ActorAlign.CENTER});
        calendarBox.add_child(this._calendarDot);
        calendarBox.add_child(this._calendarName);
        calendarBox.add_child(new St.Icon({icon_name: 'pan-down-symbolic', style_class: 'tcw-action-icon'}));
        this._calendarButton.child = calendarBox;
        this._calendarButton.connect('clicked', () => this._nextCalendar());
        this._form.add_child(this._calendarButton);

        this._status = new St.Label({style_class: 'tcw-error', visible: false});
        this._status.clutter_text.line_wrap = true;
        this._status.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;
        this._form.add_child(this._status);

        const actions = new St.BoxLayout({style_class: 'tcw-quick-event-actions', x_align: Clutter.ActorAlign.END});
        this._openCalendar = pill('Ouvrir Agenda', 'tcw-flat-button');
        this._openCalendar.connect('clicked', () => this._launchCalendar());
        actions.add_child(this._openCalendar);
        this._addEvent = pill('Ajouter', 'tcw-suggested-button');
        this._addEvent.connect('clicked', () => this._create());
        actions.add_child(this._addEvent);
        this._form.add_child(actions);
    }

    _showForm(visible) {
        this._form.visible = visible;
        if (!visible)
            return;
        this._titleEntry.set_text('');
        this._allDay.checked = false;
        this._status.hide();
        this._syncDay();
        this._loadCalendars();
        this._titleEntry.grab_key_focus();
    }

    _syncDay() {
        const now = GLib.DateTime.new_now_local();
        const today = this._day.get_year() === now.get_year() && this._day.get_day_of_year() === now.get_day_of_year();
        this._dayLabel.text = this._day.format('%a %e %b').replace(/\s+/g, ' ');
        const startHour = today ? Math.min(now.get_hour() + 1, 23) : 9;
        this._startEntry.set_text(`${String(startHour).padStart(2, '0')}:00`);
        this._endEntry.set_text(`${String(Math.min(startHour + 1, 23)).padStart(2, '0')}:${startHour === 23 ? '59' : '00'}`);
    }

    async _runHelper(args) {
        const process = Gio.Subprocess.new([GLib.find_program_in_path('gjs'), '-m', this._helper, ...args],
            Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);
        const [stdout, stderr] = await process.communicate_utf8_async(null, this._cancellable);
        // La sortie standard fait foi, pas le code de retour (voir helpers/edsCalendar.js).
        if (!stdout.trim())
            throw new Error(helperError(stderr));
        return stdout.trim();
    }

    async _loadCalendars() {
        if (this._calendars)
            return;
        try {
            this._calendars = JSON.parse(await this._runHelper(['list']));
        } catch (error) {
            if (error instanceof GLib.Error && error.matches(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED))
                return;
            // Pas de mise en cache de l'échec : on réessaiera à la prochaine ouverture.
            this._calendars = null;
            this._syncCalendar();
            this._showError(`Agendas illisibles : ${error.message}`);
            return;
        }
        const last = this._settings.get_string('last-calendar');
        this._calendarIndex = Math.max(0, this._calendars.findIndex(calendar => calendar.uid === last));
        this._syncCalendar();
    }

    _syncCalendar() {
        const calendar = this._calendars?.[this._calendarIndex];
        this._calendarButton.visible = Boolean(calendar);
        this._addEvent.reactive = Boolean(calendar);
        if (!calendar)
            return;
        this._calendarName.text = calendar.name;
        this._calendarDot.style = calendar.color ? `background-color: ${calendar.color};` : null;
    }

    _nextCalendar() {
        this._calendarIndex = (this._calendarIndex + 1) % this._calendars.length;
        this._syncCalendar();
    }

    _showError(text) {
        this._status.text = text;
        this._status.show();
    }

    _eventTimes() {
        if (this._allDay.checked)
            return {start: null, end: null};
        const start = parseTime(this._startEntry.get_text());
        const end = parseTime(this._endEntry.get_text());
        if (!start || !end)
            throw new Error('Heures attendues sous la forme 17:30 ou 17h30.');
        const at = ({hour, minute}) => GLib.DateTime.new_local(this._day.get_year(), this._day.get_month(),
            this._day.get_day_of_month(), hour, minute, 0);
        if (at(end).compare(at(start)) <= 0)
            throw new Error('L’heure de fin doit suivre l’heure de début.');
        return {start: at(start), end: at(end)};
    }

    async _create() {
        const calendar = this._calendars?.[this._calendarIndex];
        const title = this._titleEntry.get_text().trim();
        if (!calendar || !title) {
            this._showError(title ? 'Aucun agenda modifiable.' : 'Donnez un titre au rendez-vous.');
            return;
        }
        let ics;
        try {
            ics = buildIcs({title, day: this._day, ...this._eventTimes()});
        } catch (error) {
            this._showError(error.message);
            return;
        }
        // Le formulaire se ferme tout de suite ; l'enregistrement (quelques
        // secondes pour un agenda en ligne) continue en arrière-plan et ne se
        // signale qu'en cas d'échec.
        this._settings.set_string('last-calendar', calendar.uid);
        this._addButton.checked = false;
        try {
            if (await this._runHelper(['create', calendar.uid, ics]) !== 'OK')
                throw new Error('réponse inattendue de l’agenda');
        } catch (error) {
            if (error instanceof GLib.Error && error.matches(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED))
                return;
            Main.notifyError('Rendez-vous non enregistré', `« ${title} » (${calendar.name}) : ${error.message}`);
        }
    }

    _launchCalendar() {
        Gio.DesktopAppInfo.new(CALENDAR_APP).launch([], global.create_app_launch_context(0, -1));
        this._menu.close();
    }

    destroy() {
        this._cancellable.cancel();
        this._calendar.disconnect(this._dayId);
        this._menu.disconnect(this._menuId);
        this._form.destroy();
        this._header.remove_child(this._title);
        this._header.get_parent().replace_child(this._header, this._title);
        this._title.x_expand = false;
        this._header.destroy();
        this._settings = null;
        this._eventsItem = null;
        this._calendar = null;
        this._menu = null;
    }
}
