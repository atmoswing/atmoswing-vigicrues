import pytest
from atmoswing_vigicrues.exceptions import *


def test_exception_general():
    with pytest.raises(Error):
        raise Error()


def test_exception_option():
    with pytest.raises(OptionError):
        raise OptionError('some_key')


def test_exception_config():
    with pytest.raises(ConfigError):
        raise ConfigError('some_key')


def test_exception_path():
    with pytest.raises(PathError):
        raise PathError('path/to/dir')


def test_exception_file_path():
    with pytest.raises(FilePathError):
        raise FilePathError('path/to/file')
