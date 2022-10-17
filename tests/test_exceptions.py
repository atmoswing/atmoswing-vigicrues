import pytest

import atmoswing_vigicrues as asv


def test_exception_general():
    with pytest.raises(asv.Error):
        raise asv.Error()


def test_exception_option():
    with pytest.raises(asv.OptionError):
        raise asv.OptionError('some_key')


def test_exception_config():
    with pytest.raises(asv.ConfigError):
        raise asv.ConfigError('some_key')


def test_exception_path():
    with pytest.raises(asv.PathError):
        raise asv.PathError('path/to/dir')


def test_exception_file_path():
    with pytest.raises(asv.FilePathError):
        raise asv.FilePathError('path/to/file')
