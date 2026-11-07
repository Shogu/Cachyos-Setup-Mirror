# SPDX-License-Identifier: GPL-2.0-or-later
"""Conteneur OLE2 (Compound File Binary) et texte des Word 97-2003 (.doc).

Un .doc n'est ni un ZIP ni un XML : c'est un « classeur » binaire (OLE2)
contenant des flux nommés (WordDocument, 0Table/1Table, Data…). Le texte est
décrit par la « table de morceaux » (piece table, structure Clx) du flux de
table : chaque morceau est soit du texte 8 bits (cp1252), soit de l'UTF-16LE.

Ce module ne dépend de rien : ni olefile, ni antiword, ni LibreOffice. Tout est
borné (chaînes de secteurs, taille des morceaux) : un fichier abîmé ou hostile
lève une ValueError, il ne fait jamais boucler l'aperçu.
"""

import struct

MAGIC = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'

LIBRE = 0xFFFFFFFF           # secteur libre
FIN = 0xFFFFFFFE             # fin de chaîne
FAT_SPECIAL = 0xFFFFFFFA     # dernier secteur réservé de la FAT

TAILLE_ENTREE = 128
MAX_SECTEURS_CHAINE = 65536      # ~32 Mo en 512 octets : garde-fou anti-boucle
MAX_MORCEAU = 8 * 1024**2        # caractères d'un morceau de la piece table


def _est_special(n):
    return n >= FAT_SPECIAL


class Conteneur:
    """Accès en lecture aux flux nommés d'un conteneur OLE2."""

    def __init__(self, donnees):
        if len(donnees) < 512 or donnees[:8] != MAGIC:
            raise ValueError("ce fichier n'est pas un conteneur OLE2")
        self.donnees = donnees
        self.taille_secteur = 1 << struct.unpack_from('<H', donnees, 0x1E)[0]
        self.taille_mini = 1 << struct.unpack_from('<H', donnees, 0x20)[0]
        if self.taille_secteur not in (512, 4096) or self.taille_mini not in (64, 512):
            raise ValueError('tailles de secteur OLE2 invalides')
        self.seuil_mini = struct.unpack_from('<I', donnees, 0x38)[0]
        self.debut_dossier = struct.unpack_from('<I', donnees, 0x30)[0]
        self.debut_mini_fat = struct.unpack_from('<I', donnees, 0x3C)[0]
        self.debut_difat = struct.unpack_from('<I', donnees, 0x44)[0]
        self.nb_difat = struct.unpack_from('<I', donnees, 0x48)[0]
        self.fat = self._lire_fat()
        self.entrees = self._lire_dossier()
        racine = next((e for e in self.entrees if e['type'] == 5), None)
        if racine is None:
            raise ValueError('conteneur OLE2 sans entrée racine')
        self.flux_mini = self._lire_flux(racine['debut'], racine['taille'], self.fat)
        self.mini_fat = self._lire_mini_fat()

    # --- secteurs et chaînes --------------------------------------------------

    def _secteur(self, n):
        debut = 512 + n * self.taille_secteur
        if _est_special(n) or debut + self.taille_secteur > len(self.donnees):
            return None
        return self.donnees[debut:debut + self.taille_secteur]

    def _chaine(self, debut, table):
        """Numéros des secteurs de la chaîne, dans l'ordre, bornés."""
        secteurs, courant, vus = [], debut, set()
        while not _est_special(courant) and courant < len(table):
            if courant in vus or len(secteurs) >= MAX_SECTEURS_CHAINE:
                break                       # chaîne cyclique ou démesurée
            vus.add(courant)
            secteurs.append(courant)
            courant = table[courant]
        return secteurs

    # --- structures du conteneur ---------------------------------------------

    def _lire_fat(self):
        # Les 109 premiers numéros sont dans l'en-tête ; la suite se suit de
        # secteur DIFAT en secteur DIFAT (dernier entier = secteur suivant).
        emplacements = list(struct.unpack_from('<109I', self.donnees, 0x4C))
        suivant = self.debut_difat
        vus = set()
        while not _est_special(suivant) and suivant not in vus and len(vus) < 4096:
            vus.add(suivant)
            bloc = self._secteur(suivant)
            if bloc is None:
                break
            valeurs = struct.unpack_from(f'<{self.taille_secteur // 4}I', bloc, 0)
            emplacements.extend(valeurs[:-1])
            suivant = valeurs[-1]
        fat = []
        for n in emplacements:
            if _est_special(n):
                continue
            bloc = self._secteur(n)
            if bloc is None:
                break
            fat.extend(struct.unpack_from(f'<{self.taille_secteur // 4}I', bloc, 0))
        if not fat:
            raise ValueError('table FAT illisible')
        return fat

    def _lire_dossier(self):
        # Le répertoire est un arbre binaire ; une simple lecture linéaire des
        # entrées suffit pour retrouver un flux par son nom.
        brut = b''.join(self._secteur(n) or b'' for n in self._chaine(self.debut_dossier, self.fat))
        entrees = []
        for i in range(0, len(brut) - TAILLE_ENTREE + 1, TAILLE_ENTREE):
            e = brut[i:i + TAILLE_ENTREE]
            longueur = struct.unpack_from('<H', e, 0x40)[0]
            type_entree = e[0x42]
            if type_entree not in (1, 2, 5) or not 2 <= longueur <= 64:
                continue
            entrees.append({
                'nom': e[:longueur - 2].decode('utf-16-le', 'replace'),
                'type': type_entree,
                'debut': struct.unpack_from('<I', e, 0x74)[0],
                'taille': struct.unpack_from('<Q', e, 0x78)[0],
            })
        return entrees

    def _lire_mini_fat(self):
        brut = b''.join(self._secteur(n) or b'' for n in self._chaine(self.debut_mini_fat, self.fat))
        return list(struct.unpack_from(f'<{len(brut) // 4}I', brut, 0)) if brut else []

    # --- flux -----------------------------------------------------------------

    def _lire_flux(self, debut, taille, table):
        if taille <= 0:
            return b''
        morceaux = [self._secteur(n) for n in self._chaine(debut, table)]
        return b''.join(m for m in morceaux if m)[:taille]

    def _lire_mini(self, debut, taille):
        morceaux = []
        for n in self._chaine(debut, self.mini_fat):
            p = n * self.taille_mini
            if p + self.taille_mini > len(self.flux_mini):
                break
            morceaux.append(self.flux_mini[p:p + self.taille_mini])
        return b''.join(morceaux)[:taille]

    def flux(self, nom):
        """Contenu d'un flux, ou None s'il est absent."""
        for e in self.entrees:
            if e['type'] == 2 and e['nom'] == nom:
                if e['taille'] < self.seuil_mini:
                    return self._lire_mini(e['debut'], e['taille'])
                return self._lire_flux(e['debut'], e['taille'], self.fat)
        return None


