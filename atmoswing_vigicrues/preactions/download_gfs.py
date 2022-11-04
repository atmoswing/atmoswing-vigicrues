import atmoswing_vigicrues as asv
from datetime import datetime, timedelta
from urllib import request, error
from pathlib import Path

from .preaction import PreAction


class DownloadGfsData(PreAction):
    """
    Téléchargement des prévisions émises par GFS.
    """

    def __init__(self, options):
        """
        Initialisation de l'instance DownloadGfsData

        Parameters
        ----------
        options
            L'instance contenant les options de l'action. Les champs possibles sont:
            * gfs_output_dir: str
                Répertoire cible pour l'enregistrement des fichiers.
            * gfs_lead_time_max: int
                Échéance maximale de la prévision en heures.
                Valeur par defaut: 168
            * gfs_variables: list
                Variables à télécharger.
                Valeur par défaut: ['hgt']
            * gfs_levels: list
                Niveaux de pression à télécharger.
                Valeur par défaut: [300, 400, 500, 600, 700, 850, 925, 1000]
            * gfs_domain
                Domaine à télécharger.
                Valeur par défaut: [-20, 30, 25, 65]
            * gfs_resolution
                Résolution spatiale des données.
                Options: 0.25, 0.50, 1
                Valeur par défaut: 0.25
            * gfs_max_attempts
                Nombre de tentatives de téléchargement en adaptant l'heure d'échéance
                (soustrayant 6 h).
                Valeur par défaut: 8
        """
        self.output_dir = options.get('gfs_output_dir')
        asv.check_dir_exists(self.output_dir, True)

        if options.has('gfs_lead_time_max'):
            self.lead_time_max = options.get('gfs_lead_time_max')
        else:
            self.lead_time_max = 168

        if options.has('gfs_variables'):
            self.variables = options.get('gfs_variables')
        else:
            self.variables = ['hgt']

        if options.has('gfs_levels'):
            self.levels = options.get('gfs_levels')
        else:
            self.levels = [300, 400, 500, 600, 700, 850, 925, 1000]

        if options.has('gfs_domain'):
            self.domain = options.get('gfs_domain')
            if len(self.domain) != 4:
                raise ValueError("Le domaine GFS doit être défini par 4 valeurs.")
        else:
            # Ordre: left lon, right lon, bottom lat, top lat
            self.domain = [-20, 30, 25, 65]

        if options.has('gfs_resolution'):
            resolution = options.get('gfs_resolution')
            if resolution == 0.25:
                self.resolution = '0p25'
            elif resolution == 0.50:
                self.resolution = '0p50'
            elif resolution == 1:
                self.resolution = '1p00'
            else:
                raise ValueError("La résolution fournie pour GFS ne correspond pas"
                                 "aux options disponibles (0.25, 0.5, 1).")
        else:
            self.resolution = '0p25'

        if options.has('gfs_max_attempts'):
            self.max_attempts = options.get('gfs_max_attempts')
        else:
            self.max_attempts = 8

        super().__init__()

    def run(self, date) -> bool:
        """
        Exécute l'action.
        """
        return self.download(date)

    def download(self, date) -> bool:
        """
        Télécharge les prévisions de GFS pour une date d'émission de la prévision.

        Parameters
        ----------
        date: datetime
            Date d'émission de la prévision.

        Returns
        -------
        Vrai (True) en cas de succès, faux (False) autrement.
        """
        subregion = self._build_subregion_request()
        levels = self._build_levels_request()
        resol = self.resolution

        for lead_time in range(0, self.lead_time_max + 1, 6):
            lead_time_str = f'{lead_time:03d}'

            for variable in self.variables:

                attempts = 0
                while attempts < self.max_attempts:

                    forecast_date, forecast_hour = self._format_forecast_date(date)

                    url = f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_{resol}." \
                          f"pl?file=gfs.t{forecast_hour}z.pgrb2.{resol}." \
                          f"f{lead_time_str}&{levels}var_{variable.upper()}=on&" \
                          f"{subregion}&dir=%2Fgfs.{forecast_date}%2F" \
                          f"{forecast_hour}%2Fatmos"

                    file_name = f'{forecast_date}{forecast_hour}.NWS_GFS_Forecast.' \
                                f'{variable.lower()}.{lead_time_str}.grib2'

                    local_path = self._get_local_path(date)
                    file_path = local_path / file_name

                    if file_path.exists():
                        print("The GFS forecast were already downloaded.")
                        return False

                    try:
                        request.urlretrieve(url, file_path)
                        break
                    except error.HTTPError as e:
                        attempts += 1
                        date = date - timedelta(hours=6)
                        if attempts >= self.max_attempts:
                            print(e.code)
                else:
                    return False

        return True

    def _get_local_path(self, date):
        local_path = Path(self.output_dir)
        local_path = local_path / date.strftime("%Y")
        local_path = local_path / date.strftime("%m")
        local_path = local_path / date.strftime("%d")
        local_path.mkdir(parents=True, exist_ok=True)
        return local_path

    def _build_levels_request(self):
        levels = [f'lev_{int(level)}_mb=on&' for level in self.levels]
        levels = ''.join(levels)
        return levels

    def _build_subregion_request(self):
        left_lon = self.domain[0]
        right_lon = self.domain[1]
        bottom_lat = self.domain[2]
        top_lat = self.domain[3]
        subregion = f'subregion=&leftlon={left_lon}&rightlon={right_lon}&' \
                    f'toplat={top_lat}&bottomlat={bottom_lat}'
        return subregion

    @staticmethod
    def _format_forecast_date(date):
        forecast_date = date.strftime("%Y%m%d")
        hour = 6 * (date.hour // 6)
        forecast_hour = f'{hour:02d}'
        return forecast_date, forecast_hour
