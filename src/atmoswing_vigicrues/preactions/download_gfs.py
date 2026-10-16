import datetime
import re

import requests

import atmoswing_vigicrues as asv

from .preaction import PreAction

CLEAN_HTML = re.compile('<.*?>')


class DownloadGfsData(PreAction):
    """
    Téléchargement des prévisions émises par GFS.

    Parameters
    ----------
    name: str
        Le nom de l'action
    options: dict
        Un dictionnaire contenant les options de l'action. Les champs possibles sont:

        * output_dir : str
            Répertoire cible pour l'enregistrement des fichiers.
        * lead_time_max : int
            Échéance maximale de la prévision en heures.
            Valeur par défaut : 168
        * variables : list
            Variables à télécharger.
            Valeur par défaut: ['hgt']
        * levels : list
            Niveaux de pression à télécharger.
            Valeur par défaut: [300, 400, 500, 600, 700, 850, 925, 1000]
        * domain : list
            Domaine à télécharger (coordonnées géographiques).
            Valeur par défaut: [-20, 30, 25, 65]
        * resolution : float
            Résolution spatiale des données.
            Options: 0.25, 0.50, 1
            Valeur par défaut : 0.25
        * proxies : dict
            Les proxys à utiliser (si nécessaire), par protocole, au format de la
            bibliothèque requests. Exemple :
            {'http': 'http://user:pass@proxy:3128', 'https': 'http://proxy:3128'}
        * attempts_max_hours : int
            Décalage temporel autorisé pour rechercher d'anciens fichiers
        * attempts_step_hours : int
            Pas de temps auquel décrémenter la date pour rechercher d'anciens fichiers
            lorsque le fichier n'est pas trouvé
        * time_increment : int
            Pas de temps auquel décrémenter la date pour rechercher d'anciens fichiers
            afin de compléter les fichiers précédents de la journée
            Valeur par défaut : 6
        * time_step_back : int
            Nombre de pas de temps autorisé pour rechercher d'anciens fichiers
            Valeur par défaut : 4
        * timeout : float
            Délai maximal d'attente du serveur (en secondes) pour chaque requête.
            Valeur par défaut : 120

    Attributes
    ----------
    type_name : str
        Le nom du type de l'action
    name : str
        Le nom de l'action
    output_dir : str
        Répertoire cible pour l'enregistrement des fichiers.
    lead_time_max : int
        Échéance maximale de la prévision en heures.
    variables : list
        Variables à télécharger.
    levels : list
        Niveaux de pression à télécharger.
    domain : list
        Domaine à télécharger (coordonnées géographiques).
    resolution : float
        Résolution spatiale des données.
    proxies : dict
        Les proxys à utiliser, par protocole (None si aucun proxy n'est défini).
    time_increment : int
        Pas de temps auquel décrémenter la date pour rechercher d'anciens fichiers
    time_step_back : int
        Nombre de pas de temps autorisé pour rechercher d'anciens fichiers
    timeout : float
        Délai maximal d'attente du serveur (en secondes) pour chaque requête.
    """

    def __init__(self, name, options):
        self.type_name = "Téléchargement GFS"
        self.name = name
        self.output_dir = options['output_dir']
        asv.check_dir_exists(self.output_dir, True)

        self._set_attempts_attributes(options)

        if 'lead_time_max' in options:
            self.lead_time_max = options['lead_time_max']
        else:
            self.lead_time_max = 168

        if 'variables' in options:
            self.variables = options['variables']
        else:
            self.variables = ['hgt']

        if 'levels' in options:
            self.levels = options['levels']
        else:
            self.levels = [300, 400, 500, 600, 700, 850, 925, 1000]

        if 'domain' in options:
            self.domain = options['domain']
            if len(self.domain) != 4:
                raise ValueError("Le domaine GFS doit être défini par 4 valeurs.")
        else:
            # Ordre: left lon, right lon, bottom lat, top lat
            self.domain = [-20, 30, 25, 65]

        if 'resolution' in options:
            resolution = options['resolution']
            if resolution == 0.25:
                self.resolution = '0p25'
            elif resolution == 0.50:
                self.resolution = '0p50'
            elif resolution == 1:
                self.resolution = '1p00'
            else:
                raise ValueError("La résolution fournie pour GFS ne correspond pas "
                                 "aux options disponibles (0.25, 0.5, 1).")
        else:
            self.resolution = '0p25'

        # Seuls les proxys renseignés sont conservés (les valeurs vides sont ignorées)
        proxies = options.get('proxies') or {}
        self.proxies = {key: value for key, value in proxies.items() if value} or None

        # Télécharge également les 4 pas de temps précédents (pas de temps de 6 h)
        if 'time_increment' in options:
            self.time_increment = options['time_increment']
        else:
            self.time_increment = 6

        if 'time_step_back' in options:
            self.time_step_back = options['time_step_back']
        else:
            self.time_step_back = 4

        self.timeout = options.get('timeout') or 120

        super().__init__()

    def run(self, date) -> bool:
        """
        Exécute l'action.

        Parameters
        ----------
        date: datetime.datetime
            Date d'émission de la prévision.

        Returns
        -------
        bool
            Vrai (True) en cas de succès, faux (False) autrement.
        """
        return self.download(date)

    def download(self, date) -> bool:
        """
        Télécharge les prévisions de GFS pour une date d'émission de la prévision.

        Parameters
        ----------
        date: datetime.datetime
            Date d'émission de la prévision.

        Returns
        -------
        bool
            Vrai (True) en cas de succès, faux (False) autrement.
        """
        subregion = self._build_subregion_request()
        levels = self._build_levels_request()
        resol = self.resolution
        sub_product = 'pgrb2'
        if resol == '0p50':
            sub_product = 'pgrb2full'

        files_count = 0
        for time_step_back in range(0, self.time_step_back):
            date_ref = date - datetime.timedelta(
                hours=self.time_increment * time_step_back
            )

            date_msg = date_ref.strftime('%d/%m/%Y %Hh')
            print(f"  -> Téléchargement des prévisions du : {date_msg}.")
            forecast_date, forecast_hour = self._format_forecast_date(date_ref)

            for lead_time in range(0, self.lead_time_max + 1, 6):
                lead_time_str = f'{lead_time:03d}'

                for variable in self.variables:

                    url = f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_{resol}." \
                          f"pl?file=gfs.t{forecast_hour}z.{sub_product}.{resol}." \
                          f"f{lead_time_str}&{levels}var_{variable.upper()}=on&" \
                          f"{subregion}&dir=%2Fgfs.{forecast_date}%2F" \
                          f"{forecast_hour}%2Fatmos"

                    file_name = f'{forecast_date}{forecast_hour}.NWS_GFS.' \
                                f'{variable.lower()}.{lead_time_str}.grib2'

                    local_path = self._get_local_path(date_ref)
                    file_path = local_path / file_name

                    if file_path.exists():
                        continue

                    try:
                        r = requests.get(url, proxies=self.proxies,
                                         timeout=self.timeout)
                    except requests.exceptions.RequestException as e:
                        print(f"  -> {e}")
                        print("  -> Le téléchargement de GFS a échoué.")
                        return False
                    except Exception:
                        print("  -> Le téléchargement de GFS a échoué.")
                        return False

                    if r.status_code == 200:
                        with open(file_path, 'wb') as f:
                            f.write(r.content)
                        files_count += 1
                    else:
                        clean_text = re.sub(CLEAN_HTML, '', r.text)
                        print(f"  -> {clean_text}")
                        return False

        print(f"  -> Nombre de fichiers téléchargés : {files_count}.")

        return True

    def _get_local_path(self, date):
        local_path = asv.build_date_dir_structure(self.output_dir, date)
        local_path.mkdir(parents=True, exist_ok=True)
        return local_path

    def _build_levels_request(self):
        levels = []
        for level in self.levels:
            if isinstance(level, str) and level == 'surface':
                levels.append('lev_surface=on&')
            if isinstance(level, str) and level == 'entire_atmosphere':
                levels.append('lev_entire_atmosphere_%5C%28considered'
                              '_as_a_single_layer%5C%29=on&')
            if isinstance(level, int) or isinstance(level, float):
                levels.append(f'lev_{int(level)}_mb=on&')
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
