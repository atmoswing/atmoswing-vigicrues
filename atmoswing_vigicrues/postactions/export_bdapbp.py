import json
from pathlib import Path

import atmoswing_vigicrues as asv

from .postaction import PostAction


class ExportBdApBp(PostAction):
    """
    Export des prévisions au format Json de la BdApBp.
    """

    def __init__(self, output_dir, file_name='BdApBp_AtmoSwing.json'):
        asv.check_dir_exists(output_dir, True)
        self.output_dir = output_dir
        self.file_name = file_name
        super().__init__()

    def __del__(self):
        super().__del__()

    def run(self):
        """ Exécution de la post-action. """
        self._open_files()

        output = {
            'statut': self._get_metadata('status'),
            'rapport': {
                'fichier': self._get_metadata('source_file'),
                'date': self._get_metadata('date'),
                'message': self._get_metadata('message')
            },
            'metadata': {
                'atmoswing': {
                    'creation_date': None,
                    'origin': None
                },
                'predictand': {
                    'temporal_resolution': None,
                    'dataset_id': None,
                    'database': None,
                    'station_ids': None
                },
                'description': {
                    'method_id': None,
                    'method_id_display': None,
                    'specific_tag': None,
                    'specific_tag_display': None,
                },
                'entites': {
                    'names': None,
                    'ids': None,
                    'official_ids': None
                },
            },
            'data': None,
            'statistics': None
        }

        with open(Path(self.output_dir) / self.file_name, "w") as outfile:
            json.dump(output, outfile)
