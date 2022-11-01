import atmoswing_vigicrues as asv
import pysftp

from .dissemination import Dissemination


class TransferSftp(Dissemination):
    """
    Transfer des résultats par SFTP.

    Attributes
    ----------
    hostname : str
        Adresse du serveur pour la diffusion des résultats.
    username: str
        Utilisateur ayant un accès au serveur.
    password: str
        Mot de passe de l'utilisateur sur le serveur.
    remote_dir: str
        Chemin sur le serveur distant où enregistrer les fichiers.
    """

    def __init__(self, options):
        """
        Initialisation de l'instance TransferSftp
        """
        self.hostname = options.get('hostname')
        self.username = options.get('username')
        self.password = options.get('password')
        self.remote_dir = options.get('remote_dir')
        super().__init__()

    def run(self):
        """ Exécution de la diffusion par SFTP. """
        with pysftp.Connection(self.hostname, username=self.username,
                               password=self.password) as sftp:
            with sftp.cd(self.remote_dir):
                for file in self._file_paths:
                    asv.check_file_exists(file)
                    sftp.put(file)
