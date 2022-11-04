from netCDF4 import Dataset

import atmoswing_vigicrues as asv


class PreAction:
    """
    Classe de base pour les opérations nécessaires avant l'exécution des prévisions.
    """

    def __init__(self):
        """
        Initialisation de l'instance PreAction
        """

    def run(self, date) -> bool:
        """ Exécution de la pre-action. """
        raise NotImplementedError
