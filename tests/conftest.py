import logging
import os

import pytest

from atmoswing_vigicrues.__main__ import LOG_HANDLER_NAME

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


@pytest.fixture(autouse=True)
def reset_logging():
    """Retire la configuration de la journalisation faite par main()."""
    yield
    root = logging.getLogger()
    for handler in list(root.handlers):
        if handler.get_name() == LOG_HANDLER_NAME:
            root.removeHandler(handler)
    root.setLevel(logging.WARNING)
    logging.getLogger('atmoswing_vigicrues').setLevel(logging.NOTSET)


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
