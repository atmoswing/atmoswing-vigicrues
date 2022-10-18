import atmoswing_vigicrues as asv

from .postaction import PostAction


class ExportScores(PostAction):
    """
    Export des prévisions au format PRV du logiciel Scores.
    """

    def __init__(self, output_dir, file_name):
        """
        Initialisation de l'instance ExportBdApBp

        Parameters
        ----------
        output_dir : str
            Chemin de destination pour l'enregistrement des fichiers.
        file_name: str
            Nom du fichier
        """
        asv.check_dir_exists(output_dir, True)
        self.output_dir = output_dir
        self.file_name = file_name
        super().__init__()

    def __del__(self):
        super().__del__()
