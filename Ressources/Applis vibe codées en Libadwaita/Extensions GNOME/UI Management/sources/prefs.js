import Adw from 'gi://Adw';
import Gtk from 'gi://Gtk';
import Gio from 'gi://Gio';
import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

function sw(settings,key,title,subtitle='') {
  const r=new Adw.SwitchRow({title,subtitle}); settings.bind(key,r,'active',Gio.SettingsBindFlags.DEFAULT); return r;
}
function spin(settings,key,title,subtitle,lower,upper,step=1) {
  const r=new Adw.SpinRow({title,subtitle,adjustment:new Gtk.Adjustment({lower,upper,step_increment:step,page_increment:step*5})});
  settings.bind(key,r,'value',Gio.SettingsBindFlags.DEFAULT); return r;
}
function combo(settings,key,title,options,values=null) {
  const model=Gtk.StringList.new(options); const r=new Adw.ComboRow({title,model});
  const vals=values??options.map((_,i)=>i);
  const update=()=>{ const v=settings.get_int(key); const i=vals.indexOf(v); if(i>=0) r.selected=i; };
  update(); r.connect('notify::selected',()=>settings.set_int(key,vals[r.selected])); settings.connect(`changed::${key}`,update); return r;
}
function group(page,title,rows) { const g=new Adw.PreferencesGroup({title}); for(const r of rows) g.add(r); page.add(g); }

