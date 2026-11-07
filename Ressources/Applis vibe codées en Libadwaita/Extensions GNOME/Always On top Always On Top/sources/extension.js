import GObject from 'gi://GObject';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';

import {Extension, gettext as _} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

// Icônes embarquées, rangées et chargées EXACTEMENT comme celles de Copyous
// (icons/hicolor/scalable/actions/<nom>.svg + loadIcon, cf. son indicator.js
// et lib/common/icons.js). DESSIN au format Copyous/Adwaita : chemins PLEINS
// (fill #2e3436), aucun attribut stroke — les traits « stroke » se rendent
// baveux dans le rasteriseur de GNOME Shell, les pleins sont nets comme son
// clipboard. Gabarit v27 : MÊME empreinte que son clipboard, 14×16 unités
// (20×23 px rendus), encre en PLEIN CADRE 0..16 — elle touche donc les
// mêmes lignes du panel que la sienne : plus aucun décalage haut/bas
// possible (la v26 couvrait 0.25..15.75 et s'arrêtait 1,5 px avant en bas).
// Cadre de 2 unités (3 px rendus), rayons ext. 3 / int. 1 : les métriques
// exactes du corps de son clipboard, d'où la même épaisseur visuelle.
// Noms v27 inédits : GNOME Shell garde en cache les icônes par chemin de
// fichier, réutiliser un ancien nom réafficherait l'ancien dessin.
// Rien d'épinglé, épinglage possible : cadre avec encoche pleine collée au bord gauche.
const BASE_ICON = 'aot-notch-ready-symbolic';
// Rien d'épinglé, épinglage impossible : cadre avec carré plein central détaché.
const UNAVAILABLE_ICON = 'aot-square-blocked-symbolic';

// Icône monochrome générique (jamais d'icône couleur dans la topbar).
const FALLBACK_ICON = 'application-x-executable-symbolic';

// Repli du relais, au cas où : Ptyxis n'a pas sa propre icône symbolique
// dans le thème, on lui affiche le terminal générique d'Adwaita. Les
// autres apps fournissent désormais leur symbolique — première candidate
// de _appIconFor — la table n'a plus besoin d'entrées pour elles.
const APP_SYMBOLIC = {
    'ptyxis': 'utilities-terminal-symbolic',
};

// Clés du schéma GSettings (schemas/*.gschema.xml).
const SHORTCUT_ENABLED_KEY = 'shortcut-enabled';
// Les noms de raccourcis forment un espace de noms GLOBAL dans GNOME Shell
// (Mutter + toutes les extensions) : un nom générique comme « toggle-shortcut »
// peut déjà être pris, et add_keybinding échoue alors. D'où ce nom spécifique.
const SHORTCUT_KEY = 'aot-toggle-shortcut';

