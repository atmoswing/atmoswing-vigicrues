import os
import fnmatch
from pathlib import Path
import tarfile

import paramiko, socks

import atmoswing_vigicrues as asv

from .preaction import PreAction


class TransferSftpIn(PreAction):
    """
    Récupération des prévisions des modèles météo par SFTP.

    Parameters
    ----------
    options: objet
        L'instance contenant les options de l'action. Les champs possibles sont:

        * local_dir : str
            Répertoire cible pour l'enregistrement des fichiers.
        * prefix : str
            Prefix des fichiers à importer.
        * hostname : str
            Adresse du serveur distant.
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
            Chemin sur le serveur distant où se trouvent les fichiers.
    """

    def __init__(self, options):
        """
        Initialisation de l'instance TransferSftp
        """
        self.name = "Transfert SFTP"
        self.local_dir = options['local_dir']
        self.prefix = options['prefix']
        self.hostname = options['hostname']
        self.port = options['port']
        self.username = options['username']
        self.password = options['password']
        self.remote_dir = options['remote_dir']

        if 'proxy_host' in options:
            self.proxy_host = options['proxy_host']
            if 'proxy_port' in options:
                self.proxy_port = options['proxy_port']
            else:
                self.proxy_port = 1080
        else:
            self.proxy_host = None

        super().__init__()

    def run(self, date) -> bool:
        """
        Exécution de la récupération par SFTP.

        Parameters
        ----------
        date : datetime
            Date de la prévision.
        """
        try:
            if self.proxy_host:
                sock = socks.socksocket()
                sock.set_proxy(
                    proxy_type=socks.SOCKS5,
                    addr=self.proxy_host,
                    port=self.proxy_port
                )
                sock.connect((self.hostname, self.port))
                transport = paramiko.Transport(sock)
            else:
                transport = paramiko.Transport((self.hostname, self.port))

            transport.connect(None, self.username, self.password)
            sftp = paramiko.SFTPClient.from_transport(transport)
            sftp.chdir(self.remote_dir)

            local_path = Path(self._get_local_path(date))
            forecast_date = date.strftime("%Y%m%d")

            for remote_file in sftp.listdir('.'):
                if fnmatch.fnmatch(remote_file, f'{self.prefix}*_{forecast_date}*.*'):
                    local_file = local_path / remote_file
                    if local_file.exists():
                        continue
                    sftp.get(remote_file, str(local_file))
                    self._unpack_if_needed(local_file, local_path)

            if sftp:
                sftp.close()
            if transport:
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
            print(f"Le rapatriement des données par SFTP a échoué ({e}).")
            return False

        return True

    @staticmethod
    def _chdir_or_mkdir(dir_path, sftp):
        try:
            sftp.chdir(dir_path)
        except IOError:
            sftp.mkdir(dir_path)
            sftp.chdir(dir_path)

    def _get_local_path(self, date):
        local_path = asv.build_date_dir_structure(self.local_dir, date)
        local_path.mkdir(parents=True, exist_ok=True)
        return local_path

    @staticmethod
    def _unpack_if_needed(local_file, local_path):
        if local_file.suffix in ['.gz', '.tgz', '.xz', '.txz', '.bz2',
                                 '.tbz', '.tbz2', '.tb2']:
            file = tarfile.open(local_file)
            for member in file.getmembers():
                if member.isreg():
                    member.name = os.path.basename(member.name)
                    file.extract(member, local_path)
            file.close()
