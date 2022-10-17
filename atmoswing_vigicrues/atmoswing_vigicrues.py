import yaml
import sys
from pathlib import Path


class AtmoSwingVigicrues:
    """Class to manage AtmoSwing forecasts for the Vigicrues network."""

    def __int__(self, options):
        self.options = options
        self.config = None
        self._load_config()
        self._check_options()
        self._check_paths_exist()

    def run(self, file_path, options) -> int:

        print('Calculation finished.')

        return 0

    def _load_config(self):
        with open('config.yaml') as f:
            self.config = yaml.load(f, Loader=yaml.FullLoader)

    def _check_options(self):
        if not self.options.output_dir:
            print(f'The output directory was not provided.')
            sys.exit(1)

    def _check_paths_exist(self):
        batch_file = Path(self.options.batch_file)
        if not batch_file.exists():
            print(f'The file "{batch_file}" was not found.')
            sys.exit(1)
        if not batch_file.is_file():
            print(f'The provided path "{batch_file}" is not a file.')
            sys.exit(1)

        path_output = Path(self.options.output_dir)
        if not path_output.exists():
            path_output.mkdir(parents=True, exist_ok=True)
