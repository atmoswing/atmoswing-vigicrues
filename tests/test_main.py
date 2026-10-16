import os

import pytest

import atmoswing_vigicrues.__main__ as main_module

DIR_PATH = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def config_file(tmp_path):
    config_file = tmp_path / 'config.yaml'
    config_file.write_text(
        "atmoswing:\n"
        "  name: Forecast now\n"
        "  active: False\n"
        "  with:\n"
        f"    output_dir: '{(tmp_path / 'output').as_posix()}'\n",
        encoding='utf-8')
    return str(config_file)


def test_controller_instance_succeeds_through_main(config_file):
    assert main_module.main([f'--config-file={config_file}']) == 0


def test_main_with_date(config_file):
    assert main_module.main([f'--config-file={config_file}', '-d', '2023060112']) == 0


def test_main_rejects_invalid_date(config_file):
    with pytest.raises(SystemExit) as error:
        main_module.main([f'--config-file={config_file}', '-d', '2023-06-01'])
    assert error.value.code == 2


def test_main_reports_invalid_configuration(tmp_path, capsys):
    ret = main_module.main([f'--config-file={tmp_path / "absent.yaml"}'])
    assert ret == -1
    assert "La configuration est invalide" in capsys.readouterr().out


@pytest.mark.network
def test_gfs_download_through_main(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_file = DIR_PATH + '/files/config_gfs_download.yaml'
    assert main_module.main([f'--config-file={config_file}']) == 0
