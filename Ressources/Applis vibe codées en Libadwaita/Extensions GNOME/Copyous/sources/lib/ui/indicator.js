import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import GdkPixbuf from 'gi://GdkPixbuf';
import Gio from 'gi://Gio';
import Pango from 'gi://Pango';
import St from 'gi://St';

import { gettext as _, ngettext } from 'resource:///org/gnome/shell/extensions/extension.js';
import * as animationUtils from 'resource:///org/gnome/shell/misc/animationUtils.js';
import * as CheckBox from 'resource:///org/gnome/shell/ui/checkBox.js';
import * as Dialog from 'resource:///org/gnome/shell/ui/dialog.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as ModalDialog from 'resource:///org/gnome/shell/ui/modalDialog.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

import { Color } from '../common/color.js';
import { ItemType } from '../common/constants.js';
import { registerClass } from '../common/gjs.js';
import { Icon, loadIcon } from '../common/icons.js';
import { ClipboardHistory, IndicatorDisplay } from '../common/settings.js';
import { VERSION } from '../misc/compatibility.js';

var __decorate =
	(this && this.__decorate) ||
	function (decorators, target, key, desc) {
		var c = arguments.length,
			r = c < 3 ? target : desc === null ? (desc = Object.getOwnPropertyDescriptor(target, key)) : desc,
			d;
		if (typeof Reflect === 'object' && typeof Reflect.decorate === 'function')
			r = Reflect.decorate(decorators, target, key, desc);
		else
			for (var i = decorators.length - 1; i >= 0; i--)
				if ((d = decorators[i])) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
		return (c > 3 && r && Object.defineProperty(target, key, r), r);
	};

let ConfirmClearHistoryDialog = class ConfirmClearHistoryDialog extends ModalDialog.ModalDialog {
	constructor() {
		super();
		const content = new Dialog.MessageDialogContent({
			title: _('Clear Clipboard History?'),
			description: _('Are you sure you want to clear your clipboard history?'),
		});
		this.contentLayout.add_child(content);
		const checkbox = new CheckBox.CheckBox(_('Clear Pinned/Tagged Items'));
		content.add_child(checkbox);
		this.addButton({
			label: _('Cancel'),
			action: this.close.bind(this),
			default: true,
			key: Clutter.KEY_Escape,
		});
		this.addButton({
			label: _('Clear'),
			action: () => {
				this.emit(
					'clear-history',
					checkbox.checked ? ClipboardHistory.Clear : ClipboardHistory.KeepPinnedAndTagged,
				);
				this.close();
			},
		});
	}
};
ConfirmClearHistoryDialog = __decorate(
	[
		registerClass({
			Signals: {
				'clear-history': {
					param_types: [GObject.TYPE_INT],
				},
			},
		}),
	],
	ConfirmClearHistoryDialog,
);

export { ConfirmClearHistoryDialog };

