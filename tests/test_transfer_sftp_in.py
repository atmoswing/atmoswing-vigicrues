import os
import shutil
import tempfile
import types
from datetime import datetime

import paramiko
import pytest

import atmoswing_vigicrues as asv

DIR_PATH = os.path.dirname(os.path.abspath(__file__))

# Needs a running docker container (see files/sftp-docker-instructions.txt)
RUN_SFTP = False


@pytest.fixture
def options_no_variables():
    with tempfile.TemporaryDirectory() as tmp_dir:
        options_full = asv.Options(
            types.SimpleNamespace(
                config_file=DIR_PATH + '/files/config_cep_download.yaml'
            ))

        action_options = options_full.config['pre_actions'][0]['with']
        action_options['local_dir'] = tmp_dir

    return action_options


@pytest.fixture
def options_with_variables():
    with tempfile.TemporaryDirectory() as tmp_dir:
        options_full = asv.Options(
            types.SimpleNamespace(
                config_file=DIR_PATH + '/files/config_cep_download_with_variables.yaml'
            ))

        action_options = options_full.config['pre_actions'][0]['with']
        action_options['local_dir'] = tmp_dir

    return action_options


@pytest.fixture
def options_arpege():
    with tempfile.TemporaryDirectory() as tmp_dir:
        options_full = asv.Options(
            types.SimpleNamespace(
                config_file=DIR_PATH + '/files/config_arpege_download.yaml'
            ))

        action_options = options_full.config['pre_actions'][0]['with']
        action_options['local_dir'] = tmp_dir

    return action_options


def count_files_recursively(options):
    nb_files = sum([len(files) for r, d, files in os.walk(options['local_dir'])])
    return nb_files


def test_download_cep_no_variables_succeeds(options_no_variables):
    action = asv.TransferSftpIn('Get CEP data over SFTP', options_no_variables)
    date = datetime(2023, 4, 13, 12)
    if RUN_SFTP:
        assert action.run(date)
        assert count_files_recursively(options_no_variables) == 6
        shutil.rmtree(options_no_variables['local_dir'])


def test_download_cep_with_variables_succeeds(options_with_variables):
    action = asv.TransferSftpIn('Get CEP data over SFTP', options_with_variables)
    date = datetime(2023, 4, 13, 12)
    if RUN_SFTP:
        assert action.run(date)
        assert count_files_recursively(options_with_variables) == 4
        shutil.rmtree(options_with_variables['local_dir'])


def test_do_not_download_if_exists(options_with_variables, capsys):
    action = asv.TransferSftpIn('Get CEP data over SFTP', options_with_variables)
    date = datetime(2023, 4, 13, 12)
    if RUN_SFTP:
        assert action.run(date)
        assert count_files_recursively(options_with_variables) == 4
        assert action.run(date)
        captured = capsys.readouterr()
        assert captured.out == "  -> Fichiers déjà présents localement.\n"
        shutil.rmtree(options_with_variables['local_dir'])


def test_download_arpege_succeeds(options_arpege):
    action = asv.TransferSftpIn('Get ARPEGE data over SFTP', options_arpege)
    date = datetime(2023, 4, 17, 00)
    if RUN_SFTP:
        assert action.run(date)
        assert count_files_recursively(options_arpege) == 3
        shutil.rmtree(options_arpege['local_dir'])


@pytest.mark.parametrize('proxy_type', [None, 'http', 'socks5'])
def test_proxy_tunnel_is_used_for_sftp_connection(options_no_variables, monkeypatch,
                                                  proxy_type):
    options_no_variables['proxy_host'] = 'proxy.local'
    options_no_variables['proxy_port'] = 3128
    if proxy_type:
        options_no_variables['proxy_type'] = proxy_type
    proxy_socket = object()
    tunnels = []
    transports = []

    def fake_connect_via_proxy(*args):
        tunnels.append(args)
        return proxy_socket

    class FakeTransport:
        def __init__(self, sock):
            self.sock = sock
            self.closed = False
            transports.append(self)

        def connect(self, username, password):
            raise paramiko.ssh_exception.SSHException("arrêt du test")

        def close(self):
            self.closed = True

    monkeypatch.setattr(asv.utils, 'connect_via_proxy', fake_connect_via_proxy)
    monkeypatch.setattr(paramiko, 'Transport', FakeTransport)

    action = asv.TransferSftpIn('Get CEP data over SFTP', options_no_variables)
    assert not action.run(datetime(2023, 4, 13, 12))
    assert tunnels == [(proxy_type or 'http', 'proxy.local', 3128,
                        options_no_variables['hostname'],
                        int(options_no_variables['port']))]
    assert transports[0].sock is proxy_socket
    assert transports[0].closed


def test_unknown_proxy_type_is_rejected(options_no_variables):
    options_no_variables['proxy_type'] = 'ftp'
    with pytest.raises(asv.Error):
        asv.TransferSftpIn('Get CEP data over SFTP', options_no_variables)
