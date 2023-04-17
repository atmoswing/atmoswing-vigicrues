__author__ = "Pascal Horton"
__email__ = "pascal.horton@terranum.ch"

try:
    from netCDF4 import Dataset
except ImportError:
    has_netcdf = False
else:
    has_netcdf = True

try:
    import eccodes
except ImportError:
    has_eccodes = False
else:
    has_eccodes = True

from .controller import Controller
from .options import Options
from .exceptions import (ConfigError, Error, FilePathError, OptionError,
                         PathError)
from .preactions.download_gfs import DownloadGfsData
from .preactions.transfer_sftp_in import TransferSftpIn
from .preactions.transform_gfs import TransformGfsData
from .preactions.transform_ecmwf import TransformEcmwfData
from .postactions.export_bdapbp import ExportBdApBp
from .postactions.export_prv import ExportPrv
from .disseminations.transfer_sftp_out import TransferSftpOut
from .utils import file_exists, check_dir_exists, check_file_exists, \
    build_date_dir_structure


__all__ = ('Error', 'OptionError', 'ConfigError', 'PathError', 'FilePathError',
           'Controller', 'Options', 'ExportBdApBp', 'ExportPrv', 'TransferSftpOut',
           'DownloadGfsData', 'TransformGfsData', 'TransformEcmwfData', 'file_exists',
           'check_file_exists', 'check_dir_exists', 'build_date_dir_structure',
           'Dataset', 'eccodes', 'TransferSftpIn')
