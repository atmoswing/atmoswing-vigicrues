import atmoswing_vigicrues as asv
from netCDF4 import Dataset


class PostAction:
    """
    Classe de base pour les opérations de traitement des résultats d'AtmoSwing.
    """

    def __init__(self):
        """
        Initialisation de l'instance PostAction
        """
        self._file_paths = []
        self._file_contents = []
        self._metadata = None

    def __del__(self):
        self._close_files()

    def feed(self, file_paths, metadata):
        """
        Transmission des données issues de la prévision

        Parameters
        ----------
        file_paths : list
            Chemins des fichiers de prévision émis par AtmoSwing.
        metadata : dict
            Méta-données issues de la prévision.
        """
        self._file_paths = file_paths
        self._metadata = metadata

    def run(self):
        """ Exécution de la post-action. """
        raise NotImplemented

    def _open_files(self):
        """ Lecture des fichiers de prévision. """
        for file in self._file_paths:
            asv.check_file_exists(file)
            content = Dataset(file, 'r', format='NETCDF4')
            self._file_contents.append(content)

    def _close_files(self):
        """ Fermeture des fichiers de prévision. """
        for file in self._file_contents:
            file.close()

    def _get_metadata(self, key):
        """ Extraction sécurisée des métadonnées. """
        if key in self._metadata:
            return self._metadata[key]
        return None
