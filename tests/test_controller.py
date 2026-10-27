import datetime
import glob
import importlib
import os
import shutil
import subprocess
import sys
import tempfile
import types
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import atmoswing_vigicrues as asv

DIR_PATH = os.path.dirname(os.path.abspath(__file__))

# Jeu de données privé requis par les tests marqués 'atmoswing'
DATA_PATH = os.environ.get(
    'ASV_TEST_DATA_PATH',
    R'D:\_Terranum\2022 DREAL AtmoSwing\Data\Python module testing')


@pytest.fixture
def tmp_dir(tmp_path):
    tmp_dir = str(tmp_path)
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


def get_controller_with_fixed_paths_full(options, tmp_dir):
    controller = asv.Controller(options)
    controller.pre_actions[0].output_dir = DIR_PATH + '/__data_cache__'
    controller.options.config['atmoswing']['with']['output_dir'] = tmp_dir + '/output'
    controller.post_actions[0].output_dir = tmp_dir + '/bdapbp'
    controller.post_actions[1].output_dir = tmp_dir + '/prv'
    return controller


def get_controller_with_fixed_paths_preaction(options, tmp_dir):
    controller = asv.Controller(options)
    controller.pre_actions[0].output_dir = DIR_PATH + '/__data_cache__'
    controller.options.config['atmoswing']['with']['output_dir'] = tmp_dir + '/output'
    return controller


def get_controller_with_fixed_paths_simple(options, tmp_dir):
    controller = asv.Controller(options)
    controller.options.config['atmoswing']['with']['output_dir'] = tmp_dir + '/output'
    return controller


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


@pytest.mark.atmoswing
def test_run_atmoswing_now(tmp_dir):
    options = types.SimpleNamespace(
        config_file=DIR_PATH + '/files/config_atmoswing_now.yaml',
        batch_file=tmp_dir + '/batch_file.xml'
    )
    controller = get_controller_with_fixed_paths_simple(options, tmp_dir)
    controller.run()
    shutil.rmtree(tmp_dir)


@pytest.mark.atmoswing
def test_run_atmoswing_date(tmp_dir):
    options = types.SimpleNamespace(
        config_file=DIR_PATH + '/files/config_atmoswing_date.yaml',
        batch_file=tmp_dir + '/batch_file.xml'
    )
    controller = get_controller_with_fixed_paths_simple(options, tmp_dir)
    controller.run()
    shutil.rmtree(tmp_dir)


@pytest.mark.atmoswing
def test_run_atmoswing_past(tmp_dir):
    options = types.SimpleNamespace(
        config_file=DIR_PATH + '/files/config_atmoswing_past.yaml',
        batch_file=tmp_dir + '/batch_file.xml'
    )
    controller = get_controller_with_fixed_paths_simple(options, tmp_dir)
    controller.run()
    shutil.rmtree(tmp_dir)


@pytest.mark.atmoswing
def test_run_atmoswing_now_full_pipeline(tmp_dir):
    options = types.SimpleNamespace(
        config_file=DIR_PATH + '/files/config_atmoswing_now_full.yaml',
        batch_file=tmp_dir + '/batch_file.xml'
    )
    controller = get_controller_with_fixed_paths_full(options, tmp_dir)
    controller.run()
    shutil.rmtree(tmp_dir)


@pytest.mark.atmoswing
@pytest.mark.sftp
def test_run_atmoswing_now_full_pipeline_with_dissemination(tmp_dir):
    config_file_name = 'config_atmoswing_now_full_with_dissemination.yaml'
    options = types.SimpleNamespace(
        config_file=DIR_PATH + '/files/' + config_file_name,
        batch_file=tmp_dir + '/batch_file.xml'
    )
    controller = get_controller_with_fixed_paths_full(options, tmp_dir)
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


@pytest.mark.atmoswing
def test_catches_atmoswing_when_failing(tmp_dir):
    options = types.SimpleNamespace(
        config_file=DIR_PATH + '/files/config_atmoswing_now_full.yaml',
        batch_file=tmp_dir + '/batch_file_fail.xml'
    )
    controller = get_controller_with_fixed_paths_full(options, tmp_dir)
    controller.run()
    shutil.rmtree(tmp_dir)


