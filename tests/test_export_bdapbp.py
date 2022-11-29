import glob
import json
import os
import shutil
import tempfile
import types

import pytest

import atmoswing_vigicrues as asv

DIR_PATH = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def options():
    with tempfile.TemporaryDirectory() as tmp_dir:
        options_full = asv.Options(
            types.SimpleNamespace(
                config_file=DIR_PATH + '/files/config_export_bdapbp.yaml'
            ))

        action_options = options_full.config['post_actions'][0]['with']
        action_options['output_dir'] = tmp_dir

    return action_options


@pytest.fixture
def metadata():
    metadata = {
        "forecast_date": "2022-10-01 00:00:00",
    }
    return metadata


def count_files_recursively(options):
    nb_files = sum([len(files) for r, d, files in os.walk(options['output_dir'])])
    return nb_files


def test_export_bdapbp_reports_if_files_not_found(options, metadata):
    export = asv.ExportBdApBp(options)
    export.feed(['/wrong/path'], metadata)
    export.run()
    assert count_files_recursively(options) == 1
    file_path = options['output_dir'] + '/2022/10/01/path.json'
    with open(file_path) as f:
        data = json.load(f)
        assert data['status'] == 200
    shutil.rmtree(options['output_dir'])


@pytest.fixture
def forecast_files():
    return glob.glob(DIR_PATH + "/files/atmoswing-forecasts-v2.1/2022/10/01/*.nc")


def test_export_bdapbp_runs(options, forecast_files, metadata):
    export = asv.ExportBdApBp(options)
    export.feed(forecast_files, metadata)
    export.run()
    assert count_files_recursively(options) == 3

    created_files = [
        '2022-10-01_00.PC-AZ4o.Alpes_bernoises_est.json',
        '2022-10-01_00.PC-AZ4o.Chablais.json',
        '2022-10-01_00.PC-AZ4o.Cretes_sud.json'
    ]
    for created_file in created_files:
        file_path = options['output_dir'] + '/2022/10/01/' + created_file
        with open(file_path) as f:
            data = json.load(f)
            assert data['status'] == 0
    shutil.rmtree(options['output_dir'])


def test_export_bdapbp_with_no_limit(options, forecast_files, metadata):
    forecast_files.sort()
    forecast_files = [forecast_files[0]]
    options['number_analogs'] = -1
    export = asv.ExportBdApBp(options)
    export.feed(forecast_files, metadata)
    export.run()
    assert count_files_recursively(options) == 1

    created_files = [
        '2022-10-01_00.PC-AZ4o.Alpes_bernoises_est.json'
    ]
    for created_file in created_files:
        file_path = options['output_dir'] + '/2022/10/01/' + created_file
        with open(file_path) as f:
            data = json.load(f)
            assert data['status'] == 0
    shutil.rmtree(options['output_dir'])


def test_export_bdapbp_with_all_stations(options, forecast_files, metadata):
    forecast_files.sort()
    forecast_files = [forecast_files[0]]
    options['only_relevant_stations'] = False
    export = asv.ExportBdApBp(options)
    export.feed(forecast_files, metadata)
    export.run()
    assert count_files_recursively(options) == 1

    created_files = [
        '2022-10-01_00.PC-AZ4o.Alpes_bernoises_est.json'
    ]
    for created_file in created_files:
        file_path = options['output_dir'] + '/2022/10/01/' + created_file
        with open(file_path) as f:
            data = json.load(f)
            assert data['status'] == 0
    shutil.rmtree(options['output_dir'])
