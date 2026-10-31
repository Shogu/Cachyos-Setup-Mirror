# Pack Éléments Graphiques & Décors Lofi (Style Ghibli / Adwaita)

Ce paquet contient les décors de fond générés pour l'application Lofi Desktop Companion, ainsi qu'un guide technique d'intégration pour **GNOME Shell / GJS (Gnome JavaScript)** et le script Python d'automatisation.

---

## 1. Contenu du Pack

- `decor_diurne.jpg` : Décor de bureau de jour (temps clair/ensoleillé).
- `decor_pluie.jpg` : Décor de bureau par temps de pluie (gouttes d'eau sur la vitre, ciel couvert).
- `README.md` : Instructions et conseils d'intégration GJS.

---

## 2. Conseils d'Intégration & Animation GJS (GNOME Shell)

Pour créer une scène interactive et fluide dans GNOME Shell avec Clutter / St :

### A. Structure des Couches (Layers)
Organisez vos acteurs Clutter de bas en haut :
1. **Fond (Décor Fixe)** : `St.Widget` ou `Clutter.Actor` affichant `decor_diurne.jpg` ou `decor_pluie.jpg`.
2. **Couche Météo & Effets (SVG)** : 
   - `gouttes_pluie.svg` (Placées devant la vitre, animées sur l'axe Y).
   - `particules_lumineuses.svg` (Flottement doux avec variation d'opacité).
3. **Couche Mobilier / Accessoires** :
   - `lanterne_halo.svg` (Lanterne interactive / vacillement du halo).
   - `horloge_XX.svg` (Horloge mise à jour dynamiquement selon l'heure du système).
   - `vapeur_a.svg`, `vapeur_b.svg`, `vapeur_c.svg` (Placées au-dessus de la tasse de thé).
   - `origami_grue.svg` & `luciole.svg`.
4. **Couche Personnage** : Chihiro (PNG transparent).

### B. Bonnes Pratiques GJS & Clutter Animation
- **Opacité & Vacillement (Lanterne & Luciole)** :
  Utilisez `clutter_actor_ease()` avec une courbe d'animation sinusoïdale (`Clutter.AnimationMode.EASE_IN_OUT_SINE`) pour faire varier l'opacité entre `0.7` et `1.0`.
- **Animation de la Vapeur de Thé** :
  Alternez l'opacité et l'échelle (scale) des 3 variantes de vapeur pour donner l'impression d'une volute vivante :
  ```javascript
  vapeurActor.ease({
      opacity: 0,
      translation_y: -20,
      scale_x: 1.2,
      scale_y: 1.2,
      duration: 3000,
      mode: Clutter.AnimationMode.EASE_OUT_QUAD,
      onComplete: () => { /* Reset position et bascule sur vapeur_b.svg */ }
  });
  ```
- **Pluie glissante (Gouttes sur la vitre)** :
  Déplacez l'acteur `gouttes_pluie.svg` le long de la vitre avec une translation Y progressive et réinitialisez sa position une fois sortie du champ.

---

## 3. Explication du Code Python de Génération d'Horloge

Pour l'horloge déclinée en 25 exemplaires (de 22h00 à 22h48, par pas de 2 minutes), le script calcule mathématiquement l'orientation des aiguilles :

```python
# Angle de l'aiguille des minutes (360° / 60 min = 6° par minute)
minute_angle = minutes * 6.0

# Angle de l'aiguille des heures (360° / 12h = 30° par heure + progression selon les minutes)
hour_angle = (hours % 12) * 30.0 + (minutes / 60.0) * 30.0
```

Chaque fichier SVG est construit dynamiquement avec une balise `<g transform="rotate(ANGLE 70 70)">` appliquée à chaque aiguille autour du centre du cadran `(70, 70)`.

---
*Généré pour l'application Lofi Companion - Écosystème GNOME / Adwaita.*


Conseils pour l'intégration en GNOME Shell GJS :
Vapeur & Luciole :
Utilisez Clutter.Actor.set_opacity() ou des transitions CSS (transition: opacity 2.5s ease-in-out) pour faire apparaître puis disparaître alternativement les 3 variantes de vapeur et la luciole.

Animation de l'Horloge :
Il vous suffit de remplacer dynamiquement le fichier source ou la texture de l'élément St.Icon / Clutter.Texture avec la séquence de horloge_00.svg à horloge_24.svg à intervalle régulier.

Pluie & Particules :
Conservez le même Clutter.Actor et appliquez-lui une translation verticale répétée via clutter_actor_animate() ou ease() pour faire glisser doucement la goutte vers le bas.


HORLOGE: code oython pour aniamtion des aiguuiilles

import math
import opacity

def generate_clock_svg(filename, hours, minutes):
    # Calcul des angles exacts des aiguilles (0° à 12h)
    minute_angle = minutes * 6.0
    hour_angle = (hours % 12) * 30.0 + (minutes / 60.0) * 30.0

    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 140 140" width="140" height="140">
  <defs>
    <filter id="clockShadow" x="-15%" y="-15%" width="130%" height="130%">
      <feDropShadow dx="0" dy="5" stdDeviation="3" flood-color="#1B2631" flood-opacity="0.35"/>
    </filter>
    <radialGradient id="dialGrad" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#FFFDE7"/>
      <stop offset="80%" stop-color="#F9EBEA"/>
      <stop offset="100%" stop-color="#F5CBA7"/>
    </radialGradient>
  </defs>

  <g filter="url(#clockShadow)">
    <!-- Cadran extérieur en bois massif -->
    <circle cx="70" cy="70" r="62" fill="#5D4037" stroke="#3E2723" stroke-width="3"/>
    <circle cx="70" cy="70" r="55" fill="#8D6E63"/>

    <!-- Fond du cadran en papier ancien -->
    <circle cx="70" cy="70" r="52" fill="url(#dialGrad)"/>

    <!-- Repères des heures (12 tirets discrets) -->
    <g stroke="#5D4037" stroke-width="2" stroke-linecap="round" opacity="0.75">
      <line x1="70" y1="23" x2="70" y2="28" />
      <line x1="70" y1="112" x2="70" y2="117" />
      <line x1="23" y1="70" x2="28" y2="70" />
      <line x1="112" y1="70" x2="117" y2="70" />
      
      <line x1="93.5" y1="29.5" x2="91" y2="33.8" />
      <line x1="110.5" y1="46.5" x2="106.2" y2="49" />
      <line x1="110.5" y1="93.5" x2="106.2" y2="91" />
      <line x1="93.5" y1="110.5" x2="91" y2="106.2" />
      <line x1="46.5" y1="110.5" x2="49" y2="106.2" />
      <line x1="29.5" y1="93.5" x2="33.8" y2="91" />
      <line x1="29.5" y1="46.5" x2="33.8" y2="49" />
      <line x1="46.5" y1="29.5" x2="49" y2="33.8" />
    </g>

    <!-- Aiguille des Heures -->
    <g transform="rotate({hour_angle:.2f} 70 70)">
      <line x1="70" y1="78" x2="70" y2="42" stroke="#2C3E50" stroke-width="4" stroke-linecap="round"/>
    </g>

    <!-- Aiguille des Minutes -->
    <g transform="rotate({minute_angle:.2f} 70 70)">
      <line x1="70" y1="82" x2="70" y2="28" stroke="#1A252F" stroke-width="2.8" stroke-linecap="round"/>
      <line x1="70" y1="28" x2="70" y2="24" stroke="#E67E22" stroke-width="2" stroke-linecap="round"/>
    </g>

    <!-- Pivot central en cuivre -->
    <circle cx="70" cy="70" r="4" fill="#D35400"/>
    <circle cx="70" cy="70" r="1.8" fill="#FFF8DC"/>
  </g>
</svg>'''

    with open(filename, "w", encoding="utf-8") as f:
        f.write(svg_content)

# Génération des 25 horloges (Départ : 22h00, pas de 2 min)
start_hour = 22
start_minute = 0

for i in range(25):
    total_min = start_minute + (i * 2)
    h = start_hour + (total_min // 60)
    m = total_min % 60
    generate_clock_svg(f"horloge_{i:02d}.svg", h, m)

print("Les 25 fichiers SVG d'horloge ont été générés avec succès !")
