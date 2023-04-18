import atmoswing_vigicrues as asv
from datetime import datetime
#if asv.has_eccodes and asv.has_netcdf:
#    from atmoswing_toolbox.datasets import generic, grib_dataset


from .preaction import PreAction


class TransformGfsData(PreAction):
    """
    Transforme les prévisions émises par GFS en fichier netcdf.
    """

    def __init__(self, options):
        """
        Initialisation de l'instance TransformGfsData

        Parameters
        ----------
        options
            L'instance contenant les options de l'action. Les champs possibles sont:
            * transform_gfs_input_dir: str
                Répertoire contenant les fichiers originaux (grib2).
            * transform_gfs_output_dir: str
                Répertoire cible pour l'enregistrement des fichiers.
            * gfs_variables: list
                Variables à télécharger.
                Valeur par défaut: ['hgt']
        """
        if not asv.has_netcdf:
            raise ImportError("Le paquet netCDF4 est requis pour cette action.")
        if not asv.has_eccodes:
            raise ImportError("Le paquet eccodes est requis pour cette action.")

        self.name = "Transformation données GFS"
        self.input_dir = options.get('transform_gfs_input_dir')
        self.output_dir = options.get('transform_gfs_output_dir')
        asv.check_dir_exists(self.output_dir, True)

        if options.has('gfs_variables'):
            self.variables = options.get('gfs_variables')
        else:
            self.variables = ['hgt']

        super().__init__()

    def run(self, date) -> bool:
        """
        Exécute l'action.

        Parameters
        ----------
        date: datetime
            Date d'émission de la prévision.

        Returns
        -------
        Vrai (True) en cas de succès, faux (False) autrement.
        """
        return self.transform(date)

    def transform(self, date) -> bool:
        """
        Transforme les prévisions de GFS pour une date d'émission de la prévision.

        Parameters
        ----------
        date: datetime
            Date d'émission de la prévision.

        Returns
        -------
        Vrai (True) en cas de succès, faux (False) autrement.
        """

        input_dir = self._get_input_dir(date)
        forecast_date, forecast_hour = self._format_forecast_date(date)

        for variable in self.variables:
            file_name_pattern = f'{forecast_date}{forecast_hour}.NWS_GFS.' \
                                f'{variable.lower()}.*.grib2'

            input_files = sorted(input_dir.glob(file_name_pattern))

            if len(input_files) == 0:
                return False

            #data = grib_dataset.Grib(directory=input_dir,
            #                         file_pattern=file_name_pattern)
            #data.load()

            #new_file = generic.Generic(directory=self.output_dir,
            #                           var_name=variable,
            #                           ref_data=data)
            #new_file.generate(format=generic.NETCDF_4)

        return True

    def _get_input_dir(self, date):
        return asv.build_date_dir_structure(self.input_dir, date)

    def _get_output_dir(self, date):
        output_dir = asv.build_date_dir_structure(self.output_dir, date)
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    @staticmethod
    def _format_forecast_date(date):
        forecast_date = date.strftime("%Y%m%d")
        hour = 6 * (date.hour // 6)
        forecast_hour = f'{hour:02d}'
        return forecast_date, forecast_hour