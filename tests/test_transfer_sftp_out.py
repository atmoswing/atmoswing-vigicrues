import glob
import json
import os
import types
from datetime import datetime

import paramiko
import pytest

import atmoswing_vigicrues as asv

DIR_PATH = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def options():
    options = asv.Options(
        types.SimpleNamespace(
            config_file=DIR_PATH + '/files/config_dissemination_sftp_adn.yaml'
        ))

    action_options = options.config['disseminations'][0]['with']
    action_options['local_dir'] = DIR_PATH + '/atmoswing-forecasts-v2.1'

    return action_options


@pytest.fixture
def forecast_files():
    return glob.glob(DIR_PATH + "/files/atmoswing-forecasts-v2.1/2022/12/16/*.nc")


@pytest.mark.sftp
def test_upload_nc_succeeds(options, forecast_files):
    action = asv.TransferSftpOut('Upload nc files over SFTP', options)
    action.feed(forecast_files)
    date = datetime(2022, 12, 16, 00)
    assert action.run(date)


def test_proxy_type_is_used_for_sftp_connection(options, forecast_files,
                                                monkeypatch):
    options['proxy_host'] = 'proxy.local'
    options['proxy_port'] = 1080
    options['proxy_type'] = 'SOCKS5'
    options['proxy_username'] = 'utilisateur'
    options['proxy_password'] = 1234
    tunnels = []

    def fake_connect_via_proxy(*args, **kwargs):
        tunnels.append((args, kwargs))
        raise asv.Error("arrêt du test")

    monkeypatch.setattr(asv.utils, 'connect_via_proxy', fake_connect_via_proxy)
    monkeypatch.setattr(paramiko, 'Transport',
                        lambda sock: pytest.fail("Connexion directe inattendue."))

    action = asv.TransferSftpOut('Upload nc files over SFTP', options)
    action.feed(forecast_files)
    assert not action.run(datetime(2022, 12, 16, 00))
    assert tunnels == [(('socks5', 'proxy.local', 1080, options['hostname'],
                         int(options['port'])),
                        {'username': 'utilisateur', 'password': '1234'})]


def test_unknown_proxy_type_is_rejected(options):
    options['proxy_type'] = 'socks6'
    with pytest.raises(asv.Error):
        asv.TransferSftpOut('Upload nc files over SFTP', options)


class FakeSftp:
    def __init__(self, remote_files):
        self.remote_files = remote_files
        self.uploaded = []

    def chdir(self, path):
        pass

    def mkdir(self, path):
        pass

    def stat(self, filename):
        if filename not in self.remote_files:
            raise FileNotFoundError(filename)
        return types.SimpleNamespace(st_size=self.remote_files[filename])

    def put(self, local_path, filename):
        self.uploaded.append(filename)

    def close(self):
        pass


@pytest.fixture
def local_exports(tmp_path):
    ok_file = tmp_path / 'ok.json'
    ok_file.write_text(json.dumps({'status': 0, 'data': 'résultats'}))
    error_file = tmp_path / 'error.json'
    error_file.write_text(json.dumps({'status': 200, 'data': None}))
    nc_file = tmp_path / 'forecast.nc'
    nc_file.write_text('données netcdf')
    return [str(ok_file), str(error_file), str(nc_file)]


@pytest.mark.parametrize('remote_sizes, expected', [
    ({}, ['ok.json', 'error.json', 'forecast.nc']),
    ('same', ['error.json']),
    ({'ok.json': 5, 'error.json': 5, 'forecast.nc': 5}, ['ok.json', 'error.json']),
])
def test_upload_replaces_remote_exports_in_error(options, local_exports, monkeypatch,
                                                 remote_sizes, expected):
    if remote_sizes == 'same':
        remote_sizes = {os.path.basename(f): os.path.getsize(f)
                        for f in local_exports}
    sftp = FakeSftp(remote_sizes)
    monkeypatch.setattr(paramiko, 'Transport', lambda address: types.SimpleNamespace(
        connect=lambda hostkey, username, password: None, close=lambda: None))
    monkeypatch.setattr(paramiko.SFTPClient, 'from_transport',
                        lambda transport: sftp)

    action = asv.TransferSftpOut('Upload over SFTP', options)
    action.feed(local_exports)
    assert action.run(datetime(2022, 12, 16, 00))
    assert sftp.uploaded == expected
