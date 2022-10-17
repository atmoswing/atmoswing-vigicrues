from atmoswing_vigicrues.exceptions import *
from pathlib import Path


def check_file_exists(path):
    """ Contrôle du chemin vers un fichier. """
    if type(path) == str:
        path = Path(path)
    if not path.exists():
        raise FilePathError(path)
    if not path.is_file():
        raise Error(f"Le chemin '{path}' n'est pas un fichier.")
