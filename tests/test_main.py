import os
import atmoswing_vigicrues.__main__ as main_module

DIR_PATH = os.path.dirname(os.path.abspath(__file__))


def test_controller_instance_succeeds_through_main():
    config_file = DIR_PATH + '/files/config_gfs_download.yaml'
    arguments = [f'--config-file={config_file}']
    ret = main_module.main(arguments)
    assert ret == 0
