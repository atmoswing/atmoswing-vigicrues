import os
import shutil
import tempfile
import types
from datetime import datetime, timedelta

import pytest

import atmoswing_vigicrues as asv

DIR_PATH = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def options():
    with tempfile.TemporaryDirectory() as tmp_dir:
        options = asv.Options(
            types.SimpleNamespace(
                config_file=DIR_PATH + '/files/config.yaml',
                gfs_output_dir=tmp_dir,
                gfs_lead_time_max=12,
                gfs_variables=['hgt'],
                gfs_levels=[500, 1000],
                gfs_domain=[-5, 5, 40, 45],
                gfs_resolution=0.25
            ))
    return options


def test_download_gfs_fails_if_files_not_found(options):
    action = asv.DownloadGfsData(options)
    date = datetime.utcnow()
    date = date.replace(date.year + 1)
    assert action.download(date) is False
    shutil.rmtree(options.get('gfs_output_dir'))


def test_download_gfs_succeeds(options):
    action = asv.DownloadGfsData(options)
    date = datetime.utcnow() - timedelta(days=1)
    assert action.download(date)
    shutil.rmtree(options.get('gfs_output_dir'))


def test_download_gfs_for_today_succeeds(options):
    action = asv.DownloadGfsData(options)
    assert action.run(datetime.utcnow())
    shutil.rmtree(options.get('gfs_output_dir'))


def test_download_gfs_skipped_if_exists_locally(options):
    action = asv.DownloadGfsData(options)
    assert action.run(datetime.utcnow())
    assert action.run(datetime.utcnow()) is False
    shutil.rmtree(options.get('gfs_output_dir'))
