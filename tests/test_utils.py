import socket
import tempfile
import threading
from pathlib import Path

import numpy as np
import pytest

import atmoswing_vigicrues as asv


def test_check_file_exists_fails():
    with tempfile.TemporaryDirectory() as tmp_dir:
        with pytest.raises(asv.Error):
            asv.check_file_exists(tmp_dir)


def test_check_file_exists_succeeds():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_file = tmp_dir + '/file.txt'
        Path(tmp_file).touch()
        asv.check_file_exists(tmp_file)


def test_build_cumulative_frequency():
    f = asv.utils.build_cumulative_frequency(100)
    assert len(f) == 100
    assert f[0] > 0
    assert f[0] < 1/100
    assert f[99] < 1
    assert f[99] > 99/100


@pytest.fixture
def fake_proxy():
    """Proxy HTTP local renvoyant une réponse donnée à la requête CONNECT."""
    servers = []

    def start(response, close=False):
        server = socket.socket()
        server.bind(('127.0.0.1', 0))
        server.listen(1)
        received = []

        def serve():
            conn, _ = server.accept()
            with conn:
                request = b""
                while not request.endswith(b"\r\n\r\n"):
                    request += conn.recv(1)
                received.append(request.decode())
                conn.sendall(response)
                if not close:
                    conn.recv(1)  # Attend la fermeture côté client

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        servers.append((server, thread))
        return server.getsockname()[1], received

    yield start

    for server, thread in servers:
        thread.join(timeout=5)
        server.close()


def test_connect_via_http_proxy_keeps_data_after_headers(fake_proxy):
    port, received = fake_proxy(
        b"HTTP/1.1 200 OK\r\nProxy-Agent: test\r\n\r\nSSH-2.0-Banner\r\n")
    sock = asv.utils.connect_via_http_proxy('127.0.0.1', port, 'sftp.example.org', 22)
    with sock:
        assert sock.recv(64) == b"SSH-2.0-Banner\r\n"
    assert received[0].startswith("CONNECT sftp.example.org:22 HTTP/1.1\r\n")


def test_connect_via_http_proxy_fails_on_refused_tunnel(fake_proxy):
    port, _ = fake_proxy(b"HTTP/1.1 407 Proxy Authentication Required\r\n\r\n")
    with pytest.raises(asv.Error, match="407"):
        asv.utils.connect_via_http_proxy('127.0.0.1', port, 'sftp.example.org', 22)


def test_connect_via_http_proxy_fails_on_closed_connection(fake_proxy):
    port, _ = fake_proxy(b"HTTP/1.1 200", close=True)
    with pytest.raises(asv.Error, match="fermé"):
        asv.utils.connect_via_http_proxy('127.0.0.1', port, 'sftp.example.org', 22)


@pytest.mark.parametrize('value, expected', [
    (None, 'http'), ('', 'http'), ('http', 'http'), ('SOCKS5', 'socks5'),
    (' socks4 ', 'socks4')])
def test_parse_proxy_type(value, expected):
    assert asv.utils.parse_proxy_type(value) == expected


def test_parse_proxy_type_rejects_unknown_type():
    with pytest.raises(asv.Error, match="socks6"):
        asv.utils.parse_proxy_type('socks6')


@pytest.fixture
def fake_socks5_proxy():
    """Proxy SOCKS5 local (sans authentification) qui renvoie une bannière SSH."""
    server = socket.socket()
    server.bind(('127.0.0.1', 0))
    server.listen(1)
    received = []

    def recv_exact(conn, size):
        data = b""
        while len(data) < size:
            data += conn.recv(size - len(data))
        return data

    def serve():
        conn, _ = server.accept()
        with conn:
            nb_methods = recv_exact(conn, 2)[1]
            recv_exact(conn, nb_methods)
            conn.sendall(b"\x05\x00")
            address_type = recv_exact(conn, 4)[3]
            host = recv_exact(conn, recv_exact(conn, 1)[0]).decode()
            port = int.from_bytes(recv_exact(conn, 2), 'big')
            received.append((address_type, host, port))
            conn.sendall(b"\x05\x00\x00\x01\x7f\x00\x00\x01\x00\x16")
            conn.sendall(b"SSH-2.0-Banner\r\n")
            conn.recv(1)  # Attend la fermeture côté client

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    yield server.getsockname()[1], received
    thread.join(timeout=5)
    server.close()


def test_connect_via_socks5_proxy(fake_socks5_proxy):
    port, received = fake_socks5_proxy
    sock = asv.utils.connect_via_proxy('socks5', '127.0.0.1', port,
                                       'sftp.example.org', 22)
    with sock:
        assert sock.recv(64) == b"SSH-2.0-Banner\r\n"
    # Type d'adresse 3 : le nom de domaine est résolu par le proxy
    assert received == [(3, 'sftp.example.org', 22)]


def test_connect_via_proxy_uses_http_connect_by_default(fake_proxy):
    port, received = fake_proxy(b"HTTP/1.1 200 OK\r\n\r\n")
    sock = asv.utils.connect_via_proxy(None, '127.0.0.1', port,
                                       'sftp.example.org', 22)
    sock.close()
    assert received[0].startswith("CONNECT sftp.example.org:22 HTTP/1.1\r\n")


def test_connect_via_socks5_proxy_fails_when_unreachable():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    with pytest.raises(asv.Error):
        asv.utils.connect_via_proxy('socks5', '127.0.0.1', port,
                                    'sftp.example.org', 22, timeout=5)


def test_mjd_to_datetime():
    dates = asv.utils.mjd_to_datetime(np.array([59215.5, 59216.5]))
    assert dates.dtype == np.dtype('datetime64[s]')
    assert list(dates) == [np.datetime64('2021-01-01T12:00:00'),
                           np.datetime64('2021-01-02T12:00:00')]


def test_mjd_to_datetime_with_hourly_float32_dates():
    # Les dates horaires ne sont pas représentées exactement en float32
    mjd = (59853 + np.arange(48) / 24).astype(np.float32)
    expected = np.datetime64('2022-10-01T00', 's') + \
        np.arange(48).astype('timedelta64[h]')
    assert (asv.utils.mjd_to_datetime(mjd) == expected).all()


def test_mjd_to_datetime_rounds_to_nearest_hour():
    almost_noon = 59215.5 - 1e-6
    date = asv.utils.mjd_to_datetime(np.array([almost_noon]))[0]
    assert date == np.datetime64('2021-01-01T12:00:00')
