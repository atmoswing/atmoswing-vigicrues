import datetime
import glob
import importlib
import subprocess

import atmoswing_vigicrues as asv


class Controller:
    """
    Classe principale pour la gestion des prévisions AtmoSwing pour le réseau Vigicrues.

    Attributes
    ----------
    options : object
        Options de la prévision combinant les arguments passés lors de l'utilisation en
        lignes de commandes et les options du fichier de configuration.
    verbose : bool
        Affichage verbose des messages d'erreurs (pas beaucoup utilisé)
    max_attempts : int
        Nombre de tentatives de téléchargement en adaptant l'heure d'échéance
        (soustrayant 6 h). Valeur par défaut : 8
    time_increment : int
        Pas de temps (h) auquel émettre la prévision (p. ex. toutes les 6h)
    date : datetime
        Date de la prévision.
    """

    def __init__(self, cli_options):
        """
        Initialisation de l'instance Controller

        Parameters
        ----------
        cli_options : object
            Options passées en lignes de commandes à la fonction main()
        """
        self.options = asv.Options(cli_options)
        self.verbose = True
        self.max_attempts = 8
        self.time_increment = 6
        self.date = datetime.datetime.utcnow()
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
        date : datetime
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
                self._display_message(f"Chargement de la pre-action '{name}'")
                if not hasattr(importlib.import_module('atmoswing_vigicrues'), module):
                    raise asv.Error(f"L'action {module} est inconnue.")
                fct = getattr(importlib.import_module('atmoswing_vigicrues'), module)
                self.pre_actions.append(fct(action['with']))

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
                self._display_message(f"Chargement de la post-action '{name}'")
                if not hasattr(importlib.import_module('atmoswing_vigicrues'), module):
                    raise asv.Error(f"L'action {module} est inconnue.")
                fct = getattr(importlib.import_module('atmoswing_vigicrues'), module)
                self.post_actions.append(fct(action['with']))

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
                self._display_message(f"Chargement de la disseminations '{name}'")
                if not hasattr(importlib.import_module('atmoswing_vigicrues'), module):
                    raise asv.Error(f"L'action {module} est inconnue.")
                fct = getattr(importlib.import_module('atmoswing_vigicrues'), module)
                self.disseminations.append(fct(action['with']))

    def _run_pre_actions(self):
        """
        Exécute les opérations préalables à la prévision par AtmoSwing.
        """
        if not self.pre_actions:
            return

        attempts = 0
        while attempts < self.max_attempts:
            success = True
            for action in self.pre_actions:
                self._display_message(f"Exécution de : '{action.name}'")
                if not action.run(self.date):
                    attempts += 1
                    success = False
                    break
            if success:
                break
            else:
                self._back_in_time()

    def _run_atmoswing(self):
        """
        Exécution d'AtmoSwing.
        """
        run = self.options.get('atmoswing')
        name = run['name']
        options = run['with']
        cmd = self._build_atmoswing_cmd(options)
        self._display_message(f"Exécution de : '{name}'")
        print("Commande: " + ' '.join(cmd))

        try:
            ret = subprocess.run(cmd, capture_output=True, check=True)

            if ret.returncode != 0:
                print("L'exécution d'AtmoSwing Forecaster a échoué.")
                raise asv.Error("L'exécution d'AtmoSwing Forecaster a échoué.")
            else:
                print("AtmoSwing Forecaster a été exécuté avec succès.")
        except Exception as e:
            print(f"Exception lors de l'exécution d'AtmoSwing Forecaster: {e}")

    def _build_atmoswing_cmd(self, options):
        now_str = self.date.strftime("%Y%m%d%H")
        cmd = []

        if 'atmoswing_path' not in options or not options['atmoswing_path']:
            cmd.append("atmoswing-forecaster")
        else:
            cmd.append(options['atmoswing_path'])

        if 'batch_file' not in options or not options['batch_file']:
            raise asv.Error(f"Option 'batch_file' non fournie.")
        cmd.append("-f")
        cmd.append(options['batch_file'])

        if 'target' in options:
            if options['target'] == 'now':
                cmd.append(f"--forecast-date={now_str}")
            elif options['target'] == 'past':
                if 'target_nb_days' not in options or not options['target_nb_days']:
                    raise asv.Error(f"Option 'target_nb_days' non fournie.")
                nb_days = options['target_nb_days']
                cmd.append(f"--forecast-past={nb_days}")
            elif options['target'] == 'date':
                if 'target_date' not in options or not options['target_date']:
                    raise asv.Error(f"Option 'target_date' non fournie.")
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
        if not self.post_actions:
            return

        files = self._list_atmoswing_output_files()
        for action in self.post_actions:
            self._display_message(f"Exécution de : '{action.name}'")
            action.feed(files, {'forecast_date': self.date})
            action.run()

    def _run_disseminations(self):
        """
        Exécute les opérations de diffusion.
        """
        if not self.disseminations:
            return

        for action in self.disseminations:
            self._display_message(f"Exécution de : '{action.name}'")
            local_dir = action.local_dir
            extension = action.extension
            files = self._list_files(local_dir, extension)
            action.feed(files)
            action.run(self.date)

    def _display_message(self, message):
        if self.verbose:
            print(message)

    def _fix_date(self):
        date = self.date
        if isinstance(date, str):
            date = datetime.datetime.strptime(date, "%Y-%m-%d %H")
        hour = date.hour
        hour = self.time_increment * (hour // self.time_increment)
        self.date = datetime.datetime(date.year, date.month, date.day, hour)

    def _back_in_time(self):
        self.date = self.date - datetime.timedelta(hours=self.time_increment)

    def _list_atmoswing_output_files(self):
        output_dir = self.options.get('atmoswing')['with']['output_dir']
        return self._list_files(output_dir, '.nc', '%Y-%m-%d_%H')

    def _list_files(self, local_dir, ext, pattern='%Y-%m-%d_%H'):
        local_dir = asv.utils.build_date_dir_structure(local_dir, self.date)
        pattern = f"{str(local_dir)}/{self.date.strftime(pattern)}{f'.*{ext}'}"
        files = glob.glob(pattern)
        return files
