import os
import ftplib
import socks
import socket

import atmoswing_vigicrues as asv

from .dissemination import Dissemination


class TransferFtpOut(Dissemination):
    """
    Transfer des résultats par FTP.

    Parameters
    ----------
    name: str
        Le nom de l'action
    options: dict
        Un dictionnaire contenant les options de l'action. Les champs possibles sont:

        * local_dir : str
            Répertoire local contenant les fichiers à exporter.
        * extension : str
            Extension des fichiers à exporter.
        * hostname : str
            Adresse du serveur pour la diffusion des résultats.
        * port : int
            Port du serveur distant.
        * username : str
            Utilisateur ayant un accès au serveur.
        * password : str
            Mot de passe de l'utilisateur sur le serveur.
        * proxy_host : str
            Adresse du proxy, si nécessaire.
        * proxy_port : int
            Port du proxy si nécessaire (par défaut: 1080).
        * remote_dir : str
            Chemin sur le serveur distant où enregistrer les fichiers.

    Attributes
    ----------
    type_name : str
        Le nom du type de l'action.
    name : str
        Le nom de l'action.
    local_dir : str
        Répertoire local contenant les fichiers à exporter.
    extension : str
        Extension des fichiers à exporter.
    hostname : str
        Adresse du serveur pour la diffusion des résultats.
    port : int
        Port du serveur distant.
    username : str
        Utilisateur ayant un accès au serveur.
    password : str
        Mot de passe de l'utilisateur sur le serveur.
    proxy_host : str
        Adresse du proxy, si nécessaire.
    proxy_port : int
        Port du proxy si nécessaire (par défaut: 1080).
    remote_dir : str
        Chemin sur le serveur distant où enregistrer les fichiers.
    """

    def __init__(self, name, options):
        """
        Initialisation de l'instance TransferFtp
        """
        self.type_name = "Transfert FTP"
        self.name = name
        self.local_dir = options['local_dir']
        self.extension = options['extension']
        self.hostname = options['hostname']
        self.port = int(options['port'])
        self.username = options['username']
        self.password = options['password']
        self.remote_dir = options['remote_dir']

        if 'proxy_host' in options and len(options['proxy_host']) > 0:
            self.proxy_host = options['proxy_host']
            self.proxy_type = socks.HTTP
            if 'proxy_port' in options:
                if isinstance(options['proxy_port'], str) and len(
                        options['proxy_port']) > 0:
                    self.proxy_port = int(options['proxy_port'])
                elif isinstance(options['proxy_port'], int):
                    self.proxy_port = options['proxy_port']
                else:
                    raise asv.Error("Le port du proxy doit être une chaîne de "
                                    "caractères ou un entier.")
            else:
                self.proxy_port = 1080
        else:
            self.proxy_host = None

        super().__init__()

    def run(self, date) -> bool:
        """
        Exécution de la diffusion par FTP.

        Parameters
        ----------
        date : datetime.datetime
            Date de la prévision.

        Returns
        -------
        bool
            Vrai (True) en cas de succès, faux (False) autrement.
        """
        if not self._file_paths:
            print("  -> Aucun fichier à traiter")
            return False

        try:
            if self.proxy_host:
                socks.set_default_proxy(self.proxy_type, self.proxy_host, self.proxy_port)
                socket.socket = socks.socksocket  # Override the default socket

            # Connect to FTP
            ftp = ftplib.FTP()
            ftp.connect(self.hostname, self.port)
            ftp.login(self.username, self.password)

            self._chdir_or_mkdir(self.remote_dir, ftp)
            self._chdir_or_mkdir(date.strftime('%Y'), ftp)
            self._chdir_or_mkdir(date.strftime('%m'), ftp)
            self._chdir_or_mkdir(date.strftime('%d'), ftp)
            print("Directories created/changed successfully")

            for file in self._file_paths:
                filename = os.path.basename(file)
                asv.check_file_exists(file)
                with open(file, 'rb') as f:
                    ftp.storbinary(f'STOR {filename}', f)
                    print(f"File {filename} uploaded successfully")

            ftp.quit()

            return True

        except Exception as e:
            print(f"La diffusion FTP a échoué ({e}).")

        if 'ftp' in locals():
            ftp.quit()

        return False

    @staticmethod
    def _chdir_or_mkdir(dir_path, ftp):
        current_remote_dir = ftp.pwd()

        # If the path does not end with a slash, add one
        if not current_remote_dir.endswith('/'):
            current_remote_dir += '/'

        current_remote_dir += dir_path

        try:
            ftp.cwd(current_remote_dir)
        except Exception:
            ftp.mkd(dir_path)
            ftp.cwd(current_remote_dir)
