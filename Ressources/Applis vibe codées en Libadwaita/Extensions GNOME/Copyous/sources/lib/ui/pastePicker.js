// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.
import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import GObject from 'gi://GObject';
import Mtk from 'gi://Mtk';
import Pango from 'gi://Pango';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

import { ItemType } from '../common/constants.js';
import { Icon, loadIcon } from '../common/icons.js';
import { formatCompactTimeSpan } from './items/clipboardItemHeader.js';

const SHOWN = 10;
const WIDTH = 380;
const MARGIN = 12;

const TypeIcons = {
	[ItemType.Text]: Icon.Text,
	[ItemType.Code]: Icon.Code,
	[ItemType.Image]: Icon.Image,
	[ItemType.File]: Icon.File,
	[ItemType.Files]: Icon.Folder,
	[ItemType.Link]: Icon.Link,
	[ItemType.Character]: Icon.Character,
	[ItemType.Color]: Icon.Color,
};

const TypeNames = {
	[ItemType.Text]: 'Texte',
	[ItemType.Code]: 'Code',
	[ItemType.Image]: 'Image',
	[ItemType.File]: 'Fichier',
	[ItemType.Files]: 'Fichiers',
	[ItemType.Link]: 'Lien',
	[ItemType.Character]: 'Caractère',
	[ItemType.Color]: 'Couleur',
};

function fileUris(entry) {
	return entry.content.split('\n').filter((uri) => uri.length > 0);
}

function shortPath(path) {
	const home = GLib.get_home_dir();
	return path.startsWith(home) ? `~${path.slice(home.length)}` : path;
}

function titleText(entry) {
	if (entry.title) return entry.title;
	switch (entry.type) {
		case ItemType.Image:
			return 'Image';
		case ItemType.File:
			return Gio.File.new_for_uri(entry.content).get_basename() ?? 'Fichier';
		case ItemType.Files: {
			const uris = fileUris(entry);
			const first = Gio.File.new_for_uri(uris[0] ?? '').get_basename() ?? 'Fichiers';
			return uris.length > 1 ? `${first} et ${uris.length - 1} autre${uris.length > 2 ? 's' : ''}` : first;
		}
		case ItemType.Link:
		case ItemType.Character:
		case ItemType.Color:
			return entry.content;
		default:
			break;
	}
	const line = entry.content.split('\n').find((l) => l.trim().length > 0) ?? '';
	return line.replace(/\s+/g, ' ').trim().slice(0, 300);
}

function subtitleText(entry) {
	const time = formatCompactTimeSpan(entry.datetime);
	if (entry.type === ItemType.File || entry.type === ItemType.Files) {
		const parent = Gio.File.new_for_uri(fileUris(entry)[0] ?? '').get_parent()?.get_path();
		if (parent) return `${shortPath(parent)} · ${time}`;
	}
	return `${TypeNames[entry.type] ?? 'Texte'} · ${time}`;
}

function matchesEntry(entry, query) {
	if (!query) return true;
	const fields = [entry.title, entry.content, TypeNames[entry.type]];
	return fields.some((field) => field && field.toLowerCase().includes(query));
}

function accentTint() {
	const [accent] = St.ThemeContext.get_for_stage(global.stage).get_accent_color();
	return `rgba(${accent.red}, ${accent.green}, ${accent.blue}, 0.22)`;
}

// Row: round selection check (always visible), type icon or thumbnail, title and subtitle,
// accent pin for pinned entries. A click on the row pastes it; a click on the check (or Space)
// toggles the selection without closing the popup.
const PastePickerItem = GObject.registerClass(
	class PastePickerItem extends PopupMenu.PopupBaseMenuItem {
		_init(picker, entry) {
			super._init({ style_class: 'copyous-picker-item' });
			this.setOrnament(PopupMenu.Ornament.HIDDEN);
			this.picker = picker;
			this.entry = entry;

			this._check = new St.Button({
				style_class: 'copyous-picker-check',
				toggle_mode: true,
				can_focus: false,
				y_align: Clutter.ActorAlign.CENTER,
				child: new St.Icon({ icon_name: 'object-select-symbolic', style_class: 'copyous-picker-check-mark' }),
			});
			this._check.connect('clicked', () => this.toggle());
			this.add_child(this._check);

			this.add_child(this._buildLead(entry));

			const text = new St.BoxLayout({ orientation: Clutter.Orientation.VERTICAL, x_expand: true, y_align: Clutter.ActorAlign.CENTER });
			const title = new St.Label({ style_class: 'copyous-picker-title', text: titleText(entry) });
			title.clutter_text.ellipsize = Pango.EllipsizeMode.END;
			const subtitle = new St.Label({ style_class: 'copyous-picker-subtitle', text: subtitleText(entry) });
			subtitle.clutter_text.ellipsize = Pango.EllipsizeMode.END;
			text.add_child(title);
			text.add_child(subtitle);
			this.label_actor = title;
			this.add_child(text);

			if (entry.pinned) {
				this.add_child(new St.Icon({
					style_class: 'copyous-picker-pin',
					gicon: loadIcon(picker.ext, Icon.Pin),
					y_align: Clutter.ActorAlign.CENTER,
				}));
			}

			this.updateSelected();
		}

		_buildLead(entry) {
			if (entry.type === ItemType.Image) {
				const path = Gio.File.new_for_uri(entry.content).get_path();
				if (path) {
					return new St.Widget({
						style_class: 'copyous-picker-thumb',
						style: `background-image: url("${path}");`,
						y_align: Clutter.ActorAlign.CENTER,
					});
				}
			}
			return new St.Icon({
				style_class: 'copyous-picker-icon',
				gicon: loadIcon(this.picker.ext, TypeIcons[entry.type] ?? Icon.Text),
				y_align: Clutter.ActorAlign.CENTER,
			});
		}

		toggle() {
			this.picker.toggleSelected(this.entry);
		}

		updateSelected() {
			const selected = this.picker.isSelected(this.entry);
			this._check.checked = selected;
			this.style = selected ? `background-color: ${this.picker.tint};` : null;
		}

		activate(event) {
			if (event?.type() === Clutter.EventType.KEY_PRESS && event.get_key_symbol() === Clutter.KEY_space) {
				this.toggle();
				return;
			}
			super.activate(event);
		}
	},
);

