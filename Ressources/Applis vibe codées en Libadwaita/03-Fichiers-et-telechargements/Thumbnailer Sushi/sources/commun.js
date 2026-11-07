// SPDX-License-Identifier: GPL-2.0-or-later
// Outils partagés par les plugins Sushi de « sushi-thumbnailer-docs-extra ».
// Ce module n'est pas dans le dossier des plugins : Sushi ne le charge pas
// comme afficheur, il est seulement importé par les deux plugins.

import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

Gio._promisify(Gio.Subprocess.prototype, 'communicate_utf8_async');
Gio._promisify(Gio.Subprocess.prototype, 'communicate_async');
Gio._promisify(Gio.File.prototype, 'load_contents_async');

export const DOSSIER = GLib.path_get_dirname(GLib.filename_from_uri(import.meta.url)[0]);
export const PYTHON = '/usr/bin/python3';
export const DELAI_MAX_MS = 30000;   // au-delà, l'aperçu est abandonné

/** Erreur GLib affichable telle quelle par la page d'erreur de Sushi. */
export const erreur = message =>
    new GLib.Error(Gio.IOErrorEnum, Gio.IOErrorEnum.FAILED, message);

export const estAnnulation = e =>
    e instanceof GLib.Error && e.matches(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED);

/**
 * Lance un programme sans shell et attend sa fin, avec un délai maximal.
 * Le processus est tué si l'aperçu est fermé (cancellable) ou trop lent.
 * @returns {Promise<string>} la sortie standard
 */
export async function executer(argv, cancellable, delaiMs = DELAI_MAX_MS) {
    const proc = Gio.Subprocess.new(argv,
        Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);

    let delaiDepasse = false;
    const idDelai = GLib.timeout_add(GLib.PRIORITY_DEFAULT, delaiMs, () => {
        delaiDepasse = true;
        proc.force_exit();
        return GLib.SOURCE_REMOVE;
    });
    const idAnnulation = cancellable.connect(() => proc.force_exit());

    try {
        const [sortie, erreurs] = await proc.communicate_utf8_async(null, null);
        if (delaiDepasse)
            throw erreur(`Aperçu abandonné : délai de ${delaiMs / 1000} s dépassé.`);
        if (cancellable.is_cancelled())
            throw new GLib.Error(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED, 'Annulé');
        if (!proc.get_successful()) {
            const message = (erreurs ?? '').trim().split('\n').pop();
            throw erreur(message || "Échec de la préparation de l'aperçu.");
        }
        return sortie ?? '';
    } finally {
        if (!delaiDepasse)
            GLib.source_remove(idDelai);
        cancellable.disconnect(idAnnulation);
    }
}

/** Taille lisible, avec les unités de GLib (traduites par la locale). */
export const taille = octets => GLib.format_size(octets);

/**
 * Comme executer(), mais rend la sortie standard telle quelle (octets) :
 * c'est ce qu'il faut pour une image rendue par poppler.
 * @returns {Promise<Uint8Array>} la sortie standard
 */
export async function executerOctets(argv, cancellable, delaiMs = DELAI_MAX_MS) {
    const proc = Gio.Subprocess.new(argv,
        Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);

    let delaiDepasse = false;
    const idDelai = GLib.timeout_add(GLib.PRIORITY_DEFAULT, delaiMs, () => {
        delaiDepasse = true;
        proc.force_exit();
        return GLib.SOURCE_REMOVE;
    });
    const idAnnulation = cancellable.connect(() => proc.force_exit());

    try {
        const [sortie, erreurs] = await proc.communicate_async(null, null);
        if (delaiDepasse)
            throw erreur(`Aperçu abandonné : délai de ${delaiMs / 1000} s dépassé.`);
        if (cancellable.is_cancelled())
            throw new GLib.Error(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED, 'Annulé');
        if (!proc.get_successful()) {
            const texte = erreurs ? new TextDecoder('utf-8').decode(erreurs.toArray()) : '';
            const message = texte.trim().split('\n').pop();
            throw erreur(message || "Échec de la préparation de l'aperçu.");
        }
        return sortie ? sortie.toArray() : new Uint8Array();
    } finally {
        if (!delaiDepasse)
            GLib.source_remove(idDelai);
        cancellable.disconnect(idAnnulation);
    }
}
