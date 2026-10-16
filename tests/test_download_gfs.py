import os
import shutil
import tempfile
import types
from datetime import datetime, timedelta, timezone

import pytest
import requests

import atmoswing_vigicrues as asv

DIR_PATH = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def options():
    with tempfile.TemporaryDirectory() as tmp_dir:
        options_full = asv.Options(
            types.SimpleNamespace(
                config_file=DIR_PATH + '/files/config_gfs_download.yaml'
            ))

        action_options = options_full.config['pre_actions'][0]['with']
        action_options['output_dir'] = tmp_dir

    return action_options


def count_files_recursively(options):
    nb_files = sum([len(files) for r, d, files in os.walk(options['output_dir'])])
    return nb_files


@pytest.mark.network
def test_download_gfs_fails_if_files_not_found(options):
    action = asv.DownloadGfsData('Download GFS data', options)
    date = datetime.now(timezone.utc)
    date = date.replace(date.year + 1)
    assert action.download(date) is False
    shutil.rmtree(options['output_dir'])


@pytest.mark.network
def test_download_gfs_025_succeeds(options):
    options['resolution'] = 0.25
    action = asv.DownloadGfsData('Download GFS data', options)
    date = datetime.now(timezone.utc) - timedelta(days=1)
    assert action.download(date)
    assert count_files_recursively(options) == 3 * 4 * 2
    shutil.rmtree(options['output_dir'])


@pytest.mark.network
def test_download_gfs_050_succeeds(options):
    options['resolution'] = 0.50
    action = asv.DownloadGfsData('Download GFS data', options)
    date = datetime.now(timezone.utc) - timedelta(days=1)
    assert action.download(date)
    assert count_files_recursively(options) == 3 * 4 * 2
    shutil.rmtree(options['output_dir'])


@pytest.mark.network
def test_download_gfs_100_succeeds(options):
    options['resolution'] = 1
    action = asv.DownloadGfsData('Download GFS data', options)
    date = datetime.now(timezone.utc) - timedelta(days=1)
    assert action.download(date)
    assert count_files_recursively(options) == 3 * 4 * 2
    shutil.rmtree(options['output_dir'])


@pytest.mark.network
def test_download_gfs_default_succeeds(options):
    action = asv.DownloadGfsData('Download GFS data', options)
    date = datetime.now(timezone.utc) - timedelta(days=1)
    assert action.download(date)
    assert count_files_recursively(options) == 3 * 4 * 2
    shutil.rmtree(options['output_dir'])


@pytest.mark.network
def test_download_gfs_with_surface_var(options):
    options['levels'] = [500, 1000, 'surface']
    action = asv.DownloadGfsData('Download GFS data', options)
    date = datetime.now(timezone.utc) - timedelta(days=1)
    assert action.run(date)
    assert count_files_recursively(options) == 3 * 4 * 2
    shutil.rmtree(options['output_dir'])


@pytest.mark.network
def test_download_gfs_entire_atmosphere_var(options):
    options['levels'] = ['entire_atmosphere']
    options['variables'] = ['pwat']
    action = asv.DownloadGfsData('Download GFS data', options)
    date = datetime.now(timezone.utc) - timedelta(days=1)
    assert action.run(date)
    assert count_files_recursively(options) == 3 * 4
    shutil.rmtree(options['output_dir'])


@pytest.mark.parametrize('timeout, expected', [(None, 120), (30, 30)])
def test_download_gfs_uses_timeout(options, monkeypatch, timeout, expected):
    if timeout:
        options['timeout'] = timeout
    calls = []

    def fake_get(url, **kwargs):
        calls.append(kwargs)
        raise requests.exceptions.Timeout("délai dépassé")

    monkeypatch.setattr(requests, 'get', fake_get)
    action = asv.DownloadGfsData('Download GFS data', options)
    assert action.download(datetime(2023, 6, 1, 0)) is False
    assert calls[0]['timeout'] == expected
    shutil.rmtree(options['output_dir'])


@pytest.mark.parametrize('proxies, expected', [
    (None, None),
    ({'http': '', 'https': ''}, None),
    ({'http': 'http://proxy:3128', 'https': ''}, {'http': 'http://proxy:3128'}),
])
def test_download_gfs_ignores_empty_proxies(options, proxies, expected):
    options['proxies'] = proxies
    action = asv.DownloadGfsData('Download GFS data', options)
    assert action.proxies == expected
    shutil.rmtree(options['output_dir'])
