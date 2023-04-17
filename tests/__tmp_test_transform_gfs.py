import os
import shutil
import tempfile
import types
from datetime import datetime
from pathlib import Path


import pytest

import atmoswing_vigicrues as asv

DIR_PATH = os.path.dirname(os.path.abspath(__file__))


def has_required_packages() -> bool:
    return asv.has_netcdf and asv.has_eccodes

@pytest.fixture
def options():
    with tempfile.TemporaryDirectory() as tmp_dir:
        options = asv.Options(
            types.SimpleNamespace(
                config_file=DIR_PATH + '/files/config.yaml',
                gfs_lead_time_max=12,
                gfs_variables=['hgt'],
                transform_gfs_output_dir=tmp_dir,
                transform_gfs_input_dir=DIR_PATH + '/files/gfs-grib2',
            ))
    return options


def test_transform_gfs_fails_if_files_not_found(options):
    if not has_required_packages():
        return
    action = asv.TransformGfsData(options)
    date = datetime.utcnow()
    assert action.transform(date) is False
    shutil.rmtree(options.get('transform_gfs_output_dir'))


def test_eccodes_import():
    if not has_required_packages():
        return
    file = Path(DIR_PATH) / 'files' / 'gfs-grib2' / '2022' / '10' / '01'
    file = file / '2022100100.NWS_GFS_Forecast.hgt.006.grib2'
    assert file.exists()
    f = open(file, 'rb')
    msgid = asv.eccodes.codes_new_from_file(f, asv.eccodes.CODES_PRODUCT_GRIB)
    assert msgid is not None


def test_transform_gfs_succeeds(options):
    if not has_required_packages():
        return
    action = asv.TransformGfsData(options)
    date = datetime(2022, 10, 1, 0)
    assert action.transform(date)
    shutil.rmtree(options.get('transform_gfs_output_dir'))


def test_download_gfs_skipped_if_exists_locally(options):
    if not has_required_packages():
        return
    action = asv.TransformGfsData(options)
    date = datetime(2022, 10, 1, 0)
    assert action.run(date)
    assert action.run(date) is False
    shutil.rmtree(options.get('gfs_output_dir'))
