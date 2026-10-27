import ftplib
import logging
import os

import socks

import atmoswing_vigicrues as asv

from .dissemination import Dissemination

logger = logging.getLogger(__name__)


class FtpViaProxy(ftplib.FTP):
    """
    Client FTP dont les connexions (contrôle et données) passent par un proxy.

    Seules les connexions de cette instance sont concernées : le module socket
    n'est pas modifié. Seul le mode passif est supporté, le mode actif nécessitant
    une connexion entrante depuis le serveur.

    Parameters
    ----------
    proxy_type : int
        Type de proxy (socks.HTTP, socks.SOCKS4 ou socks.SOCKS5).
    proxy_host : str
        Adresse du proxy.
    proxy_port : int
        Port du proxy.
    proxy_username : str
        Utilisateur du proxy, si nécessaire.
    proxy_password : str
        Mot de passe de l'utilisateur du proxy, si nécessaire.
    """

    def __init__(self, proxy_type, proxy_host, proxy_port, proxy_username=None,
                 proxy_password=None, **kwargs):
        self.proxy_type = proxy_type
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.proxy_username = proxy_username
        self.proxy_password = proxy_password
        super().__init__(**kwargs)

    def _create_connection(self, host, port):
        return socks.create_connection(
            (host, port), self.timeout, source_address=self.source_address,
            proxy_type=self.proxy_type, proxy_addr=self.proxy_host,
            proxy_port=self.proxy_port, proxy_username=self.proxy_username,
            proxy_password=self.proxy_password)

    def connect(self, host='', port=0, timeout=-999, source_address=None):
        if host != '':
            self.host = host
        if port > 0:
            self.port = port
        if timeout != -999:
            self.timeout = timeout
        if source_address is not None:
            self.source_address = source_address
        self.sock = self._create_connection(self.host, self.port)
        self.af = self.sock.family
        self.file = self.sock.makefile('r', encoding=self.encoding)
        self.welcome = self.getresp()
        return self.welcome

    def ntransfercmd(self, cmd, rest=None):
        if not self.passiveserver:
            raise asv.Error("Le mode FTP actif n'est pas supporté via un proxy.")
        host, port = self.makepasv()
        conn = self._create_connection(host, port)
        try:
            if rest is not None:
                self.sendcmd(f"REST {rest}")
            resp = self.sendcmd(cmd)
            # Certains serveurs envoient une réponse 200 avant la réponse 150
            if resp[0] == '2':
                resp = self.getresp()
            if resp[0] != '1':
                raise ftplib.error_reply(resp)
        except BaseException:
            conn.close()
            raise
        size = None
        if resp[:3] == '150':
            size = ftplib.parse150(resp)
        return conn, size


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
        * proxy_username : str
            Utilisateur du proxy, si nécessaire (authentification Basic).
        * proxy_password : str
            Mot de passe de l'utilisateur du proxy, si nécessaire.
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
    proxy_username : str
        Utilisateur du proxy (None si non défini).
    proxy_password : str
        Mot de passe de l'utilisateur du proxy (None si non défini).
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

        self.proxy_username, self.proxy_password = \
            asv.utils.parse_proxy_credentials(options)

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
            logger.info("  -> Aucun fichier à traiter")
            return True

        try:
            if self.proxy_host:
                ftp = FtpViaProxy(self.proxy_type, self.proxy_host, self.proxy_port,
                                  self.proxy_username, self.proxy_password)
            else:
                ftp = ftplib.FTP()

            ftp.connect(self.hostname, self.port)
            ftp.login(self.username, self.password)

            self._chdir_or_mkdir(self.remote_dir, ftp)
            self._chdir_or_mkdir(date.strftime('%Y'), ftp)
            self._chdir_or_mkdir(date.strftime('%m'), ftp)
            self._chdir_or_mkdir(date.strftime('%d'), ftp)
            ftp.voidcmd('TYPE I')  # Requis par la commande SIZE
            remote_files = self._list_remote_files(ftp)

            for file in self._file_paths:
                filename = os.path.basename(file)
                asv.check_file_exists(file)

                # If file exists remotely, upload only if it must be replaced
                if filename in remote_files:
                    if not self._must_replace(file, self._remote_size(ftp, filename)):
                        logger.info(f"Le fichier {filename} existe déjà sur le serveur "
                                    f"distant.")
                        continue
                    logger.info(f"Remplacement du fichier {filename} sur le serveur "
                                f"distant.")

                with open(file, 'rb') as f:
                    ftp.storbinary(f'STOR {filename}', f)

            ftp.quit()

            return True

        except Exception as e:
            logger.error(f"La diffusion FTP a échoué ({e}).")

        if 'ftp' in locals():
            ftp.close()

        return False

    @staticmethod
    def _list_remote_files(ftp):
        try:
            return set(ftp.nlst())
        except ftplib.error_perm:
            # Certains serveurs répondent par une erreur pour un répertoire vide
            return set()

    @staticmethod
    def _remote_size(ftp, filename):
        try:
            return ftp.size(filename)
        except ftplib.all_errors:
            return None

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
