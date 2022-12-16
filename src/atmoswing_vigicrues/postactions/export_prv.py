import datetime
import numpy as np
from pathlib import Path

import atmoswing_vigicrues as asv

from .postaction import PostAction


class ExportPrv(PostAction):
    """
    Export des prévisions au format PRV du logiciel Scores.

    Parameters
    ----------
    options: objet
        L'instance contenant les options de l'action. Les champs possibles sont:

        * output_dir : str
            Chemin cible pour l'enregistrement des fichiers.
        * frequencies : list
            Les fréquences à extraire.
            Par défaut : [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
        * combine_stations_in_one_file : bool
            Combinaison des différentes stations (entités) dans un seul fichier.
    """

    def __init__(self, options):
        if not asv.has_netcdf:
            raise ImportError("Le paquet netCDF4 est requis pour cette action.")

        self.name = "Export PRV"
        self.output_dir = options['output_dir']
        asv.check_dir_exists(self.output_dir, True)

        if 'frequencies' in options:
            self.frequencies = options['frequencies']
        else:
            self.frequencies = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]

        if 'combine_stations_in_one_file' in options:
            self.combine_stations_in_one_file = options['combine_stations_in_one_file']
        else:
            self.combine_stations_in_one_file = True

        super().__init__()

    def run(self):
        """
        Exécution de la post-action.
        """
        for file in self._file_paths:
            nc_file = asv.Dataset(file, 'r', format='NETCDF4')
            station_ids = self._extract_station_ids(nc_file)
            header_comments = self._create_header_comments(nc_file)
            if self.combine_stations_in_one_file:
                header_data = self._create_header_data(nc_file, station_ids)
                content = self._create_content(nc_file, station_ids)
                full_content = f"{header_comments}{header_data}{content}"

                # File name
                file_path = self._build_file_path(file)

                with open(file_path, 'w', encoding="utf-8", newline='\r\n') as outfile:
                    outfile.write(full_content)
            else:
                for station_id in station_ids:
                    header_data = self._create_header_data(nc_file, station_id)
                    content = self._create_content(nc_file, station_id)
                    full_content = f"{header_comments}{header_data}{content}"

                    # File name
                    file_path = self._build_file_path(file, station_id)

                    with open(file_path, 'w', encoding="utf-8", newline='\r\n') as outfile:
                        outfile.write(full_content)

            nc_file.close()

    def _create_header_comments(self, nc_file):
        list_frequencies = [str(int(100 * i)) for i in self.frequencies]

        header = \
            f"# Sortie du module ExportPrv de AtmoSwing-Vigicrues\n" \
            f"# origin;{nc_file.origin}\n" \
            f"# creation_date;{nc_file.creation_date}\n" \
            f"# method_id;{nc_file.method_id}\n" \
            f"# specific_tag;{nc_file.specific_tag}\n" \
            f"# dataset_id;{nc_file.predictand_dataset_id}\n" \
            f"# freqs;{';'.join(list_frequencies)}\n"

        return header

    def _create_header_data(self, nc_file, station_ids):
        n = len(self.frequencies)
        if isinstance(station_ids, list):
            stat_ids = [f";{id}" * n for id in station_ids]
            stat_ids = "".join(stat_ids)
            elements = ";RR" * (n * len(station_ids))
            series_ids = self._build_id_series(nc_file) * len(station_ids)
        else:
            stat_ids = f";{station_ids}" * n
            elements = ";RR" * n
            series_ids = self._build_id_series(nc_file)

        header = \
            f"Stations{stat_ids}\n" \
            f"Grandeur{elements}\n" \
            f"IdSeries;{series_ids}\n"

        return header

    def _create_content(self, nc_file, station_ids):
        # Extracting variables
        ids = nc_file['station_ids'][:]
        target_dates = nc_file['target_dates'][:]
        target_dates = asv.utils.mjd_to_datetime(target_dates)
        analogs_nb = nc_file['analogs_nb'][:]
        analog_values = nc_file['analog_values_raw'][:]

        if not self.combine_stations_in_one_file:
            station_ids = [station_ids]

        time_format_target = self._get_time_format(target_dates)

        content = ""

        for i_target, target_date in enumerate(target_dates):
            # Get start/end of the analogs
            start = np.sum(analogs_nb[0:i_target])
            n_analogs = analogs_nb[i_target]
            end = start + n_analogs

            target_date_str = target_date.item().strftime(time_format_target)
            new_line = target_date_str

            for station_id in station_ids:
                i_station = np.where(ids == station_id)
                if len(i_station[0]) == 0:
                    raise RuntimeError("La station n'a pas été trouvée lors de "
                                       "l'export PRV.")
                if len(i_station[0]) > 1:
                    raise RuntimeError("Le nombre d'entités trouvées est supérieur à 1"
                                       " lors de l'export PRV.")
                # Extract relevant values and build frequencies
                analog_values_sub = analog_values[i_station, start:end]
                analog_values_sub = np.sort(analog_values_sub).flatten()
                frequencies = asv.utils.build_cumulative_frequency(n_analogs)

                for freq in self.frequencies:
                    if len(frequencies) != len(analog_values_sub):
                        raise RuntimeError("La taille des vecteurs dans l'export PRV "
                                           "n'est pas cohérente.")
                    val = np.interp(freq, frequencies, analog_values_sub)
                    new_line += f";{round(val, 2)}"

            content += f"{new_line}\n"

        return content

    def _get_output_path(self, date):
        local_path = asv.build_date_dir_structure(self.output_dir, date)
        local_path.mkdir(parents=True, exist_ok=True)
        return local_path

    def _build_file_path(self, file, station_id=None):
        original_file_name = Path(file).name
        if not original_file_name:
            now = datetime.datetime.now()
            original_file_name = now.strftime("%Y-%m-%d_%H%M%S") + '_missing'
        if station_id:
            file_name = f'{original_file_name}_{station_id}.csv'
        else:
            file_name = f'{original_file_name}.csv'
        if '.nc' in original_file_name:
            if station_id:
                file_name = original_file_name.replace('.nc', f'_{station_id}.csv')
            else:
                file_name = original_file_name.replace('.nc', '.csv')
        output_dir = self._get_output_path(self._get_metadata('forecast_date'))
        file_path = output_dir / file_name
        return file_path

    def _build_id_series(self, nc_file):
        ids = ""
        for freq in self.frequencies:
            ids += f"{nc_file.method_id}.{nc_file.specific_tag}.{int(100 * freq):03d};"
        return ids

    @staticmethod
    def _get_time_format(target_dates):
        time_step = target_dates[1] - target_dates[0]
        show_hour = time_step < 24 * 3600
        time_format_target = "%Y-%m-%d"
        if show_hour:
            time_format_target = "%Y-%m-%d %H:%M"
        return time_format_target
