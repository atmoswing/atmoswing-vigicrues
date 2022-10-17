from pathlib import Path


class Error(Exception):
    """
    Erreur générale
    """

    def __init__(self, message="Une erreur est survenue."):
        self.message = message
        super().__init__(self.message)


class OptionError(Error):
    """
    Erreur dans les options passées en lignes de commandes
    """

    def __init__(self, key, message=None):
        if not message:
            message = f"L'option '{key}' n'est pas définie."
        super().__init__(message)


class ConfigError(Error):
    """
    Erreur dans le fichier de configuration
    """

    def __init__(self, key, message=None):
        if not message:
            message = f"L'option '{key}' du fichier de configuration n'est pas définie."
        super().__init__(message)


class PathError(Error):
    """
    Erreur dans un chemin
    """

    def __init__(self, path, message=None):
        if not message:
            message = f"Erreur dans le chemin '{path}'."
        super().__init__(message)


class FilePathError(Error):
    """
    Erreur dans un chemin d'un fichier
    """

    def __init__(self, path, message=None):
        if type(path) == Path:
            path = str(path)
        if not message:
            message = f"Le fichier '{path}' n'a pas été trouvé."
        super().__init__(message)
