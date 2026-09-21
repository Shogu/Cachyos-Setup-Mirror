# Raindrop.io — extension Chrome/Vivaldi  avec icônes Adwaita

Cette variante est volontairement réduite à une seule action : cliquer sur
l’icône de l’extension pour enregistrer la page courante dans Raindrop.io.

Elle vise Chromium et Vivaldi uniquement. 

## Résultat visible

L’icône de la barre d’outils possède deux états :

| État | Ressource Adwaita | Fichier utilisé par Chromium |
| --- | --- | --- |
| Page non enregistrée | actions/bookmark-new-symbolic.svg | src/assets/target/extension/action_chrome.svg puis les PNG action_chrome_16/24/32.png |
| Page enregistrée | emblems/emblem-ok-symbolic.svg | src/assets/target/extension/action_chrome_saved.svg puis les PNG action_chrome_saved_16/24/32.png |



Les sources natives utilisées sont :

~~~text
/usr/share/icons/Adwaita/symbolic/actions/bookmark-new-symbolic.svg
/usr/share/icons/Adwaita/symbolic/emblems/emblem-ok-symbolic.svg
~~~


cp /usr/share/icons/Adwaita/symbolic/emblems/emblem-ok-symbolic.svg \
   src/assets/target/extension/action_chrome_saved.svg
~~~



1. Ouvrir une page web dans Vivaldi avec une session Raindrop.io connectée.
2. Charger l’extension non empaquetée.
3. Cliquer une fois sur l’icône normale.
4. Attendre la réponse de l’API : l’icône devient immédiatement la coche
   Adwaita.
5. Recharger la page ou changer d’onglet : l’icône cochée doit rester affichée
   si le lien existe dans Raindrop.

Si la coche ne s’affiche pas, ouvrir le lien « Service worker » de l’extension
dans vivaldi://extensions et vérifier l’erreur affichée. Les causes utiles à
distinguer sont alors : session Raindrop expirée, requête API bloquée ou page
non HTTP(S). Le code ne dépend plus d’un popup qui pourrait masquer l’erreur.
