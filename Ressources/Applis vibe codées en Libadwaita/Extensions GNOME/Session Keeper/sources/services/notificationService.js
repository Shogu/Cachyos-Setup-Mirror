import * as MessageTray from 'resource:///org/gnome/shell/ui/messageTray.js';
import { gettext as _ } from 'resource:///org/gnome/shell/extensions/extension.js';
import { Log } from '../utils/log.js';

const logger = Log.getDefault();

export class NotificationService {
    static showRestoreNotification(onRestore) {
        try {
            const source = MessageTray.getSystemSource();
            const notification = new MessageTray.Notification({
                source,
                title: _('Gestionnaire de session'),
                body: _('Une session enregistrée est disponible pour restauration'),
                // CRITICAL : la bannière reste affichée jusqu'à ce qu'on agisse dessus
                // et elle est dépliée d'office, donc « Restaurer » est visible sans
                // avoir à dérouler la notification.
                urgency: MessageTray.Urgency.CRITICAL,
            });

            let handled = false;
            const restoreOnce = () => {
                if (handled)
                    return;
                handled = true;
                onRestore();
            };

            notification.addAction(_('Restaurer'), restoreOnce);
            notification.addAction(_('Annuler'), () => {
                handled = true;
            });
            notification.connect('activated', restoreOnce);
            source.addNotification(notification);
        }
        catch (error) {
            logger.error(error, 'Échec de l’affichage de la notification de restauration');
        }
    }
}