// Multi-paste popup opened by its shortcut at the text cursor or the pointer.
export class PastePicker {
	ext;
	tint = null;
	_cursor = null;
	_menu = null;
	_anchor = null;
	_manager = null;
	_list = null;
	_filter = null;
	_hint = null;
	_actions = null;
	_count = null;
	_selected = new Set();
	_pending = new Map();
	_onPaste;

	constructor(ext, { onPaste }) {
		this.ext = ext;
		this._onPaste = onPaste;

		Main.inputMethod.connectObject(
			'cursor-location-changed',
			(_source, rect) => {
				if (isNaN(rect.get_x()) || isNaN(rect.get_y())) return;
				const p = rect.get_bottom_right();
				this._cursor = { x: p.x + 4, y: p.y + 4, width: 1, height: 1 };
			},
			'focus-out',
			() => (this._cursor = null),
			this,
		);
	}

	get isOpen() {
		return !!this._menu?.isOpen;
	}

	toggle() {
		if (this.isOpen) this.close();
		else this.open();
	}

	isSelected(entry) {
		return this._selected.has(entry.id);
	}

	toggleSelected(entry) {
		if (this._selected.has(entry.id)) this._selected.delete(entry.id);
		else this._selected.add(entry.id);
		this._refreshSelection();
	}

	clearSelection() {
		this._selected.clear();
		this._refreshSelection();
	}

	_entries() {
		return this.ext.entryTracker?.entries ?? [];
	}

	_filteredEntries() {
		const query = this._filter.get_text().trim().toLowerCase();
		const found = this._entries().filter((entry) => matchesEntry(entry, query));
		return [...found.filter((e) => e.pinned), ...found.filter((e) => !e.pinned)];
	}

	_selectedEntries() {
		const byId = new Map(this._entries().map((entry) => [entry.id, entry]));
		return [...this._selected].map((id) => byId.get(id)).filter(Boolean);
	}

	open() {
		this.close();
		this._selected.clear();
		this.tint = accentTint();

		const [pointerX, pointerY] = global.get_pointer();
		const area = this._cursor ?? { x: pointerX, y: pointerY, width: 1, height: 1 };

		this._anchor = new St.Widget({ width: 1, height: 1, x: area.x, y: area.y });
		Main.uiGroup.add_child(this._anchor);

		const menu = new PopupMenu.PopupMenu(this._anchor, 0.0, St.Side.TOP);
		menu.actor.add_style_class_name('copyous-paste-picker');
		if (Main.getStyleVariant() === 'light') menu.actor.add_style_class_name('copyous-picker-light');
		const scale = St.ThemeContext.get_for_stage(global.stage).scale_factor;
		const monitor = global.display.get_monitor_index_for_rect(
			new Mtk.Rectangle({ x: Math.round(area.x), y: Math.round(area.y), width: 1, height: 1 }),
		);
		const workArea = Main.layoutManager.getWorkAreaForMonitor(Math.max(0, monitor));
		menu.box.width = Math.min(WIDTH * scale, workArea.width - 2 * MARGIN * scale);
		Main.uiGroup.add_child(menu.actor);
		menu.actor.hide();
		this._manager = new PopupMenu.PopupMenuManager(this._anchor);
		this._manager.addMenu(menu);
		this._menu = menu;
		menu.connect('open-state-changed', (_menu, isOpen) => {
			if (!isOpen) this._destroyLater();
		});

		this._build(menu);
		menu.open();
		this._filter.clutter_text.grab_key_focus();
	}

