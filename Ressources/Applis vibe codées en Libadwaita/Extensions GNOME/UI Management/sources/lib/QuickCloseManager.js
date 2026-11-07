import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import Meta from 'gi://Meta';
import Clutter from 'gi://Clutter';
import {InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';
import {Workspace} from 'resource:///org/gnome/shell/ui/workspace.js';
import {WindowPreview} from 'resource:///org/gnome/shell/ui/windowPreview.js';
import {ControlsState} from 'resource:///org/gnome/shell/ui/overviewControls.js';

export class QuickCloseManager {
  constructor(settings) {
    this._settings = settings;
    this._refocus = new WeakSet();
    this._injection = new InjectionManager();
    this._patchClick(); this._patchDelay(); this._patchKey();
  }
  destroy() { this._injection.clear(); this._injection = null; this._refocus = null; }
  _requiredModifiers() {
    let f = 0;
    if (this._settings.get_boolean('close-require-shift')) f |= Clutter.ModifierType.SHIFT_MASK;
    if (this._settings.get_boolean('close-require-control')) f |= Clutter.ModifierType.CONTROL_MASK;
    return f;
  }
  _patchClick() {
    const self = this;
    this._injection.overrideMethod(Workspace.prototype, '_addWindowClone', original => function() {
      const clone = original.apply(this, arguments);
      let modifierState = 0;
      clone.connect('captured-event', (_actor, event) => {
        if (event.type() === Clutter.EventType.BUTTON_PRESS) modifierState = event.get_state();
        else if (event.type() === Clutter.EventType.BUTTON_RELEASE) modifierState &= event.get_state();
      });
      try {
        patchAction(clone, Clutter.ClickGesture, 'recognize', action => {
          const required = self._requiredModifiers();
          if (action.get_button() === self._settings.get_int('close-button') && (modifierState & required) === required) clone._deleteAll();
          else clone._activate();
        });
      } catch (e) { console.error(`UI Management Quick Close: ${e}`); }
      return clone;
    });
  }
  _patchDelay() {
    const settings=this._settings, refocus=this._refocus, lastIds=new WeakMap();
    this._injection.overrideMethod(Workspace.prototype, '_doRemoveWindow', original => function(metaWin) {
      let idx=this.get_focus_chain().findIndex(c=>c.metaWindow===metaWin);
      const ret=original.apply(this, arguments);
      if (refocus.has(metaWin)) { const chain=this.get_focus_chain(); if (idx>=chain.length) idx=chain.length-1; if (idx>=0) global.stage.key_focus=chain[idx]; }
      if (this._layoutFrozenId>0 && this._layoutFrozenId!==lastIds.get(this)) {
        const src=GLib.MainContext.default().find_source_by_id(this._layoutFrozenId);
        if (src) src.set_ready_time(src.get_time()+settings.get_int('rearrange-delay')*1000);
      }
      lastIds.set(this,this._layoutFrozenId); return ret;
    });
  }
  _patchKey() {
    const settings=this._settings, refocus=this._refocus;
    this._injection.overrideMethod(WindowPreview.prototype, 'vfunc_key_press_event', original => function(event) {
      if (settings.get_boolean('keyboard-close') && this._workspace._overviewAdjustment.value===ControlsState.WINDOW_PICKER) {
        const action=global.display.get_keybinding_action(event.get_key_code(), event.get_state());
        if (action===Meta.KeyBindingAction.CLOSE) {
          if (this._workspace.metaWorkspace?.active) { refocus.add(this.metaWindow); this._deleteAll(); }
          else this._workspace.metaWorkspace?.activate(global.get_current_time());
          return true;
        }
      }
      return original.apply(this, arguments);
    });
  }
}

function patchAction(obj, actionType, signalId, callback) {
  const actions=obj.get_actions().filter(a=>a instanceof actionType);
  if (actions.length!==1) throw `matched ${actions.length} click actions`;
  const action=actions[0];
  const count=GObject.signal_handlers_block_matched(action,{signalId});
  if (count===1) action.connect(signalId,callback);
  else { GObject.signal_handlers_unblock_matched(action,{signalId}); throw `matched ${count} handlers for ${signalId}`; }
}
