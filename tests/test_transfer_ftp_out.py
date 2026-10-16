import ftplib
import glob
import json
import os
import socket
import types
from datetime import datetime

import pytest
import socks

import atmoswing_vigicrues as asv
from atmoswing_vigicrues.disseminations.transfer_ftp_out import FtpViaProxy

DIR_PATH = os.path.dirname(os.path.abspath(__file__))

# Needs a running docker container
RUN_FTP = False


@pytest.fixture
def options():
    options = asv.Options(
        types.SimpleNamespace(
            config_file=DIR_PATH + '/files/config_dissemination_ftp.yaml'
        ))

    action_options = options.config['disseminations'][0]['with']
    action_options['local_dir'] = DIR_PATH + '/atmoswing-forecasts-v2.1'

    return action_options


@pytest.fixture
def forecast_files():
    return glob.glob(DIR_PATH + "/files/atmoswing-forecasts-v2.1/2022/12/16/*.nc")


def test_upload_nc_succeeds(options, forecast_files):
    action = asv.TransferFtpOut('Upload nc files over FTP', options)
    action.feed(forecast_files)
    date = datetime(2022, 12, 16, 00)
    if RUN_FTP:
        assert action.run(date)


def _closed_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def test_proxy_does_not_patch_global_socket(options, forecast_files):
    options['proxy_host'] = '127.0.0.1'
    options['proxy_port'] = _closed_port()
    original_socket = socket.socket
    action = asv.TransferFtpOut('Upload nc files over FTP', options)
    action.feed(forecast_files)
    assert not action.run(datetime(2022, 12, 16, 00))
    assert socket.socket is original_socket


@pytest.fixture
def proxied_connections(monkeypatch):
    calls = []
    peers = []

    def fake_create_connection(dest_pair, timeout=None, source_address=None,
                               **kwargs):
        calls.append((dest_pair, kwargs))
        ours, peer = socket.socketpair()
        if not calls[1:]:
            peer.sendall(b"220 Bienvenue\r\n")
        peers.append(peer)
        return ours

    monkeypatch.setattr(socks, 'create_connection', fake_create_connection)
    yield calls
    for peer in peers:
        peer.close()


def test_ftp_via_proxy_routes_control_and_data_connections(proxied_connections,
                                                           monkeypatch):
    ftp = FtpViaProxy(socks.HTTP, 'proxy.local', 3128)
    assert ftp.connect('ftp.example.org', 21) == '220 Bienvenue'

    monkeypatch.setattr(ftp, 'makepasv', lambda: ('10.0.0.5', 50000))
    monkeypatch.setattr(ftp, 'sendcmd', lambda cmd: '150 Ouverture')
    conn, _ = ftp.ntransfercmd('STOR file.nc')
    conn.close()
    ftp.close()

    proxy = {'proxy_type': socks.HTTP, 'proxy_addr': 'proxy.local',
             'proxy_port': 3128}
    assert proxied_connections == [(('ftp.example.org', 21), proxy),
                                   (('10.0.0.5', 50000), proxy)]


def test_ftp_via_proxy_rejects_active_mode(proxied_connections):
    ftp = FtpViaProxy(socks.HTTP, 'proxy.local', 3128)
    ftp.connect('ftp.example.org', 21)
    ftp.set_pasv(False)
    with pytest.raises(asv.Error):
        ftp.ntransfercmd('STOR file.nc')
    ftp.close()


class FakeFtp:
    def __init__(self, remote_files, size_supported=True):
        self.remote_files = remote_files
        self.size_supported = size_supported
        self.uploaded = []

    def connect(self, host, port):
        pass

    def login(self, username, password):
        pass

    def pwd(self):
        return '/'

    def cwd(self, path):
        pass

    def mkd(self, path):
        pass

    def voidcmd(self, cmd):
        pass

    def nlst(self):
        if not self.remote_files:
            raise ftplib.error_perm("550 No files found")
        return list(self.remote_files)

    def size(self, filename):
        if not self.size_supported:
            raise ftplib.error_perm("500 Unknown command")
        return self.remote_files[filename]

    def storbinary(self, cmd, f):
        self.uploaded.append(cmd.replace('STOR ', ''))

    def quit(self):
        pass

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


@pytest.mark.parametrize('remote_sizes, size_supported, expected', [
    ({}, True, ['ok.json', 'error.json', 'forecast.nc']),
    ('same', True, ['error.json']),
    ({'ok.json': 5, 'error.json': 5, 'forecast.nc': 5}, True,
     ['ok.json', 'error.json']),
    ('same', False, ['ok.json', 'error.json']),
])
def test_upload_replaces_remote_exports_in_error(options, local_exports, monkeypatch,
                                                 remote_sizes, size_supported,
                                                 expected):
    if remote_sizes == 'same':
        remote_sizes = {os.path.basename(f): os.path.getsize(f)
                        for f in local_exports}
    ftp = FakeFtp(remote_sizes, size_supported)
    monkeypatch.setattr(ftplib, 'FTP', lambda: ftp)

    action = asv.TransferFtpOut('Upload over FTP', options)
    action.feed(local_exports)
    assert action.run(datetime(2022, 12, 16, 00))
    assert ftp.uploaded == expected
