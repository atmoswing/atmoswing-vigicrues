import os
import shutil
import tempfile
import types
from datetime import datetime, timezone
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

        action_options = options.config['pre_actions'][2]['with']
        action_options['input_dir'] = DIR_PATH + '/files/ecmwf-grib2'
        action_options['output_dir'] = tmp_dir

    return action_options


def count_files_recursively(options):
    nb_files = sum([len(files) for r, d, files in os.walk(options['output_dir'])])
    return nb_files


def test_transform_ecmwf_fails_if_files_not_found(options):
    if not has_required_packages():
        return
    action = asv.TransformEcmwfData('Transform ECMWF data', options)
    date = datetime.now(timezone.utc)
    assert action.transform(date) is False
    shutil.rmtree(options['output_dir'])


def test_eccodes_import():
    if not has_required_packages():
        return
    file = Path(DIR_PATH) / 'files' / 'ecmwf-grib2' / '2023' / '02' / '02'
    file = file / 'CEP_Z_202302020000.grb'
    assert file.exists()
    f = open(file, 'rb')
    msgid = asv.eccodes.codes_new_from_file(f, asv.eccodes.CODES_PRODUCT_GRIB)
    assert msgid is not None
    f.close()


def test_transform_ecmwf_succeeds(options):
    if not has_required_packages():
        return
    action = asv.TransformEcmwfData('Transform ECMWF data', options)
    date = datetime(2023, 2, 2, 0)
    assert action.transform(date)
    assert count_files_recursively(options) == 1
    shutil.rmtree(options['output_dir'])
