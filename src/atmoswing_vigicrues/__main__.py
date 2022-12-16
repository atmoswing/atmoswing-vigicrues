import argparse
from crontab import CronTab

from atmoswing_vigicrues.controller import Controller


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Traite les prévisions et les exportations d'AtmoSwing pour "
                    "le réseau Vigicrues.")
    parser.add_argument(
        '--config-file', type=str, required=False,
        help="Fichier de configuration du présent module.")
    parser.add_argument(
        '--use-scheduler', action='store_true',
        help="Effectue une prévision automatiquement à pas de "
             "temps réguliers (uniquement pour Linux).")

    args = parser.parse_args()

    if args.use_scheduler:
        print("Création de la tâche automatique.")
        cron = CronTab()
        job = cron.new(
            command=f"python3 -m atmoswing_vigicrues "
                    f"--config-file=\"{args.config_file}\"")
        job.minute.every(5)
        cron.write('tasks.tab')
    else:
        controller = Controller(args)
        return controller.run()


if __name__ == "__main__":
    main()