const AlwaysOnTopIndicator = GObject.registerClass(
class AlwaysOnTopIndicator extends PanelMenu.Button {
    _init(extension) {
        this._extension = extension;
        // dontCreateMenu = true : une simple icône cliquable, pas un menu.
        super._init(0.0, _('Always on Top'), true);

        this._tracker = Shell.WindowTracker.get_default();

        // Fenêtre actuellement épinglée (si aucune, null) — indépendant du
        // focus, pour que l'icône reste correcte même après avoir changé
        // de fenêtre.
        this._pinnedWindow = null;
        this._pinnedAboveId = 0;
        this._pinnedUnmanagedId = 0;

        // Fenêtre focus : sert à détecter un épinglage fait via le menu
        // natif de la barre de titre pendant qu'elle a le focus, et à
        // signaler (carré pointillé) quand elle est maximisée.
        this._focusedWindow = null;
        this._focusedIds = [];

        // Même construction que l'indicateur de Copyous : une boîte, puis
        // une St.Icon de taille standard "system-status-icon". (Boîte
        // horizontale par défaut : pas de propriété "orientation", absente
        // de St.BoxLayout avant GNOME 48.)
        this._box = new St.BoxLayout({
            style_class: 'aot-indicator-box',
        });
        this.add_child(this._box);
        this._icon = new St.Icon({
            gicon: this._baseIcon(),
            style_class: 'system-status-icon',
        });
        this._box.add_child(this._icon);

        this.accessible_name = _('Always on Top');

        this.connect('button-press-event', this._onButtonPress.bind(this));
        this.connect('key-press-event', this._onKeyPress.bind(this));
        this.connect('destroy', this._onDestroy.bind(this));

        this._focusSignalId = global.display.connect(
            'notify::focus-window',
            () => this._onFocusChanged()
        );

        this._onFocusChanged();
    }

    // Repris de loadIcon() de Copyous (lib/common/icons.js).
    _bundledIcon(icon) {
        const file = Gio.file_new_for_path(
            `${this._extension.path}/icons/hicolor/scalable/actions/${icon}.svg`);
        if (file.query_exists(null))
            return Gio.Icon.new_for_string(file.get_path());
        else
            return Gio.Icon.new_for_string(icon);
    }

    _baseIcon() {
        return this._bundledIcon(BASE_ICON);
    }

    _unavailableIcon() {
        return this._bundledIcon(UNAVAILABLE_ICON);
    }

    // Icône monochrome de l'app épinglée. Le thème d'icônes prend la
    // première de ces trois candidates qu'il trouve :
    //   1. la symbolique propre à l'app (<icône déclarée par l'app>-symbolic),
    //      donc aussi celles ajoutées à la main dans le thème d'icônes ;
    //   2. l'icône Adwaita générique du tableau APP_SYMBOLIC (repli) ;
    //   3. l'icône monochrome générique.
    _appIconFor(win) {
        const app = this._tracker.get_window_app(win);
        if (!app)
            return this._baseIcon();

        const names = [];

        const gicon = app.get_icon();
        if (gicon instanceof Gio.ThemedIcon) {
            for (const n of gicon.get_names())
                names.push(`${n}-symbolic`);
        }

        const id = (app.get_id() || '').toLowerCase();
        for (const key in APP_SYMBOLIC) {
            if (id.includes(key)) {
                names.push(APP_SYMBOLIC[key]);
                break;
            }
        }

        names.push(FALLBACK_ICON);
        return Gio.ThemedIcon.new_from_names(names);
    }

    _disconnectFocused() {
        if (this._focusedWindow) {
            for (const id of this._focusedIds)
                this._focusedWindow.disconnect(id);
        }
        this._focusedIds = [];
    }

    _onFocusChanged() {
        this._disconnectFocused();

        const win = global.display.focus_window;
        this._focusedWindow = win;

        if (win) {
            this._focusedIds.push(
                win.connect('notify::above', () => this._onAboveChanged(win)),
                win.connect('notify::maximized-horizontally', () => this._updateSensitivity()),
                win.connect('notify::maximized-vertically', () => this._updateSensitivity())
            );
            // Rattrape une fenêtre déjà épinglée avant qu'on la surveille
            // (épinglée via le menu natif, ou avant l'activation de
            // l'extension).
            this._onAboveChanged(win);
        }

        this._updateSensitivity();
    }

    _onAboveChanged(win) {
        if (win.is_above())
            this._setPinnedWindow(win);
        else if (win === this._pinnedWindow)
            this._clearPinnedWindow();
    }

    _setPinnedWindow(win) {
        if (this._pinnedWindow === win)
            return;

        this._clearPinnedWindow();
        this._pinnedWindow = win;
        // S'il y avait déjà une autre fenêtre épinglée, elle reste
        // épinglée (pas de restriction) : c'est juste l'icône qui montre
        // désormais celle-ci, la plus récemment épinglée.
        this._pinnedAboveId = win.connect(
            'notify::above',
            () => this._onAboveChanged(win)
        );
        this._pinnedUnmanagedId = win.connect(
            'unmanaging',
            () => this._clearPinnedWindow()
        );
        this._syncIcon();
    }

    _clearPinnedWindow() {
        if (!this._pinnedWindow)
            return;

        if (this._pinnedAboveId) {
            this._pinnedWindow.disconnect(this._pinnedAboveId);
            this._pinnedAboveId = 0;
        }
        if (this._pinnedUnmanagedId) {
            this._pinnedWindow.disconnect(this._pinnedUnmanagedId);
            this._pinnedUnmanagedId = 0;
        }
        this._pinnedWindow = null;
        this._syncIcon();
    }

    _syncIcon() {
        // Une fenêtre est épinglée : relais vers l'icône monochrome de son
        // app — quelle que soit la fenêtre qui a le focus en ce moment.
        // Sinon, l'icône dit si l'on peut épingler la fenêtre active :
        // encoche collée au bord (possible) ou carré détaché (impossible).
        let gicon;
        if (this._pinnedWindow)
            gicon = this._appIconFor(this._pinnedWindow);
        else if (this._canToggle(this._focusedWindow))
            gicon = this._baseIcon();
        else
            gicon = this._unavailableIcon();

        this._icon.set_gicon(gicon);
    }

    // Même règle que l'entrée « Toujours au premier plan » du menu natif
    // de la fenêtre (js/ui/windowMenu.js de GNOME Shell) : elle est grisée
    // pour une fenêtre maximisée (Mutter ne la placerait de toute façon pas
    // au-dessus des autres) et pour les types DOCK, DESKTOP et SPLASHSCREEN.
    _canToggle(win) {
        if (!win)
            return false;
        if (win.is_maximized())
            return false;

        const type = win.get_window_type();
        return type !== Meta.WindowType.DOCK &&
            type !== Meta.WindowType.DESKTOP &&
            type !== Meta.WindowType.SPLASHSCREEN;
    }

    // Désactive le bouton (non réactif, pas de cartouche de survol) quand
    // il n'y a rien à épingler : aucune fenêtre active, ou fenêtre
    // maximisée. L'icône (carré pointillé, cf. _syncIcon) l'indique, sans grisage.
    _updateSensitivity() {
        const sensitive = this._canToggle(this._focusedWindow);

        this.reactive = sensitive;
        this.can_focus = sensitive;
        this._syncIcon();

        if (sensitive)
            this.remove_style_pseudo_class('insensitive');
        else
            this.add_style_pseudo_class('insensitive');

        // Évite un cartouche de survol resté allumé si le bouton devient inactif
        // pendant que le pointeur est dessus (sans effet tant que le bouton
        // n'est pas encore sur la scène, c'est-à-dire à la construction).
        if (this.get_stage())
            this.sync_hover();
    }

    _onButtonPress(_actor, event) {
        if (event.get_button() !== Clutter.BUTTON_PRIMARY)
            return Clutter.EVENT_PROPAGATE;

        return this.toggleFocusedWindow();
    }

    // Activation clavier (navigation Ctrl+Alt+Tab → barre supérieure).
    _onKeyPress(_actor, event) {
        const symbol = event.get_key_symbol();
        if (symbol !== Clutter.KEY_space &&
            symbol !== Clutter.KEY_Return &&
            symbol !== Clutter.KEY_KP_Enter &&
            symbol !== Clutter.KEY_ISO_Enter)
            return Clutter.EVENT_PROPAGATE;

        return this.toggleFocusedWindow();
    }

    // Appelée par le bouton ET par le raccourci clavier : un seul chemin.
    toggleFocusedWindow() {
        const win = global.display.focus_window;
        if (!this._canToggle(win))
            return Clutter.EVENT_PROPAGATE;

        // Exactement ce qu'appelle GNOME Shell en interne pour l'option
        // "Toujours au premier plan" du menu de la fenêtre.
        if (win.is_above())
            win.unmake_above();
        else
            win.make_above();

        return Clutter.EVENT_STOP;
    }

    _onDestroy() {
        if (this._focusSignalId) {
            global.display.disconnect(this._focusSignalId);
            this._focusSignalId = 0;
        }
        this._disconnectFocused();
        this._focusedWindow = null;
        this._clearPinnedWindow();
    }
});