@pytest.mark.atmoswing
def test_flux_stops_when_preprocess_failing(tmp_dir):
    options = types.SimpleNamespace(
        config_file=DIR_PATH + '/files/config_atmoswing_now_failing_preaction.yaml',
        batch_file=tmp_dir + '/batch_file_fail.xml'
    )
    controller = get_controller_with_fixed_paths_preaction(options, tmp_dir)
    controller.run()
    shutil.rmtree(tmp_dir)


class StubPreAction(asv.PreAction):
    def __init__(self, results, attempts_max_hours=24, attempts_step_hours=6):
        self.type_name = "Stub"
        self.name = "stub"
        self.results = list(results)
        self.dates = []
        self.attempts_max_hours = attempts_max_hours
        self.attempts_step_hours = attempts_step_hours
        super().__init__()

    def run(self, date) -> bool:
        self.dates.append(date)
        return self.results.pop(0) if self.results else False


class StubPostAction(asv.PostAction):
    def __init__(self, result):
        self.type_name = "Stub"
        self.name = "stub"
        self.result = result
        super().__init__()

    def run(self) -> bool:
        return self.result


class StubDissemination(asv.Dissemination):
    def __init__(self, local_dir, result):
        self.type_name = "Stub"
        self.name = "stub"
        self.local_dir = local_dir
        self.extension = '.json'
        self.result = result
        super().__init__()

    def run(self, date) -> bool:
        return self.result


@pytest.fixture
def stub_controller(tmp_path):
    output_dir = (tmp_path / 'output').as_posix()
    config_file = tmp_path / 'config.yaml'
    config_file.write_text(
        "atmoswing:\n"
        "  name: Forecast now\n"
        "  active: False\n"
        "  with:\n"
        f"    output_dir: '{output_dir}'\n",
        encoding='utf-8')
    controller = asv.Controller(types.SimpleNamespace(config_file=str(config_file)))
    controller.date = datetime.datetime(2023, 6, 1, 12)
    return controller


def test_pre_actions_step_back_in_time_until_success(stub_controller):
    action = StubPreAction([False, False, True])
    stub_controller.pre_actions = [action]
    assert stub_controller.run() == 0
    assert action.dates == [datetime.datetime(2023, 6, 1, 12),
                            datetime.datetime(2023, 6, 1, 6),
                            datetime.datetime(2023, 6, 1, 0)]
    assert stub_controller.date == datetime.datetime(2023, 6, 1, 0)


def test_flux_stops_when_pre_actions_exhaust_attempts(stub_controller):
    action = StubPreAction([], attempts_max_hours=24, attempts_step_hours=6)
    post_action = StubPostAction(True)
    stub_controller.pre_actions = [action]
    stub_controller.post_actions = [post_action]
    stub_controller._run_atmoswing = lambda: pytest.fail("AtmoSwing ne doit pas "
                                                         "être exécuté.")
    assert stub_controller.run() == -1
    assert len(action.dates) == 4


def test_pre_actions_attempted_once_when_no_step_back_allowed(stub_controller):
    action = StubPreAction([], attempts_max_hours=0)
    stub_controller.pre_actions = [action]
    assert stub_controller.run() == -1
    assert len(action.dates) == 1


def test_return_code_when_post_action_fails(stub_controller, monkeypatch):
    monkeypatch.setattr(stub_controller, '_list_atmoswing_output_files',
                        lambda: ['file.nc'])
    stub_controller.post_actions = [StubPostAction(False), StubPostAction(True)]
    assert stub_controller.run() == 1


def test_return_code_when_dissemination_fails(stub_controller, tmp_path):
    stub_controller.disseminations = [
        StubDissemination(str(tmp_path), True),
        StubDissemination(str(tmp_path), False)]
    assert stub_controller.run() == 1


def test_return_code_when_all_actions_succeed(stub_controller, monkeypatch):
    monkeypatch.setattr(stub_controller, '_list_atmoswing_output_files',
                        lambda: ['file.nc'])
    stub_controller.pre_actions = [StubPreAction([True])]
    stub_controller.post_actions = [StubPostAction(True)]
    assert stub_controller.run() == 0


def test_main_exits_with_controller_return_code(tmp_path):
    config_file = tmp_path / 'config.yaml'
    config_file.write_text(
        "atmoswing:\n"
        "  name: Forecast now\n"
        "  active: False\n"
        "  with:\n"
        f"    output_dir: '{(tmp_path / 'output').as_posix()}'\n"
        "post_actions:\n"
        "  - name: Unknown\n"
        "    uses: FakeAction\n"
        "    with: {}\n",
        encoding='utf-8')
    ret = subprocess.run(
        [sys.executable, '-m', 'atmoswing_vigicrues', '-c', str(config_file)])
    assert ret.returncode != 0


