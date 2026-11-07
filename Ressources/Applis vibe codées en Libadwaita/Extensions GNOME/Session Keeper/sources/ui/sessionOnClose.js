import * as EndSessionDialog from 'resource:///org/gnome/shell/ui/endSessionDialog.js';
import { InjectionManager } from 'resource:///org/gnome/shell/extensions/extension.js';
import { Log } from '../utils/log.js';

const logger = Log.getDefault();

let injectionManager = null;

export function initSessionOnClose(sessionManager) {
    if (injectionManager)
        return;

    const DialogClass = EndSessionDialog.EndSessionDialog;
    if (!DialogClass?.prototype?._confirm) {
        logger.warning('EndSessionDialog._confirm introuvable : enregistrement automatique désactivé');
        return;
    }

    injectionManager = new InjectionManager();
    injectionManager.overrideMethod(DialogClass.prototype, '_confirm', originalConfirm => {
        return function (...args) {
            try {
                // Flush final synchrone : contrairement aux sauvegardes continues asynchrones,
                // celui-ci doit être terminé avant que GNOME poursuive la fermeture.
                sessionManager.flushOnClose();
            }
            catch (error) {
                logger.error(error, 'Erreur lors de l’enregistrement de la session à la fermeture');
            }

            return originalConfirm.call(this, ...args);
        };
    });

    logger.info('Interception de fin de session installée via InjectionManager');
}

export function restoreSessionOnClose() {
    if (!injectionManager)
        return;

    injectionManager.clear();
    injectionManager = null;
    logger.info('Interception de fin de session supprimée');
}
