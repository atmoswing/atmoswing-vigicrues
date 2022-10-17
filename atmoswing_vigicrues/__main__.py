import argparse
from atmoswing_vigicrues import AtmoSwingVigicrues


def main() -> int:
    parser = argparse.ArgumentParser(description='Handles AtmoSwing forecasts and '
                                                 'exports for the Vigicrues network.')
    parser.add_argument('batch_file', type=str,
                        help='path to the batch file listing the methods.')
    parser.add_argument('--output-dir', type=str, required=True, metavar='DIR',
                        help='output directory to save the results.')

    args = parser.parse_args()

    atmoswing = AtmoSwingVigicrues(args)

    return atmoswing.run()


if __name__ == "__main__":
    main()