def _table_morceaux(clx):
    """Extrait le PlcPcd de la structure Clx (les Prc qui précèdent sont sautés)."""
    i = 0
    while i < len(clx):
        if clx[i] == 0x01:                                  # Prc : à ignorer
            if i + 3 > len(clx):
                break
            i += 3 + struct.unpack_from('<H', clx, i + 1)[0]
        elif clx[i] == 0x02:                                # Pcdt : ce qu'on veut
            if i + 5 > len(clx):
                break
            longueur = struct.unpack_from('<I', clx, i + 1)[0]
            return clx[i + 5:i + 5 + longueur]
        else:
            break
    return None


def texte_doc(donnees):
    """Texte d'un Word 97-2003 (.doc), tous morceaux de la piece table réunis."""
    conteneur = Conteneur(donnees)
    word = conteneur.flux('WordDocument')
    if word is None or len(word) < 0x1A8:
        raise ValueError('flux WordDocument absent ou tronqué')
    drapeaux = struct.unpack_from('<H', word, 0x0A)[0]
    table = conteneur.flux('1Table' if drapeaux & 0x0200 else '0Table')
    if table is None:                       # le drapeau ment parfois : on essaie l'autre
        table = conteneur.flux('0Table' if drapeaux & 0x0200 else '1Table')
    if table is None:
        raise ValueError('flux de table (0Table/1Table) absent')
    fc_clx, lcb_clx = struct.unpack_from('<II', word, 0x01A2)
    if lcb_clx <= 0 or fc_clx + lcb_clx > len(table):
        raise ValueError('table de morceaux absente')
    plc = _table_morceaux(table[fc_clx:fc_clx + lcb_clx])
    if plc is None or len(plc) < 16:
        raise ValueError('table de morceaux illisible')

    n = (len(plc) - 4) // 12
    if n <= 0:
        raise ValueError('table de morceaux vide')
    cps = struct.unpack_from(f'<{n + 1}I', plc, 0)
    base = 4 * (n + 1)
    morceaux = []
    for j in range(n):
        longueur = cps[j + 1] - cps[j]
        if longueur <= 0 or longueur > MAX_MORCEAU:
            continue
        fc = struct.unpack_from('<I', plc, base + j * 8 + 2)[0]
        if fc & 0x40000000:                 # texte 8 bits (cp1252)
            debut = (fc & 0x3FFFFFFF) // 2
            morceaux.append(word[debut:debut + longueur].decode('cp1252', 'replace'))
        else:                               # texte UTF-16LE, sauf les cases
            debut = fc & 0x3FFFFFFF
            morceaux.append(word[debut:debut + longueur * 2].decode('utf-16-le', 'replace'))
    if not morceaux:
        raise ValueError('aucun texte exploitable dans ce document')
    return ''.join(morceaux)
