import glob
import os
import shutil
import tempfile
import types

import netCDF4
import pytest

import atmoswing_vigicrues as asv

DIR_PATH = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def options():
    with tempfile.TemporaryDirectory() as tmp_dir:
        options_full = asv.Options(
            types.SimpleNamespace(
                config_file=DIR_PATH + '/files/config_export_prv.yaml'
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


@pytest.fixture
def forecast_files():
    return glob.glob(DIR_PATH + "/files/atmoswing-forecasts-v2.1/2022/10/01/*.nc")


def test_export_prv_runs(options, forecast_files, metadata):
    export = asv.ExportPrv('Export PRV', options)
    export.feed(forecast_files, metadata)
    export.run()
    assert count_files_recursively(options) == 3
    shutil.rmtree(options['output_dir'])


def test_export_prv_runs_separate_files(options, forecast_files, metadata):
    options['combine_stations_in_one_file'] = False
    export = asv.ExportPrv('Export PRV', options)
    export.feed(forecast_files, metadata)
    export.run()
    assert count_files_recursively(options) == 21
    shutil.rmtree(options['output_dir'])


def test_export_prv_runs_multi_time_steps(options):
    files = glob.glob(DIR_PATH + "/files/atmoswing-forecasts-v2.1/2022/12/16/*.nc")
    metadata = {
        "forecast_date": "2022-12-16 00:00:00",
    }
    export = asv.ExportPrv('Export PRV', options)
    export.feed(files, metadata)
    export.run()
    assert count_files_recursively(options) == 4
    shutil.rmtree(options['output_dir'])


@pytest.mark.parametrize('combine', [True, False])
def test_export_prv_closes_netcdf_files(options, forecast_files, metadata,
                                        monkeypatch, combine):
    options['combine_stations_in_one_file'] = combine
    opened = []

    # Fonction plutôt que sous-classe de netCDF4.Dataset : sous Python 3.14, la
    # destruction d'une sous-classe locale provoque une erreur de segmentation.
    def tracked_dataset(*args, **kwargs):
        nc_file = netCDF4.Dataset(*args, **kwargs)
        opened.append(nc_file)
        return nc_file

    monkeypatch.setattr(asv, 'Dataset', tracked_dataset)

    # Le second passage ignore les fichiers déjà exportés
    for _ in range(2):
        export = asv.ExportPrv('Export PRV', options)
        export.feed(forecast_files, metadata)
        export.run()

    assert len(opened) == 2 * len(forecast_files)
    assert not any(nc_file.isopen() for nc_file in opened)
    shutil.rmtree(options['output_dir'])
