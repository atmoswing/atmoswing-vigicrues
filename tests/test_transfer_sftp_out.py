import glob
import os
import types
from datetime import datetime

import paramiko
import pytest

import atmoswing_vigicrues as asv

DIR_PATH = os.path.dirname(os.path.abspath(__file__))

# Needs a running docker container (see files/sftp-docker-instructions.txt)
RUN_SFTP = False


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


def test_upload_nc_succeeds(options, forecast_files):
    action = asv.TransferSftpOut('Upload nc files over SFTP', options)
    action.feed(forecast_files)
    date = datetime(2022, 12, 16, 00)
    if RUN_SFTP:
        assert action.run(date)


def test_proxy_type_is_used_for_sftp_connection(options, forecast_files,
                                                monkeypatch):
    options['proxy_host'] = 'proxy.local'
    options['proxy_port'] = 1080
    options['proxy_type'] = 'SOCKS5'
    tunnels = []

    def fake_connect_via_proxy(*args):
        tunnels.append(args)
        raise asv.Error("arrêt du test")

    monkeypatch.setattr(asv.utils, 'connect_via_proxy', fake_connect_via_proxy)
    monkeypatch.setattr(paramiko, 'Transport',
                        lambda sock: pytest.fail("Connexion directe inattendue."))

    action = asv.TransferSftpOut('Upload nc files over SFTP', options)
    action.feed(forecast_files)
    assert not action.run(datetime(2022, 12, 16, 00))
    assert tunnels == [('socks5', 'proxy.local', 1080, options['hostname'],
                        int(options['port']))]


def test_unknown_proxy_type_is_rejected(options):
    options['proxy_type'] = 'socks6'
    with pytest.raises(asv.Error):
        asv.TransferSftpOut('Upload nc files over SFTP', options)
