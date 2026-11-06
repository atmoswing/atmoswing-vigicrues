import contextlib
import datetime
import io
import logging
import os
import shutil
import tempfile
from pathlib import Path

import numpy as np
import requests

import atmoswing_vigicrues as asv

from .preaction import PreAction

try:
    from ecmwf.opendata import Client
except ImportError:
    has_ecmwf_opendata = False
else:
    has_ecmwf_opendata = True

logger = logging.getLogger(__name__)

# Variables disponibles : (paramètre des données ouvertes, type de niveau)
VARIABLES = {
    'z': ('z', 'pl'),
    'gh': ('gh', 'pl'),
    't': ('t', 'pl'),
    'r': ('r', 'pl'),
    'q': ('q', 'pl'),
    'w': ('w', 'pl'),
    'u': ('u', 'pl'),
    'v': ('v', 'pl'),
    'tcwv': ('tcwv', 'sfc'),
}

RESOLUTIONS = {0.25: '0p25', 0.1: '0p1'}

# Les échéances sont horaires jusqu'à 144 h (pas de 3 h), puis par pas de 6 h
LEAD_TIME_3H_MAX = 144

# Échéance maximale des runs de 00 h et 12 h
LEAD_TIME_MAX = 360


class _IgnoreConnectionLimitNotice(logging.Filter):
    """
    Ignore l'avertissement générique du client sur la limite de connexions
    simultanées au portail, émis à chaque exécution.
    """

    def filter(self, record):
        return not str(record.msg).startswith("To ensure the stability")


logging.getLogger('ecmwf.opendata.utils').addFilter(_IgnoreConnectionLimitNotice())


class _TimeoutAdapter(requests.adapters.HTTPAdapter):
    """Adaptateur requests appliquant un délai maximal par défaut aux requêtes."""

    def __init__(self, timeout, **kwargs):
        self.timeout = timeout
        super().__init__(**kwargs)

    def send(self, request, **kwargs):
        if kwargs.get('timeout') is None:
            kwargs['timeout'] = self.timeout
        return super().send(request, **kwargs)