	_build(menu) {
		const filterItem = new PopupMenu.PopupBaseMenuItem({ reactive: false, can_focus: false });
		filterItem.setOrnament(PopupMenu.Ornament.HIDDEN);
		this._filter = new St.Entry({
			style_class: 'search-entry copyous-picker-filter',
			hint_text: 'Filtrer',
			can_focus: true,
			x_expand: true,
			primary_icon: new St.Icon({ style_class: 'search-entry-icon', icon_name: 'edit-find-symbolic' }),
		});
		filterItem.add_child(this._filter);
		menu.addMenuItem(filterItem);

		this._filter.clutter_text.connect('text-changed', () => this._show());
		this._filter.clutter_text.connect('activate', () => this._onEnter());
		this._filter.clutter_text.connect('key-press-event', (_actor, event) => {
			if (event.get_key_symbol() !== Clutter.KEY_Down) return Clutter.EVENT_PROPAGATE;
			this._items()[0]?.grab_key_focus();
			return Clutter.EVENT_STOP;
		});

		this._list = new PopupMenu.PopupMenuSection();
		menu.addMenuItem(this._list);
		this._list.connect('activate', (_section, item) => {
			if (item instanceof PastePickerItem) this._paste([item.entry]);
		});

		menu.addMenuItem(this._buildFooter());
		this._show();
	}

	_buildFooter() {
		const footer = new PopupMenu.PopupBaseMenuItem({ reactive: false, can_focus: false, style_class: 'copyous-picker-footer' });
		footer.setOrnament(PopupMenu.Ornament.HIDDEN);

		this._hint = new St.BoxLayout({ style_class: 'copyous-picker-hint', x_expand: true, x_align: Clutter.ActorAlign.CENTER });
		for (const [key, action] of [['Entrée', 'coller'], ['Espace', 'sélectionner'], ['Échap', 'fermer']]) {
			this._hint.add_child(new St.Label({ style_class: 'copyous-picker-key', text: key, y_align: Clutter.ActorAlign.CENTER }));
			this._hint.add_child(new St.Label({ style_class: 'copyous-picker-key-action', text: action, y_align: Clutter.ActorAlign.CENTER }));
		}
		footer.add_child(this._hint);

		this._actions = new St.BoxLayout({ style_class: 'copyous-picker-actions', x_expand: true });
		this._count = new St.Label({ style_class: 'copyous-picker-count', x_expand: true, y_align: Clutter.ActorAlign.CENTER });
		const cancel = new St.Button({ style_class: 'copyous-picker-pill', label: 'Annuler', can_focus: true });
		cancel.connect('clicked', () => this.clearSelection());
		const paste = new St.Button({ style_class: 'copyous-picker-pill copyous-picker-pill-accent', label: 'Coller', can_focus: true });
		paste.connect('clicked', () => this._paste(this._selectedEntries()));
		this._actions.add_child(this._count);
		this._actions.add_child(cancel);
		this._actions.add_child(paste);
		footer.add_child(this._actions);

		return footer;
	}

	_items() {
		return this._list._getMenuItems().filter((item) => item instanceof PastePickerItem);
	}

	_show() {
		this._list.removeAll();
		const found = this._filteredEntries();
		if (found.length === 0) {
			const empty = this._entries().length === 0 ? 'Aucun élément copié pour le moment' : 'Aucun résultat';
			const item = new PopupMenu.PopupMenuItem(empty, { reactive: false });
			item.setOrnament(PopupMenu.Ornament.HIDDEN);
			this._list.addMenuItem(item);
		} else {
			let separated = !found[0].pinned;
			for (const entry of found.slice(0, SHOWN)) {
				if (!separated && !entry.pinned) {
					this._list.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
					separated = true;
				}
				this._list.addMenuItem(new PastePickerItem(this, entry));
			}
		}
		this._refreshSelection();
	}

	_refreshSelection() {
		for (const item of this._items()) item.updateSelected();
		const n = this._selectedEntries().length;
		this._hint.visible = n === 0;
		this._actions.visible = n > 0;
		this._count.text = n === 1 ? '1 sélectionné' : `${n} sélectionnés`;
	}

	_onEnter() {
		const selected = this._selectedEntries();
		if (selected.length > 0) this._paste(selected);
		else if (this._items()[0]) this._paste([this._items()[0].entry]);
	}

	_paste(entries) {
		if (entries.length === 0) return;
		this.close();
		this._onPaste(entries);
	}

	close() {
		if (this._menu?.isOpen) this._menu.close();
		this._destroyLater();
	}

	// Destroy the menu outside of its own signal handlers.
	_destroyLater() {
		const menu = this._menu;
		const anchor = this._anchor;
		if (!menu) return;
		this._menu = null;
		this._anchor = null;
		this._manager = null;
		this._list = null;
		this._filter = null;
		this._hint = null;
		this._actions = null;
		this._count = null;
		menu.actor.hide();
		const id = GLib.idle_add(GLib.PRIORITY_DEFAULT, () => {
			this._pending.delete(id);
			menu.destroy();
			anchor.destroy();
			return GLib.SOURCE_REMOVE;
		});
		this._pending.set(id, [menu, anchor]);
	}

	destroy() {
		this.close();
		for (const [id, [menu, anchor]] of this._pending) {
			GLib.source_remove(id);
			menu.destroy();
			anchor.destroy();
		}
		this._pending.clear();
		Main.inputMethod.disconnectObject(this);
		this._selected.clear();
	}
}
