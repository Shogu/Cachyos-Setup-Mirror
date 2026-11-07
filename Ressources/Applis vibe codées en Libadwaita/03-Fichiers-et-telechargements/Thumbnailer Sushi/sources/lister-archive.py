#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Liste le contenu d'une archive sans rien extraire (libarchive).

Usage : lister-archive.py <archive>
Écrit du JSON sur la sortie standard :
  {"entrees": [[chemin, taille, date_unix, "f"|"d"|"l"], …],
   "tronque": bool, "taille_totale": int, "paquet": {…} | null}
Codes de sortie : 0 succès, 2 usage, 4 délai dépassé, 6 archive illisible.
"""

import json
import signal
import sys

MAX_ENTREES = 5000
DELAI_MAX_S = 25
TAILLE_MAX_PKGINFO = 64 * 1024


def _delai(signum, frame):
    raise TimeoutError


def lire_pkginfo(donnees):
    infos = {}
    for ligne in donnees.decode('utf-8', 'replace').splitlines():
        cle, sep, valeur = ligne.partition(' = ')
        if sep and cle in ('pkgname', 'pkgver', 'pkgdesc') and cle not in infos:
            infos[cle] = valeur.strip()
    if 'pkgname' not in infos:
        return None
    return {'nom': infos['pkgname'], 'version': infos.get('pkgver', ''),
            'description': infos.get('pkgdesc', '')}


def lister(chemin):
    import libarchive
    entrees, total, tronque, paquet = [], 0, False, None
    with libarchive.file_reader(chemin) as archive:
        for entree in archive:
            if len(entrees) >= MAX_ENTREES:
                tronque = True
                break
            nom = entree.pathname or ''
            if entree.isdir:
                genre, taille = 'd', 0
            elif entree.issym:
                genre, taille = 'l', 0
            else:
                genre, taille = 'f', max(0, entree.size or 0)
                total += taille
            # Paquet Arch : on lit seulement le petit fichier .PKGINFO
            if nom == '.PKGINFO' and genre == 'f' and taille <= TAILLE_MAX_PKGINFO and paquet is None:
                paquet = lire_pkginfo(b''.join(entree.get_blocks()))
            entrees.append([nom, taille, int(entree.mtime or 0), genre])
    return {'entrees': entrees, 'tronque': tronque, 'taille_totale': total, 'paquet': paquet}


def main(argv):
    if len(argv) != 2:
        print('Usage : lister-archive.py <archive>', file=sys.stderr)
        return 2
    signal.signal(signal.SIGALRM, _delai)
    signal.alarm(DELAI_MAX_S)
    try:
        resultat = lister(argv[1])
    except TimeoutError:
        print(f"Délai dépassé ({DELAI_MAX_S} s) : archive trop lente à lire.", file=sys.stderr)
        return 4
    except Exception as e:
        message = str(e) or type(e).__name__
        print(f"Archive illisible ou chiffrée ({message}).", file=sys.stderr)
        return 6
    json.dump(resultat, sys.stdout, ensure_ascii=False, separators=(',', ':'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
