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
        self.pre_actions = []
        self.post_actions = []
        self.disseminations = []
        self._register_pre_actions()
        self._register_post_actions()
        self._register_disseminations()

    def run(self) -> int:
        """
        Exécution du flux de la prévision et du postprocessing.

        Returns
        -------
        int
            Le code de retour (0 en cas de succès)
        """

        try:
            self._run_pre_actions()
            self._run_atmoswing()
            self._run_post_actions()
            self._run_disseminations()
        except asv.Error:
            print("La prévision a échoué.")
            return -1
        except Exception:
            print("La prévision a échoué.")
            return -1

        return 0

    def _register_pre_actions(self):
        """
        Enregistre les actions préalables à la prévision
        """
        if self.options.has('pre_actions'):
            for action in self.options.get('pre_actions'):
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
        for action in self.pre_actions:
            action.run()

    def _run_atmoswing(self):
        """
        Exécution d'AtmoSwing.
        """
        run = self.options.get('atmoswing')
        name = run['name']
        options = run['with']
        full_cmd = self._build_atmoswing_cmd(options)
        print(f"Exécution de '{name}'")

        ret = subprocess.run(full_cmd, capture_output=True)

        if ret.returncode != 0:
            raise asv.Error("L'exécution de la prévision a échoué.")

    @staticmethod
    def _build_atmoswing_cmd(options):
        cmd = '--forecast-now'
        proxy = ''

        if 'target' in options:
            if options['target'] == 'now':
                cmd = '--forecast-now'
            elif options['target'] == 'past':
                if 'target_nb_days' not in options or not options['target_nb_days']:
                    raise asv.Error(f"Option 'target_nb_days' non fournie.")
                nb_days = options['target_nb_days']
                cmd = f'--forecast-past={nb_days}'
            elif options['target'] == 'date':
                if 'target_date' not in options or not options['target_date']:
                    raise asv.Error(f"Option 'target_date' non fournie.")
                date = options['target_date']
                cmd = f'--forecast-date={date}'

        if 'atmoswing_path' not in options or not options['atmoswing_path']:
            raise asv.Error(f"Option 'atmoswing_path' non fournie.")
        atmoswing_path = options['atmoswing_path']

        if 'batch_file' not in options or not options['batch_file']:
            raise asv.Error(f"Option 'batch_file' non fournie.")
        batch_file = options['batch_file']

        if 'proxy' in options and options['proxy']:
            proxy = f"--proxy={options['proxy']} "
            if 'proxy_user' in options and options['proxy_user']:
                proxy += f"--proxy-user={options['proxy_user']}"

        full_cmd = f"{atmoswing_path} -f {batch_file} {cmd} {proxy}"

        return full_cmd

    def _run_post_actions(self):
        """
        Exécute les opérations postérieures à la prévision par AtmoSwing.
        """
        for action in self.post_actions:
            action.feed()
            action.run()

    def _run_disseminations(self):
        """
        Exécute les opérations de diffusion.
        """
        for action in self.disseminations:
            action.feed()
            action.run()

    def _display_message(self, message):
        if self.verbose:
            print(message)
