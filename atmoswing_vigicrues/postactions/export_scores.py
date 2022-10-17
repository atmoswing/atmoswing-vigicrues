import json

from .postaction import PostAction
import atmoswing_vigicrues as asv


class ExportScores(PostAction):
    """
    Export des prévisions au format PRV du logiciel Scores.
    """

    def __init__(self, output_dir, file_name):
        asv.check_dir_exists(output_dir, True)
        self.output_dir = output_dir
        self.file_name = file_name
        super().__init__()

    def __del__(self):
        super().__del__()
