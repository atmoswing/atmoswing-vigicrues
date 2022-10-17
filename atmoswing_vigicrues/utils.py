from pathlib import Path

import atmoswing_vigicrues as asv


def check_file_exists(path):
    """ Contrôle du chemin vers un fichier. """
    if type(path) == str:
        path = Path(path)
    if not path.exists():
        raise asv.FilePathError(path)
    if not path.is_file():
        raise asv.Error(f"Le chemin '{path}' n'est pas un fichier.")
