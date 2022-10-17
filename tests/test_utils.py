import pytest
from atmoswing_vigicrues.exceptions import *
from atmoswing_vigicrues.utils import *
import tempfile


def test_check_file_exists_fails():
    with tempfile.TemporaryDirectory() as tmp_dir:
        with pytest.raises(Error):
            check_file_exists(tmp_dir)


def test_check_file_exists_succeeds():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_file = tmp_dir + '/file.txt'
        Path(tmp_file).touch()
        check_file_exists(tmp_file)
