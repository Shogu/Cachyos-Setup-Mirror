// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.
import Clutter from 'gi://Clutter';
import St from 'gi://St';

// Pochette aux coins arrondis au rayon de GNOME (8 px) : St ne découpe pas une
// icône, mais arrondit une image de fond. La pochette locale (file://) devient
// donc le fond d'un St.Bin placé à la place de l'icône de la carte ; une
// pochette distante (navigateur) garde l'icône carrée native.
// La carte appartient à l'extension (MediaSlot) : l'icône n'a pas à être remise.
export class RoundedCover {
    constructor(message, player) {
        this._icon = message._icon;
        this._player = player;
        this._bin = new St.Bin({style_class: 'tcw-cover', y_expand: true, y_align: Clutter.ActorAlign.START});
        this._icon.get_parent().replace_child(this._icon, this._bin);
        this._changedId = player.connect('changed', () => this._sync());
        this._sync();
    }

    _sync() {
        const url = this._player.trackCoverUrl;
        const local = Boolean(url?.startsWith('file://'));
        this._bin.child = local ? null : this._icon;
        this._bin.style = local ? `background-image: url("${url.replace(/"/g, '%22')}");` : null;
        if (local)
            this._bin.add_style_class_name('tcw-cover-image');
        else
            this._bin.remove_style_class_name('tcw-cover-image');
    }

    destroy() {
        this._player.disconnect(this._changedId);
        this._bin.child = null;
        this._icon.destroy();
        this._icon = null;
        this._player = null;
        this._bin = null;
    }
}
