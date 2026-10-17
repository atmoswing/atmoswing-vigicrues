import bz2
import fnmatch
import gzip
import logging
import lzma
import os
import shutil
import tarfile
from pathlib import Path

import paramiko

import atmoswing_vigicrues as asv

from .preaction import PreAction

logger = logging.getLogger(__name__)

ARCHIVE_SUFFIXES = ['.gz', '.tgz', '.xz', '.txz', '.bz2', '.tbz', '.tbz2', '.tb2']

# Fichiers compressés seuls (hors archive tar)
COMPRESSED_FILE_OPENERS = {'.gz': gzip.open, '.bz2': bz2.open, '.xz': lzma.open}


class TransferSftpIn(PreAction):
    """
    Récupération des prévisions des modèles météo par SFTP.

    Parameters
    ----------
    name: str
        Le nom de l'action
    options: dict
        Un dictionnaire contenant les options de l'action. Les champs possibles sont:

        * local_dir : str
            Répertoire cible pour l'enregistrement des fichiers.
        * prefix : str
            Prefix des fichiers à importer.
        * variables : list (optionnel)
            Liste des variables météorologiques à importer.
        * hostname : str
            Adresse du serveur distant.
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
            Port du proxy si nécessaire (par défaut: 1080).
        * proxy_username : str
            Utilisateur du proxy, si nécessaire (authentification Basic pour
            HTTP, utilisateur/mot de passe pour SOCKS5, identifiant seul pour
            SOCKS4).
        * proxy_password : str
            Mot de passe de l'utilisateur du proxy, si nécessaire.
        * remote_dir : str
            Chemin sur le serveur distant où se trouvent les fichiers.
        * known_hosts : str
            Fichier known_hosts (format OpenSSH, ex. produit par 'ssh-keyscan')
            contenant la clé du serveur. Si défini, l'identité du serveur est
            vérifiée avant l'envoi du mot de passe (recommandé).
        * attempts_max_hours : int
            Décalage temporel autorisé pour rechercher d'anciens fichiers
        * attempts_step_hours : int
            Pas de temps auquel décrémenter la date pour rechercher d'anciens fichiers

    Attributes
    ----------
    type_name : str
        Le nom du type de l'action
    name : str
        Le nom de l'action
    local_dir : str
        Répertoire cible pour l'enregistrement des fichiers.
    prefix : str
        Prefix des fichiers à importer.
    hostname : str
        Adresse du serveur distant.
    port : int
        Port du serveur distant.
    username : str
        Utilisateur ayant un accès au serveur.
    password : str
        Mot de passe de l'utilisateur sur le serveur.
    remote_dir : str
        Chemin sur le serveur distant où se trouvent les fichiers.
    variables : list
        Liste des variables météorologiques à importer.
    proxy_type : str
        Type de proxy ('http', 'socks4' ou 'socks5').
    proxy_host : str
        Adresse du proxy, si nécessaire.
    proxy_port : int
        Port du proxy si nécessaire (par défaut: 1080).
    proxy_username : str
        Utilisateur du proxy (None si non défini).
    proxy_password : str
        Mot de passe de l'utilisateur du proxy (None si non défini).
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
        self.prefix = options['prefix']
        self.hostname = options['hostname']
        self.port = int(options['port'])
        self.username = options['username']
        self.password = options['password']
        self.remote_dir = options['remote_dir']

        self._set_attempts_attributes(options)

        if 'variables' in options and len(options['variables']) > 0:
            self.variables = options['variables']
        else:
            self.variables = None

        self.proxy_type = asv.utils.parse_proxy_type(options.get('proxy_type'))
        self.proxy_username, self.proxy_password = \
            asv.utils.parse_proxy_credentials(options, self.proxy_type)

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
                self.proxy_port = 1080
        else:
            self.proxy_host = None

        self.host_key = None
        if options.get('known_hosts'):
            self.host_key = asv.utils.load_host_key(
                options['known_hosts'], self.hostname, self.port)

        super().__init__()

    def run(self, date) -> bool:
        """
        Exécution de la récupération par SFTP.

        Parameters
        ----------
        date : datetime.datetime
            Date de la prévision.

        Returns
        -------
        bool
            Vrai (True) en cas de succès, faux (False) autrement.
        """
        transport = None
        sftp = None
        try:

            # Check if files already in the local folder (only with defined variables)
            if self.variables is not None:
                if self._files_already_present(date):
                    logger.info("  -> Fichiers déjà présents localement.")
                    return True

            if self.proxy_host:
                proxy_socket = asv.utils.connect_via_proxy(
                    self.proxy_type, self.proxy_host, self.proxy_port,
                    self.hostname, self.port, username=self.proxy_username,
                    password=self.proxy_password)
                transport = paramiko.Transport(proxy_socket)
            else:
                transport = paramiko.Transport((self.hostname, self.port))

            # Verify the server key (if defined) and authenticate
            transport.connect(hostkey=self.host_key, username=self.username,
                              password=self.password)

            # Create an SFTP client object
            sftp = transport.open_sftp_client()

            # Change the directory to the desired remote directory
            sftp.chdir(self.remote_dir)

            # Download files
            local_path = Path(self._get_local_path(date))
            forecast_datetime = date.strftime("%Y%m%d%H")
            f_exist_dt, f_new_dt = self._get_files(sftp, forecast_datetime, local_path)

            if f_exist_dt + f_new_dt == 0:
                logger.warning(f"  -> Pas de fichier disponible pour "
                               f"{forecast_datetime}.")
                return False

            forecast_date = date.strftime("%Y%m%d")
            f_exist_d, f_new_d = self._get_files(sftp, forecast_date, local_path)

            logger.info(f"  -> Nombre de fichiers existants : {f_exist_d - f_new_dt}.")
            logger.info(f"  -> Nombre de fichiers récupérés : {f_new_dt + f_new_d}.")

            return True

        except paramiko.ssh_exception.PasswordRequiredException as e:
            logger.error(f"SFTP PasswordRequiredException {e}")
        except paramiko.ssh_exception.BadAuthenticationType as e:
            logger.error(f"SFTP BadAuthenticationType {e}")
        except paramiko.ssh_exception.AuthenticationException as e:
            logger.error(f"SFTP AuthenticationException {e}")
        except paramiko.ssh_exception.ChannelException as e:
            logger.error(f"SFTP ChannelException {e}")
        except paramiko.ssh_exception.ProxyCommandFailure as e:
            logger.error(f"SFTP ProxyCommandFailure {e}")
        except paramiko.ssh_exception.SSHException as e:
            logger.error(f"SFTP SSHException {e}")
        except FileNotFoundError as e:
            logger.error(f"SFTP FileNotFoundError {e}")
        except Exception as e:
            logger.error(f"Le rapatriement des données par SFTP a échoué ({e}).")
        finally:
            if sftp is not None:
                sftp.close()
            if transport is not None:
                transport.close()

        return False

    def _get_files(self, sftp, forecast_date, local_path):
        files_count_existing = 0
        files_count_new = 0
        for remote_file in sftp.listdir('.'):
            pattern = f'{self.prefix.lower()}*_{forecast_date}*.*'
            if self.variables is not None:
                for variable in self.variables:
                    pattern = f'{self.prefix.lower()}_{variable.lower()}' \
                              f'_{forecast_date}*.*'
                    if fnmatch.fnmatch(remote_file.lower(), pattern):
                        break

            if fnmatch.fnmatch(remote_file.lower(), pattern):
                local_file = local_path / remote_file
                if local_file.exists():
                    files_count_existing += 1
                    continue
                sftp.get(remote_file, str(local_file), prefetch=False)
                self._unpack_if_needed(local_file, local_path)
                files_count_new += 1

        return files_count_existing, files_count_new

    def _get_local_path(self, date):
        local_path = asv.build_date_dir_structure(self.local_dir, date)
        local_path.mkdir(parents=True, exist_ok=True)
        return local_path

    def _files_already_present(self, date):
        local_path = Path(self._get_local_path(date))
        forecast_datetime = date.strftime("%Y%m%d%H")

        for variable in self.variables:
            pattern = f'{self.prefix.lower()}_{variable.lower()}' \
                      f'_{forecast_datetime}*.*'
            local_files = local_path.glob(pattern)
            file_found = False
            for local_file in local_files:
                if fnmatch.fnmatch(str(local_file.name).lower(), pattern):
                    file_found = True
                    break
            if not file_found:
                return False

        return True

    @staticmethod
    def _unpack_if_needed(local_file, local_path):
        """
        Décompresse un fichier récupéré, s'il s'agit d'une archive tar (compressée
        ou non) ou d'un fichier compressé seul (ex. '.grb.gz' -> '.grb').
        """
        if local_file.suffix not in ARCHIVE_SUFFIXES:
            return

        if tarfile.is_tarfile(local_file):
            with tarfile.open(local_file) as archive:
                for member in archive.getmembers():
                    # Seuls les fichiers réguliers sont extraits, à plat : les liens
                    # et les chemins (ex. '../') sont ignorés.
                    if not member.isreg():
                        continue
                    member.name = os.path.basename(member.name)
                    if hasattr(tarfile, 'data_filter'):
                        archive.extract(member, local_path, filter='data')
                    else:
                        archive.extract(member, local_path)
            return

        opener = COMPRESSED_FILE_OPENERS.get(local_file.suffix)
        if opener is None:
            raise asv.Error(f"L'archive {local_file.name} n'est pas une archive tar.")
        with opener(local_file, 'rb') as source, \
                open(local_path / local_file.stem, 'wb') as target:
            shutil.copyfileobj(source, target)
