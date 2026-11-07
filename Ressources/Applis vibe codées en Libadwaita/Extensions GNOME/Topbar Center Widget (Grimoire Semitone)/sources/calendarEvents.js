// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.
/* Topbar Center Widget — mise en forme des rendez-vous du panneau calendrier.
 *
 * Vérifié sur gnome-shell 51.1 (js/ui/dateMenu.js et js/ui/calendar.js) :
 *   - `_eventsItem` est un `EventsSection` (St.Button, style `.events-button`)
 *     qui porte `_eventsList`, `_startDate`, `_endDate` et `_eventSource` ;
 *   - `_reloadEvents()` détruit puis recrée une `.event-box` par événement, dans
 *     l'ordre exact de `_eventSource.getEvents(startDate, endDate)` ;
 *   - chaque boîte est un `St.BoxLayout` vertical (`orientation`) à deux enfants :
 *     `.event-summary` puis `.event-time` ;
 *   - les identifiants d'événement valent `sourceUid + '\n' + …`, ce qui donne
 *     une identité d'agenda stable (voir eventModel.sourceKey).
 *
 * Depuis la v28, l'agenda s'identifie par un **point** placé devant le titre, et
 * plus par un fond : le grand cartouche gris natif (`.events-button`) est aplati
 * et les cartouches teintés des journées entières / plages multi-jours sont
 * abandonnés. La ligne redevient nue, seul le point reste coloré — le texte
 * garde la couleur du thème.
 *
 * Le passage au point impose une retouche de structure : la boîte verticale du
 * shell est réorientée et reçoit [point, colonne(summary, time)]. C'est
 * réversible à l'identique (voir _restoreBox), et sans risque puisque le shell
 * reconstruit toutes les boîtes à chaque `_reloadEvents()`.
 */

import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import St from 'gi://St';