@pytest.fixture
def atmoswing_controller(tmp_path, monkeypatch):
    """Contrôleur dont la commande AtmoSwing est remplacée par un exécutable donné."""
    monkeypatch.setattr(tempfile, 'gettempdir', lambda: str(tmp_path))

    def build(executable):
        config_file = tmp_path / 'config.yaml'
        config_file.write_text(
            "atmoswing:\n"
            "  name: Forecast now\n"
            "  with:\n"
            f"    atmoswing_path: '{Path(executable).as_posix()}'\n"
            "    batch_file: 'batch_file.xml'\n"
            f"    output_dir: '{(tmp_path / 'output').as_posix()}'\n",
            encoding='utf-8')
        return asv.Controller(types.SimpleNamespace(config_file=str(config_file)))

    return build


def test_atmoswing_failure_is_reported_once(atmoswing_controller, tmp_path, caplog):
    (tmp_path / 'AtmoSwingForecaster.log').write_text("ligne du journal\n")
    # Python refuse l'option '-f' : code de retour non nul
    controller = atmoswing_controller(sys.executable)
    with pytest.raises(asv.Error, match="code de retour") as error:
        controller._run_atmoswing()
    assert "Exception" not in str(error.value)
    assert caplog.text.count("ligne du journal") == 1


def test_atmoswing_exception_is_reported(atmoswing_controller, tmp_path):
    controller = atmoswing_controller(tmp_path / 'atmoswing-introuvable')
    with pytest.raises(asv.Error, match="Exception de AtmoSwing Forecaster"):
        controller._run_atmoswing()


def test_parse_log_file_handles_missing_log(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(tempfile, 'gettempdir', lambda: str(tmp_path))
    asv.Controller._parse_log_file()
    assert "n'a pas été trouvé" in caplog.text


@pytest.mark.parametrize('config_file', sorted(
    os.path.basename(f) for f in glob.glob(DIR_PATH + '/files/config*.yaml')))
def test_example_config_files_can_be_loaded(config_file, tmp_path, monkeypatch):
    # Les répertoires relatifs des configurations sont créés dans tmp_path
    monkeypatch.chdir(tmp_path)
    with open(DIR_PATH + '/files/' + config_file, encoding='utf-8') as f:
        content = f.read()
    uses_grib = 'TransformGfsData' in content or 'TransformEcmwfData' in content
    if uses_grib and not asv.preactions.transform_grib.has_toolbox:
        pytest.skip("Nécessite eccodes et atmoswing-toolbox.")
    if 'DownloadEcmwfData' in content and not (
            asv.preactions.download_ecmwf.has_ecmwf_opendata and asv.has_eccodes):
        pytest.skip("Nécessite ecmwf-opendata et eccodes.")
    options = types.SimpleNamespace(config_file=DIR_PATH + '/files/' + config_file)
    asv.Controller(options)


def test_unknown_action_is_rejected(tmp_path):
    config_file = tmp_path / 'config.yaml'
    config_file.write_text(
        "pre_actions:\n"
        "  - name: Mauvais type\n"
        "    uses: ExportPrv\n"
        "    with: {}\n",
        encoding='utf-8')
    with pytest.raises(asv.ConfigError, match="ExportPrv"):
        asv.Controller(types.SimpleNamespace(config_file=str(config_file)))


def test_missing_action_option_is_reported(tmp_path):
    config_file = tmp_path / 'config.yaml'
    config_file.write_text(
        "post_actions:\n"
        "  - name: Export sans répertoire\n"
        "    uses: ExportPrv\n"
        "    with: {}\n",
        encoding='utf-8')
    with pytest.raises(asv.ConfigError, match="output_dir.*Export sans répertoire"):
        asv.Controller(types.SimpleNamespace(config_file=str(config_file)))


def test_base_classes_cannot_be_used_as_actions(tmp_path):
    config_file = tmp_path / 'config.yaml'
    config_file.write_text(
        "pre_actions:\n"
        "  - name: Base\n"
        "    uses: PreAction\n"
        "    with: {}\n",
        encoding='utf-8')
    with pytest.raises(asv.ConfigError):
        asv.Controller(types.SimpleNamespace(config_file=str(config_file)))
