import json
from pathlib import Path

import atmoswing_vigicrues as asv

from .postaction import PostAction


class ExportBdApBp(PostAction):
    """
    Export des prévisions au format Json de la BdApBp.

    Attributes
    ----------
    output_dir : str
        Chemin de destination pour l'enregistrement des fichiers.
    file_name: str
        Nom du fichier
    """

    def __init__(self, options):
        """
        Initialisation de l'instance ExportBdApBp

        Parameters
        ----------
        options
            L'instance options
        """
        self.output_dir = options.get('bdapbp_output_dir')
        asv.check_dir_exists(self.output_dir, True)
        if options.has('bdapbp_file_name'):
            self.file_name = options.get('bdapbp_file_name')
        else:
            self.file_name = 'BdApBp_AtmoSwing.json'
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
            'metadata': self._create_metadata_block(),
            'data': self._create_data_block(),
            'statistics': self._create_statistics_block(),
        }

        with open(Path(self.output_dir) / self.file_name, "w") as outfile:
            json.dump(output, outfile)

    def _create_metadata_block(self):
        if not self._file_contents:
            return None

        nc_file = self._file_contents[0]

        block = {
            'atmoswing': {
                'creation_date': nc_file.creation_date,
                'origin': nc_file.origin
            },
            'predictand': {
                'temporal_resolution': nc_file.predictand_temporal_resolution,
                'dataset_id': nc_file.predictand_dataset_id,
                'database': nc_file.predictand_database,
                'station_ids': nc_file.predictand_station_ids
            },
            'description': {
                'method_id': nc_file.method_id,
                'method_id_display': nc_file.method_id_display,
                'specific_tag': nc_file.specific_tag,
                'specific_tag_display': nc_file.specific_tag_display,
            },
            'entites': {
                'names': None,
                'ids': None,
                'official_ids': None
            },
        }

        return block

    def _create_data_block(self):
        if not self._file_contents:
            return None

        block = {
        }

        return block

    def _create_statistics_block(self):
        if not self._file_contents:
            return None

        block = {
        }

        return block
