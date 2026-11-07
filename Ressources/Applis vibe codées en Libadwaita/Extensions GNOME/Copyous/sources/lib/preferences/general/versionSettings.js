import Adw from 'gi://Adw';
import Gtk from 'gi://Gtk';

import { gettext as _ } from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

import { registerClass } from '../../common/gjs.js';

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

let VersionSettings = class VersionSettings extends Adw.PreferencesGroup {
	constructor(prefs, window) {
		const metadata = prefs.metadata;
		const version = metadata['version-name'] ?? metadata['version'] ?? _('Unknown');
		super({
			title: _('Version'),
		});
		const row = new Adw.ActionRow({
			title: _('Installed build'),
			subtitle: version,
			css_classes: ['property'],
		});
		const copyButton = new Gtk.Button({
			icon_name: 'edit-copy-symbolic',
			valign: Gtk.Align.CENTER,
			css_classes: ['flat'],
			tooltip_text: _('Copy version'),
		});
		copyButton.connect('clicked', () => {
			window.get_display().get_clipboard().set(version);
			window.add_toast(
				new Adw.Toast({
					title: _('Copied to clipboard'),
				}),
			);
		});
		row.add_suffix(copyButton);
		this.add(row);
	}
};
VersionSettings = __decorate([registerClass()], VersionSettings);

export { VersionSettings };
