import yaml

import atmoswing_vigicrues as asv


class Options:
    """
    Classe permettant de gérer les options passées en lignes de commande et définies
    dans le fichier config.

    ----------
    options : object
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
        self.options = cli_options
        self.config = None
        self._check_options()
        self._load_config()

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
        """ Contrôle que certaines options de base sont définies. """
        if self.options is None:
            raise asv.OptionError("Les options fournies sont vides.")
        if not hasattr(self.options, 'config_file') or self.options.config_file is None:
            raise asv.OptionError(
                "Le chemin du fichier de configuration n'a pas été fourni.")

    def _load_config(self):
        """ Chargement du fichier de configuration. """
        asv.check_file_exists(self.options.config_file)
        with open(self.options.config_file) as f:
            self.config = yaml.load(f, Loader=yaml.FullLoader)

