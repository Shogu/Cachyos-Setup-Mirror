// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GObject from 'gi://GObject';
import St from 'gi://St';
import {MediaMessage} from 'resource:///org/gnome/shell/ui/messageList.js';
import {Switch} from 'resource:///org/gnome/shell/ui/popupMenu.js';

// Ligne « Notifications » repliable sous les notes, avec l'interrupteur Ne pas
// déranger (le même réglage que la pilule native). La ligne n'apparaît que s'il
// y a des notifications, ou si Ne pas déranger est actif.
export const NotificationsDrawer = GObject.registerClass(
class NotificationsDrawer extends St.BoxLayout {
    _init(messageList, menu) {
        super._init({style_class: 'tcw-drawer', orientation: Clutter.Orientation.VERTICAL});
        this._messageList = messageList;
        this._view = messageList._messageView;
        this._menu = menu;
        this._notifications = new Gio.Settings({schema_id: 'org.gnome.desktop.notifications'});
        this._expanded = false;

        const row = new St.BoxLayout({style_class: 'events-button tcw-drawer-row'});
        const content = new St.BoxLayout({style_class: 'tcw-drawer-content'});
        this._icon = new St.Icon({style_class: 'tcw-drawer-icon', y_align: Clutter.ActorAlign.CENTER});
        content.add_child(this._icon);
        this._title = new St.Label({x_expand: true, y_align: Clutter.ActorAlign.CENTER});
        content.add_child(this._title);
        this._badge = new St.Label({style_class: 'tcw-badge', y_align: Clutter.ActorAlign.CENTER});
        content.add_child(this._badge);
        this._expander = new St.Button({style_class: 'tcw-drawer-expander', child: content, can_focus: true, x_expand: true});
        this._expander.connect('clicked', () => this._toggle());
        row.add_child(this._expander);

        this._divider = new St.Widget({style_class: 'tcw-drawer-divider', y_align: Clutter.ActorAlign.CENTER});
        row.add_child(this._divider);
        const dnd = new St.BoxLayout({style_class: 'tcw-dnd-box'});
        this._dndIcon = new St.Icon({icon_name: 'notifications-disabled-symbolic', style_class: 'tcw-drawer-icon', y_align: Clutter.ActorAlign.CENTER});
        dnd.add_child(this._dndIcon);
        this._switch = new Switch(false);
        dnd.add_child(this._switch);
        this._dndButton = new St.Button({
            style_class: 'tcw-dnd-button',
            child: dnd,
            accessible_name: 'Ne pas déranger',
            can_focus: true,
            y_align: Clutter.ActorAlign.CENTER,
        });
        this._dndButton.connect('clicked', () => {
            this._notifications.set_boolean('show-banners', !this._notifications.get_boolean('show-banners'));
        });
        row.add_child(this._dndButton);

        this._arrow = new St.Button({
            style_class: 'tcw-drawer-arrow-button',
            child: new St.Icon({icon_name: 'pan-end-symbolic', style_class: 'tcw-drawer-arrow'}),
            accessible_name: 'Afficher les notifications',
            can_focus: true,
            y_align: Clutter.ActorAlign.CENTER,
        });
        this._arrow.connect('clicked', () => this._toggle());
        row.add_child(this._arrow);
        this.add_child(row);
        this.add_child(messageList);

        this.connect('destroy', () => (this._destroyed = true));
        this._viewSignals = ['child-added', 'child-removed', 'notify::empty']
            .map(signal => this._view.connect(signal, () => this._sync()));
        this._bannersId = this._notifications.connect('changed::show-banners', () => this._sync());
        this._menuSignal = menu.connect('open-state-changed', (_menu, open) => {
            if (!open) {
                this._expanded = false;
                this._sync();
            }
        });
        this._sync();
    }

    _count() {
        return this._view.messages.filter(message => !(message instanceof MediaMessage)).length;
    }

    _toggle() {
        this._expanded = !this._expanded;
        this._sync();
    }

    _sync() {
        if (this._destroyed || !this._view || !this._messageList)
            return;
        const count = this._count();
        const dnd = !this._notifications.get_boolean('show-banners');
        if (!count)
            this._expanded = false;

        this.visible = count > 0 || dnd;
        this._icon.icon_name = count ? 'preferences-system-notifications-symbolic' : 'notifications-disabled-symbolic';
        this._title.text = count ? 'Notifications' : 'Ne pas déranger';
        this._badge.text = String(count);
        this._badge.visible = count > 0;
        this._expander.reactive = count > 0;
        this._arrow.visible = count > 0;
        this._divider.visible = count > 0;
        this._dndIcon.visible = count > 0;
        this._switch.state = dnd;

        this.y_expand = this._expanded;
        this._messageList.visible = this._expanded;
        this._messageList.y_expand = this._expanded;
        this._arrow.child.icon_name = this._expanded ? 'pan-down-symbolic' : 'pan-end-symbolic';
    }

    release() {
        for (const id of this._viewSignals)
            this._view.disconnect(id);
        this._viewSignals = [];
        this._notifications.disconnect(this._bannersId);
        this._notifications = null;
        this._menu.disconnect(this._menuSignal);
        this.remove_child(this._messageList);
        this._messageList.visible = true;
        const messageList = this._messageList;
        this._messageList = null;
        this._view = null;
        this._menu = null;
        return messageList;
    }
});
