import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';

const ignoredWindowTypes = [
  Meta.WindowType.DROPDOWN_MENU,
  Meta.WindowType.NOTIFICATION,
  Meta.WindowType.POPUP_MENU,
  Meta.WindowType.SPLASHSCREEN,
];

export class AutoActivitiesManager {
  constructor(settings) {
    this._settings = settings;
    this._workspaces = new Map();
    this._timeoutId = 0;
    for (let i = 0; i < global.workspace_manager.n_workspaces; i++)
      this._watchWorkspace(global.workspace_manager.get_workspace_by_index(i));
    this._signals = [
      [global.workspace_manager, global.workspace_manager.connect('workspace-added', (_m, i) => this._watchWorkspace(global.workspace_manager.get_workspace_by_index(i)))],
      [global.workspace_manager, global.workspace_manager.connect('workspace-removed', () => this._rebuildWorkspaceSignals())],
      [global.workspace_manager, global.workspace_manager.connect('workspaces-reordered', () => this._rebuildWorkspaceSignals())],
      [global.workspace_manager, global.workspace_manager.connect('workspace-switched', () => {
        if (!this._settings.get_boolean('skip-last-workspace')) this._checkAndShowOverview();
      })],
      [global.window_manager, global.window_manager.connect('minimize', (_wm, actor) => {
        if (this._settings.get_boolean('detect-minimized') && actor?.meta_window && !ignoredWindowTypes.includes(actor.meta_window.get_window_type()))
          this._checkAndShowOverview();
      })],
    ];
  }

  _watchWorkspace(ws) {
    if (!ws || this._workspaces.has(ws)) return;
    const removed = ws.connect('window-removed', (_ws, win) => {
      if (!ignoredWindowTypes.includes(win.get_window_type())) this._checkAndShowOverview();
    });
    const added = ws.connect('window-added', (_ws, win) => {
      if (!ignoredWindowTypes.includes(win.get_window_type()) && this._settings.get_boolean('hide-on-new-window') && Main.overview.visible)
        Main.overview.hide();
    });
    this._workspaces.set(ws, [removed, added]);
  }

  _rebuildWorkspaceSignals() {
    for (const [ws, ids] of this._workspaces) for (const id of ids) if (id) ws.disconnect(id);
    this._workspaces.clear();
    for (let i = 0; i < global.workspace_manager.n_workspaces; i++) this._watchWorkspace(global.workspace_manager.get_workspace_by_index(i));
  }

  _checkAndShowOverview() {
    if (this._timeoutId) GLib.Source.remove(this._timeoutId);
    const delay = Math.max(0, this._settings.get_int('window-checking-delay'));
    this._timeoutId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, delay, () => {
      this._timeoutId = 0;
      let windows = global.get_window_actors();
      if (this._settings.get_boolean('isolate-workspaces')) {
        const idx = global.workspace_manager.get_active_workspace().index();
        windows = windows.filter(w => w.meta_window.get_workspace()?.index() === idx);
      }
      if (this._settings.get_boolean('isolate-monitors')) {
        const monitor = global.display.get_current_monitor();
        windows = windows.filter(w => w.meta_window.get_monitor() === monitor);
      }
      if (this._settings.get_boolean('skip-taskbar')) windows = windows.filter(w => !w.meta_window.skip_taskbar);
      if (this._settings.get_boolean('detect-minimized')) windows = windows.filter(w => !w.meta_window.minimized);
      if (windows.length === 0) {
        if (this._settings.get_boolean('show-apps')) Main.overview.showApps();
        else Main.overview.show();
      }
      return GLib.SOURCE_REMOVE;
    });
  }

  destroy() {
    if (this._timeoutId) GLib.Source.remove(this._timeoutId);
    for (const [obj, id] of this._signals) if (id) obj.disconnect(id);
    for (const [ws, ids] of this._workspaces) for (const id of ids) if (id) ws.disconnect(id);
    this._signals = [];
    this._workspaces.clear();
  }
}
