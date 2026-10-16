import json
import os
from pathlib import Path


class Dissemination:
    """
    Classe de base pour les opérations de diffusion des résultats d'AtmoSwing.

    Attributes
    ----------
    _file_paths : list
        Chemins des fichiers à diffuser.
    """

    def __init__(self):
        self._file_paths = []

    def feed(self, file_paths):
        """
        Transmission des fichiers à diffuser

        Parameters
        ----------
        file_paths : list
            Chemins des fichiers à diffuser.
        """
        self._file_paths = file_paths

    def run(self, date) -> bool:
        """
        Exécution de la diffusion.

        Parameters
        ----------
        date : datetime.datetime
            Date de la prévision.

        Returns
        -------
        bool
            Vrai (True) en cas de succès, faux (False) autrement.
        """
        raise NotImplementedError

    @staticmethod
    def _must_replace(file_path, remote_size):
        """
        Détermine si un fichier déjà présent sur le serveur distant doit être
        remplacé.

        Seuls les exports JSON (comportant un champ 'status') sont concernés :

        * un export en erreur (statut non nul) est toujours transmis, afin que le
          serveur dispose de la dernière tentative ;
        * un export réussi (statut 0) remplace la copie distante si sa taille
          diffère : un export réussi n'étant jamais régénéré, une copie distante
          différente est une ancienne version en erreur.

        Parameters
        ----------
        file_path : str
            Chemin du fichier local.
        remote_size : int or None
            Taille du fichier distant (None si elle n'a pas pu être déterminée).

        Returns
        -------
        bool
            Vrai (True) si le fichier distant doit être remplacé, faux (False)
            autrement.
        """
        if Path(file_path).suffix.lower() != '.json':
            return False
        try:
            with open(file_path, encoding='utf-8') as f:
                status = json.load(f).get('status')
        except (OSError, ValueError, AttributeError):
            return False
        if status is None:
            return False
        if status != 0:
            return True
        return remote_size is None or remote_size != os.path.getsize(file_path)
