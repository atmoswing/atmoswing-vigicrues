import datetime
import os
import socket
from pathlib import Path

import numpy as np
import paramiko
import socks

import atmoswing_vigicrues as asv

PROXY_TYPES = {
    'http': None,
    'socks4': socks.SOCKS4,
    'socks5': socks.SOCKS5,
}


def file_exists(path):
    """
    Contrôle du chemin vers un fichier.

    Parameters
    ----------
    path: str or Path
        Le chemin vers le fichier.

    Returns
    -------
    bool
        Vrai (True) si le fichier existe, faux (False) sinon.

    Examples
    --------
    >>> file_exists(R'C:\\Users\\username\\Documents\\file.txt')
    True
    """
    path = Path(path)
    if not path.exists():
        return False
    if not path.is_file():
        return False
    return True


def check_file_exists(path):
    """
    Contrôle du chemin vers un fichier et lève une exception si le fichier n'existe pas.

    Parameters
    ----------
    path: str or Path
        Le chemin vers le fichier.

    Raises
    ------
    asv.FilePathError
        Si le chemin n'existe pas.
    asv.Error
        Si le chemin n'est pas un fichier.

    Examples
    --------
    >>> check_file_exists(R'C:\\Users\\username\\Documents\\file.txt')
    """
    path = Path(path)
    if not path.exists():
        raise asv.FilePathError(path)
    if not path.is_file():
        raise asv.Error(f"Le chemin '{path}' n'est pas un fichier.")


def check_dir_exists(path, create=False):
    """
    Contrôle du chemin vers un répertoire et lève une exception si le répertoire
    n'existe pas.

    Parameters
    ----------
    path: str or Path
        Le chemin vers le répertoire.
    create: bool
        Création du répertoire si celui-ci n'existe pas.

    Raises
    ------
    asv.Error
        Si le chemin n'existe pas.

    Examples
    --------
    >>> check_dir_exists(R'C:\\Users\\username\\Documents\\dir')
    """
    path_output = Path(path)
    if not path_output.exists():
        if create:
            path_output.mkdir(parents=True, exist_ok=True)
        else:
            raise asv.Error(f"Le répertoire '{path}' n'a pas été trouvé.")


def use_builtin_eccodes_definitions():
    """
    Ignore, pour le processus Python uniquement, les définitions désignées par
    ECCODES_DEFINITION_PATH lorsque la bibliothèque eccodes utilisée embarque ses
    propres définitions (paquet pip 'eccodeslib').

    L'image AtmoSwing Forecaster définit ECCODES_DEFINITION_PATH pour la version
    système d'eccodes, plus ancienne : la bibliothèque embarquée chargerait alors
    des définitions incompatibles et ne pourrait décoder aucun fichier GRIB. La
    variable d'environnement n'est pas modifiée, afin de rester valable pour
    AtmoSwing Forecaster (exécuté en sous-processus).
    """
    env_paths = os.environ.get('ECCODES_DEFINITION_PATH')
    if not env_paths:
        return
    try:
        import eccodes
        current = eccodes.codes_definition_path().split(':')
        builtin = [p for p in current if p not in env_paths.split(':')]
        if builtin:
            eccodes.codes_set_definitions_path(':'.join(builtin))
    except Exception:
        pass


def build_date_dir_structure(base, date):
    """
    Construit la structure de répertoires pour une date donnée.

    Parameters
    ----------
    base: str or Path
        Le répertoire de base.
    date: str or datetime.datetime
        La date à utiliser.

    Returns
    -------
    Path
        Le répertoire de base avec la structure de répertoires pour la date.

    Examples
    --------
    >>> build_date_dir_structure(R'D:\\Documents\\dir', '2020-01-01 00:00:00')
    Path('D:\\Documents\\dir\\2020\\01\\01')
    """
    if isinstance(date, str):
        date = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
    base = Path(base)
    base = base / date.strftime("%Y")
    base = base / date.strftime("%m")
    base = base / date.strftime("%d")
    return base


def load_host_key(known_hosts, hostname, port=22):
    """
    Charge la clé publique attendue d'un serveur SSH depuis un fichier known_hosts
    (format OpenSSH, ex. produit par 'ssh-keyscan').

    Parameters
    ----------
    known_hosts: str or Path
        Le chemin du fichier known_hosts.
    hostname: str
        L'adresse du serveur.
    port: int
        Le port du serveur.

    Returns
    -------
    paramiko.PKey
        La clé attendue du serveur.

    Raises
    ------
    asv.Error
        Si le fichier ne contient aucune clé pour ce serveur.
    """
    check_file_exists(known_hosts)
    host_keys = paramiko.HostKeys(str(known_hosts))
    entry = hostname if int(port) == 22 else f"[{hostname}]:{port}"
    keys = host_keys.lookup(entry)
    if not keys:
        raise asv.Error(f"Aucune clé pour le serveur '{entry}' dans le fichier "
                        f"'{known_hosts}'.")
    return keys[next(iter(keys))]


def parse_proxy_type(value):
    """
    Contrôle et normalise le type de proxy.

    Parameters
    ----------
    value: str or None
        Le type de proxy ('http', 'socks4' ou 'socks5'). Une valeur vide
        correspond à 'http'.

    Returns
    -------
    str
        Le type de proxy en minuscules.

    Raises
    ------
    asv.Error
        Si le type de proxy n'est pas supporté.
    """
    if not value:
        return 'http'
    proxy_type = str(value).strip().lower()
    if proxy_type not in PROXY_TYPES:
        raise asv.Error(f"Le type de proxy '{value}' n'est pas supporté "
                        f"(options : {', '.join(PROXY_TYPES)}).")
    return proxy_type