import {InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';

import {assignColors, classifyEvent, eventCountdown, rgba, sourceKey} from './eventModel.js';

const CLASS_EVENTS = 'tcw-calendar-events';
const CLASS_DOT = 'tcw-event-dot';

// Aplatit le grand cartouche gris natif de la section (`.events-button`).
// Posé en style en ligne : il prime sur la feuille de style du thème, y compris
// sur ses règles :hover/:active, sans dépendre du nom exact de la classe native.
const FLATTEN_STYLE = 'background-color: transparent; box-shadow: none;';

// Le point est dimensionné et arrondi en style en ligne, jamais par
// stylesheet.css : les extensions ne rechargent pas toujours leur feuille de
// style, et St ne gère pas `min-width`/`min-height`. `width`/`height` +
// `border-radius` est la façon dont le thème du shell peint déjà ses propres
// pastilles (`.app-well-app-running-dot`).
const DOT_SIZE_STYLE = 'width: 9px; height: 9px; border-radius: 999px; ' +
    'margin-top: 5px; margin-right: 9px;';

const dotStyle = color => color
    ? `background-color: ${rgba(color, 1)}; ${DOT_SIZE_STYLE}`
    : DOT_SIZE_STYLE;

// Marqueur d'imminence : un mot, pas une couleur.
const ONGOING_SUFFIX = ' · en cours';

const LOG_PREFIX = 'Topbar Center Widget :';

const REFRESH_S = 60;
const CLASS_PROGRESS = 'tcw-event-progress';
const CLASS_PROGRESS_FILL = 'tcw-event-progress-fill';
const OPACITY_PAST = 150;
const OPACITY_NORMAL = 255;

export class CalendarEventStyler {
    constructor(eventsItem, menu, countdown) {
        this._countdown = countdown;
        this._refreshId = 0;
        this._item = eventsItem ?? null;
        this._list = eventsItem?._eventsList ?? null;
        this._menu = menu ?? null;

        this._injections = null;
        this._menuOpenId = 0;
        this._source = null;
        this._sourceChangedId = 0;
        this._records = new Map();
        this._warnedMismatch = false;
    }

    enable() {
        if (!this._item || !this._list)
            return false;

        this._item.add_style_class_name(CLASS_EVENTS);
        this._item.set_style(FLATTEN_STYLE);

        // Seul point d'accroche fiable : le shell reconstruit toutes les lignes
        // à chaque _reloadEvents(). On décore donc juste après l'original.
        const styler = this;
        this._injections = new InjectionManager();
        this._injections.overrideMethod(
            Object.getPrototypeOf(this._item),
            '_reloadEvents',
            original => function (...args) {
                const result = original.apply(this, args);
                styler._safeDecorate();
                return result;
            });

        // Filet : `setEventSource()` a mémorisé une référence liée à l'originale
        // de `_reloadEvents`, donc le signal 'changed' de la source ne passe pas
        // par la méthode réécrite.
        this._hookSource();

        if (this._menu) {
            this._menuOpenId = this._menu.connect('open-state-changed', (_menu, isOpen) => {
                this._syncRefresh(isOpen);
                if (!isOpen)
                    return;
                // La source peut avoir été remplacée (changement de mode de
                // session) : on se raccroche à celle en cours.
                this._hookSource();
                this._safeDecorate();
            });
        }

        this._safeDecorate();
        return true;
    }

    // Mentions « dans 25 min », « reste 40 min »… recalculées chaque minute,
    // seulement tant que le menu est ouvert.
    _syncRefresh(open) {
        if (this._refreshId)
            GLib.Source.remove(this._refreshId);
        this._refreshId = 0;
        if (!open || !this._countdown)
            return;
        this._refreshId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, REFRESH_S, () => {
            this._safeDecorate();
            return GLib.SOURCE_CONTINUE;
        });
    }

    disable() {
        this._syncRefresh(false);
        if (this._menuOpenId) {
            this._menu?.disconnect(this._menuOpenId);
            this._menuOpenId = 0;
        }

        this._unhookSource();

        this._injections?.clear();
        this._injections = null;

        for (const [box, record] of this._records) {
            try {
                this._restoreBox(box, record);
            } catch (_error) {
                // Boîte déjà détruite par le shell.
            }
        }
        this._records.clear();

        this._item?.remove_style_class_name(CLASS_EVENTS);
        this._item?.set_style(null);

        this._item = null;
        this._list = null;
        this._menu = null;
    }

    // Une exception ici ne doit jamais remonter au shell : elle casserait
    // `_reloadEvents()` et, depuis `enable()`, la suite des réglages. On la
    // journalise (visible via `journalctl -f -o cat /usr/bin/gnome-shell`).
    _safeDecorate() {
        try {
            this.decorate();
        } catch (error) {
            console.error(`${LOG_PREFIX} décoration des rendez-vous impossible — ${error.message}`,
                error);
        }
    }

    /**
     * Décore les lignes présentes. Idempotent : appelable autant de fois que
     * nécessaire (ouverture du panneau, reconstruction, rafraîchissement des
     * données), les styles en ligne sont reposés, jamais empilés.
     */
    decorate() {
        const item = this._item;
        const list = this._list;
        if (!item || !list)
            return;

        const startDate = item._startDate;
        const endDate = item._endDate;
        if (!startDate || !endDate)
            return;

        let events;
        try {
            events = item._eventSource?.getEvents(startDate, endDate) ?? [];
        } catch (_error) {
            return;
        }

        // Les boîtes sont créées dans l'ordre du tableau : si les deux comptes
        // divergent (rechargement en cours, source qui vient de changer), mieux
        // vaut ne rien faire que décorer la mauvaise ligne. On le signale une
        // fois : un désaccord persistant n'est pas normal et mérite le journal.
        const boxes = [...list].filter(child => child instanceof St.BoxLayout);
        if (boxes.length !== events.length) {
            if (!this._warnedMismatch) {
                this._warnedMismatch = true;
                console.error(`${LOG_PREFIX} ${boxes.length} ligne(s) pour ` +
                    `${events.length} rendez-vous — décoration ignorée`);
            }
            return;
        }
        this._warnedMismatch = false;

        const colors = assignColors(events);
        const now = new Date();

        for (let i = 0; i < boxes.length; i++) {
            this._decorateBox(boxes[i], events[i], colors.get(sourceKey(events[i])),
                startDate, endDate, now);
        }
    }

    _decorateBox(box, event, color, startDate, endDate, now) {
        let record = this._records.get(box);
        if (!record) {
            const layout = this._buildLayout(box);
            if (!layout)
                return;

            const baseText = layout.time.text ?? '';
            record = {
                ...layout,
                baseStyle: layout.time.style ?? null,
                // Filet de sécurité : si la boîte a déjà été décorée puis
                // relâchée sans être détruite, ne pas empiler le suffixe.
                baseText: baseText.endsWith(ONGOING_SUFFIX)
                    ? baseText.slice(0, -ONGOING_SUFFIX.length)
                    : baseText,
            };
            this._records.set(box, record);
            box.connect('destroy', () => this._records.delete(box));
        }

        const {markNow, past} = classifyEvent(event, startDate, endDate, now);

        // Le point, seule couleur de la ligne : elle identifie l'agenda.
        record.dot.set_style(dotStyle(color));
        box.set_opacity(past ? OPACITY_PAST : OPACITY_NORMAL);

        // Aucun lettrage coloré. Seule la mention « en cours » est mise en gras,
        // et `bold` plutôt que 700 pour rester dans le vocabulaire du thème.
        record.time.set_style(markNow ? 'font-weight: bold;' : null);
        const countdown = this._countdown
            ? eventCountdown(event, startDate, endDate, now) : {text: '', progress: null};
        const parts = [record.baseText];
        if (markNow)
            parts.push('en cours');
        if (countdown.text)
            parts.push(countdown.text);
        record.time.text = parts.join(' · ');
        this._setProgress(record, countdown.progress, color);
    }

    // Barre de 2 px sous une plage de plusieurs jours en cours (vacances…) :
    // part écoulée, à la couleur du point de l'agenda.
    _setProgress(record, progress, color) {
        if (progress === null) {
            record.progress?.hide();
            return;
        }
        if (!record.progress) {
            record.progressFill = new St.Widget({style_class: CLASS_PROGRESS_FILL, x_expand: true});
            record.progressFill.set_pivot_point(0, 0.5);
            record.progress = new St.BoxLayout({style_class: CLASS_PROGRESS, x_expand: true});
            record.progress.add_child(record.progressFill);
            record.column.add_child(record.progress);
        }
        record.progressFill.set_style(color ? `background-color: ${rgba(color, 1)};` : null);
        record.progressFill.scale_x = Math.min(1, Math.max(0, progress));
        record.progress.show();
    }

    /**
     * Transforme la boîte verticale native [summary, time] en ligne
     * [point, colonne(summary, time)], pour poser le point devant le titre sans
     * décaler l'heure, qui reste alignée sur le texte du titre.
     *
     * @returns {{summary: St.Widget, time: St.Widget, dot: St.Widget,
     *            column: St.BoxLayout}|null}
     */
    _buildLayout(box) {
        const summary = box.get_child_at_index(0);
        const time = box.get_child_at_index(1);
        if (!summary || !time)
            return null;

        // Ce qui peut échouer est fait avant de toucher aux enfants : si une
        // étape lève, la ligne reste intacte au lieu d'être amputée de son texte.
        const dot = new St.Widget({
            style_class: CLASS_DOT,
            y_align: Clutter.ActorAlign.START,
        });
        const column = new St.BoxLayout({
            orientation: Clutter.Orientation.VERTICAL,
            x_expand: true,
        });
        this._orient(box, Clutter.Orientation.HORIZONTAL);

        box.remove_child(summary);
        box.remove_child(time);
        column.add_child(summary);
        column.add_child(time);
        box.add_child(dot);
        box.add_child(column);

        return {summary, time, dot, column};
    }

    _restoreBox(box, record) {
        record.time.set_style(record.baseStyle);
        record.time.text = record.baseText;

        const {summary, time, dot, column} = record;
        record.progress?.destroy();

        box.remove_child(dot);
        box.remove_child(column);
        column.remove_child(summary);
        column.remove_child(time);

        this._orient(box, Clutter.Orientation.VERTICAL);
        box.set_style(null);
        box.set_opacity(OPACITY_NORMAL);
        box.add_child(summary);
        box.add_child(time);

        dot.destroy();
        column.destroy();
    }

    // `St.BoxLayout:orientation` (Clutter.Orientation) est la propriété que le
    // shell utilise lui-même pour ses boîtes (js/ui/dateMenu.js). `vertical` est
    // déprécié côté C et **n'est plus exposé à GJS** : y toucher lève
    // « No property vertical on StBoxLayout ». Le `Clutter.BoxLayout` interne
    // reste un repli.
    _orient(box, orientation) {
        try {
            box.orientation = orientation;
        } catch (_error) {
            box.layout_manager.orientation = orientation;
        }
    }

    _hookSource() {
        const source = this._item?._eventSource ?? null;
        if (!source || source === this._source)
            return;

        this._unhookSource();
        this._source = source;
        try {
            this._sourceChangedId = source.connect('changed', () => this._safeDecorate());
        } catch (_error) {
            this._sourceChangedId = 0;
        }
    }

    _unhookSource() {
        if (this._source && this._sourceChangedId) {
            try {
                this._source.disconnect(this._sourceChangedId);
            } catch (_error) {
                // Source déjà détruite.
            }
        }
        this._source = null;
        this._sourceChangedId = 0;
    }
}
