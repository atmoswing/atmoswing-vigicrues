import os
import glob
import tempfile

import pytest

import atmoswing_vigicrues as asv

DIR_PATH = os.path.dirname(os.path.abspath(__file__))


def test_export_bdapbp_fails_if_files_not_found():
    with tempfile.TemporaryDirectory() as tmp_dir:
        export = asv.ExportBdApBp(tmp_dir, 'export.json')
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


def test_export_bdapbp_is_created_with_no_file(metadata):
    with tempfile.TemporaryDirectory() as tmp_dir:
        export = asv.ExportBdApBp(tmp_dir, 'export.json')
        export.feed([], metadata)
        export.run()


def test_export_bdapbp_is_created_with_no_metadata(forecast_files):
    with tempfile.TemporaryDirectory() as tmp_dir:
        export = asv.ExportBdApBp(tmp_dir, 'export.json')
        export.feed(forecast_files, {})
        export.run()


def test_export_bdapbp_runs(forecast_files, metadata):
    with tempfile.TemporaryDirectory() as tmp_dir:
        export = asv.ExportBdApBp(tmp_dir, 'export.json')
        export.feed(forecast_files, metadata)
        export.run()

