import atmoswing_vigicrues as asv
import pysftp

from .dissemination import Dissemination


class TransferSftp(Dissemination):
    """
    Transfer des résultats par SFTP.
    """

    def __init__(self, hostname, username, password, remote_dir):
        """
        Initialisation de l'instance TransferSftp

        Parameters
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
        self._hostname = hostname
        self._username = username
        self._password = password
        self._remote_dir = remote_dir
        super().__init__()

    def run(self):
        """ Exécution de la diffusion par SFTP. """
        with pysftp.Connection(self._hostname, username=self._username,
                               password=self._password) as sftp:
            with sftp.cd(self._remote_dir):
                for file in self._file_paths:
                    asv.check_file_exists(file)
                    sftp.put(file)
