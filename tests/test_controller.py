import importlib
import os
import tempfile
import types
import shutil
import xml.etree.ElementTree as ET

import pytest

import atmoswing_vigicrues as asv

DIR_PATH = os.path.dirname(os.path.abspath(__file__))

# Needs a running version of AtmoSwing Forecaster installed
RUN_ATMOSWING = True
DATA_PATH = R'D:\_Terranum\2022 DREAL AtmoSwing\Data\Python module testing'


@pytest.fixture
def tmp_dir():
    tmp_dir = tempfile.TemporaryDirectory().name
    os.mkdir(tmp_dir)
    os.mkdir(tmp_dir + '/gfs')
    os.mkdir(tmp_dir + '/output')
    batch_file = DIR_PATH + '/files/batch_file.xml'

    # Open the XML file
    tree = ET.parse(batch_file)
    root = tree.getroot()

    # Replace the "__tmp_path__" string with the temp dir in all text elements
    for elem in root.iter():
        if elem.text and "__tmp_dir__" in elem.text:
            elem.text = elem.text.replace("__tmp_dir__", tmp_dir)
        if elem.text and "__files_dir__" in elem.text:
            elem.text = elem.text.replace("__files_dir__", DIR_PATH + '/files')
        if elem.text and "__data_dir__" in elem.text:
            elem.text = elem.text.replace("__data_dir__", DATA_PATH)

    # Save the updated XML to a new file
    tree.write(tmp_dir + "/batch_file.xml")

    return tmp_dir


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
    with tempfile.TemporaryDirectory():
        options = asv.Options(
            types.SimpleNamespace(
                config_file=DIR_PATH + '/files/config_gfs_download.yaml'))
        fct = getattr(importlib.import_module('atmoswing_vigicrues'), 'DownloadGfsData')
        action = options.config['pre_actions'][0]
        fct('Download GFS data', action['with'])


def test_run_atmoswing_now(tmp_dir):
    options = types.SimpleNamespace(
        config_file=DIR_PATH + '/files/config_atmoswing_now.yaml',
        batch_file=tmp_dir + '/batch_file.xml'
    )
    controller = get_controller_with_fixed_paths(options, tmp_dir)
    if RUN_ATMOSWING:
        controller.run()
    shutil.rmtree(tmp_dir)


def test_run_atmoswing_date(tmp_dir):
    options = types.SimpleNamespace(
        config_file=DIR_PATH + '/files/config_atmoswing_date.yaml',
        batch_file=tmp_dir + '/batch_file.xml'
    )
    controller = get_controller_with_fixed_paths(options, tmp_dir)
    if RUN_ATMOSWING:
        controller.run()
    shutil.rmtree(tmp_dir)


def test_run_atmoswing_past(tmp_dir):
    options = types.SimpleNamespace(
        config_file=DIR_PATH + '/files/config_atmoswing_past.yaml',
        batch_file=tmp_dir + '/batch_file.xml'
    )
    controller = get_controller_with_fixed_paths(options, tmp_dir)
    if RUN_ATMOSWING:
        controller.run()
    shutil.rmtree(tmp_dir)


def test_run_atmoswing_now_full_pipeline(tmp_dir):
    options = types.SimpleNamespace(
        config_file=DIR_PATH + '/files/config_atmoswing_now_full.yaml',
        batch_file=tmp_dir + '/batch_file.xml'
    )
    controller = get_controller_with_fixed_paths(options, tmp_dir)
    if RUN_ATMOSWING:
        controller.run()
    shutil.rmtree(tmp_dir)


def test_special_characters_in_config_file():
    options = types.SimpleNamespace(
        config_file=DIR_PATH + '/files/config_with_special_characters.yaml',
        batch_file=DIR_PATH + '/files/batch_file.xml'
    )
    controller = asv.Controller(options)
    decoded_password = controller.options.config['pre_actions'][0]['with']['password']
    assert decoded_password == '@#°§&£¢$*[]{}()+'


def test_catches_atmoswing_when_failing(tmp_dir):
    options = types.SimpleNamespace(
        config_file=DIR_PATH + '/files/config_atmoswing_now_full.yaml',
        batch_file=tmp_dir + '/batch_file_fail.xml'
    )
    controller = get_controller_with_fixed_paths(options, tmp_dir)
    if RUN_ATMOSWING:
        controller.run()
    shutil.rmtree(tmp_dir)


def test_flux_stops_when_preprocess_failing(tmp_dir):
    options = types.SimpleNamespace(
        config_file=DIR_PATH + '/files/config_atmoswing_now_failing_preaction.yaml',
        batch_file=tmp_dir + '/batch_file_fail.xml'
    )
    controller = get_controller_with_fixed_paths(options, tmp_dir)
    if RUN_ATMOSWING:
        controller.run()
    shutil.rmtree(tmp_dir)


def test_list_only_new_forecaster_files(tmp_dir, capsys):
    options = types.SimpleNamespace(
        config_file=DIR_PATH + '/files/config_atmoswing_now_full.yaml',
        batch_file=tmp_dir + '/batch_file.xml'
    )
    controller = get_controller_with_fixed_paths(options, tmp_dir)
    if RUN_ATMOSWING:
        controller.run()
        captured = capsys.readouterr()
        assert captured.out == "  -> Exécution correcte.\n"
        controller.run()
        captured = capsys.readouterr()
        assert captured.out == "  -> Fichiers déjà présents localement.\n"

    shutil.rmtree(tmp_dir)


def get_controller_with_fixed_paths(options, tmp_dir):
    controller = asv.Controller(options)
    controller.pre_actions[0].output_dir = DIR_PATH + '/__data_cache__'
    controller.options.config['atmoswing']['with']['output_dir'] = tmp_dir + '/output'
    controller.post_actions[0].output_dir = tmp_dir + '/bdapbp'
    controller.post_actions[1].output_dir = tmp_dir + '/prv'
    return controller
