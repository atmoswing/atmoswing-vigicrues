import datetime
import glob
import importlib
import subprocess
import tempfile
from pathlib import Path

import atmoswing_vigicrues as asv


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
    existing_files : list
        Liste des fichiers de prévision d'AtmoSwing Forecaster déjà existants pour
        l'échéance en cours.
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
        self.date = datetime.datetime.utcnow()
        self.existing_files = []
        self.pre_actions = []
        self.post_actions = []
        self.disseminations = []
        self._register_pre_actions()
        self._register_post_actions()
        self._register_disseminations()

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
            Le code de retour (0 en cas de succès)
        """

        if date:
            self.date = date

        self._fix_date()

        try:
            self._run_pre_actions()
            self.existing_files = self._list_atmoswing_output_files()
            self._run_atmoswing()
            self._run_post_actions()
            self._run_disseminations()
        except asv.Error as e:
            print("La prévision a échoué.")
            print(f"Erreur: {e}")
            return -1
        except Exception as e:
            print("La prévision a échoué.")
            print(f"Erreur: {e}")
            return -1

        return 0

    def _register_pre_actions(self):
        """
        Enregistre les actions préalables à la prévision
        """
        if self.options.has('pre_actions'):
            for action in self.options.get('pre_actions'):
                if 'active' in action and not action['active']:
                    continue
                name = action['name']
                module = action['uses']
                print(f"Chargement de la pre-action '{name}'")
                if not hasattr(importlib.import_module('atmoswing_vigicrues'), module):
                    raise asv.Error(f"L'action {module} est inconnue.")
                fct = getattr(importlib.import_module('atmoswing_vigicrues'), module)
                self.pre_actions.append(fct(name, action['with']))

    def _register_post_actions(self):
        """
        Enregistre les actions postérieures à la prévision
        """
        if self.options.has('post_actions'):
            for action in self.options.get('post_actions'):
                if 'active' in action and not action['active']:
                    continue
                name = action['name']
                module = action['uses']
                print(f"Chargement de la post-action '{name}'")
                if not hasattr(importlib.import_module('atmoswing_vigicrues'), module):
                    raise asv.Error(f"L'action {module} est inconnue.")
                fct = getattr(importlib.import_module('atmoswing_vigicrues'), module)
                self.post_actions.append(fct(name, action['with']))

    def _register_disseminations(self):
        """
        Enregistre les actions préalables à la prévision
        """
        if self.options.has('disseminations'):
            for action in self.options.get('disseminations'):
                if 'active' in action and not action['active']:
                    continue
                name = action['name']
                module = action['uses']
                print(f"Chargement de la disseminations '{name}'")
                if not hasattr(importlib.import_module('atmoswing_vigicrues'), module):
                    raise asv.Error(f"L'action {module} est inconnue.")
                fct = getattr(importlib.import_module('atmoswing_vigicrues'), module)
                self.disseminations.append(fct(name, action['with']))

    def _run_pre_actions(self):
        """
        Exécute les opérations préalables à la prévision par AtmoSwing.
        """
        if not self.pre_actions or len(self.pre_actions) == 0:
            return

        attempts_max_hours = 7 * 24
        attempts_step_hours = 6
        for action in self.pre_actions:
            attempts_max_hours = min(attempts_max_hours, action.attempts_max_hours)
            attempts_step_hours = max(attempts_step_hours, action.attempts_step_hours)

        attempts_hours = 0
        while attempts_hours < attempts_max_hours:
            success = True
            for action in self.pre_actions:
                print(f"Exécution de : '{action.type_name}' [{action.name}]")
                if not action.run(self.date):
                    attempts_hours += attempts_step_hours
                    success = False
                    break
            if success:
                print("  -> Exécution correcte.")
                break
            else:
                print("  -> Recul de l'heure de la prévision.")
                self._back_in_time(attempts_step_hours)
        else:
            print("  -> Échec de l'exécution.")
            print("  -> Nombre maximum de tentatives atteint pour la pré-action.")

    def _run_atmoswing(self):
        """
        Exécution d'AtmoSwing.
        """
        run = self.options.get('atmoswing')
        if 'active' in run and run['active'] is False:
            print("  -> Prévision par AtmoSwing Forecaster désactivée.")
            return True

        name = run['name']
        options = run['with']
        cmd = self._build_atmoswing_cmd(options)
        print(f"Exécution de : '{name}'")
        print(f"Prévision pour la date : {self.date.strftime('%Y-%m-%d %H')}")
        print("Commande: " + ' '.join(cmd))

        try:
            ret = subprocess.run(cmd, capture_output=True)

            if ret.returncode != 0:
                print("  -> Échec de l'exécution.")
                self._parse_log_file()
                raise asv.Error("Erreur de AtmoSwing Forecaster.")
            else:
                print("  -> Exécution correcte.")
        except Exception as e:
            print("  -> Échec de l'exécution.")
            self._parse_log_file()
            raise asv.Error(f"Exception de AtmoSwing Forecaster: {e}")

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

    def _run_post_actions(self):
        """
        Exécute les opérations postérieures à la prévision par AtmoSwing.
        """
        if not self.post_actions or len(self.post_actions) == 0:
            return

        files = self._list_atmoswing_output_files()
        if len(files) == 0:
            print("  -> Aucun nouveau fichier à traiter en post-action.")
            return

        for action in self.post_actions:
            print(f"Exécution de : '{action.type_name}' [{action.name}]")
            action.feed(files, {'forecast_date': self.date})
            if action.run():
                print("  -> Exécution correcte.")
            else:
                print("  -> Échec de l'exécution.")

    def _run_disseminations(self):
        """
        Exécute les opérations de diffusion.
        """
        if not self.disseminations or len(self.disseminations) == 0:
            return

        for action in self.disseminations:
            print(f"Exécution de : '{action.type_name}' [{action.name}]")
            local_dir = action.local_dir
            extension = action.extension
            files = self._list_files(local_dir, extension)
            action.feed(files)
            if action.run(self.date):
                print("  -> Exécution correcte.")
            else:
                print("  -> Échec de l'exécution.")

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

    def _get_files_for_post_actions(self):
        files = self._list_atmoswing_output_files()
        files = [x for x in files if x not in self.existing_files]
        return files

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
            print(f"  -> Le journal des logs n'a pas été trouvé ({str(log_file)}).")
        with open(str(log_file)) as file:
            for item in file:
                content = item.replace("\r\n", "").replace("\n", "")
                print(f"     | {content}")
