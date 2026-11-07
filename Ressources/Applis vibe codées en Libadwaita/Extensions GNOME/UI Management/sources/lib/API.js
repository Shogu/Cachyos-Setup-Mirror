/**
 * API Library
 *
 * @author     Javad Rahmatzadeh <j.rahmatzadeh@gmail.com>
 * @copyright  2020-2026
 * @license    GPL-3.0-only
 */

const XY_POSITION = {
    TOP_START: 0,
    TOP_CENTER: 1,
    TOP_END: 2,
    BOTTOM_START: 3,
    BOTTOM_CENTER: 4,
    BOTTOM_END: 5,
    CENTER_START: 6,
    CENTER_CENTER: 7,
    CENTER_END: 8,
};

const PANEL_POSITION = {
    TOP: 0,
    BOTTOM: 1,
};

const PANEL_BOX_POSITION = {
    CENTER: 0,
    RIGHT: 1,
    LEFT: 2,
};

const PANEL_HIDE_MODE = {
    ALL: 0,
    DESKTOP: 1,
};

const SHELL_STATUS = {
    NONE: 0,
    OVERVIEW: 1,
};

const DASH_ICON_SIZES = [16, 22, 24, 32, 40, 48, 56, 64];

/**
 * API to avoid calling GNOME Shell directly
 * and make all parts compatible with different GNOME Shell versions
 */
export class API
{
    /**
     * Current shell version
     *
     * @type {number|null}
     */
    #shellVersion = null;

    /**
     * Originals holder
     *
     * @type {object}
     */
    #originals = {};

    /**
     * Timeout ids
     *
     * @type {object}
     */
    #timeoutIds = {};

    /**
     * Active method injections, by key. Each entry is [object, methodName].
     * The single InjectionManager is owned by the extension, this map only
     * remembers which of our injections are currently installed so that
     * they are never installed twice and can be restored one by one.
     *
     * @type {Map<string, Array>}
     */
    #injected = new Map();

    /**
     * Class Constructor
     *
     * @param {Object} dependencies
     *   'Main' reference to ui.main
     *   'BackgroundMenu' reference to ui.backgroundMenu
     *   'OverviewControls' reference to ui.overviewControls
     *   'WorkspaceSwitcherPopup' reference to ui.workspaceSwitcherPopup
     *   'SwitcherPopup' reference to ui.switcherPopup
     *   'InterfaceSettings' reference to Gio.Settings for 'org.gnome.desktop.interface'
     *   'SearchController' reference to ui.searchController
     *   'WorkspaceThumbnail' reference to ui.workspaceThumbnail
     *   'WorkspacesView' reference to ui.workspacesView
     *   'Panel' reference to ui.panel
     *   'PanelMenu' reference to ui.panelMenu
     *   'WindowPreview' reference to ui.windowPreview
     *   'Workspace' reference to ui.workspace
     *   'MessageTray' reference to ui.messageTray
     *   'OSDWindow' reference to ui.osdTray
     *   'WindowMenu' reference to ui.windowMenu
     *   'AltTab' reference to ui.altTab
     *   'St' reference to St
     *   'GLib' reference to GLib
     *   'Clutter' reference to Clutter
     *   'Util' reference to misc.util
     *   'Meta' reference to Meta
     *   'GObject' reference to GObject
     *   'InjectionManager' unique InjectionManager instance, created by the extension
     * @param {number} shellVersion - float in major.minor format
     */
    constructor(dependencies, shellVersion)
    {
        this._main = dependencies['Main'] || null;
        this._backgroundMenu = dependencies['BackgroundMenu'] || null;
        this._overviewControls = dependencies['OverviewControls'] || null;
        this._workspaceSwitcherPopup = dependencies['WorkspaceSwitcherPopup'] || null;
        this._switcherPopup = dependencies['SwitcherPopup'] || null;
        this._interfaceSettings = dependencies['InterfaceSettings'] || null;
        this._searchController = dependencies['SearchController'] || null;
        this._workspaceThumbnail = dependencies['WorkspaceThumbnail'] || null;
        this._workspacesView = dependencies['WorkspacesView'] || null;
        this._panel = dependencies['Panel'] || null;
        this._panelMenu = dependencies['PanelMenu'] || null;
        this._windowPreview = dependencies['WindowPreview'] || null;
        this._workspace = dependencies['Workspace'] || null;
        this._messageTray = dependencies['MessageTray'] || null;
        this._osdWindow = dependencies['OSDWindow'] || null;
        this._windowMenu = dependencies['WindowMenu'] || null;
        this._altTab = dependencies['AltTab'] || null;
        this._st = dependencies['St'] || null;
        this._glib = dependencies['GLib'] || null;
        this._clutter = dependencies['Clutter'] || null;
        this._util = dependencies['Util'] || null;
        this._meta = dependencies['Meta'] || null;
        this._gobject = dependencies['GObject'] || null;
        this._injection = dependencies['InjectionManager'] || null;

        this.#shellVersion = shellVersion;

        /**
         * whether search entry is visible
         *
         * @member {boolean}
         */
        this._searchEntryVisibility = true;
    }

