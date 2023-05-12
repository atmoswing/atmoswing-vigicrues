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
                config_file=DIR_PATH + '/files/config.yaml'
            ))

        action_options = options.config['pre_actions'][1]['with']
        action_options['input_dir'] = DIR_PATH + '/files/gfs-grib2'
        action_options['output_dir'] = tmp_dir

    return action_options


def count_files_recursively(options):
    nb_files = sum([len(files) for r, d, files in os.walk(options['output_dir'])])
    return nb_files


def test_transform_gfs_fails_if_files_not_found(options):
    if not has_required_packages():
        return
    action = asv.TransformGfsData('Transform GFS data', options)
    date = datetime.utcnow()
    assert action.transform(date) is False
    shutil.rmtree(options['output_dir'])


def test_eccodes_import():
    if not has_required_packages():
        return
    file = Path(DIR_PATH) / 'files' / 'gfs-grib2' / '2022' / '10' / '01'
    file = file / '2022100100.NWS_GFS.hgt.006.grib2'
    assert file.exists()
    f = open(file, 'rb')
    msgid = asv.eccodes.codes_new_from_file(f, asv.eccodes.CODES_PRODUCT_GRIB)
    assert msgid is not None
    f.close()


def test_transform_gfs_succeeds(options):
    if not has_required_packages():
        return
    action = asv.TransformGfsData('Transform GFS data', options)
    date = datetime(2022, 10, 1, 0)
    assert action.transform(date)
    assert count_files_recursively(options) == 1
    shutil.rmtree(options['output_dir'])
