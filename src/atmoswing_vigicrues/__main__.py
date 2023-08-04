import argparse
from datetime import datetime

from atmoswing_vigicrues.controller import Controller


def main(args=None) -> int:
    parser = argparse.ArgumentParser(
        description="Traite les prévisions et les exportations d'AtmoSwing pour "
                    "le réseau Vigicrues.")
    parser.add_argument(
        '-c', '--config-file', type=str, required=False,
        help="Fichier de configuration du présent module.")
    parser.add_argument(
        '-d', '--date', type=str, required=False,
        help="Date pour laquelle émettre une prévision (YYYYMMDDHH).")
    parser.add_argument(
        '-i', '--time-increment', type=int, required=False,
        help="Incrément en heures pour l'émission de la prévision (par défaut 6h).")

    args = parser.parse_args(args)

    controller = Controller(args)

    if args.date:
        date = datetime.strptime(args.date, '%Y%m%d%H')
        return controller.run(date)

    return controller.run()


if __name__ == "__main__":
    main()
