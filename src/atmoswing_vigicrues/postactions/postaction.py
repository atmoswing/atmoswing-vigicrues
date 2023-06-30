class PostAction:
    """
    Classe de base pour les opérations de traitement des résultats d'AtmoSwing.

    Attributes
    ----------
    _file_paths : list
        Chemins des fichiers de prévision émis par AtmoSwing.
    _metadata : dict
        Méta-données issues de la prévision.
    """

    def __init__(self):
        self._file_paths = []
        self._metadata = None

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

    def run(self) -> bool:
        """
        Exécution du traitement.

        Returns
        -------
        bool
            Vrai (True) en cas de succès, faux (False) autrement.
        """
        raise NotImplementedError

    def _get_metadata(self, key):
        if key in self._metadata:
            return self._metadata[key]
        return None

    @staticmethod
    def _extract_station_ids(nc_file):
        station_ids = nc_file.predictand_station_ids
        station_ids = station_ids.split(",")
        station_ids = [int(i) for i in station_ids]
        return station_ids
