#!/usr/bin/env python3
"""Extension Nautilus : ouvrir une session OpenCode dans le dossier sélectionné.

Chargeable par nautilus-python (Nautilus 51 / API 4.1).
Ajoute une entrée au menu contextuel :
  - "Ouvrir dans Opencode" sur un dossier (clic droit)
  - "Ouvrir dans Opencode" sur le fond d'un dossier (clic droit + onglet vide)
"""

import gi

gi.require_version('Nautilus', '4.1')
from gi.repository import Nautilus, GObject  # noqa: E402

import subprocess  # noqa: E402

LABEL = 'Ouvrir dans Opencode'
TIP = 'Ouvrir une session OpenCode dans ce dossier'


class OpenCodeMenuProvider(GObject.GObject, Nautilus.MenuProvider):
    def __init__(self):
        super().__init__()

    # --- lancement -------------------------------------------------------
    def _launch(self, _menu, path):
        subprocess.Popen(
            ['ptyxis', '-d', path, '-x', 'opencode'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    # --- fabrication de l'entrée de menu --------------------------------
    def _make_item(self, path):
        item = Nautilus.MenuItem(
            name='OpenCodeExtension::OpenHere',
            label=LABEL,
            tip=TIP,
        )
        item.connect('activate', self._launch, path)
        return item

    @staticmethod
    def _file_path(f):
        """Chemin local si c'est un dossier 'file://', sinon None."""
        if not f.is_directory() or f.get_uri_scheme() != 'file':
            return None
        return f.get_location().get_path()

    # --- menu sur un fichier/dossier sélectionné ------------------------
    def get_file_items(self, files):
        paths = [self._file_path(f) for f in files]
        paths = [p for p in paths if p is not None]
        # N'ajoute l'entrée que si UN SEUL dossier est sélectionné
        if len(paths) != 1:
            return []
        return [self._make_item(paths[0])]

    # --- menu sur le fond d'un dossier (clic droit en zone vide) --------
    def get_background_items(self, current_folder):
        path = self._file_path(current_folder)
        if path is None:
            return []
        return [self._make_item(path)]
