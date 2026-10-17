import bz2
import gzip
import logging
import lzma
import os
import shutil
import socket
import tarfile
import tempfile
import threading
import types
from datetime import datetime

import paramiko
import pytest

import atmoswing_vigicrues as asv

DIR_PATH = os.path.dirname(os.path.abspath(__file__))


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


@pytest.mark.sftp
def test_download_cep_no_variables_succeeds(options_no_variables):
    action = asv.TransferSftpIn('Get CEP data over SFTP', options_no_variables)
    date = datetime(2023, 4, 13, 12)
    assert action.run(date)
    assert count_files_recursively(options_no_variables) == 6
    shutil.rmtree(options_no_variables['local_dir'])


@pytest.mark.sftp
def test_download_cep_with_variables_succeeds(options_with_variables):
    action = asv.TransferSftpIn('Get CEP data over SFTP', options_with_variables)
    date = datetime(2023, 4, 13, 12)
    assert action.run(date)
    assert count_files_recursively(options_with_variables) == 4
    shutil.rmtree(options_with_variables['local_dir'])


@pytest.mark.sftp
def test_do_not_download_if_exists(options_with_variables, caplog):
    action = asv.TransferSftpIn('Get CEP data over SFTP', options_with_variables)
    date = datetime(2023, 4, 13, 12)
    assert action.run(date)
    assert count_files_recursively(options_with_variables) == 4
    caplog.set_level(logging.INFO, logger='atmoswing_vigicrues')
    caplog.clear()
    assert action.run(date)
    assert caplog.messages == ["  -> Fichiers déjà présents localement."]
    shutil.rmtree(options_with_variables['local_dir'])


@pytest.mark.sftp
def test_download_arpege_succeeds(options_arpege):
    action = asv.TransferSftpIn('Get ARPEGE data over SFTP', options_arpege)
    date = datetime(2023, 4, 17, 00)
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

    def fake_connect_via_proxy(*args, **kwargs):
        tunnels.append(args)
        return proxy_socket

    class FakeTransport:
        def __init__(self, sock):
            self.sock = sock
            self.closed = False
            transports.append(self)

        def connect(self, hostkey, username, password):
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


def test_proxy_credentials_are_used_for_sftp_connection(options_no_variables,
                                                        monkeypatch):
    options_no_variables['proxy_host'] = 'proxy.local'
    options_no_variables['proxy_port'] = 3128
    options_no_variables['proxy_username'] = 'utilisateur'
    options_no_variables['proxy_password'] = 'mot de passe é'
    credentials = []

    def fake_connect_via_proxy(*args, **kwargs):
        credentials.append(kwargs)
        raise asv.Error("arrêt du test")

    monkeypatch.setattr(asv.utils, 'connect_via_proxy', fake_connect_via_proxy)

    action = asv.TransferSftpIn('Get CEP data over SFTP', options_no_variables)
    assert not action.run(datetime(2023, 4, 13, 12))
    assert credentials == [{'username': 'utilisateur',
                            'password': 'mot de passe é'}]


def test_unknown_proxy_type_is_rejected(options_no_variables):
    options_no_variables['proxy_type'] = 'ftp'
    with pytest.raises(asv.Error):
        asv.TransferSftpIn('Get CEP data over SFTP', options_no_variables)


class RecordingSshServer(paramiko.ServerInterface):
    """Serveur SSH minimal qui enregistre les mots de passe reçus."""

    def __init__(self):
        self.passwords = []

    def get_allowed_auths(self, username):
        return 'password'

    def check_auth_password(self, username, password):
        self.passwords.append(password)
        return paramiko.AUTH_SUCCESSFUL


@pytest.fixture(scope='module')
def ssh_server_key():
    return paramiko.RSAKey.generate(1024)


@pytest.fixture
def ssh_server(ssh_server_key):
    """Serveur SSH local, exécuté dans un thread (une seule connexion)."""
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen(1)
    server = RecordingSshServer()
    transports = []

    def serve():
        try:
            conn, _ = listener.accept()
        except OSError:
            return
        transport = paramiko.Transport(conn)
        transports.append(transport)
        transport.add_server_key(ssh_server_key)
        try:
            transport.start_server(server=server)
            transport.join(timeout=10)
        except Exception:
            pass

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    yield listener.getsockname()[1], server
    listener.close()
    for transport in transports:
        transport.close()
    thread.join(timeout=10)


def write_known_hosts(path, port, key):
    host_keys = paramiko.HostKeys()
    host_keys.add(f'[127.0.0.1]:{port}', key.get_name(), key)
    host_keys.save(str(path))
    return str(path)


@pytest.mark.parametrize('known_key, password_sent', [
    ('server', True),
    ('other', False),
    (None, True),
])
def test_server_key_is_verified_before_sending_password(
        options_no_variables, ssh_server, ssh_server_key, tmp_path, known_key,
        password_sent):
    port, server = ssh_server
    options_no_variables['hostname'] = '127.0.0.1'
    options_no_variables['port'] = port
    options_no_variables['password'] = 'secret'
    if known_key:
        key = ssh_server_key if known_key == 'server' else \
            paramiko.RSAKey.generate(1024)
        options_no_variables['known_hosts'] = write_known_hosts(
            tmp_path / 'known_hosts', port, key)

    action = asv.TransferSftpIn('Get CEP data over SFTP', options_no_variables)
    # Le serveur de test ne fournit pas le sous-système SFTP : échec après
    # l'authentification dans tous les cas.
    assert not action.run(datetime(2023, 4, 13, 12))
    assert server.passwords == (['secret'] if password_sent else [])


def test_missing_known_hosts_file_is_rejected(options_no_variables, tmp_path):
    options_no_variables['known_hosts'] = str(tmp_path / 'absent')
    with pytest.raises(asv.FilePathError):
        asv.TransferSftpIn('Get CEP data over SFTP', options_no_variables)


def test_unpack_tar_archive_extracts_regular_files_flat(tmp_path):
    source = tmp_path / 'source'
    (source / 'sub').mkdir(parents=True)
    (source / 'sub' / 'CEP_z_2023041312.grb').write_bytes(b'grib')
    archive_path = tmp_path / 'CEP_2023041312.tar.gz'
    with tarfile.open(archive_path, 'w:gz') as archive:
        archive.add(source / 'sub' / 'CEP_z_2023041312.grb',
                    arcname='../../sub/CEP_z_2023041312.grb')
        link = tarfile.TarInfo('lien')
        link.type = tarfile.SYMTYPE
        link.linkname = '/etc/passwd'
        archive.addfile(link)

    target = tmp_path / 'target'
    target.mkdir()
    asv.TransferSftpIn._unpack_if_needed(archive_path, target)
    assert sorted(p.name for p in target.iterdir()) == ['CEP_z_2023041312.grb']
    assert (target / 'CEP_z_2023041312.grb').read_bytes() == b'grib'


@pytest.mark.parametrize('suffix, opener', [
    ('.gz', gzip.open), ('.bz2', bz2.open), ('.xz', lzma.open)])
def test_unpack_single_compressed_file(tmp_path, suffix, opener):
    compressed = tmp_path / f'CEP_z_2023041312.grb{suffix}'
    with opener(compressed, 'wb') as f:
        f.write(b'grib')
    asv.TransferSftpIn._unpack_if_needed(compressed, tmp_path)
    assert (tmp_path / 'CEP_z_2023041312.grb').read_bytes() == b'grib'
