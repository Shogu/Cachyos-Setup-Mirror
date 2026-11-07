import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import Gio from 'gi://Gio';
import Meta from 'gi://Meta';
import St from 'gi://St';

import { Color } from '../common/color.js';
import { ItemType, getImagesPath } from '../common/constants.js';
import { registerClass } from '../common/gjs.js';
import { ClipboardEntry, FileOperation } from '../database/database.js';
import { Keyboard } from './keyboard.js';

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

Gio._promisify(Gio.File.prototype, 'load_contents_async');
Gio._promisify(Gio.File.prototype, 'replace_contents_async');
Gio._promisify(Gio.MemoryOutputStream.prototype, 'splice_async');
Gio._promisify(Meta.SelectionSource.prototype, 'read_async');
const Utf8Decoder = new TextDecoder();
const Utf8Encoder = new TextEncoder();
const GraphemeSegmenter = new Intl.Segmenter();
const MimeTypes = {
	Text: ['text/plain;charset=utf-8', 'UTF8_STRING', 'text/plain', 'STRING'],
	Image: ['image/png', 'image/jxl', 'image/webp', 'image/avif', 'image/jpeg'],
	File: ['x-special/gnome-copied-files', 'text/uri-list'],
	Sensitive: ['x-kde-passwordManagerHint'],
};

export const ContentType = {
	Text: 0,
	Image: 1,
	File: 2,
};

function contentChecksum(content) {
	switch (content.type) {
		case ContentType.Text:
			return GLib.compute_checksum_for_string(GLib.ChecksumType.MD5, content.text, content.text.length);
		case ContentType.Image:
			return content.checksum;
		case ContentType.File: {
			const s = content.paths.map((f) => decodeURI(f).substring('file://'.length)).join('\n');
			return GLib.compute_checksum_for_string(GLib.ChecksumType.MD5, s, s.length);
		}
	}
}

function hasMoreGraphemes(text, max) {
	const iterator = GraphemeSegmenter.segment(text)[Symbol.iterator]();
	for (let i = 0; i < max; i++) iterator.next();
	return iterator.next().value !== undefined;
}