let ClipboardIndicator = class ClipboardIndicator extends PanelMenu.Button {
	ext;
	_incognito = false;
	_box;
	_icon;
	_accumulateSwitch;
	_incognitoSwitch;
	_previewWidget;
	_hoverTimeoutId = 0;
	_hoverSuppressed = false;

	constructor(ext) {
		super(0.5, ext.metadata.name, false);
		this.ext = ext;
		this.configurePanelMenuClickGesture();
		this._box = new St.BoxLayout({
			style_class: 'copyous-indicator-box',
			orientation: Clutter.Orientation.HORIZONTAL,
		});
		this.add_child(this._box);
		this._icon = new St.Icon({
			gicon: loadIcon(ext, Icon.Clipboard),
			style_class: 'system-status-icon',
		});
		this._box.add_child(this._icon);
		this._accumulateSwitch = new PopupMenu.PopupSwitchMenuItem(
			_('Accumulate Mode'),
			ext.settings.get_boolean('accumulate'),
		);
		this._accumulateSwitch.connect('toggled', (_item, state) => this.ext.settings.set_boolean('accumulate', state));
		this.menu.addMenuItem(this._accumulateSwitch);
		this._incognitoSwitch = new PopupMenu.PopupSwitchMenuItem(_('Incognito Mode'), false);
		this.menu.addMenuItem(this._incognitoSwitch);
		this._multiPickerSwitch = new PopupMenu.PopupSwitchMenuItem(_('Multi-Paste Picker'), ext.settings.get_boolean('paste-picker-enabled'));
		this._multiPickerSwitch.connect('toggled', (_item, state) => {
			ext.settings.set_boolean('paste-picker-enabled', state);
			ext.shortcutsManager.registerPastePickerShortcut();
		});
		this.menu.addMenuItem(this._multiPickerSwitch);
		this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
		this.menu.addAction(_('Clear History'), () => this.confirmClearHistory());
		this.menu.addAction(_('Settings'), () => ext.openPreferences());
		const menu = this.menu;
		const origToggle = menu.toggle.bind(this.menu);
		const origOpen = menu.open.bind(this.menu);
		let allowOpen = false;
		menu.toggle = (...args) => {
			allowOpen = true;
			try {
				return origToggle(...args);
			} finally {
				allowOpen = false;
			}
		};
		menu.open = (...args) => {
			const type = Clutter.get_current_event()?.type();
			const fromKeyboard = type === Clutter.EventType.KEY_PRESS || type === Clutter.EventType.KEY_RELEASE;
			if (!allowOpen && !fromKeyboard) return;
			return origOpen(...args);
		};

		// Add to panel
		Main.panel.addToStatusArea(ext.uuid, this, 1, 'right');

		// Bind properties
		this.ext.settings.connectObject(
			'changed::indicator-display',
			this.updateSettings.bind(this),
			'changed::incognito',
			this.updateSettings.bind(this),
			'changed::accumulate',
			() => {
				this._accumulateSwitch.setToggleState(this.ext.settings.get_boolean('accumulate'));
				this.updateIcon();
			},
			this,
		);
		this.bind_property('incognito', this._incognitoSwitch, 'state', GObject.BindingFlags.BIDIRECTIONAL);
		this.updateSettings();
		this.updateIcon();
	}

	/**
	 * Icône du panneau selon l'état. Priorité : Mode cumul (presse-papiers avec un +)
	 * avant Mode incognito (presse-papiers barré), avant l'état normal.
	 */
	updateIcon() {
		let icon = Icon.Clipboard;
		if (this.ext.settings.get_boolean('accumulate')) icon = Icon.ClipboardAdd;
		else if (this._incognito) icon = Icon.ClipboardDisabled;
		this._icon.gicon = loadIcon(this.ext, icon);
	}

	configurePanelMenuClickGesture() {
		if (VERSION < 50) return;
		this._clickGesture?.set_required_button(Clutter.BUTTON_SECONDARY);
	}

	get incognito() {
		return this._incognito;
	}

	set incognito(value) {
		if (this._incognito === value) return;
		this._incognitoSwitch.state = value;
		this._incognito = value;
		this.updateIcon();
		this.ext.settings.set_boolean('incognito', value);
		this.notify('incognito');
	}

	set previewWidget(widget) {
		this._previewWidget?.destroy();
		this._previewWidget = widget;
		this._box.add_child(widget);
		this.updateSettings();
	}

	updateSettings() {
		const indicatorDisplay = this.ext.settings.get_enum('indicator-display');
		const showContentIndicator =
			indicatorDisplay === IndicatorDisplay.ClipboardContentOnly ||
			indicatorDisplay === IndicatorDisplay.IconAndClipboardContent;
		const showIconIndicator =
			indicatorDisplay === IndicatorDisplay.IconOnly ||
			indicatorDisplay === IndicatorDisplay.IconAndClipboardContent ||
			(showContentIndicator && !this._previewWidget);
		this.visible = indicatorDisplay !== IndicatorDisplay.Hidden;
		this._icon.visible = showIconIndicator;
		if (this._previewWidget) this._previewWidget.visible = showContentIndicator;
		this.incognito = this.ext.settings.get_boolean('incognito');
	}

	toggleIncognito() {
		this.incognito = !this.incognito;
	}

	animate() {
		if (this._icon.visible && this.ext.settings.get_boolean('wiggle-indicator')) {
			animationUtils.wiggle(this._icon, { offset: 2, duration: 65, wiggleCount: 3 });
		}
	}

	showEntry(entry) {
		switch (entry.type) {
			case ItemType.Text:
			case ItemType.Code:
			case ItemType.Link:
			case ItemType.Character:
				this.showText(entry.content.split('\n')[0] ?? '');
				break;
			case ItemType.Image:
				this.showImageFile(Gio.File.new_for_uri(entry.content));
				break;
			case ItemType.File: {
				const file = Gio.File.new_for_uri(entry.content).get_basename();
				this.showText(file ?? '', true);
				break;
			}
			case ItemType.Files: {
				const n = entry.content.split('\n').length;
				this.showText(ngettext('%d File', '%d Files', n).format(n));
				break;
			}
			case ItemType.Color: {
				const color = Color.parse(entry.content)?.hex();
				if (!color) return;
				const pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, false, 8, 32, 32);
				pixbuf.fill(parseInt(color.toString().padEnd(9, 'f').replace('#', '0x')));
				const [, buffer] = pixbuf.save_to_bufferv('png', null, null);
				this.showImageBytes(buffer);
				break;
			}
		}
	}

	showText(text, start = false) {
		const label = new St.Label({
			style_class: 'indicator-label',
			y_align: Clutter.ActorAlign.CENTER,
			text,
		});
		label.clutter_text.ellipsize = start ? Pango.EllipsizeMode.START : Pango.EllipsizeMode.END;
		this.previewWidget = label;
	}

	showImageFile(file) {
		if (!file.query_exists(null)) return;
		this.previewWidget = new St.Icon({
			style_class: 'system-status-icon',
			gicon: Gio.FileIcon.new(file),
			y_align: Clutter.ActorAlign.CENTER,
		});
	}

	showImageBytes(bytes) {
		this.previewWidget = new St.Icon({
			style_class: 'system-status-icon',
			gicon: Gio.BytesIcon.new(bytes),
			y_align: Clutter.ActorAlign.CENTER,
		});
	}

	confirmClearHistory() {
		const dialog = new ConfirmClearHistoryDialog();
		dialog.connect('clear-history', (_dialog, history) => this.emit('clear-history', history));
		dialog.open();
	}

	// DIAG v8 : mémorise l'origine de l'ouverture et le retard entre l'événement physique et son traitement
	// par le shell (indicatif). À retirer une fois la latence d'ouverture comprise.
	markOpen(source, event = null) {
		this.diagSource = source;
		this.diagEventDelay = null;
		try {
			if (event) {
				const delay = GLib.get_monotonic_time() / 1000 - event.get_time();
				if (Math.abs(delay) < 60000) this.diagEventDelay = Math.round(delay);
			}
		} catch {
			// Ignore
		}
	}

	cancelHoverOpen() {
		if (this._hoverTimeoutId) {
			GLib.source_remove(this._hoverTimeoutId);
			this._hoverTimeoutId = 0;
		}
	}

	isPointerInside() {
		const [x, y] = global.get_pointer();
		const box = this.get_transformed_extents();
		return (
			x >= box.get_x() &&
			x < box.get_x() + box.get_width() &&
			y >= box.get_y() &&
			y < box.get_y() + box.get_height()
		);
	}

	/**
	 * Called when the clipboard dialog closes. If the pointer is still resting on the
	 * indicator (e.g. the dialog was closed by clicking the icon), do not reopen it by
	 * hover until the pointer has left the indicator.
	 */
	suppressHoverOpen() {
		this.cancelHoverOpen();
		this._hoverSuppressed = this.isPointerInside();
	}

	vfunc_enter_event(event) {
		this.cancelHoverOpen();
		if (this._hoverSuppressed) return super.vfunc_enter_event(event);

		// Open the dialog after the pointer has rested on the indicator for a short delay,
		// so that merely crossing the top bar does not open it.
		const delay = this.ext.settings.get_int('hover-open-delay');
		if (this.ext.settings.get_boolean('open-on-hover') && delay > 0) {
			this._hoverTimeoutId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, delay, () => {
				this._hoverTimeoutId = 0;
				const buttons =
					Clutter.ModifierType.BUTTON1_MASK |
					Clutter.ModifierType.BUTTON2_MASK |
					Clutter.ModifierType.BUTTON3_MASK;
				if (this.hover && !this.menu.isOpen && (global.get_pointer()[2] & buttons) === 0) {
					this.markOpen('survol');
					this.emit('open-dialog');
				}
				return GLib.SOURCE_REMOVE;
			});
		}
		return super.vfunc_enter_event(event);
	}

	vfunc_leave_event(event) {
		this.cancelHoverOpen();

		// Grabs can emit spurious leave events: only re-arm hover once the pointer is really outside
		if (this._hoverSuppressed && !this.isPointerInside()) this._hoverSuppressed = false;
		return super.vfunc_leave_event(event);
	}

	vfunc_button_press_event(event) {
		if (event.get_button() === Clutter.BUTTON_PRIMARY) {
			// Open on release: opening during the press competes with the implicit
			// pointer grab, which could make the modal grab fail silently.
			this.cancelHoverOpen();
			return Clutter.EVENT_STOP;
		}
		if (event.get_button() === Clutter.BUTTON_MIDDLE) {
			this.ext.openPreferences();
			return Clutter.EVENT_STOP;
		}
		return Clutter.EVENT_PROPAGATE;
	}

	vfunc_button_release_event(event) {
		if (event.get_button() === Clutter.BUTTON_PRIMARY) {
			this.markOpen('clic', event);
			this.emit('open-dialog');
			return Clutter.EVENT_STOP;
		}
		return Clutter.EVENT_PROPAGATE;
	}

	vfunc_touch_event(event) {
		if (event.type() === Clutter.EventType.TOUCH_BEGIN) {
			this.markOpen('tactile', event);
			this.emit('open-dialog');
			return Clutter.EVENT_STOP;
		}
		return Clutter.EVENT_PROPAGATE;
	}

	destroy() {
		this.cancelHoverOpen();
		this.ext.settings.disconnectObject(this);
		super.destroy();
	}
};
ClipboardIndicator = __decorate(
	[
		registerClass({
			Properties: {
				incognito: GObject.ParamSpec.boolean('incognito', null, null, GObject.ParamFlags.READWRITE, false),
			},
			Signals: {
				'open-dialog': {},
				'clear-history': {
					param_types: [GObject.TYPE_INT],
				},
			},
		}),
	],
	ClipboardIndicator,
);

export { ClipboardIndicator };
