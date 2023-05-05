import importlib
import os
import tempfile
import types

import pytest

import atmoswing_vigicrues as asv

DIR_PATH = os.path.dirname(os.path.abspath(__file__))
RUN_ATMOSWING = False


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
    options = types.SimpleNamespace(
        config_file=DIR_PATH + '/files/config_gfs_download.yaml')
    asv.Controller(options)


def test_controller_active_option():
    options = types.SimpleNamespace(
        config_file=DIR_PATH + '/files/config_active_tag.yaml')
    controller = asv.Controller(options)
    assert len(controller.pre_actions) == 2
    assert len(controller.post_actions) == 2
    assert len(controller.disseminations) == 2


def test_controller_can_identify_non_existing_actions():
    assert not hasattr(importlib.import_module('atmoswing_vigicrues'), 'FakeAction')


def test_controller_can_instantiate_actions():
    assert hasattr(importlib.import_module('atmoswing_vigicrues'), 'DownloadGfsData')
    with tempfile.TemporaryDirectory() as tmp_dir:
        options = asv.Options(
            types.SimpleNamespace(
                config_file=DIR_PATH + '/files/config_gfs_download.yaml'))
        fct = getattr(importlib.import_module('atmoswing_vigicrues'), 'DownloadGfsData')
        action = options.config['pre_actions'][0]
        fct(action['with'])


def test_run_atmoswing_now():
    options = types.SimpleNamespace(
        config_file=DIR_PATH + '/files/config_atmoswing_now.yaml',
        batch_file=DIR_PATH + '/files/batch_file.xml'
    )
    controller = asv.Controller(options)
    if RUN_ATMOSWING:
        controller.run()


def test_run_atmoswing_date():
    options = types.SimpleNamespace(
        config_file=DIR_PATH + '/files/config_atmoswing_date.yaml',
        batch_file=DIR_PATH + '/files/batch_file.xml'
    )
    controller = asv.Controller(options)
    if RUN_ATMOSWING:
        controller.run()


def test_run_atmoswing_past():
    options = types.SimpleNamespace(
        config_file=DIR_PATH + '/files/config_atmoswing_past.yaml',
        batch_file=DIR_PATH + '/files/batch_file.xml'
    )
    controller = asv.Controller(options)
    if RUN_ATMOSWING:
        controller.run()


def test_run_atmoswing_now_full_pipeline():
    options = types.SimpleNamespace(
        config_file=DIR_PATH + '/files/config_atmoswing_now_full.yaml',
        batch_file=DIR_PATH + '/files/batch_file.xml'
    )
    controller = asv.Controller(options)
    if RUN_ATMOSWING:
        controller.run()


def test_special_characters_in_config_file():
    options = types.SimpleNamespace(
        config_file=DIR_PATH + '/files/config_with_special_characters.yaml',
        batch_file=DIR_PATH + '/files/batch_file.xml'
    )
    controller = asv.Controller(options)
    decoded_password = controller.options.config['pre_actions'][0]['with']['password']
    assert decoded_password == '@#°§&£¢$*[]{}()+'

