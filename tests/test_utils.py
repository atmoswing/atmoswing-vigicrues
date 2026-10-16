import socket
import tempfile
import threading
from pathlib import Path

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
