import os

import paramiko

import atmoswing_vigicrues as asv

from .dissemination import Dissemination


class TransferSftpOut(Dissemination):
    """
    Transfer des résultats par SFTP.

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
        Initialisation de l'instance TransferSftp
        """
        self.type_name = "Transfert SFTP"
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
            if 'proxy_port' in options and len(options['proxy_port']) > 0:
                self.proxy_port = int(options['proxy_port'])
            else:
                self.proxy_port = 1080
        else:
            self.proxy_host = None

        super().__init__()

    def run(self, date) -> bool:
        """
        Exécution de la diffusion par SFTP.

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
            # Create a transport object for the SFTP connection
            transport = paramiko.Transport((self.hostname, self.port))

            if self.proxy_host:
                transport.start_client()
                transport.open_channel('direct-tcpip',
                                       (self.hostname, self.port),
                                       (self.proxy_host, self.proxy_port))

            # Authenticate with the SFTP server
            transport.connect(username=self.username, password=self.password)

            # Create an SFTP client object
            sftp = transport.open_sftp_client()

            self._chdir_or_mkdir(self.remote_dir, sftp)
            self._chdir_or_mkdir(date.strftime('%Y'), sftp)
            self._chdir_or_mkdir(date.strftime('%m'), sftp)
            self._chdir_or_mkdir(date.strftime('%d'), sftp)

            for file in self._file_paths:
                filename = os.path.basename(file)
                asv.check_file_exists(file)
                sftp.put(file, filename)

            # Close the SFTP client and transport objects
            sftp.close()
            transport.close()

        except paramiko.ssh_exception.PasswordRequiredException as e:
            print(f"SFTP PasswordRequiredException {e}")
            return False
        except paramiko.ssh_exception.BadAuthenticationType as e:
            print(f"SFTP BadAuthenticationType {e}")
            return False
        except paramiko.ssh_exception.AuthenticationException as e:
            print(f"SFTP AuthenticationException {e}")
            return False
        except paramiko.ssh_exception.ChannelException as e:
            print(f"SFTP ChannelException {e}")
            return False
        except paramiko.ssh_exception.ProxyCommandFailure as e:
            print(f"SFTP ProxyCommandFailure {e}")
            return False
        except paramiko.ssh_exception.SSHException as e:
            print(f"SFTP SSHException {e}")
            return False
        except FileNotFoundError as e:
            print(f"SFTP FileNotFoundError {e}")
            return False
        except Exception as e:
            print(f"La diffusion SFTP a échoué ({e}).")
            return False

        return True

    @staticmethod
    def _chdir_or_mkdir(dir_path, sftp):
        try:
            sftp.chdir(dir_path)
        except OSError:
            sftp.mkdir(dir_path)
            sftp.chdir(dir_path)
