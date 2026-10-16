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
        * proxy_type : str
            Type de proxy : 'http' (méthode CONNECT), 'socks4' ou 'socks5'
            (par défaut: 'http').
        * proxy_host : str
            Adresse du proxy, si nécessaire.
        * proxy_port : int
            Port du proxy si nécessaire (par défaut: 8080).
        * remote_dir : str
            Chemin sur le serveur distant où enregistrer les fichiers.
        * known_hosts : str
            Fichier known_hosts (format OpenSSH, ex. produit par 'ssh-keyscan')
            contenant la clé du serveur. Si défini, l'identité du serveur est
            vérifiée avant l'envoi du mot de passe (recommandé).

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
    proxy_type : str
        Type de proxy ('http', 'socks4' ou 'socks5').
    proxy_host : str
        Adresse du proxy, si nécessaire.
    proxy_port : int
        Port du proxy si nécessaire (par défaut: 8080).
    remote_dir : str
        Chemin sur le serveur distant où enregistrer les fichiers.
    host_key : paramiko.PKey
        Clé attendue du serveur (None si l'identité du serveur n'est pas vérifiée).
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

        self.proxy_type = asv.utils.parse_proxy_type(options.get('proxy_type'))

        if 'proxy_host' in options and len(options['proxy_host']) > 0:
            self.proxy_host = options['proxy_host']
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
                self.proxy_port = 8080
        else:
            self.proxy_host = None

        self.host_key = None
        if options.get('known_hosts'):
            self.host_key = asv.utils.load_host_key(
                options['known_hosts'], self.hostname, self.port)

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
            if self.proxy_host:
                proxy_socket = asv.utils.connect_via_proxy(
                    self.proxy_type, self.proxy_host, self.proxy_port,
                    self.hostname, self.port)
                transport = paramiko.Transport(proxy_socket)

            else:
                # Create a transport object for the SFTP connection
                transport = paramiko.Transport((self.hostname, self.port))

            # Verify the server key (if defined) and authenticate
            transport.connect(hostkey=self.host_key, username=self.username,
                              password=self.password)

            # Create SFTP client
            sftp = paramiko.SFTPClient.from_transport(transport)

            self._chdir_or_mkdir(self.remote_dir, sftp)
            self._chdir_or_mkdir(date.strftime('%Y'), sftp)
            self._chdir_or_mkdir(date.strftime('%m'), sftp)
            self._chdir_or_mkdir(date.strftime('%d'), sftp)

            for file in self._file_paths:
                filename = os.path.basename(file)
                asv.check_file_exists(file)

                # If file exists remotely, upload only if it must be replaced
                try:
                    remote_size = sftp.stat(filename).st_size
                except FileNotFoundError:
                    remote_size = None
                else:
                    if not self._must_replace(file, remote_size):
                        print(f"Le fichier {filename} existe déjà sur le serveur "
                              f"distant.")
                        continue
                    print(f"Remplacement du fichier {filename} sur le serveur "
                          f"distant.")

                sftp.put(file, filename)

            sftp.close()
            transport.close()

            return True

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

        if 'sftp' in locals():
            sftp.close()
        if 'transport' in locals():
            transport.close()

        return False

    @staticmethod
    def _chdir_or_mkdir(dir_path, sftp):
        try:
            sftp.chdir(dir_path)
        except OSError:
            sftp.mkdir(dir_path)
            sftp.chdir(dir_path)
