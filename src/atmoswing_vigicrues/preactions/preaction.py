class PreAction:
    """
    Classe de base pour les opérations nécessaires avant l'exécution des prévisions.
    """

    def __init__(self):
        pass

    def run(self, date) -> bool:
        """
        Exécution de la pre-action.

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

    def _set_attempts_attributes(self, options):
        if 'attempts_max_hours' in options:
            self.attempts_max_hours = options['attempts_max_hours']
        else:
            self.attempts_max_hours = 24

        if 'attempts_step_hours' in options:
            self.attempts_step_hours = options['attempts_step_hours']
        else:
            self.attempts_step_hours = 6
