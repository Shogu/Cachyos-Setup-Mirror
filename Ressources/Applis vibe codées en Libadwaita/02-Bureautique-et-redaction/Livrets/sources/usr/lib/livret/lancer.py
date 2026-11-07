"""Point d'entrée de Livret, installé dans /usr/lib/livret/.

Le code vit dans son propre dossier, hors de /usr/lib/python3.X/site-packages :
n'importe quelle version de Python 3 lit ce fichier, une mise à jour de Python
ne casse donc pas l'appli.
"""
import sys
from pathlib import Path


def _nommer_processus(nom: bytes = b"livret"):
    """Nom du processus (/proc/PID/comm) : « livret » au lieu de « python3 »
    dans les gestionnaires de tâches. Sans effet en dehors de Linux."""
    try:
        import ctypes
        import ctypes.util
        libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6", use_errno=True)
        libc.prctl(15, ctypes.c_char_p(nom), 0, 0, 0)  # 15 = PR_SET_NAME
    except (OSError, AttributeError):
        pass


_nommer_processus()
sys.path.insert(0, str(Path(__file__).resolve().parent))

from livret.app import main  # noqa: E402

sys.exit(main())
