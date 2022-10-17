import argparse
from atmoswing_vigicrues.controller import Controller


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Traite les prévisions et les exportations d'AtmoSwing pour "
                    "le réseau Vigicrues.")
    parser.add_argument(
        'batch_file', type=str,
        help="chemin vers le fichier batch listant les méthodes d\'analogie.")
    parser.add_argument(
        '--config-file', type=str, required=False,
        help="fichier de configuration du présent module.")
    parser.add_argument(
        '--output-dir', type=str, required=False, metavar='DIR',
        help="répertoire de sortie pour enregistrer les résultats.")

    args = parser.parse_args()

    controller = Controller(args)

    return controller.run()


if __name__ == "__main__":
    main()
