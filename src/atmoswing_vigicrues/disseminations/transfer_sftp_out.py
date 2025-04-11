import os
import socket
import ssl
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
                proxy_socket = self._connect_via_http_proxy(
                    self.proxy_host, self.proxy_port, self.hostname, self.port)
                transport = paramiko.Transport(proxy_socket)

            else:
                # Create a transport object for the SFTP connection
                transport = paramiko.Transport((self.hostname, self.port))

            # Authenticate with the SFTP server
            transport.connect(username=self.username, password=self.password)

            # Create SFTP client
            sftp = paramiko.SFTPClient.from_transport(transport)

            self._chdir_or_mkdir(self.remote_dir, sftp)
            self._chdir_or_mkdir(date.strftime('%Y'), sftp)
            self._chdir_or_mkdir(date.strftime('%m'), sftp)
            self._chdir_or_mkdir(date.strftime('%d'), sftp)

            for file in self._file_paths:
                filename = os.path.basename(file)
                asv.check_file_exists(file)

                # If file exists remotely, do not upload
                try:
                    sftp.stat(filename)
                    print(f"Le fichier {filename} existe déjà sur le serveur distant.")
                    continue
                except FileNotFoundError:
                    pass

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
    def _connect_via_http_proxy(proxy_host, proxy_port, target_host, target_port):
        sock = socket.create_connection((proxy_host, proxy_port))
        connect_str = (f"CONNECT {target_host}:{target_port} HTTP/1.1\r\nHost: "
                       f"{target_host}:{target_port}\r\n\r\n")
        sock.sendall(connect_str.encode())

        # Wait for HTTP 200 connection established
        response = sock.recv(4096).decode()
        if "200 connection established" not in response.lower():
            raise Exception(f"Failed to connect via proxy. Response:\n{response}")

        return sock

    @staticmethod
    def _chdir_or_mkdir(dir_path, sftp):
        try:
            sftp.chdir(dir_path)
        except OSError:
            sftp.mkdir(dir_path)
            sftp.chdir(dir_path)
