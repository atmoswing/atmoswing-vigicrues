import os

import paramiko

import atmoswing_vigicrues as asv

from .dissemination import Dissemination


class TransferSftp(Dissemination):
    """
    Transfer des résultats par SFTP.

    Parameters
    ----------
    options: objet
        L'instance contenant les options de l'action. Les champs possibles sont:

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
        * remote_dir : str
            Chemin sur le serveur distant où enregistrer les fichiers.
    """

    def __init__(self, options):
        """
        Initialisation de l'instance TransferSftp
        """
        self.name = "Transfert SFTP"
        self.local_dir = options['local_dir']
        self.extension = options['extension']
        self.hostname = options['hostname']
        self.port = options['port']
        self.username = options['username']
        self.password = options['password']
        self.remote_dir = options['remote_dir']

        super().__init__()

    def run(self, date):
        """
        Exécution de la diffusion par SFTP.

        Parameters
        ----------
        date : datetime
            Date de la prévision.
        """
        try:
            transport = paramiko.Transport((self.hostname, self.port))
            transport.connect(None, self.username, self.password)
            sftp = paramiko.SFTPClient.from_transport(transport)
            self._chdir_or_mkdir(self.remote_dir, sftp)
            self._chdir_or_mkdir(date.strftime('%Y'), sftp)
            self._chdir_or_mkdir(date.strftime('%m'), sftp)
            self._chdir_or_mkdir(date.strftime('%d'), sftp)

            for file in self._file_paths:
                filename = os.path.basename(file)
                asv.check_file_exists(file)
                sftp.put(file, filename)

            if sftp:
                sftp.close()
            if transport:
                transport.close()

        except paramiko.ssh_exception.PasswordRequiredException as e:
            print(f"SFTP PasswordRequiredException {e}")
        except paramiko.ssh_exception.BadAuthenticationType as e:
            print(f"SFTP BadAuthenticationType {e}")
        except paramiko.ssh_exception.AuthenticationException as e:
            print(f"SFTP AuthenticationException {e}")
        except paramiko.ssh_exception.ChannelException as e:
            print(f"SFTP ChannelException {e}")
        except paramiko.ssh_exception.ProxyCommandFailure as e:
            print(f"SFTP ProxyCommandFailure {e}")
        except paramiko.ssh_exception.SSHException as e:
            print(f"SFTP SSHException {e}")
        except FileNotFoundError as e:
            print(f"SFTP FileNotFoundError {e}")
        except Exception as e:
            print(f"La diffusion SFTP a échoué ({e}).")

    def _chdir_or_mkdir(self, dir, sftp):
        try:
            sftp.chdir(dir)
        except IOError:
            sftp.mkdir(dir)
            sftp.chdir(dir)