export default class UIManagementPrefs extends ExtensionPreferences {
  fillPreferencesWindow(window) {
    const s=this.getSettings(); window.set_default_size(920,760);

    const vis=new Adw.PreferencesPage({title:'Visibilité',icon_name:'view-reveal-symbolic'}); window.add(vis);
    group(vis,'Panneau et menus',[
      sw(s,'panel','Panneau'), sw(s,'panel-in-overview',"Panneau dans la vue d’ensemble"), sw(s,'activities-button','Bouton des activités'), sw(s,'clock-menu','Menu horloge'), sw(s,'keyboard-layout','Disposition du clavier'), sw(s,'accessibility-menu',"Menu d’accessibilité"), sw(s,'quick-settings','Réglages rapides'), sw(s,'quick-settings-dark-mode','Bouton du mode sombre'), sw(s,'quick-settings-backlight','Bouton du rétroéclairage'), sw(s,'quick-settings-do-not-disturb','Bouton Ne pas déranger'), sw(s,'quick-settings-night-light','Bouton veilleuse'), sw(s,'quick-settings-airplane-mode','Bouton mode avion'),
    ]);
    group(vis,'Horloge et indicateurs',[
      sw(s,'screen-sharing-indicator',"Indicateur de partage d’écran"), sw(s,'screen-recording-indicator',"Indicateur d’enregistrement d’écran"), sw(s,'world-clock','Horloge mondiale'), sw(s,'weather','Météo'), sw(s,'calendar','Calendrier'), sw(s,'events-button','Événements'), sw(s,'panel-notification-icon','Icône de notification du panneau'), sw(s,'power-icon','Icône de charge'), sw(s,'window-picker-icon','Icône de sélecteur de fenêtre'),
    ]);
    group(vis,'Vue d’ensemble et fenêtres',[
      sw(s,'search','Barre de recherche'), sw(s,'dash','Barre de raccourcis'), sw(s,'dash-separator','Séparateur du dash'), sw(s,'dash-app-running',"Indicateur d’application en cours"), sw(s,'show-apps-button','Afficher le bouton des applications'), sw(s,'osd','OSD'), sw(s,'workspace-popup',"Fenêtre contextuelle de l’espace de travail"), sw(s,'workspace',"Commutateur d’espace de travail"), sw(s,'workspaces-in-app-grid',"Grille d’applications des espaces de travail"), sw(s,'window-preview-close-button','Bouton de fermeture du sélecteur de fenêtre'), sw(s,'window-preview-caption','Légende du sélecteur de fenêtre'), sw(s,'background-menu',"Menu d’arrière-plan"), sw(s,'ripple-box',"Boîte d’ondulation"), sw(s,'window-menu','Menu de fenêtre'), sw(s,'window-menu-take-screenshot-button',"Bouton capture d’écran dans le menu Fenêtre"),
    ]);

    const beh=new Adw.PreferencesPage({title:'Comportement',icon_name:'preferences-system-symbolic'}); window.add(beh);
    group(beh,'Espaces de travail',[sw(s,'workspace-wrap-around',"Boucler les espaces de travail"),sw(s,'workspace-peek',"Aperçu de l’espace de travail"),sw(s,'workspace-thumbnail-to-main-view',"Clic sur une vignette : revenir à la vue principale"),sw(s,'workspace-switcher-should-show',"Toujours afficher le sélecteur d’espace de travail")]);
    group(beh,'Fenêtres et recherche',[sw(s,'window-demands-attention-focus',"Donner le focus aux fenêtres demandant l’attention"),sw(s,'window-maximized-on-create','Fenêtre agrandie par défaut'),sw(s,'type-to-search','Tapez pour rechercher')]);
    group(beh,'Clavier et transitions',[sw(s,'overlay-key','Touche Super active'),sw(s,'double-super-to-appgrid','Double appui sur Super : grille d’applications'),sw(s,'switcher-popup-delay','Supprimer le délai des pop-up'),combo(s,'startup-status','État de démarrage',['Bureau','Aperçu','Grille d’applications'],[0,1,2])]);

    const cus=new Adw.PreferencesPage({title:'Personnaliser',icon_name:'applications-graphics-symbolic'}); window.add(cus);
    group(cus,'Apparence',[sw(s,'accent-color-icon',"Couleur d’accentuation pour les icônes"),sw(s,'invert-calendar-column-items','Inverser les éléments de la colonne du calendrier')]);
    group(cus,'Panneau',[combo(s,'top-panel-position','Position du panneau',['Haut','Bas'],[0,1]),combo(s,'clock-menu-position',"Position du menu de l’horloge",['Centre','Droite','Gauche'],[0,1,2]),spin(s,'clock-menu-position-offset',"Décalage de la position du menu de l’horloge",'',0,20,1)]);
    group(cus,"Vue d’ensemble",[combo(s,'controls-manager-spacing-size',"Espacement de la vue d’ensemble",['Par défaut','Compact','Large'],[0,8,32]),combo(s,'workspace-background-corner-size',"Rayon de l’arrière-plan des espaces de travail",['Par défaut','0','8','16'],[0,1,2,3]),combo(s,'workspace-switcher-size',"Taille du sélecteur d’espace de travail",['Par défaut','Petit','Grand'],[0,1,2]),combo(s,'animation','Animation',['Désactivée','Vitesse par défaut','Rapide','Lente'],[0,1,2,3]),combo(s,'dash-icon-size','Taille des icônes du dash',['Par défaut','16','22','24','32','48','64'],[0,16,22,24,32,48,64])]);
    group(cus,'Notifications et sélecteurs',[combo(s,'notification-banner-position','Position des notifications',['En haut au centre','En haut à droite','En haut à gauche','En bas au centre','En bas à droite','En bas à gauche'],[1,2,3,4,5,6]),combo(s,'osd-position',"Position de l’OSD",['Par défaut','Haut','Centre','Bas'],[0,1,2,3]),combo(s,'alt-tab-window-preview-size',"Taille de l’aperçu de fenêtre Alt-Tab",['Par défaut','Petit','Moyen','Grand'],[0,128,192,256]),combo(s,'alt-tab-small-icon-size',"Taille de l’icône d’aperçu Alt-Tab",['Par défaut','16','24','32'],[0,16,24,32]),combo(s,'alt-tab-icon-size',"Taille de l’icône Alt-Tab",['Par défaut','32','48','64'],[0,32,48,64])]);

    const auto=new Adw.PreferencesPage({title:'Automatisation',icon_name:'system-run-symbolic'}); window.add(auto);
    group(auto,'Auto Activities',[sw(s,'auto-activities-enabled','Activer Auto Activities','Ouvrir la vue d’ensemble quand l’espace de travail devient vide'),sw(s,'isolate-workspaces','Limiter à l’espace de travail actif'),sw(s,'isolate-monitors','Limiter au moniteur actif'),sw(s,'skip-taskbar','Ignorer les fenêtres absentes de la barre des tâches'),sw(s,'skip-last-workspace','Ignorer le changement d’espace de travail'),sw(s,'detect-minimized','Considérer les fenêtres minimisées comme absentes'),sw(s,'hide-on-new-window','Fermer la vue d’ensemble lorsqu’une fenêtre apparaît'),spin(s,'window-checking-delay','Délai de vérification','millisecondes',0,5000,50),sw(s,'show-apps','Afficher directement la grille des applications')]);
    group(auto,'Hot Edge',[sw(s,'hot-edge-enabled','Activer Hot Edge','Bord inférieur chaud pour ouvrir la vue d’ensemble'),spin(s,'pressure-threshold','Pression d’activation','pixels',0,500,25),spin(s,'edge-size','Largeur du bord chaud','% de la largeur de l’écran',1,100,5),sw(s,'suppress-activation-when-button-held','Ne pas activer pendant un clic souris'),sw(s,'suppress-activation-when-fullscreen','Ne pas activer en plein écran'),sw(s,'primary-monitor-only','Moniteur principal uniquement'),sw(s,'show-animation','Animation lors de l’activation')]);
    group(auto,'Quick Close in Overview',[sw(s,'quick-close-enabled','Activer la fermeture rapide','Fermer une fenêtre dans la vue d’ensemble avec un clic'),spin(s,'close-button','Bouton de souris','1=gauche, 2=milieu, 3=droit',1,9,1),sw(s,'close-require-shift','Exiger Maj'),sw(s,'close-require-control','Exiger Ctrl'),sw(s,'keyboard-close','Autoriser la fermeture au clavier'),spin(s,'rearrange-delay','Délai avant réorganisation','millisecondes',0,5000,50)]);
  }
}