let ClipboardManager = class ClipboardManager extends GObject.Object {
	ext;
	tracker;
	selection;
	clipboard;
	keyboard;
	signalId = -1;
	pasteSignalId = -1;
	prevClipboard = null;
	accumulateBuffer = [];
	pasteSequence = 0;
	delayIds = new Set();

	constructor(ext, tracker) {
		super();
		this.ext = ext;
		this.tracker = tracker;
		this.selection = global.display.get_selection();
		this.clipboard = St.Clipboard.get_default();
		this.signalId = this.selection.connect('owner-changed', this.ownerChanged.bind(this));

		// Accumulate mode: the buffer lives in memory, so always start disabled and
		// clear the buffer whenever the mode is toggled.
		this.ext.settings.set_boolean('accumulate', false);
		this.ext.settings.connectObject('changed::accumulate', () => (this.accumulateBuffer = []), this);
	}

	destroy() {
		this.ext.settings.disconnectObject(this);
		this.accumulateBuffer = [];
		this.pasteSequence++;
		for (const id of this.delayIds) GLib.source_remove(id);
		this.delayIds.clear();
		this.keyboard?.destroy();
		this.keyboard = undefined;
		if (this.signalId >= 0) this.selection.disconnect(this.signalId);
		if (this.pasteSignalId >= 0) GLib.source_remove(this.pasteSignalId);
		this.signalId = -1;
		this.pasteSignalId = -1;
	}

	copyContent(content) {
		const checksum = contentChecksum(content);
		if (!checksum) return;
		this.prevClipboard = [content.type, checksum];

		// Text
		if (content.type === ContentType.Text) {
			this.clipboard.set_text(St.ClipboardType.CLIPBOARD, content.text);
			if (this.ext.settings.get_boolean('sync-primary')) {
				this.clipboard.set_text(St.ClipboardType.PRIMARY, content.text);
			}
			return;
		}

		// Image
		if (content.type === ContentType.Image) {
			this.clipboard.set_content(St.ClipboardType.CLIPBOARD, content.mimetype, content.data);
			return;
		}

		// File
		if (content.type === ContentType.File) {
			const s = `${FileOperation.Copy}\n${content.paths.join('\n')}`;
			const bytes = Utf8Encoder.encode(s);
			this.clipboard.set_content(St.ClipboardType.CLIPBOARD, MimeTypes.File[0], bytes);
			return;
		}
	}

	pasteContent(content) {
		this.copyContent(content);
		if (this.pasteSignalId >= 0) GLib.source_remove(this.pasteSignalId);
		return new Promise((resolve) => {
			this.pasteSignalId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 250, () => {
				this.keyboard ??= new Keyboard();

				// https://github.com/Tudmotu/gnome-shell-extension-clipboard-indicator/blob/89c57703641a9d5d15f899f6e780174641911d95/extension.js#L1094
				if (this.keyboard.purpose === Clutter.InputContentPurpose.TERMINAL) {
					this.keyboard.press(Clutter.KEY_Control_L);
					this.keyboard.press(Clutter.KEY_Shift_L);
					this.keyboard.press(Clutter.KEY_Insert);
					this.keyboard.release(Clutter.KEY_Insert);
					this.keyboard.release(Clutter.KEY_Shift_L);
					this.keyboard.release(Clutter.KEY_Control_L);
				} else {
					this.keyboard.press(Clutter.KEY_Shift_L);
					this.keyboard.press(Clutter.KEY_Insert);
					this.keyboard.release(Clutter.KEY_Insert);
					this.keyboard.release(Clutter.KEY_Shift_L);
				}
				this.pasteSignalId = -1;
				resolve();
				return GLib.SOURCE_REMOVE;
			});
		});
	}

	copyText(s) {
		this.copyContent({ type: ContentType.Text, text: s });
		this.emit('text', s);
	}

	pasteText(s) {
		this.pasteContent({ type: ContentType.Text, text: s });
	}

	copyPng(data, width, height) {
		const checksum = GLib.compute_checksum_for_bytes(GLib.ChecksumType.MD5, data);
		if (!checksum) return;
		this.copyContent({ type: ContentType.Image, mimetype: 'image/png', data, checksum });
		this.emit('image', data, width, height);
	}

	async copyEntry(entry) {
		await this.handleEntry(entry, false);
	}

	async pasteEntry(entry) {
		await this.handleEntry(entry, true);
	}

	/**
	 * Pastes several entries one after the other in the focused application.
	 * Each entry is put on the clipboard, pasted, then the next one replaces the
	 * clipboard once the application had time to process the paste.
	 * @param {Array} entries the entries to paste, in order
	 */
	async pasteEntries(entries) {
		const token = ++this.pasteSequence;
		for (const entry of entries) {
			if (token !== this.pasteSequence) return;
			await this.pasteEntry(entry);
			if (token !== this.pasteSequence) return;
			// Let the application process the paste before the clipboard changes.
			await new Promise((resolve) => {
				const id = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 300, () => {
					this.delayIds.delete(id);
					resolve();
					return GLib.SOURCE_REMOVE;
				});
				this.delayIds.add(id);
			});
		}
	}

	async handleEntry(entry, paste) {
		const fn = paste ? this.pasteContent.bind(this) : this.copyContent.bind(this);
		if (this.ext.settings.get_boolean('update-date-on-copy')) {
			entry.datetime = GLib.DateTime.new_now_utc();
		}
		switch (entry.type) {
			case ItemType.Text:
			case ItemType.Code:
			case ItemType.Link:
			case ItemType.Character:
			case ItemType.Color:
				return fn({ type: ContentType.Text, text: entry.content });
			case ItemType.Image:
				try {
					const image = Gio.File.new_for_uri(entry.content);
					const [contents, _etag] = await image.load_contents_async(null);
					const [contentType] = Gio.content_type_guess(image.get_path(), contents);
					const mimetype = Gio.content_type_get_mime_type(contentType);
					if (!mimetype) break;
					const checksum = GLib.compute_checksum_for_bytes(GLib.ChecksumType.MD5, contents);
					if (!checksum) return;
					return fn({ type: ContentType.Image, mimetype, data: contents, checksum });
				} catch {
					break;
				}
			case ItemType.File:
			case ItemType.Files: {
				const paths = entry.content.split('\n');
				return fn({ type: ContentType.File, paths, operation: FileOperation.Copy });
			}
		}
	}

	shouldSave(mimeTypes) {
		// Mime Type
		if (MimeTypes.Sensitive.some((value) => mimeTypes.includes(value))) {
			return false;
		}

		// WM Class
		const window = global.display.focus_window;
		if (window) {
			const exclusions = this.ext.settings.get_strv('wmclass-exclusions');
			if (exclusions.includes(window.wm_class)) return false;
		}
		return !this.ext.settings.get_boolean('incognito');
	}

	async ownerChanged(_selection, selectionType, selectionSource) {
		try {
			if (selectionSource === null) return;
			if (selectionType !== Meta.SelectionType.SELECTION_CLIPBOARD) return;
			const mimeTypes = selectionSource.get_mimetypes();
			const content = await this.getContent(selectionSource, mimeTypes);
			if (!content) return;
			const checksum = contentChecksum(content);
			if (!checksum) return;

			// Check duplicate
			if (this.prevClipboard) {
				const [type, prevChecksum] = this.prevClipboard;
				if (type === content.type && prevChecksum === checksum) {
					return;
				}

				// Do not update clipboard when clipboard ownership of a copied file is lost
				// i.e. nautilus is closed
				if (type === ContentType.File && content.type === ContentType.Text && prevChecksum === checksum) {
					return;
				}
			}
			this.prevClipboard = [content.type, checksum];

			// Accumulate mode: append copied text to the buffer and replace the
			// clipboard with all accumulated pieces, so a single paste inserts them all.
			if (
				content.type === ContentType.Text &&
				this.ext.settings.get_boolean('accumulate') &&
				!MimeTypes.Sensitive.some((value) => mimeTypes.includes(value))
			) {
				this.accumulateBuffer.push(content.text);
				if (this.accumulateBuffer.length > 1) {
					const combined = this.accumulateBuffer.reduce((acc, piece) =>
						acc.endsWith('\n') ? acc + piece : `${acc}\n${piece}`,
					);

					// copyContent updates prevClipboard, so the resulting owner-changed is ignored
					this.copyContent({ type: ContentType.Text, text: combined });
				}
			}

			// Check if history should be saved after setting the previous clipboard item.
			// This ensures that content copied in incognito mode is not saved to history
			// after copying an item after exiting incognito mode.
			if (!this.shouldSave(mimeTypes)) return;
			const res = await this.convertContent(content);
			if (!res) return;
			const [type, text, metadata] = res;
			const entry = await this.tracker.insert(type, text, metadata);
			if (entry) {
				this.emit('clipboard', entry);
			}
		} catch (e) {
			this.ext.logger.error(e);
		}
	}

	async getContent(selectionSource, mimeTypes) {
		async function getBytes(mimeType) {
			const source = await selectionSource.read_async(mimeType, null);
			const out = Gio.MemoryOutputStream.new_resizable();
			await out.splice_async(
				source,
				Gio.OutputStreamSpliceFlags.CLOSE_SOURCE | Gio.OutputStreamSpliceFlags.CLOSE_TARGET,
				GLib.PRIORITY_DEFAULT,
				null,
			);
			return out.steal_as_bytes().toArray();
		}

		// Image
		const imageMimeType = MimeTypes.Image.find((value) => mimeTypes.includes(value));
		if (imageMimeType) {
			const bytes = await getBytes(imageMimeType);
			if (bytes.length > 0) {
				const checksum = GLib.compute_checksum_for_bytes(GLib.ChecksumType.MD5, bytes);
				if (!checksum) return null;
				return { type: ContentType.Image, mimetype: imageMimeType, data: bytes, checksum };
			} else {
				return null;
			}
		}

		// File
		const fileMimeType = MimeTypes.File.find((value) => mimeTypes.includes(value));
		if (fileMimeType) {
			const bytes = await getBytes(fileMimeType);
			const text = Utf8Decoder.decode(bytes).trim();
			if (text) {
				const files = text
					.split('\n')
					.map((f) => f.trim())
					.filter((f) => f.length !== 0);
				const operation = files[0]?.toLowerCase();
				if (operation === FileOperation.Copy || operation === FileOperation.Cut) {
					return { type: ContentType.File, paths: files.slice(1), operation };
				} else {
					return { type: ContentType.File, paths: files, operation: FileOperation.Copy };
				}
			} else {
				return null;
			}
		}

		// Text
		const textMimeType = MimeTypes.Text.find((value) => mimeTypes.includes(value));
		if (textMimeType) {
			const bytes = await getBytes(textMimeType);
			const text = Utf8Decoder.decode(bytes);
			if (text && text.trim()) {
				return { type: ContentType.Text, text };
			} else {
				return null;
			}
		}
		return null;
	}

	async convertContent(content) {
		if (content.type === ContentType.Text) {
			const trimmed = content.text.trim();

			// Link
			try {
				if (trimmed.startsWith('http') && GLib.uri_is_valid(trimmed, GLib.UriFlags.NONE)) {
					return [ItemType.Link, content.text, null];
				}
			} catch {
				// Ignore
			}

			// Character
			const maxCharacters = this.ext.settings.get_child('character-item').get_int('max-characters');
			if (!hasMoreGraphemes(trimmed, maxCharacters)) {
				return [ItemType.Character, content.text, null];
			}

			// Color
			if (Color.parse(trimmed)) {
				return [ItemType.Color, content.text, null];
			}

			// Code
			const slice = trimmed.slice(0, 10000);
			const n = Math.max(1, slice.length / 100);
			const highlightResult = this.ext.hljs?.highlightAuto(slice);
			if (highlightResult && highlightResult.language && highlightResult.relevance / n >= 3) {
				const id = highlightResult.language;
				const name = this.ext.hljs?.getLanguage(id)?.name ?? id;
				const metadata = {
					language: { id, name: id.length < name.length - 3 ? id.charAt(0) + id.slice(1) : name },
				};
				return [ItemType.Code, content.text, metadata];
			}

			// Text
			return [ItemType.Text, content.text, null];
		}

		// Image
		if (content.type === ContentType.Image) {
			try {
				const path = getImagesPath(this.ext);
				if (!path.query_exists(null)) path.make_directory_with_parents(null);
				const extension = content.mimetype.split('/')[1];
				const image = path.get_child(`${content.checksum}.${extension}`);
				if (!image.query_exists(null)) {
					await image.replace_contents_async(
						content.data,
						null,
						false,
						Gio.FileCreateFlags.REPLACE_DESTINATION,
						null,
					);
				}
				return [ItemType.Image, image.get_uri(), null];
			} catch {
				return null;
			}
		}

		// File
		if (content.type === ContentType.File) {
			const metadata = { operation: content.operation };
			if (content.paths.length === 1) {
				return [ItemType.File, content.paths[0], metadata];
			} else {
				return [ItemType.Files, content.paths.join('\n'), metadata];
			}
		}
		return null;
	}
};
ClipboardManager = __decorate(
	[
		registerClass({
			Signals: {
				clipboard: {
					param_types: [ClipboardEntry.$gtype],
				},
				text: {
					param_types: [GObject.TYPE_STRING],
				},
				image: {
					param_types: [GObject.TYPE_JSOBJECT, GObject.TYPE_INT, GObject.TYPE_INT],
				},
			},
		}),
	],
	ClipboardManager,
);

export { ClipboardManager };
