import glob
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
