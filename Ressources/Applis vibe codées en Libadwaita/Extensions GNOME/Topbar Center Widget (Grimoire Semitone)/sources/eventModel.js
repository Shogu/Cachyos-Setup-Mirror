// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.
/* Topbar Center Widget — modèle des rendez-vous du panneau calendrier.
 *
 * Module volontairement sans dépendance GI : importé par calendarEvents.js dans
 * le shell, et exécutable directement sous gjs ou Node pour être testé.
 *
 * La couleur d'agenda ne sert qu'à teinter les fonds de cartouche : aucun
 * lettrage n'est coloré, le texte garde la couleur du thème.
 */

// Teintes Adwaita, utilisées uniquement en fond très peu opaque.
export const PALETTE = [
    [0x35, 0x84, 0xe4], // bleu
    [0x26, 0xa2, 0x69], // vert
    [0x91, 0x41, 0xac], // violet
    [0xc6, 0x46, 0x00], // orange
    [0xe5, 0xa5, 0x0a], // jaune
    [0x21, 0x90, 0xa4], // sarcelle
];

export const rgba = (rgb, alpha) => `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${alpha})`;

// FNV-1a : stable pour une même chaîne, réparti sur la palette.
export function hashIndex(str, modulo) {
    let hash = 2166136261;
    for (let i = 0; i < str.length; i++) {
        hash ^= str.charCodeAt(i);
        hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0) % modulo;
}

// L'identifiant fourni par org.gnome.Shell.CalendarServer commence par l'UID de
// la source de l'agenda suivie d'un saut de ligne : le shell s'en sert lui-même
// pour purger le cache (`_removeMatching(sourceUid + '\n')` dans calendar.js).
// C'est donc une identité d'agenda stable, sans passer par ECal ou ESource.
export function sourceKey(event) {
    const id = typeof event.id === 'string' ? event.id : '';
    const sourceUid = id.split('\n')[0];
    return sourceUid || event.summary || '';
}

/**
 * Teintes des agendas **sans doublon** parmi les rendez-vous affichés.
 *
 * Le hachage seul laissait deux agendas sur la même teinte une fois sur trois
 * environ (6 teintes), ce qui annule l'individualisation. On garde le hachage
 * comme base — donc une teinte stable pour un agenda donné — et on décale le
 * second en cas de collision. Les clés sont triées pour que le résultat ne
 * dépende pas de l'ordre d'affichage des rendez-vous.
 *
 * @param {Array<{id?: string, summary?: string}>} events
 * @returns {Map<string, number[]>} clé d'agenda → composantes RGB
 */
export function assignColors(events) {
    const keys = [...new Set(events.map(sourceKey))].sort();
    const used = new Set();
    const colors = new Map();

    for (const key of keys) {
        let index = hashIndex(key, PALETTE.length);
        while (used.has(index) && used.size < PALETTE.length)
            index = (index + 1) % PALETTE.length;
        used.add(index);
        colors.set(key, PALETTE[index]);
    }

    return colors;
}

/**
 * Reproduit les tests de `EventsSection._formatEventTime` (js/ui/dateMenu.js)
 * et en déduit la forme à donner à la ligne.
 *
 * @param {{date: Date, end: Date}} event
 * @param {Date} startDate début de la journée affichée (minuit local)
 * @param {Date} endDate lendemain de la journée affichée (minuit local)
 * @param {Date} now
 */
export function classifyEvent(event, startDate, endDate, now) {
    const allDay = event.date.getTime() === startDate.getTime() &&
                   event.end.getTime() === endDate.getTime();
    const spans = event.date < startDate || event.end > endDate;
    const ongoing = !allDay && event.date <= now && now < event.end;
    const past = event.end <= now;
    const cartouche = spans || allDay;

    // Le cartouche dit déjà « ça dure » : inutile d'y ajouter « en cours ».
    const markNow = ongoing && !cartouche;

    return {allDay, spans, ongoing, past, cartouche, markNow};
}

const MINUTE_MS = 60 * 1000;
const DAY_MS = 24 * 60 * MINUTE_MS;

function duration(ms) {
    const minutes = Math.max(1, Math.round(ms / MINUTE_MS));
    if (minutes < 60)
        return `${minutes} min`;
    const hours = Math.floor(minutes / 60);
    const rest = minutes % 60;
    return rest ? `${hours} h ${String(rest).padStart(2, '0')}` : `${hours} h`;
}

function midnight(date) {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

/**
 * Mention de temps ajoutée à la ligne de l'heure (sans couleur) et, pour une
 * plage de plusieurs jours en cours, la part déjà écoulée (barre fine).
 *
 * @param {{date: Date, end: Date}} event
 * @param {Date} startDate début de la journée affichée (minuit local)
 * @param {Date} endDate lendemain de la journée affichée (minuit local)
 * @param {Date} now
 * @returns {{text: string, progress: number|null}}
 */
export function eventCountdown(event, startDate, endDate, now) {
    const {allDay, spans, ongoing, past} = classifyEvent(event, startDate, endDate, now);
    const daysAhead = Math.round((startDate - midnight(now)) / DAY_MS);

    if (past || daysAhead < 0)
        return {text: '', progress: null};
    if (daysAhead > 0 && event.date >= startDate)
        return {text: daysAhead === 1 ? 'demain' : `dans ${daysAhead} jours`, progress: null};
    if (spans && event.date <= now && now < event.end) {
        const daysLeft = Math.ceil((event.end - now) / DAY_MS);
        return {
            text: daysLeft <= 1 ? 'dernier jour' : `encore ${daysLeft} jours`,
            progress: (now - event.date) / (event.end - event.date),
        };
    }
    if (ongoing)
        return {text: `reste ${duration(event.end - now)}`, progress: null};
    if (!allDay && !spans && event.date > now)
        return {text: `dans ${duration(event.date - now)}`, progress: null};
    return {text: '', progress: null};
}
