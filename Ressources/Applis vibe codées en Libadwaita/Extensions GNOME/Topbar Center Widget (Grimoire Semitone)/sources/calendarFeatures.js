// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.
import {CalendarEventStyler} from './calendarEvents.js';
import {QuickEvent} from './quickEvent.js';

const EVENTS_MAX_HEIGHT = 300;

// Colonne du calendrier (à droite) : rendez-vous distingués par agenda, avec
// temps restant, bouton + de rendez-vous, date du bas masquée (réglages)
// et liste des rendez-vous à la hauteur de son contenu, jusqu'à 300 px, quel que
// soit le jour affiché.
export class CalendarFeatures {
    constructor(dateMenu, settings, extensionPath) {
        this._dateMenu = dateMenu;
        this._settings = settings;
        this._extensionPath = extensionPath;
        this._styler = null;
        this._quickEvent = null;
        this._section = dateMenu._displaysSection;
        this._box = this._section.child;

        this._settingsIds = ['calendar-event-style', 'calendar-countdown']
            .map(key => settings.connect(`changed::${key}`, () => this._syncStyle()));
        this._settingsIds.push(settings.connect('changed::quick-event', () => this._syncQuickEvent()));
        this._settingsIds.push(settings.connect('changed::hide-today-date', () => this._syncTodayDate()));
        this._boxId = this._box.connect('notify::height', () => this._fitEvents());
        // GNOME fige la hauteur du menu dès qu'on quitte aujourd'hui : un jour
        // chargé débordait alors sous le menu. On le laisse suivre son contenu.
        this._menuLayout = dateMenu.menu.box.get_first_child().layout_manager;
        this._dateId = dateMenu._calendar.connect('selected-date-changed', () => {
            this._menuLayout.frozen = false;
        });
        this._menuId = dateMenu.menu.connect('open-state-changed', (_menu, open) => {
            if (open)
                this._fitEvents();
        });
        this._syncStyle();
        this._syncQuickEvent();
        this._syncTodayDate();
        this._fitEvents();
    }

    _syncQuickEvent() {
        this._quickEvent?.destroy();
        this._quickEvent = this._settings.get_boolean('quick-event')
            ? new QuickEvent(this._dateMenu, this._settings, this._extensionPath) : null;
    }

    // La date sous le calendrier (« lundi 26 octobre 2026 ») répète la barre du haut.
    _syncTodayDate() {
        this._dateMenu._date.visible = !this._settings.get_boolean('hide-today-date');
    }

    _syncStyle() {
        this._styler?.disable();
        this._styler = null;
        if (!this._settings.get_boolean('calendar-event-style'))
            return;
        this._styler = new CalendarEventStyler(this._dateMenu._eventsItem, this._dateMenu.menu,
            this._settings.get_boolean('calendar-countdown'));
        this._styler.enable();
    }

    _fitEvents() {
        const [, natural] = this._box.get_preferred_height(-1);
        this._section.set_style(`min-height: ${Math.min(Math.ceil(natural), EVENTS_MAX_HEIGHT)}px;`);
    }

    destroy() {
        for (const id of this._settingsIds)
            this._settings.disconnect(id);
        this._box.disconnect(this._boxId);
        this._dateMenu._calendar.disconnect(this._dateId);
        this._menuLayout = null;
        this._dateMenu.menu.disconnect(this._menuId);
        this._styler?.disable();
        this._styler = null;
        this._quickEvent?.destroy();
        this._quickEvent = null;
        this._dateMenu._date.show();
        this._section.set_style(null);
        this._dateMenu = null;
        this._settings = null;
        this._section = null;
        this._box = null;
    }
}
