import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import Meta from 'gi://Meta';
import St from 'gi://St';
import * as AltTab from 'resource:///org/gnome/shell/ui/altTab.js';
import * as BackgroundMenu from 'resource:///org/gnome/shell/ui/backgroundMenu.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as MessageTray from 'resource:///org/gnome/shell/ui/messageTray.js';
import * as OSDWindow from 'resource:///org/gnome/shell/ui/osdWindow.js';
import * as OverviewControls from 'resource:///org/gnome/shell/ui/overviewControls.js';
import * as Panel from 'resource:///org/gnome/shell/ui/panel.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as SearchController from 'resource:///org/gnome/shell/ui/searchController.js';
import * as SwitcherPopup from 'resource:///org/gnome/shell/ui/switcherPopup.js';
import * as WindowMenu from 'resource:///org/gnome/shell/ui/windowMenu.js';
import * as WindowPreview from 'resource:///org/gnome/shell/ui/windowPreview.js';
import * as Workspace from 'resource:///org/gnome/shell/ui/workspace.js';
import * as WorkspacesView from 'resource:///org/gnome/shell/ui/workspacesView.js';
import * as WorkspaceSwitcherPopup from 'resource:///org/gnome/shell/ui/workspaceSwitcherPopup.js';
import * as WorkspaceThumbnail from 'resource:///org/gnome/shell/ui/workspaceThumbnail.js';
import * as Config from 'resource:///org/gnome/shell/misc/config.js';
import * as Util from 'resource:///org/gnome/shell/misc/util.js';
import {Extension, InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';
import {API} from './lib/API.js';
import {Manager} from './lib/Manager.js';
import {AutoActivitiesManager} from './lib/AutoActivitiesManager.js';
import {HotEdgeManager} from './lib/HotEdgeManager.js';
import {QuickCloseManager} from './lib/QuickCloseManager.js';

export default class UIManagement extends Extension {
  enable() {
    this._settings=this.getSettings();
    // Réglages retirés de l'interface (taille du panneau, des icônes, marges) :
    // on les remet à leur valeur par défaut pour que le thème Shell s'applique.
    for (const key of ['panel-size','panel-icon-size','panel-button-padding-size','panel-indicator-padding-size'])
      if (this._settings.get_user_value(key)!==null) this._settings.reset(key);
    const shellVersion=parseFloat(Config.PACKAGE_VERSION);
    const interfaceSettings=new Gio.Settings({schema_id:'org.gnome.desktop.interface'});
    // un seul InjectionManager pour tous les remplacements de méthodes de l'API ; vidé dans disable()
    this._injection=new InjectionManager();
    this._api=new API({Main,BackgroundMenu,OverviewControls,WorkspaceSwitcherPopup,SwitcherPopup,InterfaceSettings:interfaceSettings,SearchController,WorkspaceThumbnail,WorkspacesView,Panel,PanelMenu,WindowPreview,Workspace,MessageTray,OSDWindow,WindowMenu,AltTab,St,GLib,Clutter,Util,Meta,GObject,InjectionManager:this._injection}, shellVersion);
    this._api.open();
    this._manager=new Manager({API:this._api,Settings:this._settings});
    this._manager.start();
    this._featureIds=[
      this._settings.connect('changed::auto-activities-enabled',()=>this._syncFeatures()),
      this._settings.connect('changed::hot-edge-enabled',()=>this._syncFeatures()),
      this._settings.connect('changed::quick-close-enabled',()=>this._syncFeatures()),
    ];
    this._syncFeatures();
  }
  _syncFeatures() {
    const sync=(prop,key,Ctor)=>{
      const enabled=this._settings.get_boolean(key);
      if (enabled && !this[prop]) this[prop]=new Ctor(this._settings);
      else if (!enabled && this[prop]) { this[prop].destroy(); this[prop]=null; }
    };
    sync('_auto','auto-activities-enabled',AutoActivitiesManager);
    sync('_hot','hot-edge-enabled',HotEdgeManager);
    sync('_quick','quick-close-enabled',QuickCloseManager);
  }
  disable() {
    this._auto?.destroy(); this._auto=null;
    this._hot?.destroy(); this._hot=null;
    this._quick?.destroy(); this._quick=null;
    for (const id of this._featureIds ?? []) this._settings.disconnect(id);
    this._featureIds=[];
    this._manager?.stop(); this._manager=null;
    this._api?.close(); this._api=null;
    this._injection?.clear(); this._injection=null;
    this._settings=null;
  }
}
