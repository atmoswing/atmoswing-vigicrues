import yaml

import atmoswing_vigicrues as asv


class Options:
    """
    Classe permettant de gérer les options passées en lignes de commande et définies
    dans le fichier config.

    ----------
    cli_options : object
        Options de la prévision généralement passées sous la forme d'arguments lors de
        l'utilisation en lignes de commandes.
    config : dict
        Configuration chargée du fichier défini par l'argument config_file.
    """

    def __init__(self, cli_options):
        """
        Initialisation de l'instance Options

        Parameters
        ----------
        cli_options : object
            Options passées en lignes de commandes à la fonction main()
        """
        self.cli_options = cli_options
        self.config = None
        self._check_options()
        self._load_config()
        self._override_options()

    @property
    def cli_options(self):
        return self._cli_options

    @cli_options.setter
    def cli_options(self, cli_options):
        self._cli_options = cli_options

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config):
        self._config = config

    def has(self, key) -> bool:
        """
        Contrôle si une option existe.

        Parameters
        ----------
        key
            Le nom de l'option.

        Returns
        -------
            Vrai (True) si l'option existe, faux (False) sinon.
        """
        if key in self.config and self.config[key]:
            return True
        return False

    def get(self, key):
        """
        Extraction d'une option avec contrôle de son existence.

        Parameters
        ----------
        key
            Le nom de l'option.

        Returns
        -------
            La valeur de l'option.
        """
        if self.has(key):
            return self.config[key]
        raise asv.OptionError(key)

    def _check_options(self):
        if self.cli_options is None:
            raise asv.OptionError("Les options fournies sont vides.")
        if not hasattr(self.cli_options, 'config_file') or \
                self.cli_options.config_file is None:
            raise asv.OptionError(
                "Le chemin du fichier de configuration n'a pas été fourni.")

    def _load_config(self):
        asv.check_file_exists(self.cli_options.config_file)
        with open(self.cli_options.config_file, mode='rb') as f:
            self.config = yaml.load(f, Loader=yaml.FullLoader)

    def _override_options(self):
        if hasattr(self.cli_options, 'batch_file'):
            self.config['atmoswing']['with']['batch_file'] = self.cli_options.batch_file
