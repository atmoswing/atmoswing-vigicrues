import sys
import argparse
import yaml
from atmoswing_vigicrues import atmoswing_vigicrues
from pathlib import Path


def check_arguments(args):

    if not args.output_dir:
        print(f'The output directory was not provided.')
        sys.exit(1)


def check_paths_exist(args):
    batch_file = Path(args.batch_file)
    if not batch_file.exists():
        print(f'The file "{batch_file}" was not found.')
        sys.exit(1)
    if not batch_file.is_file():
        print(f'The provided path "{batch_file}" is not a file.')
        sys.exit(1)

    path_output = Path(args.output_dir)
    if not path_output.exists():
        path_output.mkdir(parents=True, exist_ok=True)


def load_config():
    with open('config.yaml') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    return config


def main() -> int:
    parser = argparse.ArgumentParser(description='Handles AtmoSwing forecasts and '
                                                 'exports for the Vigicrues network.')
    parser.add_argument('batch_file', type=str,
                        help='path to the batch file listing the methods.')
    parser.add_argument('--output-dir', type=str, required=True, metavar='DIR',
                        help='output directory to save the results.')

    args = parser.parse_args()

    check_arguments(args)
    check_paths_exist(args)

    config = load_config()

    return atmoswing_vigicrues.run(Path(args.batch_file), config, args)


if __name__ == "__main__":
    main()
