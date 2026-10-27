import datetime
import glob
import logging
import subprocess
import tempfile
from pathlib import Path

import atmoswing_vigicrues as asv

logger = logging.getLogger(__name__)


class Controller:
    """
    Classe principale pour la gestion des prévisions AtmoSwing pour le réseau Vigicrues.

    Parameters
    ----------
    cli_options : retour de la fonction parse_args() de la classe
                  argparse.ArgumentParser
        Options passées en lignes de commandes à la fonction main()

    Attributes
    ----------
    options : instance de la classe Options
        Options de la prévision combinant les arguments passés lors de l'utilisation en
        lignes de commandes et les options du fichier de configuration.
    time_increment : int
        Incrément de temps en heures pour l'émission de la prévision
        (par défaut 6 heures).
    date : datetime.datetime
        Date de la prévision.
    pre_actions : list
        Liste des actions préalables à la prévision.
    post_actions : list
        Liste des actions postérieures à la prévision.
    disseminations : list
        Liste des actions de dissémination.
    """

    def __init__(self, cli_options):
        """
        Initialisation de l'instance Controller
        """
        self.options = asv.Options(cli_options)
        self.time_increment = 6
        if hasattr(cli_options, 'time_increment') and \
                cli_options.time_increment is not None:
            self.time_increment = cli_options.time_increment
        self.date = datetime.datetime.now(datetime.timezone.utc)
        self.pre_actions = self._register_actions(
            'pre_actions', asv.PreAction, "la pré-action")
        self.post_actions = self._register_actions(
            'post_actions', asv.PostAction, "la post-action")
        self.disseminations = self._register_actions(
            'disseminations', asv.Dissemination, "la dissémination")

    def run(self, date=None) -> int:
        """
        Exécution du flux de la prévision et du postprocessing.

        Parameters
        ----------
        date : datetime.datetime
            La date de la prévision (par défaut, la date actuelle est utilisée).

        Returns
        -------
        int
            Le code de retour :

            * 0 : succès.
            * 1 : la prévision a été émise, mais au moins une post-action ou une
              dissémination a échoué.
            * -1 : échec de la prévision (pré-actions, AtmoSwing ou exception).
        """

        if date:
            self.date = date

        self._fix_date()

        try:
            self._run_pre_actions()
            self._run_atmoswing()
            post_actions_ok = self._run_post_actions()
            disseminations_ok = self._run_disseminations()
        except asv.Error as e:
            logger.error(f"La prévision a échoué. Erreur: {e}")
            return -1
        except Exception:
            # Erreur inattendue : la trace complète est journalisée
            logger.exception("La prévision a échoué (erreur inattendue).")
            return -1

        if not post_actions_ok or not disseminations_ok:
            logger.warning("La prévision a été émise, mais certaines actions ont "
                           "échoué.")
            return 1

        return 0

    def _register_actions(self, key, base_class, label):
        """
        Instancie les actions actives d'une section du fichier de configuration.

        Parameters
        ----------
        key : str
            La section du fichier de configuration ('pre_actions', 'post_actions'
            ou 'disseminations').
        base_class : type
            La classe de base dont les actions de cette section doivent hériter.
        label : str
            Le libellé du type d'action, pour les messages.

        Returns
        -------
        list
            Les actions instanciées.

        Raises
        ------
        asv.ConfigError
            Si une action est inconnue, n'est pas du bon type, ou si une option
            requise n'est pas définie.
        """
        actions = []
        if not self.options.has(key):
            return actions

        for action in self.options.get(key):
            if not action.get('active', True):
                continue
            uses = action.get('uses')
            name = action.get('name') or uses
            logger.info(f"Chargement de {label} '{name}'")

            cls = getattr(asv, str(uses), None)
            if not isinstance(cls, type) or not issubclass(cls, base_class) or \
                    cls is base_class:
                raise asv.ConfigError(
                    key, f"L'action '{uses}' est inconnue en tant que {label} "
                         f"('{name}').")

            try:
                actions.append(cls(name, action.get('with') or {}))
            except KeyError as e:
                raise asv.ConfigError(
                    e.args[0], f"L'option {e} n'est pas définie pour {label} "
                               f"'{name}'.") from e

        return actions

    def _run_pre_actions(self):
        """
        Exécute les opérations préalables à la prévision par AtmoSwing.

        En cas d'échec d'une pré-action, la date de la prévision est reculée de
        'attempts_step_hours' et l'ensemble des pré-actions est relancé, jusqu'à
        un recul maximal de 'attempts_max_hours'.

        Raises
        ------
        asv.Error
            Si les pré-actions échouent pour toutes les dates tentées.
        """
        if not self.pre_actions:
            return

        attempts_max_hours = 7 * 24
        attempts_step_hours = 6
        for action in self.pre_actions:
            attempts_max_hours = min(attempts_max_hours, action.attempts_max_hours)
            attempts_step_hours = max(attempts_step_hours, action.attempts_step_hours)

        attempts_hours = 0
        while True:
            success = True
            for action in self.pre_actions:
                logger.info(f"Exécution de : '{action.type_name}' [{action.name}]")
                if not action.run(self.date):
                    success = False
                    break
            if success:
                logger.info("  -> Exécution correcte.")
                return

            attempts_hours += attempts_step_hours
            if attempts_hours >= attempts_max_hours:
                break
            logger.warning("  -> Recul de l'heure de la prévision.")
            self._back_in_time(attempts_step_hours)

        logger.error("  -> Échec de l'exécution.")
        raise asv.Error("Nombre maximum de tentatives atteint pour les pré-actions.")

    def _run_atmoswing(self):
        """
        Exécution d'AtmoSwing.
        """
        run = self.options.get('atmoswing')
        if 'active' in run and run['active'] is False:
            logger.info("  -> Prévision par AtmoSwing Forecaster désactivée.")
            return True

        name = run['name']
        options = run['with']
        cmd = self._build_atmoswing_cmd(options)
        logger.info(f"Exécution de : '{name}'")
        logger.info(f"Prévision pour la date : {self.date.strftime('%Y-%m-%d %H')}")
        logger.info("Commande: " + ' '.join(cmd))

        try:
            ret = subprocess.run(cmd, capture_output=True)
        except Exception as e:
            logger.error("  -> Échec de l'exécution.")
            self._parse_log_file()
            raise asv.Error(f"Exception de AtmoSwing Forecaster: {e}") from e

        if ret.returncode != 0:
            logger.error("  -> Échec de l'exécution.")
            self._parse_log_file()
            raise asv.Error(f"Erreur de AtmoSwing Forecaster (code de retour "
                            f"{ret.returncode}).")

        logger.info("  -> Exécution correcte.")

    def _build_atmoswing_cmd(self, options):
        now_str = self.date.strftime("%Y%m%d%H")
        cmd = []

        if 'atmoswing_path' not in options or not options['atmoswing_path']:
            cmd.append("atmoswing-forecaster")
        else:
            cmd.append(options['atmoswing_path'])

        if 'batch_file' not in options or not options['batch_file']:
            raise asv.Error("Option 'batch_file' non fournie.")
        cmd.append("-f")
        cmd.append(options['batch_file'])

        if 'target' in options:
            if options['target'] == 'now':
                cmd.append(f"--forecast-date={now_str}")
            elif options['target'] == 'past':
                if 'target_nb_days' not in options or not options['target_nb_days']:
                    raise asv.Error("Option 'target_nb_days' non fournie.")
                nb_days = options['target_nb_days']
                cmd.append(f"--forecast-past={nb_days}")
            elif options['target'] == 'date':
                if 'target_date' not in options or not options['target_date']:
                    raise asv.Error("Option 'target_date' non fournie.")
                date = options['target_date']
                cmd.append(f"--forecast-date={date}")
        else:
            cmd.append(f"--forecast-date={now_str}")

        if 'proxy' in options and options['proxy']:
            cmd.append(f"--proxy={options['proxy']}")
            if 'proxy_user' in options and options['proxy_user']:
                cmd.append(f"--proxy-user={options['proxy_user']}")

        return cmd

    def _run_post_actions(self) -> bool:
        """
        Exécute les opérations postérieures à la prévision par AtmoSwing.

        Returns
        -------
        bool
            Vrai (True) si toutes les post-actions ont réussi, faux (False) autrement.
        """
        if not self.post_actions:
            return True

        files = self._list_atmoswing_output_files()
        if len(files) == 0:
            logger.info("  -> Aucun nouveau fichier à traiter en post-action.")
            return True

        all_ok = True
        for action in self.post_actions:
            logger.info(f"Exécution de : '{action.type_name}' [{action.name}]")
            action.feed(files, {'forecast_date': self.date})
            if action.run():
                logger.info("  -> Exécution correcte.")
            else:
                logger.error("  -> Échec de l'exécution.")
                all_ok = False

        return all_ok

    def _run_disseminations(self) -> bool:
        """
        Exécute les opérations de diffusion.

        Returns
        -------
        bool
            Vrai (True) si toutes les disséminations ont réussi, faux (False)
            autrement.
        """
        if not self.disseminations:
            return True

        all_ok = True
        for action in self.disseminations:
            logger.info(f"Exécution de : '{action.type_name}' [{action.name}]")
            local_dir = action.local_dir
            extension = action.extension
            files = self._list_files(local_dir, extension)
            action.feed(files)
            if action.run(self.date):
                logger.info("  -> Exécution correcte.")
            else:
                logger.error("  -> Échec de l'exécution.")
                all_ok = False

        return all_ok

    def _fix_date(self):
        date = self.date
        if isinstance(date, str):
            date = datetime.datetime.strptime(date, "%Y-%m-%d %H")
        hour = date.hour
        hour = self.time_increment * (hour // self.time_increment)
        self.date = datetime.datetime(date.year, date.month, date.day, hour)

    def _back_in_time(self, time_increment):
        self.date = self.date - datetime.timedelta(hours=time_increment)

    def _list_atmoswing_output_files(self):
        output_dir = self.options.get('atmoswing')['with']['output_dir']
        return self._list_files(output_dir, '.nc', '%Y-%m-%d_%H')

    def _list_files(self, local_dir, ext, pattern='%Y-%m-%d_%H'):
        local_dir = asv.utils.build_date_dir_structure(local_dir, self.date)
        pattern = f"{str(local_dir)}/{self.date.strftime(pattern)}{f'.*{ext}'}"
        files = glob.glob(pattern)
        return files

    @staticmethod
    def _parse_log_file():
        tmp_dir = Path(tempfile.gettempdir())
        log_file = tmp_dir / "AtmoSwingForecaster.log"
        if not log_file.exists():
            logger.warning(f"  -> Le journal des logs n'a pas été trouvé "
                           f"({str(log_file)}).")
            return
        with open(str(log_file), errors='replace') as file:
            lines = [f"     | {item.rstrip()}" for item in file]
        logger.error("Journal d'AtmoSwing Forecaster :\n" + "\n".join(lines))
