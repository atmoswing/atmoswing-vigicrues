import argparse
import sys
from datetime import datetime

import atmoswing_vigicrues as asv
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

    date = None
    if args.date:
        try:
            date = datetime.strptime(args.date, '%Y%m%d%H')
        except ValueError:
            parser.error(f"La date '{args.date}' ne respecte pas le format "
                         f"YYYYMMDDHH.")

    try:
        controller = Controller(args)
    except (asv.Error, ImportError) as e:
        print("La configuration est invalide.")
        print(f"Erreur: {e}")
        return -1

    return controller.run(date)


if __name__ == "__main__":
    sys.exit(main())
