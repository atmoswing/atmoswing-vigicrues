import os
import types

import pytest

import atmoswing_vigicrues as asv

DIR_PATH = os.path.dirname(os.path.abspath(__file__))


def test_config_fail_without_file():
    cli_options = types.SimpleNamespace(some_var='42')
    with pytest.raises(asv.OptionError):
        asv.Options(cli_options)


def test_load_config_file():
    cli_options = types.SimpleNamespace(config_file=DIR_PATH + '/files/config.yaml')
    asv.Options(cli_options)


def test_options_has_key():
    cli_options = types.SimpleNamespace(config_file=DIR_PATH + '/files/config.yaml')
    options = asv.Options(cli_options)
    assert options.has('pre_actions')
    assert options.has('post_actions')
    assert options.has('disseminations')
    assert not options.has('42')


def test_retrieve_option_with_key():
    cli_options = types.SimpleNamespace(config_file=DIR_PATH + '/files/config.yaml')
    options = asv.Options(cli_options)
    assert isinstance(options.get('pre_actions'), list)
    assert isinstance(options.get('post_actions'), list)
    assert isinstance(options.get('disseminations'), list)
    with pytest.raises(asv.OptionError):
        options.get('42')
