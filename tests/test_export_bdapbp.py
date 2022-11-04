import glob
import os
import tempfile
import types

import pytest

import atmoswing_vigicrues as asv

DIR_PATH = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def options():
    with tempfile.TemporaryDirectory() as tmp_dir:
        options = asv.Options(
            types.SimpleNamespace(
                config_file=DIR_PATH + '/files/config.yaml',
                bdapbp_output_dir=tmp_dir
            ))
    return options


def test_export_bdapbp_fails_if_files_not_found(options):
    export = asv.ExportBdApBp(options)
    export.feed(['/wrong/path'], {})
    with pytest.raises(asv.FilePathError):
        export.run()


@pytest.fixture
def forecast_files():
    return glob.glob(DIR_PATH + "/files/forecasts-v2.1/2022/10/01/*.nc")


@pytest.fixture
def metadata():
    metadata = {
        "status": 0,
        "request": "atmoswing-forecaster -n",
        "date": "2022-10-01 00:00:00",
        "duration": 344,
        "message": "exécution correcte"
    }
    return metadata


def test_export_bdapbp_is_created_with_no_file(options, metadata):
    export = asv.ExportBdApBp(options)
    export.feed([], metadata)
    export.run()


def test_export_bdapbp_is_created_with_no_metadata(options, forecast_files):
    export = asv.ExportBdApBp(options)
    export.feed(forecast_files, {})
    export.run()


def test_export_bdapbp_runs(options, forecast_files, metadata):
    export = asv.ExportBdApBp(options)
    export.feed(forecast_files, metadata)
    export.run()