export default class AlwaysOnTopAlwaysOnTopExtension extends Extension {
    enable() {
        this._settings = this.getSettings();

        this._indicator = new AlwaysOnTopIndicator(this);
        // Avant-dernière place de la zone de droite : juste avant le menu
        // système (Quick Settings), qui reste en bout de ligne.
        const rightBox = Main.panel._rightBox;
        const position = Math.max(0, rightBox.get_n_children() - 1);
        Main.panel.addToStatusArea(this.uuid, this._indicator, position, 'right');

        // Raccourci clavier optionnel (préférence « Activer le raccourci
        // Super+T ») : enregistré par l'extension elle-même, retiré dès que
        // la préférence est coupée ou que l'extension est désactivée.
        this._shortcutActive = false;
        this._settingsChangedId = this._settings.connect(
            `changed::${SHORTCUT_ENABLED_KEY}`,
            () => this._syncShortcut()
        );
        this._syncShortcut();
    }

    disable() {
        if (this._settings && this._settingsChangedId) {
            this._settings.disconnect(this._settingsChangedId);
            this._settingsChangedId = 0;
        }
        this._removeShortcut();
        this._settings = null;

        this._indicator?.destroy();
        this._indicator = null;
    }

    _syncShortcut() {
        const wanted = this._settings?.get_boolean(SHORTCUT_ENABLED_KEY) ?? false;
        if (wanted === this._shortcutActive)
            return;

        if (!wanted) {
            this._removeShortcut();
            return;
        }

        const action = Main.wm.addKeybinding(
            SHORTCUT_KEY,
            this._settings,
            Meta.KeyBindingFlags.IGNORE_AUTOREPEAT,
            Shell.ActionMode.NORMAL,
            () => this._indicator?.toggleFocusedWindow()
        );

        if (action === Meta.KeyBindingAction.NONE) {
            // Échec d'enregistrement : on repasse la préférence à « désactivé »
            // pour que l'interrupteur dise la vérité.
            console.warn(`${this.uuid}: impossible d'enregistrer le raccourci "${SHORTCUT_KEY}" ` +
                '(nom déjà enregistré ? cherche « Trying to re-add keybinding » dans le journal)');
            Main.notify(_('Always on Top'), _('Could not register the Super+T shortcut.'));
            this._settings.set_boolean(SHORTCUT_ENABLED_KEY, false);
            return;
        }

        this._shortcutActive = true;
    }

    _removeShortcut() {
        if (!this._shortcutActive)
            return;

        Main.wm.removeKeybinding(SHORTCUT_KEY);
        this._shortcutActive = false;
    }
}
