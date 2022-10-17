import os
import pytest
import types
import tempfile
from atmoswing_vigicrues.controller import Controller
from atmoswing_vigicrues.exceptions import *

DIR_PATH = os.path.dirname(os.path.abspath(__file__))


def test_controller_instance_fails_if_config_is_none():
    with pytest.raises(OptionError):
        Controller(None)


def test_controller_instance_fails_if_config_file_is_none():
    options = types.SimpleNamespace(config_file=None)
    with pytest.raises(OptionError):
        Controller(options)


def test_controller_instance_fails_if_config_file_is_not_found():
    options = types.SimpleNamespace(config_file='/some/path')
    with pytest.raises(FilePathError):
        Controller(options)


def test_controller_instance_succeeds():
    options = types.SimpleNamespace(config_file=DIR_PATH + '/files/config.yaml')
    Controller(options)
