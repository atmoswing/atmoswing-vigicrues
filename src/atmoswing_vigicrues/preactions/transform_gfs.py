from .transform_grib import TransformGribData


class TransformGfsData(TransformGribData):
    """
    Transforme les prévisions émises par GFS en fichier netcdf.

    Fichiers traités : '<YYYYMMDDHH>.NWS_GFS.<variable>.<échéance>.grib2'.
    Voir TransformGribData pour les options.
    """

    type_name = "Transformation données GFS"
    dataset_tag = "NWS_GFS"

    def _input_file_pattern(self, variable, forecast_date, forecast_hour):
        return f'{forecast_date}{forecast_hour}.NWS_GFS.{variable.lower()}.*.grib2'
