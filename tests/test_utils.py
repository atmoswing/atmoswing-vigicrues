import tempfile
from pathlib import Path

import pytest

import atmoswing_vigicrues as asv


def test_check_file_exists_fails():
    with tempfile.TemporaryDirectory() as tmp_dir:
        with pytest.raises(asv.Error):
            asv.check_file_exists(tmp_dir)


def test_check_file_exists_succeeds():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_file = tmp_dir + '/file.txt'
        Path(tmp_file).touch()
        asv.check_file_exists(tmp_file)


def test_build_cumulative_frequency():
    f = asv.utils.build_cumulative_frequency(100)
