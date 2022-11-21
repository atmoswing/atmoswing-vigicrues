class PreAction:
    """
    Classe de base pour les opérations nécessaires avant l'exécution des prévisions.
    """

    def __init__(self):
        self.name = "Pré-action"

    def run(self, date) -> bool:
        """ Exécution de la pre-action. """
        raise NotImplementedError
