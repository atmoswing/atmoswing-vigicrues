import argparse
import logging
import sys
from datetime import datetime

import atmoswing_vigicrues as asv
from atmoswing_vigicrues.controller import Controller

logger = logging.getLogger('atmoswing_vigicrues')

LOG_HANDLER_NAME = 'atmoswing_vigicrues'


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

    configure_logging()

    try:
        controller = Controller(args)
    except (asv.Error, ImportError) as e:
        logger.error(f"La configuration est invalide. Erreur: {e}")
        return -1

    return controller.run(date)


def configure_logging():
    """
    Configure l'affichage des messages sur la sortie standard (horodatage et niveau).

    Les messages du module sont affichés à partir du niveau INFO, ceux des
    bibliothèques tierces (ex. paramiko) à partir du niveau WARNING.
    """
    root = logging.getLogger()
    if any(handler.get_name() == LOG_HANDLER_NAME for handler in root.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.set_name(LOG_HANDLER_NAME)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    root.addHandler(handler)
    root.setLevel(logging.WARNING)
    logging.getLogger('atmoswing_vigicrues').setLevel(logging.INFO)


if __name__ == "__main__":
    sys.exit(main())