    /**
     * prepare everything needed for API
     *
     * @returns {void}
     */
    open()
    {
        this.UIStyleClassAdd(this.#getAPIClassname('shell-version'));
    }

    /**
     * remove everything from GNOME Shell been added by this class
     *
     * @returns {void}
     */
    close()
    {
        try {
            for (let [name, id] of Object.entries(this.#timeoutIds)) {
                if (id) {
                    this._glib.source_remove(id);
                }
                delete(this.#timeoutIds[name]);
            }

            this.UIStyleClassRemove(this.#getAPIClassname('shell-version'));
            this.#startSearchSignal(false);
            this.#computeWorkspacesBoxForStateSetDefault();
            this.#altTabSizesSetDefault();
            this.#stopAllOnQuickSettingsPropertyCalls();
        } finally {
            // safety net: whatever happened above, no injection stays installed
            this.#uninjectAll();
        }
    }

    /**
     * install a method override with the extension's InjectionManager.
     * An override with the same key is restored first, so the same method
     * is never overridden twice.
     *
     * @param {string} key unique key of this injection
     * @param {object} object prototype (or instance) holding the method
     * @param {string} methodName name of the method to override
     * @param {Function} createOverrideFunc receives the original method and
     *   returns the override. see InjectionManager.overrideMethod()
     *
     * @returns {boolean} false when the method doesn't exist in this
     *   GNOME Shell version (nothing is installed in this case)
     */
    #inject(key, object, methodName, createOverrideFunc)
    {
        this.#uninject(key);

        if (typeof object?.[methodName] !== 'function') {
            console.warn(`UI Management: ${methodName} doesn't exist in this GNOME Shell version`);
            return false;
        }

        this._injection.overrideMethod(object, methodName, createOverrideFunc);
        this.#injected.set(key, [object, methodName]);

        return true;
    }

    /**
     * restore the method overridden by `#inject()`
     *
     * @param {string} key unique key of the injection
     *
     * @returns {boolean} false when nothing was injected with this key
     */
    #uninject(key)
    {
        const entry = this.#injected.get(key);

        if (!entry) {
            return false;
        }

        this.#injected.delete(key);
        this._injection.restoreMethod(entry[0], entry[1]);

        return true;
    }

    /**
     * check whether an injection is currently installed
     *
     * @param {string} key unique key of the injection
     *
     * @returns {boolean}
     */
    #isInjected(key)
    {
        return this.#injected.has(key);
    }

    /**
     * restore all injections
     *
     * @returns {void}
     */
    #uninjectAll()
    {
        for (const key of [...this.#injected.keys()]) {
            this.#uninject(key);
        }
    }

    /**
     * get x and y align for position
     *
     * @param int pos position
     *   see XY_POSITION
     *
     * @returns {array}
     *  - 0 Clutter.ActorAlign
     *  - 1 Clutter.ActorAlign
     */
    #xyAlignGet(pos)
    {
        if (XY_POSITION.TOP_START === pos) {
            return [this._clutter.ActorAlign.START, this._clutter.ActorAlign.START];
        }

        if (XY_POSITION.TOP_CENTER === pos) {
            return [this._clutter.ActorAlign.CENTER, this._clutter.ActorAlign.START];
        }

        if (XY_POSITION.TOP_END === pos) {
            return [this._clutter.ActorAlign.END, this._clutter.ActorAlign.START];
        }

        if (XY_POSITION.CENTER_START === pos) {
            return [this._clutter.ActorAlign.START, this._clutter.ActorAlign.CENTER];
        }

        if (XY_POSITION.CENTER_CENTER === pos) {
            return [this._clutter.ActorAlign.CENTER, this._clutter.ActorAlign.CENTER];
        }

        if (XY_POSITION.CENTER_END === pos) {
            return [this._clutter.ActorAlign.END, this._clutter.ActorAlign.CENTER];
        }

        if (XY_POSITION.BOTTOM_START === pos) {
            return [this._clutter.ActorAlign.START, this._clutter.ActorAlign.END];
        }

        if (XY_POSITION.BOTTOM_CENTER === pos) {
            return [this._clutter.ActorAlign.CENTER, this._clutter.ActorAlign.END];
        }

        if (XY_POSITION.BOTTOM_END === pos) {
            return [this._clutter.ActorAlign.END, this._clutter.ActorAlign.END];
        }
    }

    /**
     * add to animation duration
     *
     * @param {number} duration in milliseconds
     *
     * @returns {number}
     */
    #addToAnimationDuration(duration)
    {
        let settings = this._st.Settings.get();

        return (settings.enable_animations) ? settings.slow_down_factor * duration : 1;
    }

    /**
     * get signal id of the event
     *
     * @param {Gtk.Widget} widget to find signal in
     * @param {string} signalName signal name
     *
     * @returns {number}
     */
    #getSignalId(widget, signalName)
    {
        return this._gobject.signal_handler_find(widget, {signalId: signalName});
    }

    /**
     * get the css class name for API
     *
     * @param {string} type
     *
     * @returns {string}
     */
    #getAPIClassname(type)
    {
        let starter = 'just-perfection-api-';

        if (type === 'shell-version') {
            let shellVerMajor = Math.trunc(this.#shellVersion);
            return `${starter}gnome${shellVerMajor}`;
        }

        return `${starter}${type}`;
    }

    /**
     * set panel size to default
     *
     * @returns {void}
     */
    panelSetDefaultSize()
    {
        if (!this.#originals['panelHeight']) {
            return;
        }

        this.panelSetSize(this.#originals['panelHeight'], false);
    }

    /**
     * change panel size
     *
     * @param {number} size 0 to 100
     * @param {boolean} fake true means it shouldn't change the last size,
     *   false otherwise
     *
     * @returns {void}
     */
    panelSetSize(size, fake)
    {
        if (!this.#originals['panelHeight']) {
            this.#originals['panelHeight'] = this._main.panel.height;
        }

        if (size > 100 || size < 0) {
            return;
        }

        this._main.panel.height = size;

        if (!fake) {
            this._panelSize = size;
        }
    }

    /**
     * get the last size of the panel
     *
     * @returns {number}
     */
    panelGetSize()
    {
        if (this._panelSize !== undefined) {
            return this._panelSize;
        }

        if (this.#originals['panelHeight']) {
            return this.#originals['panelHeight'];
        }

        return this._main.panel.height;
    }

    /**
     * emit refresh styles
     * this is useful when changed style doesn't emit change because doesn't have
     * standard styles. for example, style with only `-natural-hpadding`
     * won't notify any change. so you need to call this function
     * to refresh that
     *
     * @returns {void}
     */
    #emitRefreshStyles()
    {
        let classname = this.#getAPIClassname('refresh-styles');

        this.UIStyleClassAdd(classname);
        this.UIStyleClassRemove(classname);
    }

    /**
     * show panel
     *
     * @returns {void}
     */
    panelShow()
    {
        this._panelVisibility = true;

        let classname = this.#getAPIClassname('no-panel');

        if (!this.UIStyleClassContain(classname)) {
            return;
        }

        // The class name should be removed before addChrome the panelBox
        // removing after can cause `st_theme_node_lookup_shadow` crash
        this.UIStyleClassRemove(classname);

        let overview = this._main.overview;
        let searchEntryParent = overview.searchEntry.get_parent();
        let panelBox = this._main.layoutManager.panelBox;

        panelBox.translation_y = 0;

        this._main.layoutManager.overviewGroup.remove_child(panelBox);
        this._main.layoutManager.addChrome(panelBox, {
            affectsStruts: true,
            trackFullscreen: true,
        });

        if (this._hidePanelWorkareasChangedSignal) {
            global.display.disconnect(this._hidePanelWorkareasChangedSignal);
            delete(this._hidePanelWorkareasChangedSignal);
        }

        if (this._hidePanelHeightSignal) {
            panelBox.disconnect(this._hidePanelHeightSignal);
            delete(this._hidePanelHeightSignal);
        }

        searchEntryParent.set_style(`margin-top: 0;`);

        // hide and show can fix windows going under panel
        panelBox.hide();
        panelBox.show();

        if (this.#timeoutIds.panelHide) {
            this._glib.source_remove(this.#timeoutIds.panelHide);
            delete(this.#timeoutIds.panelHide);
        }
    }

    /**
     * hide panel
     *
     * @param {mode} hide mode see PANEL_HIDE_MODE. defaults to hide all
     * @param {boolean} force apply hide even if it is hidden
     *
     * @returns {void}
     */
    panelHide(mode)
    {
        this._panelVisibility = false;
        this._panelHideMode = mode;

        let overview = this._main.overview;
        let searchEntryParent = overview.searchEntry.get_parent();
        let panelBox = this._main.layoutManager.panelBox;
        let panelHeight = this._main.panel.height;
        let panelPosition = this.panelGetPosition();
        let direction = (panelPosition === PANEL_POSITION.BOTTOM) ? 1 : -1;

        if (panelBox.get_parent() === this._main.layoutManager.uiGroup) {
            this._main.layoutManager.removeChrome(panelBox);
            this._main.layoutManager.overviewGroup.add_child(panelBox);
        }

        panelBox.translation_y = (mode === PANEL_HIDE_MODE.DESKTOP) ? 0 : panelHeight * direction;

        if (panelPosition === PANEL_POSITION.TOP) {
            // when panel is hidden the first element gets too close to the top,
            // so we fix it with top margin in search entry
            // the panel height is the actual scaled height
            // css engine applies the scale automatically so we need to use
            // the original non-scaled value as initial value
            const scaleFactor = this._st.ThemeContext.get_for_stage(global.stage).scale_factor;
            let marginTop = (mode === PANEL_HIDE_MODE.ALL) ? 15 : Math.round(panelHeight / scaleFactor);
            searchEntryParent.set_style(`margin-top: ${marginTop}px;`);
        } else {
            searchEntryParent.set_style(`margin-top: 0;`);
        }

        // hide and show can fix windows going under panel
        panelBox.hide();
        panelBox.show();

        if (this._hidePanelWorkareasChangedSignal) {
            global.display.disconnect(this._hidePanelWorkareasChangedSignal);
            delete(this._hidePanelWorkareasChangedSignal);
        }

        this._hidePanelWorkareasChangedSignal = global.display.connect(
            'workareas-changed',
            () => {
                this.panelHide(this._panelHideMode);
            }
        );

        if (!this._hidePanelHeightSignal) {
            this._hidePanelHeightSignal = panelBox.connect(
                'notify::height',
                () => {
                    this.panelHide(this._panelHideMode);
                }
            );
        }

        let classname = this.#getAPIClassname('no-panel');
        this.UIStyleClassAdd(classname);

        // update hot corners since we need to make them available
        // outside overview
        this._main.layoutManager._updateHotCorners();

        // For GNOME Shell 45-48
        // Maximized windows will have bad maximized gap after unlock in Wayland
        // This is a Mutter issue,
        // See https://gitlab.gnome.org/GNOME/mutter/-/issues/1627
        if (this.#shellVersion <= 48 && this._meta.is_wayland_compositor()) {
            let duration = this.#addToAnimationDuration(180);
            if (this.#timeoutIds.panelHide) {
                this._glib.source_remove(this.#timeoutIds.panelHide);
                delete(this.#timeoutIds.panelHide);
            }
            this.#timeoutIds.panelHide = this._glib.timeout_add(
                this._glib.PRIORITY_DEFAULT,
                duration,
                () => {
                    panelBox.hide();
                    panelBox.show();
                    this.#timeoutIds.panelHide = null;
                    return this._glib.SOURCE_REMOVE;
                }
            );
        }
    }

    /**
     * check whether panel is visible
     *
     * @returns {boolean}
     */
    isPanelVisible()
    {
        if (this._panelVisibility === undefined) {
            return true;
        }

        let fullyHidden = this._panelHideMode === PANEL_HIDE_MODE.ALL;

        return this._panelVisibility || (!this._panelVisibility && !fullyHidden);
    }

    /**
     * check whether dash is visible
     *
     * @returns {boolean}
     */
    isDashVisible()
    {
        return this._dashVisibility === undefined || this._dashVisibility;
    }

    /**
     * show dash
     *
     * @returns {void}
     */
    dashShow()
    {
        if (!this._main.overview.dash || this.isDashVisible()) {
            return;
        }

        this._dashVisibility = true;

        this._main.overview.dash.show();

        this._main.overview.dash.height = -1;
        this._main.overview.dash.setMaxSize(-1, -1);

        this.#updateWindowPreviewOverlap();
    }

    /**
     * hide dash
     *
     * @returns {void}
     */
    dashHide()
    {
        if (!this._main.overview.dash || !this.isDashVisible()) {
            return;
        }

        this._dashVisibility = false;

        this._main.overview.dash.hide();

        this._main.overview.dash.height = 0;

        this.#updateWindowPreviewOverlap();
    }

    /**
     * update window preview overlap
     *
     * @returns {void}
     */
    #updateWindowPreviewOverlap()
    {
        let wpp = this._windowPreview.WindowPreview.prototype;

        if (this.isDashVisible()) {
            this.#uninject('windowPreviewOverlapHeights');
            return;
        }

        this.#inject('windowPreviewOverlapHeights', wpp, 'overlapHeights', original => function () {
            let [top, bottom] = original.call(this);
            return [top + 24, bottom + 24];
        });
    }

    /**
     * add class name to the UI group
     *
     * @param {string} classname class name
     *
     * @returns {void}
     */
    UIStyleClassAdd(classname)
    {
        this._main.layoutManager.uiGroup.add_style_class_name(classname);
    }

    /**
     * remove class name from UI group
     *
     * @param {string} classname class name
     *
     * @returns {void}
     */
    UIStyleClassRemove(classname)
    {
        this._main.layoutManager.uiGroup.remove_style_class_name(classname);
    }

    /**
     * check whether UI group has class name
     *
     * @param {string} classname class name
     *
     * @returns {boolean}
     */
    UIStyleClassContain(classname)
    {
        return this._main.layoutManager.uiGroup.has_style_class_name(classname);
    }

    /**
     * enable background menu
     *
     * @returns {void}
     */
    backgroundMenuEnable()
    {
        this.#uninject('backgroundMenuOpen');
    }

    /**
     * disable background menu
     *
     * @returns {void}
     */
    backgroundMenuDisable()
    {
        this.#inject(
            'backgroundMenuOpen',
            this._backgroundMenu.BackgroundMenu.prototype,
            'open',
            () => function () {}
        );
    }

    /**
     * show search
     *
     * @param {boolean} fake true means it just needs to do the job but
     *   don't need to change the search visibility status
     *
     * @returns {void}
     */
    searchEntryShow(fake)
    {
        let classname = this.#getAPIClassname('no-search');

        if (!this.UIStyleClassContain(classname)) {
            return;
        }

        this.UIStyleClassRemove(classname);

        let searchEntry = this._main.overview.searchEntry;
        let searchEntryParent = searchEntry.get_parent();

        searchEntryParent.height = 0;
        searchEntry.opacity = 0;
        searchEntry.show();

        searchEntryParent.ease({
            height: searchEntry.height,
            opacity: 255,
            mode: this._clutter.AnimationMode.EASE,
            duration: 90,
            onStopped: () => {
                searchEntryParent.height = -1;
                searchEntry.ease({
                    opacity: 255,
                    mode: this._clutter.AnimationMode.EASE,
                    duration: 300,
                });
            },
        });

        if (!fake) {
            this._searchEntryVisibility = true;
        }

        this.#computeWorkspacesBoxForStateChanged();
    }

    /**
     * hide search
     *
     * @param {boolean} fake true means it just needs to do the job
     *   but don't need to change the search visibility status
     *
     * @returns {void}
     */
    searchEntryHide(fake)
    {
        this.UIStyleClassAdd(this.#getAPIClassname('no-search'));

        let searchEntry = this._main.overview.searchEntry;

        searchEntry.hide();

        if (!fake) {
            this._searchEntryVisibility = false;
        }

        this.#computeWorkspacesBoxForStateChanged();
    }

    /**
     * enable start search
     *
     * @returns {void}
     */
    startSearchEnable()
    {
        this.#startSearchSignal(true);

        this.#uninject('startSearch');
    }

    /**
     * disable start search
     *
     * @returns {void}
     */
    startSearchDisable()
    {
        this.#startSearchSignal(false);

        // `startSearch` doesn't exist anymore in GNOME Shell 51: nothing is
        // installed there (see #inject()), the type to search behavior is
        // not handled by this method in that version.
        this.#inject(
            'startSearch',
            this._searchController.SearchController.prototype,
            'startSearch',
            () => function () {}
        );
    }

    /**
     * add search signals that needs to be show search entry when the
     * search entry is hidden
     *
     * @param {boolean} add true means add the signal, false means remove
     *   the signal
     *
     * @returns {void}
     */
    #startSearchSignal(add)
    {
        let controller
        = this._main.overview.viewSelector ||
          this._main.overview._overview.viewSelector ||
          this._main.overview._overview.controls._searchController;

        // remove
        if (!add) {
            if (this._searchActiveSignal) {
                controller.disconnect(this._searchActiveSignal);
                this._searchActiveSignal = null;
            }
            return;
        }

        // add
        if (this._searchActiveSignal) {
            return;
        }

        this._searchActiveSignal = controller.connect('notify::search-active', () => {
            if (this._searchEntryVisibility) {
                return;
            }

            let inSearch = controller.searchActive;

            if (inSearch) {
                this.UIStyleClassAdd(this.#getAPIClassname('type-to-search'));
                this.searchEntryShow(true);
            } else {
                this.UIStyleClassRemove(this.#getAPIClassname('type-to-search'));
                this.searchEntryHide(true);
            }
        });
    }

    /**
     * enable OSD
     *
     * @returns {void}
     */
    OSDEnable()
    {
        this.#uninject('osdWindowManagerShow');
        this.#uninject('osdWindowManagerShowOne');
        this.#uninject('osdWindowManagerShowAll');
    }

    /**
     * disable OSD
     *
     * @returns {void}
     */
    OSDDisable()
    {
        const osdWindowManager = this._main.osdWindowManager;

        this.#inject('osdWindowManagerShow', osdWindowManager, 'show', () => function () {});
        this.#inject('osdWindowManagerShowOne', osdWindowManager, 'showOne', () => function () {});
        this.#inject('osdWindowManagerShowAll', osdWindowManager, 'showAll', () => function () {});
    }

    /**
     * enable workspace popup
     *
     * @returns {void}
     */
    workspacePopupEnable()
    {
        this.#uninject('workspaceSwitcherPopupDisplay');
    }

    /**
     * disable workspace popup
     *
     * @returns {void}
     */
    workspacePopupDisable()
    {
        this.#inject(
            'workspaceSwitcherPopupDisplay',
            this._workspaceSwitcherPopup.WorkspaceSwitcherPopup.prototype,
            'display',
            () => function (_index) {
                this.destroy();
            }
        );
    }

    /**
     * show workspace switcher
     *
     * @returns {void}
     */
    workspaceSwitcherShow()
    {
        this.UIStyleClassRemove(this.#getAPIClassname('no-workspace'));

        this.#workspaceSwitcherShouldShowSetToLast();
    }

    /**
     * hide workspace switcher
     *
     * @returns {void}
     */
    workspaceSwitcherHide()
    {
        this.workspaceSwitcherShouldShow(false, true);

        // should be after `this.workspaceSwitcherShouldShow()`
        // since it checks whether it's visible or not
        this.UIStyleClassAdd(this.#getAPIClassname('no-workspace'));
    }

    /**
     * check whether workspace switcher is visible
     *
     * @returns {boolean}
     */
    isWorkspaceSwitcherVisible()
    {
        return !this.UIStyleClassContain(this.#getAPIClassname('no-workspace'));
    }

    /**
     * set workspace switcher to its default size
     *
     * @returns {void}
     */
    workspaceSwitcherSetDefaultSize()
    {
        let thumbnailsBox = this._main.overview._overview._controls._thumbnailsBox;

        if (!this.#uninject('thumbnailsBoxInit')) {
            return;
        }

        thumbnailsBox._maxThumbnailScale = this._workspaceThumbnail.MAX_THUMBNAIL_SCALE;
    }

    /**
     * set workspace switcher size
     *
     * @param {number} size in float
     *
     * @returns {void}
     */
    workspaceSwitcherSetSize(size)
    {
        let thumbnailsBox = this._main.overview._overview._controls._thumbnailsBox;
        let ThumbnailsBoxProto = this._workspaceThumbnail.ThumbnailsBox.prototype;

        thumbnailsBox._maxThumbnailScale = size;

        this.#inject('thumbnailsBoxInit', ThumbnailsBoxProto, '_init', original => function (...params) {
            this._maxThumbnailScale = size;
            original.apply(this, params);
        });
    }

    /**
     * use default behavior for the workspace thumbnail click
     *
     * @returns {void}
     */
    workspaceThumbnailClickToDefault()
    {
        this.#uninject('workspaceThumbnailActivate');
    }

    /**
     * workspace thumbnail click always goes to the main view
     * instead of just changing the workspace
     *
     * @returns {void}
     */
    workspaceThumbnailClickToMainView()
    {
        if (this.#isInjected('workspaceThumbnailActivate')) {
            return;
        }

        let WorkspaceThumbnailProto = this._workspaceThumbnail.WorkspaceThumbnail.prototype;

        const Main = this._main;
        const ThumbnailState = this._workspaceThumbnail.ThumbnailState;

        this.#inject('workspaceThumbnailActivate', WorkspaceThumbnailProto, 'activate', () => function (time) {
            if (this.state > ThumbnailState.NORMAL) {
                return;
            }
            if (!this.metaWorkspace.active) {
                this.metaWorkspace.activate(time);
            }
            Main.overview.hide();
        });
    }

    /**
     * add element to stage
     *
     * @param {St.Widget} element widget
     *
     * @returns {void}
     */
    chromeAdd(element)
    {
        this._main.layoutManager.addChrome(element, {
            affectsInputRegion : true,
            affectsStruts : false,
            trackFullscreen : true,
        });
    }

    /**
     * remove element from stage
     *
     * @param {St.Widget} element widget
     *
     * @returns {void}
     */
    chromeRemove(element)
    {
        this._main.layoutManager.removeChrome(element);
    }

    /**
     * show activities button
     *
     * @returns {void}
     */
    activitiesButtonShow()
    {
        let activities = this._main.panel.statusArea.activities;

        if (!this.isLocked() && activities) {
            activities.container.show();
        }
    }

    /**
     * hide activities button
     *
     * @returns {void}
     */
    activitiesButtonHide()
    {
        let activities = this._main.panel.statusArea.activities;

        if (activities) {
            activities.container.hide();
        }
    }

    /**
     * show date menu
     *
     * @returns {void}
     */
    dateMenuShow()
    {
        if (!this.isLocked()) {
            this._main.panel.statusArea.dateMenu.container.show();
        }
    }

    /**
     * hide date menu
     *
     * @returns {void}
     */
    dateMenuHide()
    {
        this._main.panel.statusArea.dateMenu.container.hide();
    }

    /**
     * show keyboard layout
     *
     * @returns {void}
     */
    keyboardLayoutShow()
    {
        this._main.panel.statusArea.keyboard.container.show();
    }

    /**
     * hide keyboard layout
     *
     * @returns {void}
     */
    keyboardLayoutHide()
    {
        this._main.panel.statusArea.keyboard.container.hide();
    }

    /**
     * show accessibility menu
     *
     * @returns {void}
     */
    accessibilityMenuShow()
    {
        this._main.panel.statusArea.a11y?.container.show();
    }

    /**
     * hide accessibility menu
     *
     * @returns {void}
     */
    accessibilityMenuHide()
    {
        this._main.panel.statusArea.a11y?.container.hide();
    }

    /**
     * show quick settings menu
     *
     * @returns {void}
     */
    quickSettingsMenuShow()
    {
        this._main.panel.statusArea.quickSettings.container.show();
    }

    /**
     * hide quick settings menu
     *
     * @returns {void}
     */
    quickSettingsMenuHide()
    {
        this._main.panel.statusArea.quickSettings.container.hide();
    }

    /**
     * check whether lock dialog is currently showing
     *
     * @returns {boolean}
     */
    isLocked()
    {
        return this._main.sessionMode.isLocked;
    }

    /**
     * enable window picker icon
     *
     * @returns {void}
     */
    windowPickerIconEnable()
    {
        this.UIStyleClassRemove(this.#getAPIClassname('no-window-picker-icon'));
    }

    /**
     * disable window picker icon
     *
     * @returns {void}
     */
    windowPickerIconDisable()
    {
        this.UIStyleClassAdd(this.#getAPIClassname('no-window-picker-icon'));
    }

    /**
     * show power icon
     *
     * @returns {void}
     */
    powerIconShow()
    {
        this.UIStyleClassRemove(this.#getAPIClassname('no-power-icon'));
    }

    /**
     * hide power icon
     *
     * @returns {void}
     */
    powerIconHide()
    {
        this.UIStyleClassAdd(this.#getAPIClassname('no-power-icon'));
    }

    /**
     * get primary monitor information
     *
     * @returns {false|Object} false when monitor does not exist | object
     *  x: int
     *  y: int
     *  width: int
     *  height: int
     *  geometryScale: float
     */
    monitorGetInfo()
    {
        let pMonitor = this._main.layoutManager.primaryMonitor;

        if (!pMonitor) {
            return false;
        }

        return {
            'x': pMonitor.x,
            'y': pMonitor.y,
            'width': pMonitor.width,
            'height': pMonitor.height,
            'geometryScale': pMonitor.geometry_scale,
        };
    }

    /**
     * get panel position
     *
     * @returns {number} see PANEL_POSITION
     */
    panelGetPosition()
    {
        if (this._panelPosition === undefined) {
            return PANEL_POSITION.TOP;
        }

        return this._panelPosition;
    }

    /**
     * move panel position
     *
     * @param {number} position see PANEL_POSITION
     * @param {boolean} force allow to set even when the current position
     *   is the same
     *
     * @returns {void}
     */
    panelSetPosition(position, force = false)
    {
        let monitorInfo = this.monitorGetInfo();
        let panelBox = this._main.layoutManager.panelBox;

        if (!force && position === this.panelGetPosition()) {
            return;
        }

        if (position === PANEL_POSITION.TOP) {
            this._panelPosition = PANEL_POSITION.TOP;
            if (this._workareasChangedSignal) {
                global.display.disconnect(this._workareasChangedSignal);
                this._workareasChangedSignal = null;
            }
            if (this._panelHeightSignal) {
                panelBox.disconnect(this._panelHeightSignal);
                this._panelHeightSignal = null;
            }
            let topX = (monitorInfo) ? monitorInfo.x : 0;
            let topY = (monitorInfo) ? monitorInfo.y : 0;
            panelBox.set_position(topX, topY);
            this.UIStyleClassRemove(this.#getAPIClassname('bottom-panel'));
            this.#fixPanelMenuSide(this._st.Side.TOP);
            return;
        }

        this._panelPosition = PANEL_POSITION.BOTTOM;

        // only change it when a monitor detected
        // 'workareas-changed' signal will do the job on next monitor detection
        if (monitorInfo) {
            let BottomX = monitorInfo.x;
            let BottomY = monitorInfo.y + monitorInfo.height - this.panelGetSize();

            panelBox.set_position(BottomX, BottomY);
            this.UIStyleClassAdd(this.#getAPIClassname('bottom-panel'));
        }

        if (!this._workareasChangedSignal) {
            this._workareasChangedSignal
            = global.display.connect('workareas-changed', () => {
                this.panelSetPosition(PANEL_POSITION.BOTTOM, true);
            });
        }

        if (!this._panelHeightSignal) {
            this._panelHeightSignal = panelBox.connect('notify::height', () => {
                this.panelSetPosition(PANEL_POSITION.BOTTOM, true);
            });
        }

        this.#fixPanelMenuSide(this._st.Side.BOTTOM);
    }

    /**
     * fix panel menu opening side based on panel position
     *
     * @param {number} position St.Side value
     *   is the same
     *
     * @returns {void}
     */
    #fixPanelMenuSide(position)
    {
        let PanelMenuButton = this._panelMenu.Button;
        let PanelMenuButtonProto = PanelMenuButton.prototype;

        // Set Instances
        let findPanelMenus = (widget) => {
            if (widget instanceof PanelMenuButton && widget.menu?._boxPointer) {
                widget.menu._boxPointer._userArrowSide = position;
            }
            widget.get_children().forEach(subWidget => {
                findPanelMenus(subWidget)
            });
        }

        let panelBoxes = [
            this._main.panel._centerBox,
            this._main.panel._rightBox,
            this._main.panel._leftBox,
        ];
        panelBoxes.forEach(panelBox => findPanelMenus(panelBox));

        // Set Prototypes
        if (position === this._st.Side.TOP) {
            // reset to default since GNOME Shell panel is top by default
            this.#uninject('panelMenuButtonSetMenu');
            return;
        }

        this.#inject('panelMenuButtonSetMenu', PanelMenuButtonProto, 'setMenu', original => function (menu) {
            original.call(this, menu);
            if (menu) {
                menu._boxPointer._userArrowSide = position;
            }
        });
    }

    /**
     * enable panel notification icon
     *
     * @returns {void}
     */
    panelNotificationIconEnable()
    {
        this.UIStyleClassRemove(this.#getAPIClassname('no-panel-notification-icon'));
    }

    /**
     * disable panel notification icon
     *
     * @returns {void}
     */
    panelNotificationIconDisable()
    {
        this.UIStyleClassAdd(this.#getAPIClassname('no-panel-notification-icon'));
    }

    /**
     * disconnect all clock menu position signals
     *
     * @returns {void}
     */
    #disconnectClockMenuPositionSignals()
    {
        let panelBoxes = [
            this._main.panel._centerBox,
            this._main.panel._rightBox,
            this._main.panel._leftBox,
        ];

        if (this._clockMenuPositionSignals) {
            for (let i = 0; i <= 2; i++) {
                panelBoxes[i].disconnect(this._clockMenuPositionSignals[i]);
            }
            delete(this._clockMenuPositionSignals);
        }
    }

    /**
     * set the clock menu position to default
     *
     * @returns {void}
     */
    clockMenuPositionSetDefault()
    {
        this.clockMenuPositionSet(0, 0);
        this.#disconnectClockMenuPositionSignals();
    }

    /**
     * set the clock menu position
     *
     * @param {number} pos see PANEL_BOX_POSITION
     * @param {number} offset starts from 0
     *
     * @returns {void}
     */
    clockMenuPositionSet(pos, offset)
    {
        let dateMenu = this._main.panel.statusArea.dateMenu;

        let panelBoxes = [
            this._main.panel._centerBox,
            this._main.panel._rightBox,
            this._main.panel._leftBox,
        ];

        this.#disconnectClockMenuPositionSignals();

        let fromPos = -1;
        let fromIndex = -1;
        let toIndex = -1;
        let childLength = 0;
        for (let i = 0; i <= 2; i++) {
            let child = panelBoxes[i].get_children();
            let childIndex = child.indexOf(dateMenu.container);
            if (childIndex !== -1) {
                fromPos = i;
                fromIndex = childIndex;
                childLength = panelBoxes[pos].get_children().length;
                toIndex = (offset > childLength) ? childLength : offset;
                break;
            }
        }

        // couldn't find the from and to position because it has been removed
        if (fromPos === -1 || fromIndex === -1 || toIndex === -1) {
            return;
        }

        if (pos === fromPos && toIndex === fromIndex) {
            return;
        }

        panelBoxes[fromPos].remove_child(dateMenu.container);
        panelBoxes[pos].insert_child_at_index(dateMenu.container, toIndex);

        if (this.isLocked()) {
            this.dateMenuHide();
        }

        if (!this._clockMenuPositionSignals) {
            this._clockMenuPositionSignals = [null, null, null];
            for (let i = 0; i <= 2; i++) {
                this._clockMenuPositionSignals[i] = panelBoxes[i].connect(
                    (this.#shellVersion >= 46) ? 'child-added' : 'actor-added',
                    () => {
                        this.clockMenuPositionSet(pos, offset);
                    }
                );
            }
        }
    }

    /**
     * enable show apps button
     *
     * @returns {void}
     */
    showAppsButtonEnable()
    {
        this.UIStyleClassRemove(this.#getAPIClassname('no-show-apps-button'));
    }

    /**
     * disable show apps button
     *
     * @returns {void}
     */
    showAppsButtonDisable()
    {
        this.UIStyleClassAdd(this.#getAPIClassname('no-show-apps-button'));
    }

    /**
     * set animation speed as default
     *
     * @returns {void}
     */
    animationSpeedSetDefault()
    {
        if (this.#originals['StSlowDownFactor'] === undefined) {
            return;
        }

        this._st.Settings.get().slow_down_factor = this.#originals['StSlowDownFactor'];
    }

    /**
     * change animation speed
     *
     * @param {number} factor in float. bigger number means slower
     *
     * @returns {void}
     */
    animationSpeedSet(factor)
    {
        if (this.#originals['StSlowDownFactor'] === undefined) {
            this.#originals['StSlowDownFactor']
            = this._st.Settings.get().slow_down_factor;
        }

        this._st.Settings.get().slow_down_factor = factor;
    }

    /**
     * set the enable animation as default
     *
     * @returns {void}
     */
    enableAnimationsSetDefault()
    {
        if (this.#originals['enableAnimations'] === undefined) {
            return;
        }

        let status = this.#originals['enableAnimations'];

        this._interfaceSettings.set_boolean('enable-animations', status);
    }

    /**
     * set the enable animation status
     *
     * @param {boolean} status true to enable, false otherwise
     *
     * @returns {void}
     */
    enableAnimationsSet(status)
    {
        if (this.#originals['enableAnimations'] ===  undefined) {
            this.#originals['enableAnimations']
            = this._interfaceSettings.get_boolean('enable-animations');
        }

        this._interfaceSettings.set_boolean('enable-animations', status);
    }

    /**
     * enable focus when window demands attention happens
     *
     * @returns {void}
     */
    windowDemandsAttentionFocusEnable()
    {
        if (
            this._displayWindowDemandsAttentionSignal ||
            this._displayWindowMarkedUrgentSignal
        ) {
            return;
        }

        let display = global.display;

        let demandFunction = (display, window) => {
            if (!window || window.has_focus() || window.is_skip_taskbar()) {
                return;
            }
            this._main.activateWindow(window);
        };

        this._displayWindowDemandsAttentionSignal
        = display.connect('window-demands-attention', demandFunction);
        this._displayWindowMarkedUrgentSignal
        = display.connect('window-marked-urgent', demandFunction);

        // since removing '_windowDemandsAttentionId' doesn't have any effect
        // we remove the original signal and re-connect it on disable
        let signalId = this.#getSignalId(global.display, 'window-demands-attention');
        let signalId2 = this.#getSignalId(global.display, 'window-marked-urgent');
        display.disconnect(signalId);
        display.disconnect(signalId2);
    }

    /**
     * disable focus when window demands attention happens
     *
     * @returns {void}
     */
    windowDemandsAttentionFocusDisable()
    {
        if (
            !this._displayWindowDemandsAttentionSignal ||
            !this._displayWindowMarkedUrgentSignal
        ) {
            return;
        }

        let display = global.display;

        display.disconnect(this._displayWindowDemandsAttentionSignal);
        display.disconnect(this._displayWindowMarkedUrgentSignal);
        this._displayWindowDemandsAttentionSignal = null;
        this._displayWindowMarkedUrgentSignal = null;

        let wah = this._main.windowAttentionHandler;
        wah._windowDemandsAttentionId = display.connect(
            'window-demands-attention',
            wah._onWindowDemandsAttention.bind(wah)
        );
        wah._windowDemandsAttentionId = display.connect(
            'window-marked-urgent',
            wah._onWindowDemandsAttention.bind(wah)
        );
    }

    /**
     * enable maximizing windows on creation
     *
     * @returns {void}
     */
    windowMaximizedOnCreateEnable()
    {
        if (this._displayWindowCreatedSignal) {
            return;
        }

        this._displayWindowCreatedSignal = global.display.connect(
            'window-created',
            (display, window) => {
                if (!window.can_maximize()) {
                    return;
                }
                if (this.#shellVersion >= 49) {
                    window.maximize();
                } else {
                    window.maximize(this._meta.MaximizeFlags.HORIZONTAL | this._meta.MaximizeFlags.VERTICAL);
                }
            }
        );
    }

    /**
     * disable maximizing windows on creation
     *
     * @returns {void}
     */
    windowMaximizedOnCreateDisable()
    {
        if (!this._displayWindowCreatedSignal) {
            return;
        }

        global.display.disconnect(this._displayWindowCreatedSignal);
        delete(this._displayWindowCreatedSignal);
    }

    /**
     * set startup status
     *
     * @param {number} status see SHELL_STATUS for available status
     *
     * @returns {void}
     */
    startupStatusSet(status)
    {
        let sessionMode = this._main.sessionMode;
        let layoutManager = this._main.layoutManager;

        if (!layoutManager._startingUp) {
            return;
        }

        if (this.#originals['sessionModeHasOverview'] === undefined) {
            this.#originals['sessionModeHasOverview'] = sessionMode.hasOverview;
        }

        let ControlsState = this._overviewControls.ControlsState;
        let Controls = this._main.overview._overview.controls;

        switch (status) {

            case SHELL_STATUS.NONE:
                sessionMode.hasOverview = false;
                layoutManager.startInOverview = false;
                Controls._stateAdjustment.value = ControlsState.HIDDEN;
                break;

            case SHELL_STATUS.OVERVIEW:
            default:
                sessionMode.hasOverview = true;
                layoutManager.startInOverview = true;
                break;
        }

        if (!this._startupCompleteSignal) {
            this._startupCompleteSignal
            = layoutManager.connect('startup-complete', () => {
                sessionMode.hasOverview = this.#originals['sessionModeHasOverview'];
            });
        }
    }

    /**
     * set startup status to default
     *
     * @returns {void}
     */
    startupStatusSetDefault()
    {
        if (this.#originals['sessionModeHasOverview'] === undefined) {
            return;
        }

        if (this._startupCompleteSignal) {
            this._main.layoutManager.disconnect(this._startupCompleteSignal);
        }
    }

    /**
     * set dash icon size to default
     *
     * @returns {void}
     */
    dashIconSizeSetDefault()
    {
        let classnameStarter = this.#getAPIClassname('dash-icon-size');

        DASH_ICON_SIZES.forEach(size => {
            this.UIStyleClassRemove(classnameStarter + size);
        });
    }

    /**
     * set dash icon size
     *
     * @param {number} size in pixels
     *   see DASH_ICON_SIZES for available sizes
     *
     * @returns {void}
     */
    dashIconSizeSet(size)
    {
        this.dashIconSizeSetDefault();

        if (!DASH_ICON_SIZES.includes(size)) {
            return;
        }

        let classnameStarter = this.#getAPIClassname('dash-icon-size');

        this.UIStyleClassAdd(classnameStarter + size);
    }

    /**
     * change ControlsManagerLayout._computeWorkspacesBoxForState
     * base on the current state
     *
     * @returns {void}
     */
    #computeWorkspacesBoxForStateChanged()
    {
        let controlsLayout = this._main.overview._overview._controls.layout_manager;

        this.#inject('computeWorkspacesBoxForState', controlsLayout, '_computeWorkspacesBoxForState', original => (state, box, searchHeight, ...args) => {

            let inAppGrid = state === this._overviewControls.ControlsState.APP_GRID;

            if (inAppGrid && !this._searchEntryVisibility) {
                // We need some spacing on top of workspace box in app grid
                // when the search entry is not visible.
                searchHeight = 40;
            }

            box = original.call(
                controlsLayout, state, box, searchHeight, ...args);

            if (inAppGrid && this._workspacesInAppGridHeight !== undefined) {
                box.set_size(
                    box.get_width(),
                    this._workspacesInAppGridHeight
                );
            }

            return box;
        });

        // Since workspace background has shadow around it, it can cause
        // unwanted shadows in app grid when the workspace height is 0.
        // so we are removing the shadow when we are in app grid
        // but first, we need to remove the already connected signals
        // since this function can be called in different situations
        // (ie. workspace app grid, search visibility)
        let showAppsButton = this._main.overview.dash.showAppsButton;
        let classname = this.#getAPIClassname('no-workspaces-in-app-grid');
        if (this._appButtonForComputeWorkspacesSignal) {
            showAppsButton.disconnect(this._appButtonForComputeWorkspacesSignal);
            this.UIStyleClassRemove(classname);
        }

        if (!this.#isWorkspacesInAppGridEnabled()) {
            this._appButtonForComputeWorkspacesSignal =
            showAppsButton.connect(
                'notify::checked',
                () => {
                    if (showAppsButton.checked) {
                        this.UIStyleClassAdd(classname);
                    } else {
                        this.UIStyleClassRemove(classname);
                    }
                }
            );
        }
    }

    /**
     * change ControlsManagerLayout._computeWorkspacesBoxForState to its default
     *
     * @returns {void}
     */
    #computeWorkspacesBoxForStateSetDefault()
    {
        if (!this.#uninject('computeWorkspacesBoxForState')) {
            return;
        }

        if (this._appButtonForComputeWorkspacesSignal) {
            let showAppsButton = this._main.overview.dash.showAppsButton;
            showAppsButton.disconnect(this._appButtonForComputeWorkspacesSignal);
            delete(this._appButtonForComputeWorkspacesSignal);
            this.UIStyleClassRemove(this.#getAPIClassname('no-workspaces-in-app-grid'));
        }
    }

    /**
     * disable workspaces in app grid
     *
     * @returns {void}
     */
    workspacesInAppGridDisable()
    {
        this._workspacesInAppGridHeight = 0;

        this._workspacesInAppGrid = false;

        this.#computeWorkspacesBoxForStateChanged();
    }

    /**
     * enable workspaces in app grid
     *
     * @returns {void}
     */
    workspacesInAppGridEnable()
    {
        if (this._workspacesInAppGridHeight === undefined) {
            return;
        }

        this._workspacesInAppGrid = true;

        delete(this._workspacesInAppGridHeight);
        this.#computeWorkspacesBoxForStateChanged();
    }

    /**
     * check whether the workspaces in app grid is enabled
     *
     * @returns {boolean}
     */
    #isWorkspacesInAppGridEnabled()
    {
        return this._workspacesInAppGrid === undefined || this._workspacesInAppGrid;
    }

    /**
     * change notification banner position
     *
     * @param {number} pos
     *   see XY_POSITION for available positions
     *
     * @returns {void}
     */
    notificationBannerPositionSet(pos)
    {
        let messageTray = this._main.messageTray;
        let bannerBin = messageTray._bannerBin;

        if (this.#originals['bannerAlignmentX'] === undefined) {
            this.#originals['bannerAlignmentX'] = messageTray.bannerAlignment;
        }

        if (this.#originals['bannerAlignmentY'] === undefined) {
            this.#originals['bannerAlignmentY'] = bannerBin.get_y_align();
        }

        // TOP
        this.#uninject('messageTrayHideNotification');

        bannerBin.set_y_align(this._clutter.ActorAlign.START);

        if (pos === XY_POSITION.TOP_START) {
            messageTray.bannerAlignment = this._clutter.ActorAlign.START;
            return;
        }

        if (pos === XY_POSITION.TOP_END) {
            messageTray.bannerAlignment = this._clutter.ActorAlign.END;
            return;
        }

        if (pos === XY_POSITION.TOP_CENTER) {
            messageTray.bannerAlignment = this._clutter.ActorAlign.CENTER;
            return;
        }

        // BOTTOM

        // >>
        // This block is going to fix the animation when the notification is
        // in bottom area
        // this is the same function from (ui.messageTray.messageTray._hideNotification)
        // with clutter animation mode set to EASE.
        // because the EASE_OUT_BACK (original code) causes glitch when
        // the tray is on bottom
        const State = this._messageTray.State;
        const ANIMATION_TIME = this._messageTray.ANIMATION_TIME;
        const Clutter = this._clutter;

        this.#inject('messageTrayHideNotification', messageTray, '_hideNotification', () => function (animate) {
            this._notificationFocusGrabber.ungrabFocus();
            this._banner.disconnectObject(this);
            this._resetNotificationLeftTimeout();
            this._bannerBin.remove_all_transitions();

            if (animate) {
                this._notificationState = State.HIDING;
                this._bannerBin.ease({
                    opacity: 0,
                    duration: ANIMATION_TIME,
                    mode: Clutter.AnimationMode.EASE,
                });
                this._bannerBin.ease({
                    opacity: 0,
                    y: this._bannerBin.height,
                    duration: ANIMATION_TIME,
                    mode: Clutter.AnimationMode.EASE,
                    onComplete: () => {
                        this._notificationState = State.HIDDEN;
                        this._hideNotificationCompleted();
                        this._updateState();
                    },
                });
            } else {
                this._bannerBin.y = this._bannerBin.height;
                this._bannerBin.opacity = 0;
                this._notificationState = State.HIDDEN;
                this._hideNotificationCompleted();
            }
        });
        // <<

        bannerBin.set_y_align(this._clutter.ActorAlign.END);

        if (pos === XY_POSITION.BOTTOM_START) {
            messageTray.bannerAlignment = this._clutter.ActorAlign.START;
            return;
        }

        if (pos === XY_POSITION.BOTTOM_END) {
            messageTray.bannerAlignment = this._clutter.ActorAlign.END;
            return;
        }

        if (pos === XY_POSITION.BOTTOM_CENTER) {
            messageTray.bannerAlignment = this._clutter.ActorAlign.CENTER;
            return;
        }
    }

    /**
     * set notification banner position to default position
     *
     * @returns {void}
     */
    notificationBannerPositionSetDefault()
    {
        if (this.#originals['bannerAlignmentX'] === undefined ||
            this.#originals['bannerAlignmentY'] === undefined
        ) {
            return;
        }

        let messageTray = this._main.messageTray;
        let bannerBin = messageTray._bannerBin;

        messageTray.bannerAlignment = this.#originals['bannerAlignmentX'];
        bannerBin.set_y_align(this.#originals['bannerAlignmentY']);
        this.#uninject('messageTrayHideNotification');
    }

    /**
     * set the workspace switcher to always/never show
     *
     * @param {boolean} show true for always show, false for never show
     * @param {boolean} fake true means set the current should show status
     *
     * @returns {void}
     */
    workspaceSwitcherShouldShow(shouldShow = true, fake = false)
    {
        if (!fake) {
            this._shouldShow = shouldShow;
        }

        if (!this.isWorkspaceSwitcherVisible()) {
            return;
        }

        let ThumbnailsBoxProto = this._workspaceThumbnail.ThumbnailsBox.prototype;

        this.#inject('thumbnailsBoxUpdateShouldShow', ThumbnailsBoxProto, '_updateShouldShow', () => function () {
            if (this._shouldShow === shouldShow) {
                return;
            }
            this._shouldShow = shouldShow;
            this.notify('should-show');
        });
    }

    /**
     * set the always show workspace switcher status to last real status
     *
     * @returns {void}
     */
    #workspaceSwitcherShouldShowSetToLast()
    {
        if (this._shouldShow === undefined) {
            this.workspaceSwitcherShouldShowSetDefault();
            return;
        }

        this.workspaceSwitcherShouldShow(this._shouldShow);
    }

    /**
     * set the always show workspace switcher status to default
     *
     * @returns {void}
     */
    workspaceSwitcherShouldShowSetDefault()
    {
        if (!this.#isInjected('thumbnailsBoxUpdateShouldShow') || !this.isWorkspaceSwitcherVisible()) {
            return;
        }

        this.#uninject('thumbnailsBoxUpdateShouldShow');
        delete(this._shouldShow);
    }

    /**
     * set panel button hpadding to default
     *
     * @returns {void}
     */
    panelButtonHpaddingSetDefault()
    {
        if (this._panelButtonHpaddingSize === undefined) {
            return;
        }

        let classnameStarter = this.#getAPIClassname('panel-button-padding-size');
        this.UIStyleClassRemove(classnameStarter + this._panelButtonHpaddingSize);
        this.#emitRefreshStyles();

        delete this._panelButtonHpaddingSize;
    }

    /**
     * set panel button hpadding size
     *
     * @param {number} size in pixels (0 - 60)
     *
     * @returns {void}
     */
    panelButtonHpaddingSizeSet(size)
    {
        this.panelButtonHpaddingSetDefault();

        if (size < 0 || size > 60) {
            return;
        }

        this._panelButtonHpaddingSize = size;

        let classnameStarter = this.#getAPIClassname('panel-button-padding-size');
        this.UIStyleClassAdd(classnameStarter + size);
        this.#emitRefreshStyles();
    }

    /**
     * set panel indicator padding to default
     *
     * @returns {void}
     */
    panelIndicatorPaddingSetDefault()
    {
        if (this._panelIndicatorPaddingSize === undefined) {
            return;
        }

        let classnameStarter = this.#getAPIClassname('panel-indicator-padding-size');
        this.UIStyleClassRemove(classnameStarter + this._panelIndicatorPaddingSize);
        this.#emitRefreshStyles();

        delete this._panelIndicatorPaddingSize;
    }

    /**
     * set panel indicator padding size
     *
     * @param {number} size in pixels (0 - 60)
     *
     * @returns {void}
     */
    panelIndicatorPaddingSizeSet(size)
    {
        this.panelIndicatorPaddingSetDefault();

        if (size < 0 || size > 60) {
            return;
        }

        this._panelIndicatorPaddingSize = size;

        let classnameStarter = this.#getAPIClassname('panel-indicator-padding-size');
        this.UIStyleClassAdd(classnameStarter + size);
        this.#emitRefreshStyles();
    }

    /**
     * get window preview prototype
     *
     * @returns {Object}
     */
    #windowPreviewGetPrototype()
    {
        return this._windowPreview.WindowPreview.prototype;
    }

    /**
     * enable window preview caption
     *
     * @returns {void}
     */
    windowPreviewCaptionEnable()
    {
        if (!this.#uninject('windowPreviewGetCaption')) {
            return;
        }

        this.UIStyleClassRemove(this.#getAPIClassname('no-window-caption'));
    }

    /**
     * disable window preview caption
     *
     * @returns {void}
     */
    windowPreviewCaptionDisable()
    {
        let windowPreviewProto = this.#windowPreviewGetPrototype();

        this.#inject('windowPreviewGetCaption', windowPreviewProto, '_getCaption', () => function () {
            return '';
        });

        this.UIStyleClassAdd(this.#getAPIClassname('no-window-caption'));
    }

    /**
     * set workspace background border radius to default size
     *
     * @returns {void}
     */
    workspaceBackgroundRadiusSetDefault()
    {
        if (this._workspaceBackgroundRadiusSize === undefined) {
            return;
        }

        this.#uninject('workspaceBackgroundUpdateBorderRadius');

        let classnameStarter = this.#getAPIClassname('workspace-background-radius-size');
        this.UIStyleClassRemove(classnameStarter + this._workspaceBackgroundRadiusSize);

        delete this._workspaceBackgroundRadiusSize;
    }

    /**
     * set workspace background border radius size
     *
     * @param {number} size in pixels (0 - 60)
     *
     * @returns {void}
     */
    workspaceBackgroundRadiusSet(size)
    {
        if (size < 0 || size > 60) {
            return;
        }

        this.workspaceBackgroundRadiusSetDefault();

        let workspaceBackgroundProto = this._workspace.WorkspaceBackground.prototype;

        const Util = this._util;
        const St = this._st;

        this.#inject('workspaceBackgroundUpdateBorderRadius', workspaceBackgroundProto, '_updateBorderRadius', () => function () {
            const {scaleFactor} = St.ThemeContext.get_for_stage(global.stage);
            const cornerRadius = scaleFactor * size;

            const backgroundContent = this._bgManager.backgroundActor.content;
            backgroundContent.rounded_clip_radius =
                Util.lerp(0, cornerRadius, this._stateAdjustment.value);
        });

        this._workspaceBackgroundRadiusSize = size;

        let classnameStarter = this.#getAPIClassname('workspace-background-radius-size');
        this.UIStyleClassAdd(classnameStarter + size);
    }

    /**
     * enable workspace wraparound
     *
     * @returns {void}
     */
    workspaceWraparoundEnable()
    {
        let metaWorkspaceProto = this._meta.Workspace.prototype;

        const Meta = this._meta;

        this.#inject('metaWorkspaceGetNeighbor', metaWorkspaceProto, 'get_neighbor', () => function (dir) {

            let index = this.index();
            let lastIndex = global.workspace_manager.n_workspaces - 1;
            let neighborIndex;

            if (dir === Meta.MotionDirection.UP || dir === Meta.MotionDirection.LEFT) {
                // prev
                neighborIndex = (index > 0) ? index - 1 : lastIndex;
            } else {
                // next
                neighborIndex = (index < lastIndex) ? index + 1 : 0;
            }

            return global.workspace_manager.get_workspace_by_index(neighborIndex);
        });
    }

    /**
     * disable workspace wraparound
     *
     * @returns {void}
     */
    workspaceWraparoundDisable()
    {
        this.#uninject('metaWorkspaceGetNeighbor');
    }

    /**
     * enable window preview close button
     *
     * @returns {void}
     */
    windowPreviewCloseButtonEnable()
    {
        this.UIStyleClassRemove(this.#getAPIClassname('no-window-close'));
    }

    /**
     * disable window preview close button
     *
     * @returns {void}
     */
    windowPreviewCloseButtonDisable()
    {
        this.UIStyleClassAdd(this.#getAPIClassname('no-window-close'));
    }

    /**
     * enable ripple box
     *
     * @returns {void}
     */
    rippleBoxEnable()
    {
        this.UIStyleClassRemove(this.#getAPIClassname('no-ripple-box'));
    }

    /**
     * disable ripple box
     *
     * @returns {void}
     */
    rippleBoxDisable()
    {
        this.UIStyleClassAdd(this.#getAPIClassname('no-ripple-box'));
    }

    /**
     * unblock overlay key
     *
     * @returns {void}
     */
    unblockOverlayKey()
    {
        if (!this._overlayKeyOldSignalId) {
            return;
        }

        this._gobject.signal_handler_unblock(
            global.display,
            this._overlayKeyOldSignalId
        );

        delete(this._overlayKeyOldSignalId);
    }

    /**
     * block overlay key
     *
     * @returns {void}
     */
    blockOverlayKey()
    {
        this._overlayKeyOldSignalId = this.#getSignalId(global.display, 'overlay-key');

        if (!this._overlayKeyOldSignalId) {
            return;
        }

        this._gobject.signal_handler_block(global.display, this._overlayKeyOldSignalId);
    }

    /**
     * enable double super press to toggle app grid
     *
     * @returns {void}
     */
    doubleSuperToAppGridEnable()
    {
        if (this._isDoubleSuperToAppGrid === true) {
            return;
        }

        if (!this._overlayKeyNewSignalId) {
            return;
        }

        global.display.disconnect(this._overlayKeyNewSignalId);
        delete(this._overlayKeyNewSignalId);
        this.unblockOverlayKey();

        this._isDoubleSuperToAppGrid = true;
    }

    /**
     * disable double super press to toggle app grid
     *
     * @returns {void}
     */
    doubleSuperToAppGridDisable()
    {
        if (this._isDoubleSuperToAppGrid === false) {
            return;
        }

        this.blockOverlayKey();

        this._overlayKeyNewSignalId = global.display.connect('overlay-key', () => {
            this._main.overview.toggle();
        });

        this._isDoubleSuperToAppGrid = false;
    }

    /**
     * disable the removal of switcher popup delay
     *
     * @returns {void}
     */
    switcherPopupDelaySetDefault()
    {
        this.#uninject('switcherPopupShow');
    }

    /**
     * enable the removal of switcher popup delay
     *
     * @returns {void}
     */
    removeSwitcherPopupDelay()
    {
        let SwitcherPopupProto = this._switcherPopup.SwitcherPopup.prototype;

        this.#inject('switcherPopupShow', SwitcherPopupProto, 'show', original => function (...args) {
            let res = original.apply(this, args);
            if (res) {
                this._showImmediately();
            }
            return res;
        });
    }

    /**
     * set default OSD position
     *
     * @returns {void}
     */
    osdPositionSetDefault()
    {
        if (!this.#uninject('osdWindowShow')) {
            return;
        }

        if (
            this.#originals['osdWindowXAlign'] !== undefined &&
            this.#originals['osdWindowYAlign'] !== undefined
        ) {
            let osdWindows = this._main.osdWindowManager._osdWindows;
            osdWindows.forEach(osdWindow => {
                osdWindow.x_align = this.#originals['osdWindowXAlign'];
                osdWindow.y_align = this.#originals['osdWindowYAlign'];
            });
            delete(this.#originals['osdWindowXAlign']);
            delete(this.#originals['osdWindowYAlign']);
        }

        this.UIStyleClassRemove(this.#getAPIClassname('osd-position-top'));
        this.UIStyleClassRemove(this.#getAPIClassname('osd-position-bottom'));
        this.UIStyleClassRemove(this.#getAPIClassname('osd-position-center'));
    }

    /**
     * set OSD position
     *
     * @param int pos position XY_POSITION
     *
     * @returns {void}
     */
    osdPositionSet(pos)
    {
        let osdWindowProto = this._osdWindow.OsdWindow.prototype;

        if (
            this.#originals['osdWindowXAlign'] === undefined ||
            this.#originals['osdWindowYAlign'] === undefined
        ) {
            let osdWindows = this._main.osdWindowManager._osdWindows;
            this.#originals['osdWindowXAlign'] = osdWindows[0].x_align;
            this.#originals['osdWindowYAlign'] = osdWindows[0].y_align;
        }

        let [xAlign, yAlign] = this.#xyAlignGet(pos);
        this.#inject('osdWindowShow', osdWindowProto, 'show', original => function () {
            this.x_align = xAlign;
            this.y_align = yAlign;
            original.call(this);
        });

        if (
            pos === XY_POSITION.TOP_START ||
            pos === XY_POSITION.TOP_CENTER ||
            pos === XY_POSITION.TOP_END
        ) {
            this.UIStyleClassAdd(this.#getAPIClassname('osd-position-top'));
        }

        if (
            pos === XY_POSITION.BOTTOM_START ||
            pos === XY_POSITION.BOTTOM_CENTER ||
            pos === XY_POSITION.BOTTOM_END
        ) {
            this.UIStyleClassAdd(this.#getAPIClassname('osd-position-bottom'));
        }

        if (
            pos === XY_POSITION.CENTER_START ||
            pos === XY_POSITION.CENTER_CENTER ||
            pos === XY_POSITION.CENTER_END
        ) {
            this.UIStyleClassAdd(this.#getAPIClassname('osd-position-center'));
        }
    }

    /**
     * revert the calendar items position to default
     *
     * @returns {void}
     */
    revertCalendarColumnItemsToDefault()
    {
        if (!this._isCalendarColumnInverted) {
            return;
        }

        let dateMenu = this._main.panel.statusArea.dateMenu;
        let calendar = dateMenu._calendar;
        let date = dateMenu._date;
        let eventsItem = dateMenu._eventsItem;
        let clocksItem = dateMenu._clocksItem;
        let weatherItem = dateMenu._weatherItem;

        let displayBox = eventsItem.get_parent();
        if (displayBox) {
            displayBox.remove_child(eventsItem);
            displayBox.remove_child(clocksItem);
            displayBox.remove_child(weatherItem);
            displayBox.insert_child_at_index(eventsItem, 1);
            displayBox.insert_child_at_index(clocksItem, 2);
            displayBox.insert_child_at_index(weatherItem, 3);
        }

        let calendarBox = calendar.get_parent();
        if (calendarBox) {
            calendarBox.remove_child(date);
            calendarBox.remove_child(calendar);
            calendarBox.insert_child_at_index(date, 0);
            calendarBox.insert_child_at_index(calendar, 1);
        }

        this._isCalendarColumnInverted = false;
    }

    /**
     * invert the position of calendar column items
     *
     * @returns {void}
     */
    invertCalendarColumnItems()
    {
        if (this._isCalendarColumnInverted) {
            return;
        }

        let dateMenu = this._main.panel.statusArea.dateMenu;
        let calendar = dateMenu._calendar;
        let date = dateMenu._date;
        let eventsItem = dateMenu._eventsItem;
        let clocksItem = dateMenu._clocksItem;
        let weatherItem = dateMenu._weatherItem;

        let displayBox = eventsItem.get_parent();
        if (displayBox) {
            displayBox.remove_child(clocksItem);
            displayBox.remove_child(eventsItem);
            displayBox.remove_child(weatherItem);
            displayBox.insert_child_at_index(weatherItem, 1);
            displayBox.insert_child_at_index(clocksItem, 2);
            displayBox.insert_child_at_index(eventsItem, 3);
        }

        let calendarBox = calendar.get_parent();
        if (calendarBox) {
            calendarBox.remove_child(calendar);
            calendarBox.remove_child(date);
            calendarBox.insert_child_at_index(calendar, 1);
            calendarBox.insert_child_at_index(date, 2);
        }

        this._isCalendarColumnInverted = true;
    }

    /**
     * show weather in date menu
     *
     * @returns {void}
     */
    weatherShow()
    {
        this.UIStyleClassRemove(this.#getAPIClassname('no-weather'));
    }

    /**
     * hide weather in date menu
     *
     * @returns {void}
     */
    weatherHide()
    {
        this.UIStyleClassAdd(this.#getAPIClassname('no-weather'));
    }

    /**
     * show world clocks in date menu
     *
     * @returns {void}
     */
    worldClocksShow()
    {
        if (!this.#uninject('clocksItemSync')) {
            return;
        }

        let clocksItem = this._main.panel.statusArea.dateMenu._clocksItem;

        if (this._clocksItemShowSignal) {
            clocksItem.disconnect(this._clocksItemShowSignal);
            delete(this._clocksItemShowSignal);
        }

        clocksItem._sync();
    }

    /**
     * hide world clocks in date menu
     *
     * @returns {void}
     */
    worldClocksHide()
    {
        let clocksItem = this._main.panel.statusArea.dateMenu._clocksItem;

        this.#inject('clocksItemSync', clocksItem, '_sync', () => function () {
            this.visible = false;
        });

        if (!this._clocksItemShowSignal) {
            this._clocksItemShowSignal = clocksItem.connect('show', () => {
                clocksItem._sync();
            });
        }

        clocksItem._sync();
    }

    /**
     * show events button in date menu
     *
     * @returns {void}
     */
    eventsButtonShow()
    {
        this.UIStyleClassRemove(this.#getAPIClassname('no-events-button'));
    }

    /**
     * hide events button in date menu
     *
     * @returns {void}
     */
    eventsButtonHide()
    {
        this.UIStyleClassAdd(this.#getAPIClassname('no-events-button'));
    }

    /**
     * show calendar in date menu
     *
     * @returns {void}
     */
    calendarShow()
    {
        this._main.panel.statusArea.dateMenu._calendar.show();
    }

    /**
     * hide calendar in date menu
     *
     * @returns {void}
     */
    calendarHide()
    {
        this._main.panel.statusArea.dateMenu._calendar.hide();
    }

    /**
     * set default panel icon size
     *
     * @returns {void}
     */
    panelIconSetDefaultSize()
    {
        if (this._panelIconSize === undefined || !this.#originals['panelIconSize']) {
            return;
        }

        let classnameStarter = this.#getAPIClassname('panel-icon-size');
        this.UIStyleClassRemove(classnameStarter + this._panelIconSize);
        this.#emitRefreshStyles();

        let defaultSize = this.#originals['panelIconSize'];
        this.#changeDateMenuIndicatorIconSize(defaultSize);

        delete(this._panelIconSize);
    }

    /**
     * set panel icon size
     *
     * @param {number} size 1-60
     *
     * @returns {void}
     */
    panelIconSetSize(size)
    {
        if (size < 1 || size > 60) {
            return;
        }

        if (!this.#originals['panelIconSize']) {
            this.#originals['panelIconSize'] = this._panel.PANEL_ICON_SIZE;
        }

        let classnameStarter = this.#getAPIClassname('panel-icon-size');
        this.UIStyleClassRemove(classnameStarter + this.panelIconGetSize());
        this.UIStyleClassAdd(classnameStarter + size);
        this.#emitRefreshStyles();

        this.#changeDateMenuIndicatorIconSize(size);

        this._panelIconSize = size;
    }

    /**
     * change date menu indicator icon size
     *
     * @param {number} size
     *
     * @returns {void}
     */
    #changeDateMenuIndicatorIconSize(size)
    {
        let dateMenu = this._main.panel.statusArea.dateMenu;

        // we get set_icon_size is not a function in some setups
        // in case the date menu has been removed or not created
        if (
            dateMenu &&
            dateMenu._indicator &&
            dateMenu._indicator.set_icon_size
        ) {
            dateMenu._indicator.set_icon_size(size);
        }
    }

    /**
     * get panel icon size
     *
     * @returns {void}
     */
    panelIconGetSize()
    {
        if (this._panelIconSize !== undefined) {
            return this._panelIconSize;
        }

        return this._panel.PANEL_ICON_SIZE;
    }

    /**
     * show dash separator
     *
     * @returns {void}
     */
    dashSeparatorShow()
    {
        this.UIStyleClassRemove(this.#getAPIClassname('no-dash-separator'));
    }

    /**
     * hide dash separator
     *
     * @returns {void}
     */
    dashSeparatorHide()
    {
        this.UIStyleClassAdd(this.#getAPIClassname('no-dash-separator'));
    }

    /**
     * show window menu
     *
     * @returns {void}
     */
    windowMenuShow()
    {
        this.#uninject('windowMenuManagerShowWindowMenuForWindow');
    }

    /**
     * hide window menu
     *
     * @returns {void}
     */
    windowMenuHide()
    {
        let WindowMenuManagerProto = this._windowMenu.WindowMenuManager.prototype;

        this.#inject('windowMenuManagerShowWindowMenuForWindow', WindowMenuManagerProto, 'showWindowMenuForWindow', () => function (window, _type, _rect) {
            window.focus(global.get_current_time());
            window.raise();
        });
    }

    /**
     * show screenshot in window menu
     *
     * @returns {void}
     */
    screenshotInWindowMenuShow()
    {
        this.#uninject('windowMenuBuildMenu');
    }

    /**
     * hide screenshot in window menu
     *
     * @returns {void}
     */
    screenshotInWindowMenuHide()
    {
        let windowMenuProto = this._windowMenu.WindowMenu.prototype;

        this.#inject('windowMenuBuildMenu', windowMenuProto, '_buildMenu', original => function (window) {
            original.call(this, window);
            this.firstMenuItem?.hide();
        });
    }

    /**
     * set all alt tab sizes to default
     *
     * @returns {void}
     */
    #altTabSizesSetDefault()
    {
        this.#uninject('altTabWindowIconInit');

        delete(this._altTabAPP_ICON_SIZE);
        delete(this._altTabAPP_ICON_SIZE_SMALL);
        delete(this._altTabWINDOW_PREVIEW_SIZE);
    }

    /**
     * set alt tab sizes
     *
     * @param {number|null} appIconSize
     * @param {number|null} appIconSizeSmall
     * @param {number|null} windowPreviewSize
     *
     * @returns {void}
     */
    #altTabSizesSet(appIconSize, appIconSizeSmall, windowPreviewSize)
    {
        let WindowIconProto = this._altTab.WindowIcon.prototype;

        this._altTabAPP_ICON_SIZE ||= this._altTab.APP_ICON_SIZE;
        this._altTabAPP_ICON_SIZE_SMALL ||= this._altTab.APP_ICON_SIZE_SMALL;
        this._altTabWINDOW_PREVIEW_SIZE ||= this._altTab.WINDOW_PREVIEW_SIZE;

        const APP_ICON_SIZE = appIconSize || this._altTabAPP_ICON_SIZE;
        const APP_ICON_SIZE_SMALL = appIconSizeSmall || this._altTabAPP_ICON_SIZE_SMALL;
        const WINDOW_PREVIEW_SIZE = windowPreviewSize || this._altTabWINDOW_PREVIEW_SIZE;

        this.#inject('altTabWindowIconInit', WindowIconProto, '_init', original => function (window, mode) {
            original.call(this, window, mode);
        });
    }

    /**
     * set default alt tab window preview size
     *
     * @returns {void}
     */
    altTabWindowPreviewSetDefaultSize()
    {
        if (!this.#originals['altTabWindowPreviewSize']) {
            return;
        }

        this.#altTabSizesSet(null, null, this.#originals['altTabWindowPreviewSize']);
    }

    /**
     * set alt tab window preview size
     *
     * @param {number} size 1-512
     *
     * @returns {void}
     */
    altTabWindowPreviewSetSize(size)
    {
        if (size < 1 || size > 512) {
            return;
        }

        if (!this.#originals['altTabWindowPreviewSize']) {
            this.#originals['altTabWindowPreviewSize'] = this._altTab.WINDOW_PREVIEW_SIZE;
        }

        this.#altTabSizesSet(null, null, size);
    }

    /**
     * set default alt tab small icon size
     *
     * @returns {void}
     */
    altTabSmallIconSetDefaultSize()
    {
        if (!this.#originals['altTabAppIconSizeSmall']) {
            return;
        }

        this.#altTabSizesSet(null, this.#originals['altTabAppIconSizeSmall'], null);
    }

    /**
     * set alt tab small icon size
     *
     * @param {number} size 1-512
     *
     * @returns {void}
     */
    altTabSmallIconSetSize(size)
    {
        if (size < 1 || size > 512) {
            return;
        }

        if (!this.#originals['altTabAppIconSizeSmall']) {
            this.#originals['altTabAppIconSizeSmall'] = this._altTab.APP_ICON_SIZE_SMALL;
        }

        this.#altTabSizesSet(null, size, null);
    }

    /**
     * set default alt tab icon size
     *
     * @returns {void}
     */
    altTabIconSetDefaultSize()
    {
        if (!this.#originals['altTabAppIconSize']) {
            return;
        }

        this.#altTabSizesSet(this.#originals['altTabAppIconSize'], null, null);
    }

    /**
     * set alt tab icon size
     *
     * @param {number} size 1-512
     *
     * @returns {void}
     */
    altTabIconSetSize(size)
    {
        if (size < 1 || size > 512) {
            return;
        }

        if (!this.#originals['altTabAppIconSize']) {
            this.#originals['altTabAppIconSize'] = this._altTab.APP_ICON_SIZE;
        }

        this.#altTabSizesSet(size, null, null);
    }

    /**
     * enable screen sharing indicator
     *
     * @returns {void}
     */
    screenSharingIndicatorEnable()
    {
        this.UIStyleClassRemove(this.#getAPIClassname('no-screen-sharing-indicator'));
    }

    /**
     * disable screen sharing indicator
     *
     * @returns {void}
     */
    screenSharingIndicatorDisable()
    {
        this.UIStyleClassAdd(this.#getAPIClassname('no-screen-sharing-indicator'));
    }

    /**
     * enable screen recording indicator
     *
     * @returns {void}
     */
    screenRecordingIndicatorEnable()
    {
        this.UIStyleClassRemove(this.#getAPIClassname('no-screen-recording-indicator'));
    }

    /**
     * disable screen recording indicator
     *
     * @returns {void}
     */
    screenRecordingIndicatorDisable()
    {
        this.UIStyleClassAdd(this.#getAPIClassname('no-screen-recording-indicator'));
    }

    /**
     * set controls manager spacing to default
     *
     * @returns {void}
     */
    controlsManagerSpacingSetDefault()
    {
        if (this._controlsManagerSpacingSize === undefined) {
            return;
        }

        let classnameStarter = this.#getAPIClassname('controls-manager-spacing-size');
        this.UIStyleClassRemove(classnameStarter + this._controlsManagerSpacingSize);

        delete this._controlsManagerSpacingSize;
    }

    /**
     * set controls manager spacing size
     *
     * @param {number} size in pixels (0 - 150)
     *
     * @returns {void}
     */
    controlsManagerSpacingSizeSet(size)
    {
        this.controlsManagerSpacingSetDefault();

        if (size < 0 || size > 150) {
            return;
        }

        this._controlsManagerSpacingSize = size;

        let classnameStarter = this.#getAPIClassname('controls-manager-spacing-size');
        this.UIStyleClassAdd(classnameStarter + size);
    }

    /**
     * set workspaces view spacing to default
     *
     * @returns {void}
     */
    workspacesViewSpacingSetDefault()
    {
        this.#uninject('workspacesViewGetSpacing');
    }

    /**
     * set workspaces view spacing size
     *
     * @param {number} size in pixels (0 - 500)
     *
     * @returns {void}
     */
    workspacesViewSpacingSizeSet(size)
    {
        if (size < 0 || size > 500) {
            return;
        }

        let wsvp = this._workspacesView.WorkspacesView.prototype;

        this.#inject('workspacesViewGetSpacing', wsvp, '_getSpacing', original => function (box, fitMode, vertical) {
            if (fitMode === 0) {
                return size;
            }
            return original.call(this, box, fitMode, vertical);
        });
    }

    /**
     * show dash app running dot
     *
     * @returns {void}
     */
    dashAppRunningDotShow()
    {
        this.UIStyleClassRemove(this.#getAPIClassname('no-dash-app-running-dot'));
    }

    /**
     * hide dash app running dot
     *
     * @returns {void}
     */
    dashAppRunningDotHide()
    {
        this.UIStyleClassAdd(this.#getAPIClassname('no-dash-app-running-dot'));
    }

    /**
     * show airplane mode toggle button in quick settings
     *
     * @returns {void}
     */
    quickSettingsAirplaneModeToggleShow()
    {
        this.#onQuickSettingsPropertyCall('_rfkill', (rfkill) => {
            if (this._rfkillToggleShowSignal) {
                rfkill._rfkillToggle.disconnect(this._rfkillToggleShowSignal);
            }

            if (this.#originals['rfkilToggleVisibleDefaultStatus'] !== undefined) {
                rfkill._rfkillToggle.visible = this.#originals['rfkilToggleVisibleDefaultStatus'];
                rfkill._sync();
                delete(this.#originals['rfkilToggleVisibleDefaultStatus']);
            }
        });
    }

    /**
     * hide airplane mode toggle button in quick settings
     *
     * @returns {void}
     */
    quickSettingsAirplaneModeToggleHide()
    {
        this._rfkillToggleShowSignal;

        this.#onQuickSettingsPropertyCall('_rfkill', (rfkill) => {
            if (!this.#originals['rfkilToggleVisibleDefaultStatus']) {
                this.#originals['rfkilToggleVisibleDefaultStatus'] = rfkill._rfkillToggle.visible;
            }

            rfkill._rfkillToggle.hide();
            rfkill._sync();

            if (!this._rfkillToggleShowSignal) {
                this._rfkillToggleShowSignal = rfkill._rfkillToggle.connect('show', () => {
                    rfkill._rfkillToggle.hide();
                    rfkill._sync();
                });
            }
        });
    }

    /**
     * show dark style toggle button in quick settings
     *
     * @returns {void}
     */
    quickSettingsDarkStyleToggleShow()
    {
        this.#onQuickSettingsPropertyCall('_darkMode', (darkMode) => {
            darkMode.quickSettingsItems[0].show();
        });
    }

    /**
     * hide dark style toggle button in quick settings
     *
     * @returns {void}
     */
    quickSettingsDarkStyleToggleHide()
    {
        this.#onQuickSettingsPropertyCall('_darkMode', (darkMode) => {
            darkMode.quickSettingsItems[0].hide();
        });
    }

    /**
     * show night light toggle button in quick settings
     *
     * @returns {void}
     */
    quickSettingsNightLightToggleShow()
    {
        this.#onQuickSettingsPropertyCall('_nightLight', (nightLight) => {
            nightLight.quickSettingsItems[0].show();
        });
    }

    /**
     * hide night light toggle button in quick settings
     *
     * @returns {void}
     */
    quickSettingsNightLightToggleHide()
    {
        this.#onQuickSettingsPropertyCall('_nightLight', (nightLight) => {
            nightLight.quickSettingsItems[0].hide();
        });
    }

    /**
     * show do not disturb toggle button in quick settings
     *
     * @returns {void}
     */
    quickSettingsDoNotDisturbToggleShow()
    {
        if (this.#shellVersion < 49) {
            return;
        }

        this.#onQuickSettingsPropertyCall('_doNotDisturb', (doNotDisturb) => {
            doNotDisturb.quickSettingsItems[0].show();
        });
    }

    /**
     * hide do not disturb toggle button in quick settings
     *
     * @returns {void}
     */
    quickSettingsDoNotDisturbToggleHide()
    {
        if (this.#shellVersion < 49) {
            return;
        }

        this.#onQuickSettingsPropertyCall('_doNotDisturb', (doNotDisturb) => {
            doNotDisturb.quickSettingsItems[0].hide();
        });
    }

    /**
     * show backlight toggle button in quick settings
     *
     * @returns {void}
     */
    quickSettingsBacklightToggleShow()
    {
        this.#onQuickSettingsPropertyCall('_backlight', (backlight) => {
            let item = backlight.quickSettingsItems[0];

            if (this.#originals['backlightToggleVisibleDefaultStatus'] !== undefined) {
                item.visible = this.#originals['backlightToggleVisibleDefaultStatus'];
                delete(this.#originals['backlightToggleVisibleDefaultStatus']);
            }

            if (this._backlightToggleShowSignal) {
                item.disconnect(this._backlightToggleShowSignal);
            }
        });
    }

    /**
     * hide backlight toggle button in quick settings
     *
     * @returns {void}
     */
    quickSettingsBacklightToggleHide()
    {
        this._backlightToggleShowSignal;

        this.#onQuickSettingsPropertyCall('_backlight', (backlight) => {
            let item = backlight.quickSettingsItems[0];

            if (!this.#originals['backlightToggleVisibleDefaultStatus']) {
                this.#originals['backlightToggleVisibleDefaultStatus'] = item.visible;
            }

            item.hide();

            if (!this._backlightToggleShowSignal) {
                this._backlightToggleShowSignal = item.connect('show', () => {
                    item.hide();
                });
            }
        });
    }

