import importlib
import os
import tempfile
import types

import pytest

import atmoswing_vigicrues as asv

DIR_PATH = os.path.dirname(os.path.abspath(__file__))


def test_controller_instance_fails_if_config_is_none():
    with pytest.raises(asv.OptionError):
        asv.Controller(None)


def test_controller_instance_fails_if_config_file_is_none():
    options = types.SimpleNamespace(config_file=None)
    with pytest.raises(asv.OptionError):
        asv.Controller(options)


def test_controller_instance_fails_if_config_file_is_not_found():
    options = types.SimpleNamespace(config_file='/some/path')
    with pytest.raises(asv.FilePathError):
        asv.Controller(options)


def test_controller_instance_succeeds():
    options = types.SimpleNamespace(config_file=DIR_PATH + '/files/config.yaml')
    asv.Controller(options)


def test_controller_can_identify_non_existing_actions():
    assert not hasattr(importlib.import_module('atmoswing_vigicrues'), 'FakeAction')


def test_controller_can_instantiate_actions():
    assert hasattr(importlib.import_module('atmoswing_vigicrues'), 'ExportBdApBp')
    with tempfile.TemporaryDirectory() as tmp_dir:
        options = asv.Options(
            types.SimpleNamespace(config_file=DIR_PATH + '/files/config.yaml',
                                  bdapbp_output_dir=tmp_dir))
        fct = getattr(importlib.import_module('atmoswing_vigicrues'), 'ExportBdApBp')
        fct(options)
