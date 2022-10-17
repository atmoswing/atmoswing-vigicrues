from pathlib import Path

import yaml

import atmoswing_vigicrues as asv


class Controller:
    """
    Classe principale pour la gestion des prévisions AtmoSwing pour le réseau Vigicrues.

    Attributes
    ----------
    options : object
        Options de la prévision généralement passées sous la forme d'arguments lors de
        l'utilisation en lignes de commandes.
    config : dict
        Configuration chargée du fichier défini par l'argument config_file.
    """

    def __init__(self, options):
        """
        Initialisation de l'instance Controller

        Parameters
        ----------
        options : object
            Options passées en lignes de commandes à la fonction main()
        """
        self.options = options
        self.config = None
        self._check_options()
        self._load_config()
        self._merge_config_options()
        self._check_paths_exist()

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, options):
        self._options = options

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config):
        self._config = config

    def run(self) -> int:
        """
        Exécution du flux de la prévision et du postprocessing.

        Returns
        -------
        int
            Le code de retour (0 en cas de succès)
        """
        return -1

    def _check_options(self):
        """ Contrôle que certaines options de base sont définies. """
        if self.options is None:
            raise asv.OptionError("Les options fournies sont vides.")
        if self.options.config_file is None:
            raise asv.OptionError(
                "Le chemin du fichier de configuration n'a pas été fourni.")

    def _load_config(self):
        """ Chargement du fichier de configuration. """
        asv.check_file_exists(self.options.config_file)
        with open(self.options.config_file) as f:
            self.config = yaml.load(f, Loader=yaml.FullLoader)

    def _merge_config_options(self):
        """
        Assemble les options définies en lignes de commandes et celles du
        fichier de configuration. La ligne de commande prévaut.
        """
        self.options.output_dir = self._find_option('output_dir')
        self.options.batch_file = self._find_option('batch_file')

    def _find_option(self, key):
        """ Cherche une valeur dans les arguments passés ou le fichier config. """
        if hasattr(self.options, key) and getattr(self.options, key):
            return getattr(self.options, key)
        if key in self.config and self.config[key]:
            return self.config[key]
        raise asv.OptionError(key)

    def _check_paths_exist(self):
        """ Contrôle que les chemins nécessaires existent. """
        asv.check_file_exists(self.options.batch_file)

        path_output = Path(self.options.output_dir)
        if not path_output.exists():
            path_output.mkdir(parents=True, exist_ok=True)
