from .transform_grib import TransformGribData


class TransformEcmwfData(TransformGribData):
    """
    Transforme les prévisions émises par le CEP (ECMWF) en fichier netcdf.

    Fichiers traités : 'CEP_<variable>_<YYYYMMDDHH>00.grb'.
    Voir TransformGribData pour les options.
    """

    type_name = "Transformation données CEP"
    dataset_tag = "ECMWF_IFS"

    def _input_file_pattern(self, variable, forecast_date, forecast_hour):
        return f'CEP_{variable}_{forecast_date}{forecast_hour}00.grb'
