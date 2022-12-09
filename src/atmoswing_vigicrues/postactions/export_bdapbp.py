import json
import datetime
import numpy as np
from pathlib import Path

import atmoswing_vigicrues as asv

from .postaction import PostAction


class ExportBdApBp(PostAction):
    """
    Export des prévisions au format Json de la BdApBp.

    Parameters
    ----------
    options: objet
        L'instance contenant les options de l'action. Les champs possibles sont:

        * output_dir : str
            Chemin cible pour l'enregistrement des fichiers.
        * number_analogs : int
            Nombre d'analogues maximal à conserver (valeurs les plus élevées).
            -1 pour toutes les analogues.
        * only_relevant_stations : bool
            Exporter uniquement les stations pour lesquelles la méthode a été calibrée.
        * use_indentation : bool
            Ajouter une indentation aux fichiers produits.
    """

    def __init__(self, options):
        if not asv.has_netcdf:
            raise ImportError("Le paquet netCDF4 est requis pour cette action.")

        self.name = "Export BdApBp"
        self.status = 100
        self.message = ""

        self.output_dir = options['output_dir']
        asv.check_dir_exists(self.output_dir, True)

        if 'number_analogs' in options:
            self.number_analogs = options['number_analogs']
        else:
            self.number_analogs = -1

        if 'only_relevant_stations' in options:
            self.only_relevant_stations = options['only_relevant_stations']
        else:
            self.only_relevant_stations = True

        if 'use_indentation' in options:
            self.use_indentation = options['use_indentation']
        else:
            self.use_indentation = False

        self._reset_status()

        super().__init__()

    def run(self):
        """
        Exécution de la post-action.

        Erreurs possibles:

        * 100 : Absence du fichier netcdf.
        * 110 : Fichier netcdf corrompu.
        * 200 : Erreur lors du traitement fichier netcdf.
        """
        for file in self._file_paths:
            file = Path(file)
            self._reset_status()
            nc_file = None

            if not asv.file_exists(file):
                self.status = 100
                self.message = "Absence du fichier netcdf."
            else:
                try:
                    nc_file = asv.Dataset(file, 'r', format='NETCDF4')
                except:
                    self.status = 110
                    self.message = "Fichier netcdf corrompu."

            try:
                metadata = self._create_metadata_block(nc_file)
                data = self._create_data_block(nc_file)
                statistics = self._create_statistics_block(nc_file)
            except:
                metadata = None
                data = None
                statistics = None
                self.status = 200
                self.message = "Erreur lors du traitement fichier netcdf."

            exported_analogs = "full"
            if self.number_analogs > 0:
                exported_analogs = f"{self.number_analogs} best"

            data = {
                'status': self.status,
                'report': {
                    'file': file.name,
                    'date': self._get_now_formatted(),
                    'message': self.message,
                    'exported_analogs': exported_analogs
                },
                'metadata': metadata,
                'data': data,
                'statistics': statistics,
            }

            # Nom du fichier
            file_path = self._build_file_path(file)

            with open(file_path, "w", encoding="utf-8", newline='\r\n') as outfile:
                if self.use_indentation:
                    json.dump(data, outfile, indent=4, ensure_ascii=False)
                else:
                    json.dump(data, outfile, ensure_ascii=False)

            if nc_file:
                nc_file.close()

    def _create_metadata_block(self, nc_file):
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
            'entities': self._create_entities_block(nc_file),
        }

        return block

    @staticmethod
    def _create_entities_block(nc_file):
        ids = [str(x) for x in nc_file['station_ids'][:]]
        names = [str(x) for x in nc_file['station_names'][:]]
        oids = [str(x) for x in nc_file['station_official_ids'][:]]

        block = {}
        for id, name, oid in zip(ids, names, oids):
            block[id] = [name, oid]

        return block

    def _create_data_block(self, nc_file):
        # Extracting variables
        station_ids = nc_file['station_ids'][:]
        target_dates = nc_file['target_dates'][:]
        target_dates = asv.utils.mjd_to_datetime(target_dates)
        analog_dates = nc_file['analog_dates'][:]
        analog_dates = asv.utils.mjd_to_datetime(analog_dates)
        analogs_nb = nc_file['analogs_nb'][:]
        analog_criteria = nc_file['analog_criteria'][:]
        analog_values = nc_file['analog_values_raw'][:]

        assert analog_values.shape[0] == len(station_ids)

        time_format_analogs, time_format_target = self._get_time_format(target_dates)

        if self.only_relevant_stations:
            station_ids_slct = self._extract_station_ids(nc_file)
        else:
            station_ids_slct = station_ids

        block = {}
        for station_id in station_ids_slct:
            i_station = np.where(station_ids == station_id)
            block_target_date = {}
            for i_target, target_date in enumerate(target_dates):
                block_analogs = []

                # Get start/end of the analogs
                start = np.sum(analogs_nb[0:i_target])
                n_analogs = analogs_nb[i_target]
                end = start + n_analogs

                # Extract relevant values
                analog_dates_sub = analog_dates[start:end]
                analog_criteria_sub = analog_criteria[start:end]
                analog_values_sub = analog_values[i_station, start:end].flatten()

                # Sort by decreasing precipitation values
                permutation = (-analog_values_sub).argsort()
                analog_dates_sub = analog_dates_sub[permutation]
                analog_criteria_sub = analog_criteria_sub[permutation]
                analog_values_sub = analog_values_sub[permutation]

                ranks = np.arange(1, n_analogs + 1)[permutation]
                frequency = asv.utils.build_cumulative_frequency(n_analogs)
                frequency = np.flip(frequency)

                if 0 < self.number_analogs < n_analogs:
                    analog_dates_sub = analog_dates_sub[0:self.number_analogs]
                    analog_criteria_sub = analog_criteria_sub[0:self.number_analogs]
                    analog_values_sub = analog_values_sub[0:self.number_analogs]
                    ranks = ranks[0:self.number_analogs]
                    frequency = frequency[0:self.number_analogs]

                for i_analog, analog_date in enumerate(analog_dates_sub):
                    block_analogs.append([
                        round(frequency[i_analog], 3),
                        analog_date.item().strftime(time_format_analogs),
                        round(float(analog_criteria_sub[i_analog]), 2),
                        round(float(analog_values_sub[i_analog]), 2)
                    ])

                target_date_str = target_date.item().strftime(time_format_target)
                block_target_date[target_date_str] = block_analogs
            block[str(station_id)] = block_target_date

        return block

    def _create_statistics_block(self, nc_file):
        # Extracting variables
        station_ids = nc_file['station_ids'][:]
        target_dates = nc_file['target_dates'][:]
        target_dates = asv.utils.mjd_to_datetime(target_dates)
        analogs_nb = nc_file['analogs_nb'][:]
        analog_values = nc_file['analog_values_raw'][:]

        time_format_analogs, time_format_target = self._get_time_format(target_dates)

        if self.only_relevant_stations:
            station_ids_slct = self._extract_station_ids(nc_file)
        else:
            station_ids_slct = station_ids

        block = {}
        for station_id in station_ids_slct:
            i_station = np.where(station_ids == station_id)
            block_target_date = {}
            for i_target, target_date in enumerate(target_dates):
                block_analogs = []

                # Get start/end of the analogs
                start = np.sum(analogs_nb[0:i_target])
                n_analogs = analogs_nb[i_target]
                end = start + n_analogs

                # Extract relevant values
                analog_values_sub = analog_values[i_station, start:end].flatten()

                # Sort by decreasing precipitation values
                analog_values_sub = np.sort(analog_values_sub)[::-1]

                frequency = asv.utils.build_cumulative_frequency(n_analogs)
                frequency = np.flip(frequency)

                for i_analog, analog_value in enumerate(analog_values_sub):
                    block_analogs.append([
                        round(frequency[i_analog], 3),
                        round(float(analog_value), 2)
                    ])

                target_date_str = target_date.item().strftime(time_format_target)
                block_target_date[target_date_str] = block_analogs
            block[str(station_id)] = block_target_date

        return block

    @staticmethod
    def _get_time_format(target_dates):
        time_step = target_dates[1] - target_dates[0]
        show_hour = time_step < 24 * 3600
        time_format_target = "%Y%m%d"
        time_format_analogs = "%Y-%m-%d"
        if show_hour:
            time_format_target = "%Y%m%d%H"
            time_format_analogs = "%Y-%m-%d %H"
        return time_format_analogs, time_format_target

    @staticmethod
    def _to_str_dict(var):
        var = var.flatten()
        new_list = [str(x) for x in var]
        return dict(enumerate(new_list))

    @staticmethod
    def _to_int_dict(var):
        var = var.flatten()
        new_list = [int(x) for x in var]
        return dict(enumerate(new_list))

    def _reset_status(self):
        self.status = 0
        self.message = "Exécution correcte"

    @staticmethod
    def _get_now_formatted():
        now = datetime.datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")

    def _get_output_path(self, date):
        local_path = asv.build_date_dir_structure(self.output_dir, date)
        local_path.mkdir(parents=True, exist_ok=True)
        return local_path

    def _build_file_path(self, file):
        original_file_name = Path(file).name
        if not original_file_name:
            now = datetime.datetime.now()
            original_file_name = now.strftime("%Y-%m-%d_%H%M%S") + '_missing'
        file_name = f'{original_file_name}.json'
        if '.nc' in original_file_name:
            file_name = original_file_name.replace('.nc', '.json')
        output_dir = self._get_output_path(self._get_metadata('forecast_date'))
        file_path = output_dir / file_name
        return file_path

