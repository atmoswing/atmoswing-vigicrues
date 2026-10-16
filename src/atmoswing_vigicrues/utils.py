import datetime
import socket
from pathlib import Path

import numpy as np
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
    if type(path) == str:
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
    if type(path) == str:
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


def jd_to_date(jd):
    """
    Transforme un nombre de jour julien en date (année, mois, jour).
    De https://gist.github.com/jiffyclub/1294443

    Parameters
    ----------
    jd: float
        Le nombre de jour julien.

    Returns
    -------
    year: int
        L'année.
    month: int
        Le mois.
    day: int
        Le jour.

    Examples
    --------
    >>> jd_to_date(2460096.5)
    (2023, 6, 1)
    """
    jd = jd + 0.5

    f, i = np.modf(jd)
    i = i.astype(int)

    a = np.trunc((i - 1867216.25) / 36524.25)
    b = np.zeros(len(jd))

    idx = tuple([i > 2299160])
    b[idx] = i[idx] + 1 + a[idx] - np.trunc(a[idx] / 4.)
    idx = tuple([i <= 2299160])
    b[idx] = i[idx]

    c = b + 1524
    d = np.trunc((c - 122.1) / 365.25)
    e = np.trunc(365.25 * d)
    g = np.trunc((c - e) / 30.6001)

    day = c - e + f - np.trunc(30.6001 * g)

    month = np.zeros(len(jd))
    month[g < 13.5] = g[g < 13.5] - 1
    month[g >= 13.5] = g[g >= 13.5] - 13
    month = month.astype(int)

    year = np.zeros(len(jd))
    year[month > 2.5] = d[month > 2.5] - 4716
    year[month <= 2.5] = d[month <= 2.5] - 4715
    year = year.astype(int)

    return year, month, day


def days_to_hours_mins(days):
    """
    Transforme un nombre de jours en heures et minutes.

    Parameters
    ----------
    days: float
        Le nombre de jours.

    Returns
    -------
    hour: int
        L'heure.
    minute: int
        La minute.

    Examples
    --------
    >>> days_to_hours_mins(0.5)
    (12, 0)
    """
    hours = days * 24.
    hours, hour = np.modf(hours)

    minutes = hours * 60.
    _, minute = np.modf(minutes)

    return hour.astype(int), minute.astype(int)


def mjd_to_datetime(mjd):
    """
    Transforme un tableau de nombre de jour julien modifié (MJD) en date
    (année, mois, jour, heure, minute).

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
    jd = mjd + 2400000.5
    year, month, day = jd_to_date(jd)

    frac_days, day = np.modf(day)
    day = day.astype(int)

    hour, minute = days_to_hours_mins(frac_days)

    date = np.empty(len(mjd), dtype='datetime64[s]')

    for idx, _ in enumerate(year):
        date[idx] = datetime.datetime(year[idx], month[idx], day[idx],
                                      hour[idx], minute[idx], 0, 0)

    return date


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
