import glob
import os
import types
from datetime import datetime

import pytest

import atmoswing_vigicrues as asv

DIR_PATH = os.path.dirname(os.path.abspath(__file__))

# Needs a running docker container
RUN_FTP = False


@pytest.fixture
def options():
    options = asv.Options(
        types.SimpleNamespace(
            config_file=DIR_PATH + '/files/config_dissemination_ftp.yaml'
        ))

    action_options = options.config['disseminations'][0]['with']
    action_options['local_dir'] = DIR_PATH + '/atmoswing-forecasts-v2.1'

    return action_options


@pytest.fixture
def forecast_files():
    return glob.glob(DIR_PATH + "/files/atmoswing-forecasts-v2.1/2022/12/16/*.nc")


def test_upload_nc_succeeds(options, forecast_files):
    action = asv.TransferFtpOut('Upload nc files over FTP', options)
    action.feed(forecast_files)
    date = datetime(2022, 12, 16, 00)
    if RUN_FTP:
        assert action.run(date)
