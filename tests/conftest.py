import os

import pytest

# Tests nécessitant une ressource externe : ignorés (et signalés comme tels) sauf
# si la variable d'environnement correspondante vaut 1.
EXTERNAL_MARKERS = {
    'atmoswing': ('ASV_TEST_ATMOSWING', "AtmoSwing Forecaster et le jeu de données "
                                        "de test (ASV_TEST_DATA_PATH)"),
    'sftp': ('ASV_TEST_SFTP', "un serveur SFTP (voir "
                              "files/sftp-docker-instructions.txt)"),
    'ftp': ('ASV_TEST_FTP', "un serveur FTP"),
    'network': ('ASV_TEST_NETWORK', "un accès aux serveurs NOMADS"),
}


def pytest_configure(config):
    for marker, (env, description) in EXTERNAL_MARKERS.items():
        config.addinivalue_line(
            'markers', f"{marker}: nécessite {description} ({env}=1)")


def pytest_collection_modifyitems(config, items):
    for item in items:
        for marker, (env, description) in EXTERNAL_MARKERS.items():
            if marker in item.keywords and os.environ.get(env) != '1':
                item.add_marker(pytest.mark.skip(
                    reason=f"nécessite {description} ({env}=1)"))
