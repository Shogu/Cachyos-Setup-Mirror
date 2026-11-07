// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

import {clearDirectory, writeTextFile} from './notesFolder.js';
import {eventTime} from './noteText.js';

const ICS_LINE_OCTETS = 75;
const encoder = new TextEncoder();

function escapeText(text) {
    return text.replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\r?\n/g, '\\n');
}

function fold(line) {
    const parts = [];
    let current = '';
    let octets = 0;
    for (const char of line) {
        const size = encoder.encode(char).length;
        if (octets + size > ICS_LINE_OCTETS) {
            parts.push(current);
            current = ' ';
            octets = 1;
        }
        current += char;
        octets += size;
    }
    parts.push(current);
    return parts.join('\r\n');
}

export function eventDescription(day) {
    const now = GLib.DateTime.new_now_local();
    const today = day.get_year() === now.get_year() && day.get_day_of_year() === now.get_day_of_year();
    return today ? 'aujourd’hui' : `le ${day.format('%e %B').trim()}`;
}

// start et end : GLib.DateTime locaux, ou null pour un rendez-vous sur la journée entière.
export function buildIcs({title, description = '', day, start = null, end = null}) {
    const lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Ogu//Topbar Center Widget//FR',
        'BEGIN:VEVENT',
        `UID:${GLib.uuid_string_random()}@topbar-center-widget`,
        `DTSTAMP:${GLib.DateTime.new_now_utc().format('%Y%m%dT%H%M%SZ')}`,
    ];
    if (start)
        lines.push(`DTSTART:${start.format('%Y%m%dT%H%M%S')}`, `DTEND:${end.format('%Y%m%dT%H%M%S')}`);
    else
        lines.push(`DTSTART;VALUE=DATE:${day.format('%Y%m%d')}`, `DTEND;VALUE=DATE:${day.add_days(1).format('%Y%m%d')}`);
    lines.push(`SUMMARY:${escapeText(title)}`);
    if (description)
        lines.push(`DESCRIPTION:${escapeText(description)}`);
    lines.push('END:VEVENT', 'END:VCALENDAR');
    return `${lines.map(fold).join('\r\n')}\r\n`;
}

// Depuis une note : l'heure éventuelle est lue dans le titre (« Réunion 17h30 »).
export function buildEvent(title, description, day) {
    const time = eventTime(title);
    const start = time
        ? GLib.DateTime.new_local(day.get_year(), day.get_month(), day.get_day_of_month(), time.hour, time.minute, 0)
        : null;
    return buildIcs({title, description, day, start, end: start?.add_hours(1) ?? null});
}

export async function openEvent(ics, launchContext) {
    const app = Gio.AppInfo.get_default_for_type('text/calendar', false);
    if (!app)
        throw new Error('aucune application d’agenda n’ouvre les fichiers .ics');
    const directory = Gio.File.new_for_path(GLib.build_filenamev([GLib.get_user_runtime_dir(), 'topbar-center-widget']));
    if (directory.query_exists(null))
        await clearDirectory(directory);
    else
        directory.make_directory_with_parents(null);
    const file = directory.get_child(`${GLib.uuid_string_random()}.ics`);
    await writeTextFile(file, ics, Gio.FileCreateFlags.PRIVATE);
    app.launch([file], launchContext);
}
