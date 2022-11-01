import atmoswing_vigicrues as asv


class Dissemination:
    """
    Classe de base pour les opérations de diffusion des résultats d'AtmoSwing.
    """

    def __init__(self):
        """
        Initialisation de l'instance Dissemination
        """
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

    def run(self):
        """ Exécution de la diffusion. """
        raise NotImplementedError
