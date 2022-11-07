import os
import shutil
import tempfile
import types
from datetime import datetime


import pytest

import atmoswing_vigicrues as asv

DIR_PATH = os.path.dirname(os.path.abspath(__file__))


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
                eccodes_dir=''
            ))
    return options


def test_transform_gfs_fails_if_files_not_found(options):
    action = asv.TransformGfsData(options)
    date = datetime.utcnow()
    assert action.transform(date) is False
    shutil.rmtree(options.get('transform_gfs_output_dir'))


def test_transform_gfs_succeeds(options):
    action = asv.TransformGfsData(options)
    date = datetime(2022, 10, 1, 0)
    assert action.transform(date)
    shutil.rmtree(options.get('transform_gfs_output_dir'))






def test_download_gfs_skipped_if_exists_locally(options):
    action = asv.DownloadGfsData(options)
    assert action.run()
    assert action.run() is False
    shutil.rmtree(options.get('gfs_output_dir'))