def connect_via_proxy(proxy_type, proxy_host, proxy_port, target_host, target_port,
                      timeout=30):
    """
    Ouvre une connexion TCP vers un serveur distant au travers d'un proxy.

    Parameters
    ----------
    proxy_type: str
        Le type de proxy ('http', 'socks4' ou 'socks5').
    proxy_host: str
        L'adresse du proxy.
    proxy_port: int
        Le port du proxy.
    target_host: str
        L'adresse du serveur distant.
    target_port: int
        Le port du serveur distant.
    timeout: float
        Le délai maximal (en secondes) pour l'établissement de la connexion.

    Returns
    -------
    socket.socket
        Le socket connecté au serveur distant au travers du proxy.
    """
    proxy_type = parse_proxy_type(proxy_type)
    if proxy_type == 'http':
        return connect_via_http_proxy(proxy_host, proxy_port, target_host,
                                      target_port, timeout)

    try:
        sock = socks.create_connection(
            (target_host, target_port), timeout,
            proxy_type=PROXY_TYPES[proxy_type], proxy_addr=proxy_host,
            proxy_port=proxy_port, proxy_rdns=True)
    except socks.ProxyError as e:
        raise asv.Error(f"Échec de la connexion via le proxy ({e}).") from e
    sock.settimeout(None)
    return sock


def connect_via_http_proxy(proxy_host, proxy_port, target_host, target_port,
                           timeout=30):
    """
    Ouvre un tunnel TCP vers un serveur distant au travers d'un proxy HTTP
    (méthode CONNECT).

    Parameters
    ----------
    proxy_host: str
        L'adresse du proxy.
    proxy_port: int
        Le port du proxy.
    target_host: str
        L'adresse du serveur distant.
    target_port: int
        Le port du serveur distant.
    timeout: float
        Le délai maximal (en secondes) pour l'établissement du tunnel.

    Returns
    -------
    socket.socket
        Le socket connecté au serveur distant au travers du proxy.

    Raises
    ------
    asv.Error
        Si le proxy refuse ou interrompt la connexion.
    """
    sock = socket.create_connection((proxy_host, proxy_port), timeout=timeout)
    try:
        request = (f"CONNECT {target_host}:{target_port} HTTP/1.1\r\n"
                   f"Host: {target_host}:{target_port}\r\n\r\n")
        sock.sendall(request.encode())

        # Lecture octet par octet jusqu'à la fin des en-têtes, afin de ne pas
        # consommer les données envoyées par le serveur distant (ex. bannière SSH).
        response = b""
        while not response.endswith(b"\r\n\r\n"):
            byte = sock.recv(1)
            if not byte:
                raise asv.Error("Le proxy a fermé la connexion.")
            response += byte
            if len(response) > 16384:
                raise asv.Error("Réponse du proxy trop longue.")

        status_line = response.split(b"\r\n", 1)[0].decode(errors='replace')
        status = status_line.split()
        if len(status) < 2 or status[1] != '200':
            raise asv.Error(f"Échec de la connexion via le proxy ({status_line}).")

        sock.settimeout(None)
        return sock

    except BaseException:
        sock.close()
        raise


MJD_EPOCH = np.datetime64('1858-11-17T00:00:00', 's')


def mjd_to_datetime(mjd):
    """
    Transforme un tableau de nombre de jour julien modifié (MJD) en date, arrondie
    à l'heure la plus proche.

    AtmoSwing enregistre les dates en float32, dont la précision n'est que
    d'environ 5.6 minutes autour de MJD 60000 : une date horaire (ex. 1/24 jour)
    n'est donc pas représentée exactement. Les dates d'AtmoSwing étant toujours
    des heures pleines, l'arrondi à l'heure restitue la date exacte.

    Parameters
    ----------
    mjd: ndarray
        Le tableau de nombre de jour julien modifié (MJD).

    Returns
    -------
    date: ndarray
        Le tableau de date.

    Examples
    --------
    >>> mjd_to_datetime(np.array([59215.5, 59216.5]))
    array(['2021-01-01T12:00:00', '2021-01-02T12:00:00'], dtype='datetime64[s]')
    """
    hours = np.round(np.asarray(mjd, dtype=np.float64) * 24).astype(np.int64)
    return MJD_EPOCH + hours.astype('timedelta64[h]')


def build_cumulative_frequency(size):
    """
    Construit une distribution de fréquence cumulée.

    Parameters
    ----------
    size: int
        La taille de la distribution.

    Returns
    -------
    f: ndarray
        La distribution de fréquence cumulée.

    Examples
    --------
    >>> build_cumulative_frequency(10)
    """
    # Parameters for the estimated distribution from Gringorten (a=0.44, b=0.12).
    # Choice based on [Cunnane, C., 1978, Unbiased plotting positions—A review:
    # Journal of Hydrology, v. 37, p. 205–222.]
    irep = 0.44
    nrep = 0.12

    divisor = 1.0 / (size + nrep)

    f = np.arange(size, dtype=float)
    f += 1.0 - irep
    f *= divisor

    return f
