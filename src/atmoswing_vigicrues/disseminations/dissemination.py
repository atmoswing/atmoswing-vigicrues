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
        """
        raise NotImplementedError
