from abc import ABC, abstractmethod


class PreAction(ABC):
    """
    Classe de base pour les opérations nécessaires avant l'exécution des prévisions.

    Attributes
    ----------
    type_name : str
        Le nom du type de l'action (défini par les classes dérivées).
    name : str
        Le nom de l'action (défini par les classes dérivées).
    attempts_max_hours : int
        Décalage temporel autorisé pour rechercher d'anciens fichiers.
    attempts_step_hours : int
        Pas de temps auquel décrémenter la date pour rechercher d'anciens fichiers.
    """

    @abstractmethod
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

    def _set_attempts_attributes(self, options):
        if 'attempts_max_hours' in options:
            self.attempts_max_hours = options['attempts_max_hours']
        else:
            self.attempts_max_hours = 24

        if 'attempts_step_hours' in options:
            self.attempts_step_hours = options['attempts_step_hours']
        else:
            self.attempts_step_hours = 6
