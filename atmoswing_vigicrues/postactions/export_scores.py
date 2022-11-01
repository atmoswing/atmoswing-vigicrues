import atmoswing_vigicrues as asv

from .postaction import PostAction


class ExportScores(PostAction):
    """
    Export des prévisions au format PRV du logiciel Scores.

    Attributes
    ----------
    output_dir : str
        Chemin de destination pour l'enregistrement des fichiers.
    file_name: str
        Nom du fichier
    """

    def __init__(self, options):
        """
        Initialisation de l'instance ExportScores

        Parameters
        ----------
        options
            L'instance options
        """
        self.output_dir = options.get('scores_output_dir')
        asv.check_dir_exists(self.output_dir, True)
        self.file_name = options.get('scores_file_name')
        super().__init__()

    def __del__(self):
        super().__del__()

    def run(self):
        raise NotImplementedError
