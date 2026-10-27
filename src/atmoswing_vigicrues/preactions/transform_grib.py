from abc import abstractmethod

import atmoswing_vigicrues as asv

from .preaction import PreAction

has_toolbox = False
if asv.has_eccodes and asv.has_netcdf:
    try:
        from atmoswing_toolbox.datasets import generic_dataset, grib_dataset
    except ImportError:
        pass
    else:
        has_toolbox = True


class TransformGribData(PreAction):
    """
    Classe de base pour la transformation de prévisions GRIB en fichiers netcdf.

    Les classes dérivées définissent le motif des fichiers GRIB à traiter
    (_input_file_pattern), l'étiquette du jeu de données utilisée dans le nom des
    fichiers produits (dataset_tag) et le nom du type de l'action (type_name).

    Parameters
    ----------
    name: str
        Le nom de l'action
    options: dict
        Un dictionnaire contenant les options de l'action. Les champs possibles sont:

        * input_dir : str
            Chemin vers le répertoire contenant les fichiers à traiter (organisé
            par date : YYYY/MM/DD).
        * output_dir : str
            Chemin cible pour l'enregistrement des fichiers.
        * variables : list
            Les variables météorologiques à convertir.
        * attempts_max_hours : int
            Décalage temporel autorisé pour rechercher d'anciens fichiers
        * attempts_step_hours : int
            Pas de temps auquel décrémenter la date pour rechercher d'anciens fichiers

    Attributes
    ----------
    type_name : str
        Le nom du type de l'action.
    name : str
        Le nom de l'action.
    input_dir : str
        Le chemin vers le répertoire contenant les fichiers à traiter.
    output_dir : str
        Le chemin vers le répertoire où seront enregistrés les fichiers.
    variables : list
        Les variables météorologiques à convertir.
    """

    type_name = None
    dataset_tag = None

    def __init__(self, name, options):
        if not asv.has_netcdf:
            raise ImportError("Le paquet netCDF4 est requis pour cette action.")
        if not asv.has_eccodes:
            raise ImportError("Le paquet eccodes est requis pour cette action.")
        if not has_toolbox:
            raise ImportError("Le paquet atmoswing-toolbox est requis pour cette "
                              "action.")

        self.name = name
        self.input_dir = options['input_dir']
        self.output_dir = options['output_dir']
        self.variables = options['variables']

        asv.check_dir_exists(self.output_dir, True)

        self._set_attempts_attributes(options)

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
        return self.transform(date)

    def transform(self, date) -> bool:
        """
        Transforme les prévisions pour une date d'émission de la prévision.

        Parameters
        ----------
        date: datetime.datetime
            Date d'émission de la prévision.

        Returns
        -------
        bool
            Vrai (True) en cas de succès, faux (False) autrement.
        """
        input_dir = asv.build_date_dir_structure(self.input_dir, date)
        forecast_date, forecast_hour = self._format_forecast_date(date)

        for variable in self.variables:
            file_name_pattern = self._input_file_pattern(
                variable, forecast_date, forecast_hour)
            new_file_name = f'{forecast_date}{forecast_hour}.{self.dataset_tag}.' \
                            f'{variable.lower()}.nc'

            input_files = sorted(input_dir.glob(file_name_pattern))

            if len(input_files) == 0:
                return False

            data = grib_dataset.GribDataset(
                directory=input_dir,
                file_pattern=file_name_pattern)
            data.load()

            new_file = generic_dataset.GenericDataset(
                directory=self.output_dir,
                var_name=variable,
                ref_data=data)
            new_file.generate(
                format=generic_dataset.NETCDF_4,
                file_name=new_file_name)

        return True

    @abstractmethod
    def _input_file_pattern(self, variable, forecast_date, forecast_hour):
        """
        Motif (glob) des fichiers GRIB d'une variable pour une date d'émission.
        """

    @staticmethod
    def _format_forecast_date(date):
        forecast_date = date.strftime("%Y%m%d")
        hour = 6 * (date.hour // 6)
        forecast_hour = f'{hour:02d}'
        return forecast_date, forecast_hour
