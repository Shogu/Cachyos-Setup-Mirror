import Clutter from 'gi://Clutter';
import GObject from 'gi://GObject';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import * as Layout from 'resource:///org/gnome/shell/ui/layout.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as Ripples from 'resource:///org/gnome/shell/ui/ripples.js';

const PRESSURE_TIMEOUT = 1000;
const KEYS = ['pressure-threshold','fallback-timeout','edge-size','suppress-activation-when-button-held','suppress-activation-when-fullscreen','primary-monitor-only','show-animation'];

export class HotEdgeManager {
  constructor(settings) {
    this._settings = settings;
    this._ids = KEYS.map(k => settings.connect(`changed::${k}`, () => Main.layoutManager._updateHotCorners()));
    this._edgeHandlerId = Main.layoutManager.connect('hot-corners-changed', () => this._updateHotEdges());
    Main.layoutManager._updateHotCorners();
  }
  destroy() {
    if (this._edgeHandlerId) Main.layoutManager.disconnect(this._edgeHandlerId);
    for (const id of this._ids) this._settings.disconnect(id);
    Main.layoutManager._updateHotCorners();
  }
  _updateHotEdges() {
    const pressure = this._settings.get_uint('pressure-threshold');
    const timeout = this._settings.get_uint('fallback-timeout');
    const fraction = this._settings.get_uint('edge-size') / 100;
    for (let i = 0; i < Main.layoutManager.monitors.length; i++) {
      if (this._settings.get_boolean('primary-monitor-only') && i !== Main.layoutManager.primaryIndex) continue;
      const monitor = Main.layoutManager.monitors[i];
      const left = monitor.x, right = monitor.x + monitor.width, bottom = monitor.y + monitor.height;
      let haveBottom = true;
      for (let j = 0; j < Main.layoutManager.monitors.length; j++) {
        if (i === j) continue;
        const other = Main.layoutManager.monitors[j];
        if (other.y >= bottom && other.x < right && other.x + other.width > left) { haveBottom = false; break; }
      }
      if (haveBottom) {
        const edge = new HotEdge(Main.layoutManager, monitor, left, bottom, this._settings, pressure, timeout, fraction);
        edge.setBarrierSize(monitor.width);
        Main.layoutManager.hotCorners.push(edge);
      } else Main.layoutManager.hotCorners.push(null);
    }
  }
}

const HotEdge = GObject.registerClass(class HotEdge extends Clutter.Actor {
  _init(layoutManager, monitor, x, y, settings, pressure, timeout, fraction) {
    super._init();
    this._monitor = monitor; this._x = x; this._y = y; this._settings = settings;
    this._fallbackTimeout = timeout; this._edgeSize = fraction;
    this._suppressButton = settings.get_boolean('suppress-activation-when-button-held');
    this._suppressFullscreen = settings.get_boolean('suppress-activation-when-fullscreen');
    this._showAnimation = settings.get_boolean('show-animation');
    this._ignoredButtons = [Clutter.ModifierType.BUTTON1_MASK, Clutter.ModifierType.BUTTON2_MASK, Clutter.ModifierType.BUTTON3_MASK];
    this._setupFallback(layoutManager);
    this._pressureBarrier = new Layout.PressureBarrier(pressure, PRESSURE_TIMEOUT, Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW);
    this._pressureBarrier.connect('trigger', () => this._toggleOverview());
    this._ripples = new Ripples.Ripples(0.5, 0.5, 'ripple-centered');
    this._ripples.addTo(layoutManager.uiGroup);
    this.connect('destroy', () => this._onDestroy());
  }
  setBarrierSize(size) {
    if (this._barrier) { this._pressureBarrier.removeBarrier(this._barrier); this._barrier.destroy(); this._barrier = null; }
    if (size > 0) {
      size = this._monitor.width * this._edgeSize;
      const offset = (this._monitor.width - size) / 2;
      this._barrier = new Meta.Barrier({backend: global.backend, x1: this._x + offset, x2: this._x + offset + size, y1: this._y, y2: this._y, directions: Meta.BarrierDirection.NEGATIVE_Y});
      this._pressureBarrier.addBarrier(this._barrier);
    }
  }
  _setupFallback(layoutManager) {
    if ((global.backend.capabilities & Meta.BackendCapabilities.BARRIERS) === 0) {
      this._settings.set_boolean('fallback-in-use', true);
      const size = this._monitor.width * this._edgeSize;
      const offset = (this._monitor.width - size) / 2;
      this.set({name:'hot-edge', x:this._x+offset, y:this._y-1, width:size, height:1, reactive:true});
      layoutManager.addChrome(this);
    } else this._settings.set_boolean('fallback-in-use', false);
  }
  _toggleOverview() {
    if (this._suppressButton && this._ignoredButtons.some(b => (global.get_pointer()[2] & b) !== 0)) return;
    if (this._suppressFullscreen && this._monitor.inFullscreen && !Main.overview.visible) return;
    if (Main.overview.shouldToggleByCornerOrButton()) {
      Main.overview.toggle();
      if (this._showAnimation && Main.overview.animationInProgress) this._ripples.playAnimation(global.get_pointer()[0], this._y);
    }
  }
  vfunc_enter_event() {
    if (!this._timeoutId) this._timeoutId = GLib.timeout_add(GLib.PRIORITY_HIGH, this._fallbackTimeout, () => { this._timeoutId = 0; this._toggleOverview(); return GLib.SOURCE_REMOVE; });
    return Clutter.EVENT_PROPAGATE;
  }
  vfunc_leave_event() {
    if (this._timeoutId) { GLib.Source.remove(this._timeoutId); this._timeoutId = 0; }
    return Clutter.EVENT_PROPAGATE;
  }
  _onDestroy() {
    if (this._timeoutId) GLib.Source.remove(this._timeoutId);
    this.setBarrierSize(0);
    this._pressureBarrier?.destroy(); this._pressureBarrier = null;
    this._ripples?.destroy();
  }
});
