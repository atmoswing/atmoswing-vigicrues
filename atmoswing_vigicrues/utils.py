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


def check_dir_exists(path, create=False):
    path_output = Path(path)
    if not path_output.exists():
        if create:
            path_output.mkdir(parents=True, exist_ok=True)
        else:
            raise asv.Error(f"Le répertoire '{path}' n'a pas été trouvé.")
