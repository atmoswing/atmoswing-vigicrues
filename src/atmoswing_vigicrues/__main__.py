import argparse
from datetime import datetime

from atmoswing_vigicrues.controller import Controller


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Traite les prévisions et les exportations d'AtmoSwing pour "
                    "le réseau Vigicrues.")
    parser.add_argument(
        '--config-file', type=str, required=False,
        help="Fichier de configuration du présent module.")
    parser.add_argument(
        '--date', type=str, required=False,
        help="Date pour laquelle émettre une prévision (YYYYMMDDHH).")

    args = parser.parse_args()

    controller = Controller(args)

    if args.date:
        date = datetime.strptime(args.date, '%Y%m%d%H')
        return controller.run(date)

    return controller.run()


if __name__ == "__main__":
    main()