    /**
     * call a function when async property of quick settings is available
     *
     * @param {string} propertyName
     * @param {Function} func function to call when the property is available
     *
     * @returns {void}
     */
    #onQuickSettingsPropertyCall(propertyName, func)
    {
        const quickSettings = this._main.panel.statusArea.quickSettings;
        const indicators = quickSettings._indicators;

        if (quickSettings[propertyName]) {
            func(quickSettings[propertyName]);
            return;
        }

        if (!this._quickSettingsCallSignals) {
            this._quickSettingsCallSignals = {};
        }

        if (this._quickSettingsCallSignals[propertyName]) {
            indicators.disconnect(this._quickSettingsCallSignals[propertyName]);
        }

        this._quickSettingsCallSignals[propertyName] = indicators.connect(
            (this.#shellVersion >= 46) ? 'child-added' : 'actor-added',
            () => {
                if (!quickSettings[propertyName]) {
                    return;
                }

                if (this._quickSettingsCallSignals[propertyName]) {
                    indicators.disconnect(this._quickSettingsCallSignals[propertyName]);
                }

                func(quickSettings[propertyName]);
            }
        );
    }

    /**
     * disconnect all quick settings property calls
     *
     * @returns {void}
     */
    #stopAllOnQuickSettingsPropertyCalls()
    {
        if (!this._quickSettingsCallSignals) {
            return;
        }

        const indicators = this._main.panel.statusArea.quickSettings._indicators;

        for (let [_name, id] of Object.entries(this._quickSettingsCallSignals)) {
            if (id) {
                indicators.disconnect(id);
            }
        }

        delete(this._quickSettingsCallSignals);
    }

    /**
     * enable accent color icon
     *
     * @returns {void}
     */
    accentColorIconEnable()
    {
        this.UIStyleClassAdd(this.#getAPIClassname('accent-color-icon'));
    }

    /**
     * disable accent color icon
     *
     * @returns {void}
     */
    accentColorIconDisable()
    {
        this.UIStyleClassRemove(this.#getAPIClassname('accent-color-icon'));
    }
}