class DownloadEcmwfData(PreAction):
    """
    Téléchargement des prévisions du CEP (ECMWF IFS) depuis les données ouvertes
    (open data), à l'aide du client officiel 'ecmwf-opendata'.

    Les champs GRIB2 des données ouvertes sont découpés sur le domaine demandé
    (sans autre modification) et enregistrés, un fichier par variable et par run :
    '<prefix>_<VARIABLE>_<YYYYMMDDHH>00.grb', dans l'arborescence YYYY/MM/DD du
    répertoire cible. Ces fichiers sont lus par le jeu de données
    'Custom_Vigicrues_IFS' d'AtmoSwing (version lisant les fichiers du CEP au
    format GRIB2).

    Un fichier n'est écrit qu'une fois complet : les fichiers déjà présents sont
    ignorés, et une exécution interrompue reprend avec les variables manquantes.
    Les flux qui partagent un même répertoire cible doivent donc demander les mêmes
    niveaux et échéances : un fichier existant n'est pas complété.

    Les runs précédents sont aussi complétés s'ils manquent (ex. après une panne) :
    AtmoSwing lit les premières échéances d'une prévision dans le run précédent.
    Leur échec n'empêche pas la prévision et est seulement signalé.

    Chaque variable est d'abord téléchargée sur la grille complète dans un
    répertoire temporaire, puis découpée. Un échec du téléchargement (données pas
    encore disponibles) fait échouer l'action, et la date de la prévision est
    reculée. Un échec du découpage (données disponibles mais non traitables)
    interrompt l'exécution (asv.ProcessingError), sans reculer la date : le
    fichier téléchargé est alors conservé dans le répertoire temporaire, dont le
    chemin est indiqué dans le message d'erreur.

    Parameters
    ----------
    name: str
        Le nom de l'action
    options: dict
        Un dictionnaire contenant les options de l'action. Les champs possibles sont:

        * output_dir : str
            Répertoire cible pour l'enregistrement des fichiers.
        * variables : list
            Variables à télécharger : 'z' (géopotentiel), 'r' (humidité relative),
            'tcwv' (eau précipitable), ainsi que 'gh', 't', 'q', 'w', 'u' et 'v'.
            Valeur par défaut : ['z', 'r', 'tcwv']
        * levels : list ou dict
            Niveaux de pression (hPa) des variables en altitude. Une liste
            s'applique à toutes les variables ; un dictionnaire permet de
            définir les niveaux par variable (ex. {'z': [500, 1000], 'r': [850]}).
            Valeur par défaut : [300, 400, 500, 600, 700, 850, 925, 1000]
        * domain : list
            Domaine à extraire : [lon. ouest, lon. est, lat. sud, lat. nord], en
            degrés, aligné sur la grille.
            Valeur par défaut : [-20, 30, 20, 65]
        * resolution : float
            Résolution spatiale des données (0.25 ou 0.1).
            Valeur par défaut : 0.25
        * lead_time_max : int
            Échéance maximale de la prévision en heures (360 au maximum).
            Valeur par défaut : 192
        * time_step : int
            Pas de temps des échéances en heures (3 ou un multiple de 6 ; au-delà
            de 144 h, seules les échéances multiples de 6 h existent).
            Valeur par défaut : 6
        * run_hours : list
            Heures des runs à télécharger. Pour une autre heure, l'action échoue
            et la date de la prévision est reculée.
            Valeur par défaut : [0, 12]
        * previous_runs : int
            Nombre de runs précédents (parmi 'run_hours') à compléter s'ils
            manquent. 0 pour désactiver.
            Valeur par défaut : 1
        * prefix : str
            Préfixe des fichiers produits.
            Valeur par défaut : 'CEP'
        * source : str
            Serveur des données : 'ecmwf', 'aws', 'azure', 'google' ou une URL.
            Valeur par défaut : 'ecmwf'
        * proxies : dict
            Les proxys à utiliser (si nécessaire), par protocole, au format de la
            bibliothèque requests. Exemple :
            {'http': 'http://user:pass@proxy:3128', 'https': 'http://proxy:3128'}
        * maximum_retries : int
            Nombre maximal de tentatives par requête en cas d'erreur réseau.
            Valeur par défaut : 3
        * retry_after : int
            Délai (en secondes) entre deux tentatives.
            Valeur par défaut : 30
        * timeout : float
            Délai maximal d'attente du serveur (en secondes) pour chaque requête.
            Valeur par défaut : 120
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
    output_dir : str
        Répertoire cible pour l'enregistrement des fichiers.
    variables : list
        Variables à télécharger (en minuscules).
    levels : dict
        Niveaux de pression par variable en altitude.
    domain : list
        Domaine à extraire : [lon. ouest, lon. est, lat. sud, lat. nord].
    resolution : float
        Résolution spatiale des données.
    steps : list
        Échéances à télécharger (en heures).
    run_hours : list
        Heures des runs à télécharger.
    previous_runs : int
        Nombre de runs précédents à compléter s'ils manquent.
    prefix : str
        Préfixe des fichiers produits.
    source : str
        Serveur des données.
    proxies : dict
        Les proxys à utiliser, par protocole (None si aucun proxy n'est défini).
    maximum_retries : int
        Nombre maximal de tentatives par requête.
    retry_after : int
        Délai (en secondes) entre deux tentatives.
    timeout : float
        Délai maximal d'attente du serveur (en secondes) pour chaque requête.
    """

    def __init__(self, name, options):
        if not has_ecmwf_opendata:
            raise ImportError("Le paquet ecmwf-opendata est requis pour cette "
                              "action.")
        if not asv.has_eccodes:
            raise ImportError(
                "Le paquet Python eccodes est requis pour cette action "
                "(pip install eccodes, ou avec conda : conda install -c "
                "conda-forge python-eccodes ; le paquet conda eccodes seul ne "
                "fournit que la librairie C).")

        self.type_name = "Téléchargement CEP"
        self.name = name
        self.output_dir = options['output_dir']
        asv.check_dir_exists(self.output_dir, True)

        self._set_attempts_attributes(options)

        self.variables = [str(v).lower() for v in
                          options.get('variables') or ['z', 'r', 'tcwv']]
        for variable in self.variables:
            if variable not in VARIABLES:
                raise asv.Error(f"La variable CEP '{variable}' n'est pas supportée "
                                f"(options : {', '.join(VARIABLES)}).")

        self.levels = self._parse_levels(options.get('levels'))

        self.resolution = float(options.get('resolution') or 0.25)
        if self.resolution not in RESOLUTIONS:
            raise asv.Error("La résolution fournie pour le CEP ne correspond pas "
                            "aux options disponibles (0.25, 0.1).")

        self.domain = [float(v) for v in options.get('domain') or [-20, 30, 20, 65]]
        self._check_domain()

        lead_time_max = int(options.get('lead_time_max') or 192)
        time_step = int(options.get('time_step') or 6)
        if lead_time_max > LEAD_TIME_MAX:
            raise asv.Error(f"L'échéance maximale du CEP ne peut dépasser "
                            f"{LEAD_TIME_MAX} h.")
        if time_step != 3 and time_step % 6 != 0:
            raise asv.Error("Le pas de temps du CEP doit valoir 3 h ou un multiple "
                            "de 6 h.")
        self.steps = [step for step in range(0, lead_time_max + 1, time_step)
                      if step <= LEAD_TIME_3H_MAX or step % 6 == 0]

        self.run_hours = [int(h) for h in options.get('run_hours') or [0, 12]]
        self.previous_runs = int(options.get('previous_runs', 1))
        if self.previous_runs < 0:
            raise asv.Error("Le nombre de runs précédents du CEP ne peut être "
                            "négatif.")
        self.prefix = options.get('prefix') or 'CEP'
        self.source = options.get('source') or 'ecmwf'

        # Seuls les proxys renseignés sont conservés (les valeurs vides sont ignorées)
        proxies = options.get('proxies') or {}
        self.proxies = {key: value for key, value in proxies.items() if value} or None

        self.maximum_retries = int(options.get('maximum_retries') or 3)
        self.retry_after = int(options.get('retry_after') or 30)
        self.timeout = options.get('timeout') or 120

        self._client = None

        super().__init__()

    def run(self, date) -> bool:
        """
        Exécute l'action.

        Parameters
        ----------
        date: datetime.datetime
            Date d'émission de la prévision.

        Returns
        -------
        bool
            Vrai (True) en cas de succès, faux (False) autrement.
        """
        return self.download(date)

    def download(self, date) -> bool:
        """
        Télécharge les prévisions du CEP pour une date d'émission de la prévision.

        Parameters
        ----------
        date: datetime.datetime
            Date d'émission de la prévision.

        Returns
        -------
        bool
            Vrai (True) en cas de succès, faux (False) autrement.
        """
        if date.hour not in self.run_hours:
            logger.warning(f"  -> Pas de run CEP téléchargé à {date.hour:02d} h "
                           f"(runs : {self.run_hours}).")
            return False

        try:
            files_count = self._download_run(date)
        except asv.ProcessingError:
            # Les données sont disponibles : reculer la date n'y changerait rien
            raise
        except asv.Error as e:
            logger.error(f"  -> {e}")
            return False

        # Le run demandé est disponible : les runs précédents le sont aussi
        for previous_run in self._get_previous_runs(date):
            try:
                files_count += self._download_run(previous_run)
            except asv.Error as e:
                logger.warning(f"  -> Run précédent incomplet : {e}")

        logger.info(f"  -> Nombre de fichiers téléchargés : {files_count}.")

        return True

    def _download_run(self, date):
        """
        Télécharge les variables manquantes d'un run et retourne le nombre de
        fichiers téléchargés.

        Raises
        ------
        asv.Error
            Si le téléchargement d'une variable échoue.
        asv.ProcessingError
            Si une variable téléchargée ne peut être découpée.
        """
        local_path = asv.build_date_dir_structure(self.output_dir, date)
        missing = [variable for variable in self.variables
                   if not (local_path / self._file_name(variable, date)).exists()]
        if not missing:
            return 0

        date_msg = date.strftime('%d/%m/%Y %Hh')
        logger.info(f"  -> Téléchargement des prévisions du : {date_msg}.")
        local_path.mkdir(parents=True, exist_ok=True)

        for variable in missing:
            file_path = local_path / self._file_name(variable, date)
            self._download_variable(variable, date, file_path)

        return len(missing)

    def _get_previous_runs(self, date):
        """
        Retourne les 'previous_runs' runs qui précèdent une date, du plus récent au
        plus ancien. La date doit correspondre à l'une des heures de 'run_hours'.
        """
        runs = []
        run = date
        while len(runs) < self.previous_runs:
            run -= datetime.timedelta(hours=1)
            if run.hour in self.run_hours:
                runs.append(run)
        return runs

    def _file_name(self, variable, date):
        return f"{self.prefix}_{variable.upper()}_{date.strftime('%Y%m%d%H')}00.grb"

    def _download_variable(self, variable, date, file_path):
        """
        Télécharge une variable, puis l'enregistre sur le domaine.
        Le fichier cible n'est créé qu'une fois complet.

        La grille complète est téléchargée dans un répertoire temporaire, supprimé
        une fois le fichier cible créé ou si le téléchargement échoue. Il est
        conservé si le découpage échoue (ou si le processus s'arrête pendant le
        découpage), pour permettre l'analyse du fichier téléchargé.

        Raises
        ------
        asv.Error
            Si le téléchargement échoue ou est incomplet.
        asv.ProcessingError
            Si le fichier téléchargé ne peut être découpé.
        """
        param, levtype = VARIABLES[variable]
        request = {
            'date': date.strftime('%Y%m%d'),
            'time': date.hour,
            'stream': 'oper',
            'type': 'fc',
            'step': self.steps,
            'param': param,
            'levtype': levtype,
        }
        expected = len(self.steps)
        if levtype == 'pl':
            request['levelist'] = self.levels[variable]
            expected *= len(self.levels[variable])

        tmp_path = file_path.with_name(file_path.name + '.part')
        tmp_dir = Path(tempfile.mkdtemp(prefix='asv_cep_'))
        source = tmp_dir / f"{file_path.stem}.grib2"
        keep_source = False
        try:
            logger.info(f"  -> Téléchargement de '{variable}'.")
            try:
                # Les barres de progression et messages affichés par le client
                # sont ignorés (journal des exécutions planifiées)
                with contextlib.redirect_stdout(io.StringIO()), \
                        contextlib.redirect_stderr(io.StringIO()):
                    self._get_client().retrieve(request, target=str(source))
            except Exception as e:
                raise asv.Error(f"Le téléchargement de '{variable}' (CEP) a échoué "
                                f"({e}).") from e

            # Chemin journalisé avant le découpage : il reste connu même si le
            # processus s'arrête sans message d'erreur
            logger.info(f"  -> Découpage de '{variable}' (fichier téléchargé : "
                        f"{source}).")
            try:
                count = crop_grib(source, tmp_path, self.domain)
            except Exception as e:
                keep_source = True
                raise asv.ProcessingError(
                    f"Le fichier de '{variable}' (CEP) a été téléchargé mais n'a "
                    f"pas pu être découpé ({e}). Fichier téléchargé conservé : "
                    f"{source}") from e

            if count != expected:
                raise asv.Error(f"Le téléchargement de '{variable}' (CEP) est "
                                f"incomplet ({count} champs reçus sur {expected} "
                                f"attendus).")
            os.replace(tmp_path, file_path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
            if not keep_source:
                shutil.rmtree(tmp_dir, ignore_errors=True)

    def _get_client(self):
        if self._client is None:
            self._client = Client(
                source=self.source,
                resol=RESOLUTIONS[self.resolution],
                maximum_retries=self.maximum_retries,
                retry_after=self.retry_after)
            session = self._client.session
            if self.proxies:
                session.proxies.update(self.proxies)
            for prefix in ('http://', 'https://'):
                session.mount(prefix, _TimeoutAdapter(self.timeout))
        return self._client

    def _parse_levels(self, levels):
        default = [300, 400, 500, 600, 700, 850, 925, 1000]
        pl_variables = [v for v in self.variables if VARIABLES[v][1] == 'pl']
        if isinstance(levels, dict):
            levels = {str(k).lower(): v for k, v in levels.items()}
            missing = [v for v in pl_variables if v not in levels]
            if missing:
                raise asv.Error(f"Les niveaux ne sont pas définis pour les "
                                f"variables CEP {missing}.")
            return {v: [int(lev) for lev in levels[v]] for v in pl_variables}
        levels = [int(lev) for lev in levels or default]
        return {v: levels for v in pl_variables}

    def _check_domain(self):
        if len(self.domain) != 4:
            raise asv.Error("Le domaine CEP doit être défini par 4 valeurs.")
        lon_min, lon_max, lat_min, lat_max = self.domain
        if lon_min >= lon_max or lat_min >= lat_max or lat_min < -90 or lat_max > 90:
            raise asv.Error(f"Le domaine CEP {self.domain} n'est pas valide "
                            f"([lon. ouest, lon. est, lat. sud, lat. nord]).")
        for value in self.domain:
            if not _is_multiple(value, self.resolution):
                raise asv.Error(f"Les limites du domaine CEP doivent être des "
                                f"multiples de la résolution ({self.resolution}).")


def _is_multiple(value, step):
    ratio = value / step
    return abs(ratio - round(ratio)) < 1e-6


def crop_grib(source, target, domain):
    """
    Découpe les champs d'un fichier GRIB (grille régulière lat/lon) sur un domaine,
    sans changer de format : les métadonnées et la compression des champs
    d'origine sont conservées.

    Parameters
    ----------
    source: str or Path
        Le fichier GRIB d'origine (GRIB2 des données ouvertes).
    target: str or Path
        Le fichier GRIB à créer.
    domain: list
        Domaine à extraire : [lon. ouest, lon. est, lat. sud, lat. nord].

    Returns
    -------
    int
        Le nombre de champs enregistrés.
    """
    eccodes = asv.eccodes
    count = 0
    with open(source, 'rb') as f_in, open(target, 'wb') as f_out:
        for message in iter_grib_messages(f_in):
            handle = eccodes.codes_new_from_message(message)
            try:
                values, grid = _crop_field(eccodes, handle, domain)
                output = eccodes.codes_clone(handle)
                try:
                    _set_grid(eccodes, output, grid)
                    eccodes.codes_set_values(output, values.astype(float).flatten())
                    eccodes.codes_write(output, f_out)
                finally:
                    eccodes.codes_release(output)
            finally:
                eccodes.codes_release(handle)
            count += 1
    return count


def iter_grib_messages(f):
    """
    Lit un à un les messages d'un fichier GRIB (éditions 1 et 2).

    Les messages sont lus en Python puis transmis à eccodes en mémoire, plutôt que
    de passer le fichier ouvert à eccodes ('codes_grib_new_from_file') : sous
    Windows, la bibliothèque eccodes peut utiliser une autre version de la
    bibliothèque C que Python (ex. avec conda), et le processus s'arrête alors
    sans message d'erreur.

    Parameters
    ----------
    f: file
        Le fichier GRIB, ouvert en mode binaire.

    Yields
    ------
    bytes
        Un message GRIB complet.
    """
    while True:
        header = f.read(16)
        if not header:
            return
        if len(header) < 8 or header[:4] != b'GRIB':
            raise asv.Error("Le fichier GRIB est invalide (message mal formé).")
        edition = header[7]
        if edition == 2:
            if len(header) < 16:
                raise asv.Error("Le fichier GRIB est tronqué.")
            length = int.from_bytes(header[8:16], 'big')
        elif edition == 1:
            length = int.from_bytes(header[4:7], 'big')
        else:
            raise asv.Error(f"Édition GRIB non supportée ({edition}).")
        if length < len(header):
            raise asv.Error("Le fichier GRIB est invalide (longueur de message).")
        message = header + f.read(length - len(header))
        if len(message) != length or message[-4:] != b'7777':
            raise asv.Error("Le fichier GRIB est tronqué.")
        yield message


def _crop_field(eccodes, handle, domain):
    if eccodes.codes_get(handle, 'gridType') != 'regular_ll':
        raise asv.Error("Seules les grilles régulières lat/lon sont supportées.")
    if eccodes.codes_get(handle, 'iScansNegatively'):
        raise asv.Error("Les grilles parcourues d'est en ouest ne sont pas "
                        "supportées.")

    ni = eccodes.codes_get(handle, 'Ni')
    nj = eccodes.codes_get(handle, 'Nj')
    di = eccodes.codes_get_double(handle, 'iDirectionIncrementInDegrees')
    dj = eccodes.codes_get_double(handle, 'jDirectionIncrementInDegrees')
    lat_first = eccodes.codes_get_double(handle, 'latitudeOfFirstGridPointInDegrees')
    lon_first = eccodes.codes_get_double(handle, 'longitudeOfFirstGridPointInDegrees')
    values = eccodes.codes_get_values(handle).reshape(nj, ni)

    # Lignes ordonnées du nord au sud
    lat_north = lat_first
    if eccodes.codes_get(handle, 'jScansPositively'):
        values = values[::-1, :]
        lat_north = lat_first + (nj - 1) * dj

    lon_min, lon_max, lat_min, lat_max = domain
    lats = lat_max - np.arange(int(round((lat_max - lat_min) / dj)) + 1) * dj
    lons = lon_min + np.arange(int(round((lon_max - lon_min) / di)) + 1) * di

    rows = np.rint((lat_north - lats) / dj).astype(int)
    if rows.min() < 0 or rows.max() >= nj:
        raise asv.Error("Le domaine CEP dépasse la grille des données.")

    offsets = (lons - lon_first) % 360 / di
    cols = np.rint(offsets).astype(int)
    is_global = abs(ni * di - 360) < 1e-6
    if is_global:
        cols %= ni
    if np.abs(offsets - np.rint(offsets)).max() > 1e-6 or cols.max() >= ni:
        raise asv.Error("Le domaine CEP n'est pas aligné sur la grille des données.")

    grid = {
        'Ni': len(lons),
        'Nj': len(lats),
        'lat_first': lat_max,
        'lat_last': lats[-1],
        'lon_first': lon_min,
        'lon_last': lons[-1],
        'di': di,
        'dj': dj,
    }
    return values[np.ix_(rows, cols)], grid


def _set_grid(eccodes, output, grid):
    # Les longitudes GRIB2 sont positives (0 à 360°)
    lon_first = grid['lon_first'] % 360
    lon_last = grid['lon_last'] % 360
    eccodes.codes_set(output, 'Ni', grid['Ni'])
    eccodes.codes_set(output, 'Nj', grid['Nj'])
    eccodes.codes_set(output, 'latitudeOfFirstGridPointInDegrees', grid['lat_first'])
    eccodes.codes_set(output, 'longitudeOfFirstGridPointInDegrees', lon_first)
    eccodes.codes_set(output, 'latitudeOfLastGridPointInDegrees', grid['lat_last'])
    eccodes.codes_set(output, 'longitudeOfLastGridPointInDegrees', lon_last)
    eccodes.codes_set(output, 'iDirectionIncrementInDegrees', grid['di'])
    eccodes.codes_set(output, 'jDirectionIncrementInDegrees', grid['dj'])
    eccodes.codes_set(output, 'iScansNegatively', 0)
    eccodes.codes_set(output, 'jScansPositively', 0)
