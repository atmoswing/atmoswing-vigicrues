import logging
import os
import sys
import types
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest
import requests

import atmoswing_vigicrues as asv
import atmoswing_vigicrues.preactions.download_ecmwf as download_ecmwf

DIR_PATH = os.path.dirname(os.path.abspath(__file__))

has_dependencies = download_ecmwf.has_ecmwf_opendata and asv.has_eccodes
requires_eccodes = pytest.mark.skipif(not asv.has_eccodes,
                                      reason="Nécessite eccodes.")


class FakeClient:
    """Client ecmwf-opendata factice qui enregistre les requêtes."""

    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.session = requests.Session()
        self.requests = []
        self.fail_on = None
        FakeClient.instances.append(self)

    def retrieve(self, request, target):
        self.requests.append(request)
        # Comme le client réel : barre de progression et message d'attribution
        print("By downloading data from the ECMWF open data dataset...")
        print("<multiple>:  10%|█", file=sys.stderr)
        if request['param'] == self.fail_on:
            raise RuntimeError("404 Client Error: Not Found")
        with open(target, 'wb') as f:
            f.write(b'GRIB')


@pytest.fixture
def fake_backend(monkeypatch):
    """Remplace le client et le découpage des champs (aucune dépendance requise)."""
    FakeClient.instances = []
    backend = types.SimpleNamespace(missing_fields=0, crops=[])

    def fake_crop(source, target, domain):
        backend.crops.append(domain)
        with open(target, 'wb') as f:
            f.write(b'GRIB')
        request = FakeClient.instances[-1].requests[-1]
        count = len(request['step']) * len(request.get('levelist', [0]))
        return count - backend.missing_fields

    monkeypatch.setattr(download_ecmwf, 'has_ecmwf_opendata', True)
    monkeypatch.setattr(asv, 'has_eccodes', True)
    monkeypatch.setattr(download_ecmwf, 'Client', FakeClient, raising=False)
    monkeypatch.setattr(download_ecmwf, 'crop_grib', fake_crop)
    return backend


@pytest.fixture
def options(tmp_path):
    return {'output_dir': str(tmp_path / 'CEP')}


def client():
    assert len(FakeClient.instances) == 1
    return FakeClient.instances[0]


def output_file(options, name):
    return os.path.join(options['output_dir'], '2026', '10', '22', name)


def test_download_writes_files_in_date_structure(fake_backend, options):
    action = asv.DownloadEcmwfData('Download ECMWF', options)
    assert action.run(datetime(2026, 10, 22, 12))
    for name in ['CEP_Z_202610221200.grb', 'CEP_R_202610221200.grb',
                 'CEP_TCWV_202610221200.grb']:
        assert os.path.isfile(output_file(options, name))
    assert not [f for f in os.listdir(output_file(options, ''))
                if f.endswith('.part')]


def test_download_requests(fake_backend, options):
    options['variables'] = ['Z', 'tcwv']
    options['levels'] = [500, 1000]
    options['lead_time_max'] = 24
    action = asv.DownloadEcmwfData('Download ECMWF', options)
    assert action.run(datetime(2026, 10, 22, 0))
    steps = [0, 6, 12, 18, 24]
    assert client().requests == [
        {'date': '20261022', 'time': 0, 'stream': 'oper', 'type': 'fc',
         'step': steps, 'param': 'z', 'levtype': 'pl', 'levelist': [500, 1000]},
        {'date': '20261022', 'time': 0, 'stream': 'oper', 'type': 'fc',
         'step': steps, 'param': 'tcwv', 'levtype': 'sfc'}]
    assert fake_backend.crops == [[-20, 30, 20, 65]] * 2


def test_client_options(fake_backend, options):
    options['source'] = 'aws'
    options['resolution'] = 0.1
    options['proxies'] = {'http': '', 'https': 'http://proxy:3128'}
    action = asv.DownloadEcmwfData('Download ECMWF', options)
    assert action.run(datetime(2026, 10, 22, 0))
    assert client().kwargs == {'source': 'aws', 'resol': '0p1',
                               'maximum_retries': 3, 'retry_after': 30}
    assert client().session.proxies == {'https': 'http://proxy:3128'}
    assert client().session.get_adapter('https://data.ecmwf.int').timeout == 120


def test_requests_get_a_default_timeout(monkeypatch):
    sent = []
    monkeypatch.setattr(requests.adapters.HTTPAdapter, 'send',
                        lambda self, request, **kwargs: sent.append(kwargs))
    adapter = download_ecmwf._TimeoutAdapter(45)
    adapter.send(None, timeout=None)
    adapter.send(None, timeout=5)
    assert [kwargs['timeout'] for kwargs in sent] == [45, 5]


def test_client_output_does_not_pollute_the_log(fake_backend, options, capfd):
    action = asv.DownloadEcmwfData('Download ECMWF', options)
    assert action.run(datetime(2026, 10, 22, 0))
    captured = capfd.readouterr()
    assert captured.out == '' and captured.err == ''


def test_connection_limit_notice_is_filtered(caplog):
    client_logger = logging.getLogger('ecmwf.opendata.utils')
    client_logger.warning("To ensure the stability of our systems ...")
    client_logger.warning("No index entries for %s=%s", 'levelist', '450')
    assert caplog.messages == ["No index entries for levelist=450"]


@pytest.mark.skipif(not download_ecmwf.has_ecmwf_opendata,
                    reason="Nécessite ecmwf-opendata.")
def test_real_client_creation_is_quiet(caplog, monkeypatch):
    import ecmwf.opendata.utils
    monkeypatch.setattr(ecmwf.opendata.utils, 'ONCE', set())
    download_ecmwf.Client(source='ecmwf')
    assert not [m for m in caplog.messages if "stability" in m]


def test_levels_by_variable(fake_backend, options):
    options['levels'] = {'z': [500, 1000], 'R': [850]}
    action = asv.DownloadEcmwfData('Download ECMWF', options)
    assert action.run(datetime(2026, 10, 22, 0))
    levels = {r['param']: r.get('levelist') for r in client().requests}
    assert levels == {'z': [500, 1000], 'r': [850], 'tcwv': None}


def test_steps_beyond_144h_are_6_hourly(fake_backend, options):
    options['lead_time_max'] = 168
    options['time_step'] = 3
    action = asv.DownloadEcmwfData('Download ECMWF', options)
    assert action.steps == list(range(0, 145, 3)) + [150, 156, 162, 168]


def test_default_lead_times(fake_backend, options):
    action = asv.DownloadEcmwfData('Download ECMWF', options)
    assert action.steps == list(range(0, 193, 6))


def test_full_lead_time_range(fake_backend, options):
    options['lead_time_max'] = 360
    action = asv.DownloadEcmwfData('Download ECMWF', options)
    assert action.steps == list(range(0, 361, 6))


def test_existing_files_are_skipped(fake_backend, options):
    action = asv.DownloadEcmwfData('Download ECMWF', options)
    existing = output_file(options, 'CEP_Z_202610220000.grb')
    os.makedirs(os.path.dirname(existing))
    with open(existing, 'wb') as f:
        f.write(b'existant')
    assert action.run(datetime(2026, 10, 22, 0))
    assert [r['param'] for r in client().requests] == ['r', 'tcwv']
    with open(existing, 'rb') as f:
        assert f.read() == b'existant'


def test_other_run_hours_fail(fake_backend, options):
    action = asv.DownloadEcmwfData('Download ECMWF', options)
    assert not action.run(datetime(2026, 10, 22, 6))
    assert not FakeClient.instances


def test_incomplete_download_is_not_kept(fake_backend, options):
    fake_backend.missing_fields = 1
    action = asv.DownloadEcmwfData('Download ECMWF', options)
    assert not action.run(datetime(2026, 10, 22, 0))
    assert os.listdir(output_file(options, '')) == []


def test_download_resumes_after_failure(fake_backend, options):
    action = asv.DownloadEcmwfData('Download ECMWF', options)
    action._get_client().fail_on = 'r'
    assert not action.run(datetime(2026, 10, 22, 0))
    assert os.listdir(output_file(options, '')) == ['CEP_Z_202610220000.grb']

    action._get_client().fail_on = None
    assert action.run(datetime(2026, 10, 22, 0))
    assert [r['param'] for r in client().requests] == ['z', 'r', 'r', 'tcwv']
    assert len(os.listdir(output_file(options, ''))) == 3


@pytest.mark.parametrize('key, value, match', [
    ('variables', ['z', 'pv'], "pv"),
    ('resolution', 0.5, "résolution"),
    ('lead_time_max', 366, "360"),
    ('time_step', 4, "pas de temps"),
    ('domain', [-20, 30, 25], "4 valeurs"),
    ('domain', [-20.1, 30, 25, 65], "multiples"),
    ('domain', [30, -20, 25, 65], "pas valide"),
    ('levels', {'z': [500]}, "niveaux")])
def test_invalid_options_are_rejected(fake_backend, options, key, value, match):
    options[key] = value
    with pytest.raises(asv.Error, match=match):
        asv.DownloadEcmwfData('Download ECMWF', options)


def test_missing_client_package_is_reported(fake_backend, options, monkeypatch):
    monkeypatch.setattr(download_ecmwf, 'has_ecmwf_opendata', False)
    with pytest.raises(ImportError, match="ecmwf-opendata"):
        asv.DownloadEcmwfData('Download ECMWF', options)


def test_missing_eccodes_is_reported(fake_backend, options, monkeypatch):
    monkeypatch.setattr(asv, 'has_eccodes', False)
    with pytest.raises(ImportError, match="eccodes"):
        asv.DownloadEcmwfData('Download ECMWF', options)


def write_global_grib2(path, short_name, levels, steps, lon_first=0.0,
                       south_to_north=False):
    """Fichier GRIB2 global (1°) dont les valeurs encodent la position."""
    eccodes = asv.eccodes
    sample = 'regular_ll_pl_grib2' if levels else 'regular_ll_sfc_grib2'
    lats = np.arange(90, -91, -1.0)
    lons = lon_first + np.arange(360)
    if south_to_north:
        lats = lats[::-1]
    lon_values = (lons + 180) % 360 - 180
    values = lats[:, None] * 1000 + lon_values[None, :]

    with open(path, 'wb') as f:
        for step in steps:
            for level in levels or [None]:
                h = eccodes.codes_grib_new_from_samples(sample)
                eccodes.codes_set(h, 'shortName', short_name)
                eccodes.codes_set(h, 'dataDate', 20261022)
                eccodes.codes_set(h, 'dataTime', 1200)
                eccodes.codes_set(h, 'stepUnits', 'h')
                eccodes.codes_set(h, 'step', step)
                if level is not None:
                    eccodes.codes_set(h, 'typeOfLevel', 'isobaricInhPa')
                    eccodes.codes_set(h, 'level', level)
                eccodes.codes_set(h, 'Ni', 360)
                eccodes.codes_set(h, 'Nj', 181)
                eccodes.codes_set(h, 'iDirectionIncrementInDegrees', 1.0)
                eccodes.codes_set(h, 'jDirectionIncrementInDegrees', 1.0)
                eccodes.codes_set(h, 'jScansPositively', int(south_to_north))
                eccodes.codes_set(h, 'latitudeOfFirstGridPointInDegrees', lats[0])
                eccodes.codes_set(h, 'latitudeOfLastGridPointInDegrees', lats[-1])
                eccodes.codes_set(h, 'longitudeOfFirstGridPointInDegrees', lons[0])
                eccodes.codes_set(h, 'longitudeOfLastGridPointInDegrees', lons[-1])
                eccodes.codes_set(h, 'bitsPerValue', 24)
                eccodes.codes_set_values(h, values.flatten())
                eccodes.codes_write(h, f)
                eccodes.codes_release(h)


def read_grib(path):
    eccodes = asv.eccodes
    fields = []
    with open(path, 'rb') as f:
        while True:
            h = eccodes.codes_grib_new_from_file(f)
            if h is None:
                break
            keys = {k: eccodes.codes_get(h, k) for k in [
                'edition', 'centre', 'paramId', 'shortName', 'typeOfLevel', 'level',
                'dataDate', 'dataTime', 'step', 'Ni', 'Nj', 'packingType',
                'latitudeOfFirstGridPointInDegrees',
                'longitudeOfFirstGridPointInDegrees',
                'latitudeOfLastGridPointInDegrees',
                'longitudeOfLastGridPointInDegrees']}
            keys['values'] = eccodes.codes_get_values(h).reshape(keys['Nj'],
                                                                 keys['Ni'])
            eccodes.codes_release(h)
            fields.append(keys)
    return fields


def expected_values(domain):
    lon_min, lon_max, lat_min, lat_max = domain
    lats = np.arange(lat_max, lat_min - 1, -1.0)
    lons = np.arange(lon_min, lon_max + 1, 1.0)
    return lats[:, None] * 1000 + lons[None, :]


@requires_eccodes
def test_crop_rejects_misaligned_domain(tmp_path):
    source = tmp_path / 'z.grib2'
    write_global_grib2(source, 'z', [500], [0])
    with pytest.raises(asv.Error, match="aligné"):
        download_ecmwf.crop_grib(source, tmp_path / 'out.grb', [-10.5, 5, 40, 50])


@requires_eccodes
@pytest.mark.parametrize('lon_first', [0.0, -180.0])
def test_crop_pressure_levels(tmp_path, lon_first):
    source = tmp_path / 'z.grib2'
    target = tmp_path / 'CEP_Z_202610221200.grb'
    write_global_grib2(source, 'z', [500, 1000], [0, 6], lon_first=lon_first)
    domain = [-10, 5, 40, 50]
    assert download_ecmwf.crop_grib(source, target, domain) == 4

    fields = read_grib(target)
    assert [(f['step'], f['level']) for f in fields] == [
        (0, 500), (0, 1000), (6, 500), (6, 1000)]
    for field in fields:
        assert (field['edition'], field['paramId'], field['shortName']) == \
            (2, 129, 'z')
        assert field['typeOfLevel'] == 'isobaricInhPa'
        assert (field['dataDate'], field['dataTime']) == (20261022, 1200)
        assert (field['Ni'], field['Nj']) == (16, 11)
        assert field['latitudeOfFirstGridPointInDegrees'] == 50
        # Longitudes GRIB2 positives : le domaine commence à 350° (-10°)
        assert field['longitudeOfFirstGridPointInDegrees'] == 350
        assert field['latitudeOfLastGridPointInDegrees'] == 40
        assert field['longitudeOfLastGridPointInDegrees'] == 5
        np.testing.assert_allclose(field['values'], expected_values(domain),
                                   atol=1)


@requires_eccodes
def test_crop_surface_field_scanned_northwards(tmp_path):
    source = tmp_path / 'tcwv.grib2'
    target = tmp_path / 'CEP_TCWV_202610221200.grb'
    write_global_grib2(source, 'tcwv', None, [12], south_to_north=True)
    domain = [-6, -5, 47, 48]
    assert download_ecmwf.crop_grib(source, target, domain) == 1

    field = read_grib(target)[0]
    assert (field['edition'], field['paramId'], field['step']) == (2, 137, 12)
    np.testing.assert_allclose(field['values'], expected_values(domain), atol=1)


@pytest.mark.skipif(not asv.preactions.transform_grib.has_toolbox,
                    reason="Nécessite netCDF4, eccodes et atmoswing-toolbox.")
def test_cropped_file_can_be_transformed(tmp_path):
    input_dir = tmp_path / 'CEP' / '2026' / '10' / '22'
    input_dir.mkdir(parents=True)
    source = tmp_path / 'z.grib2'
    write_global_grib2(source, 'z', [500, 1000], [0, 6, 12])
    download_ecmwf.crop_grib(source, input_dir / 'CEP_Z_202610221200.grb',
                             [-10, 5, 40, 50])

    action = asv.TransformEcmwfData('Transform ECMWF data', {
        'input_dir': str(tmp_path / 'CEP'),
        'output_dir': str(tmp_path / 'generic'),
        'variables': ['Z']})
    assert action.run(datetime(2026, 10, 22, 12))
    assert len(os.listdir(tmp_path / 'generic')) == 1


@pytest.mark.network
@pytest.mark.skipif(not has_dependencies,
                    reason="Nécessite ecmwf-opendata et eccodes.")
def test_download_from_ecmwf_open_data(tmp_path):
    options = {'output_dir': str(tmp_path), 'variables': ['z', 'tcwv'],
               'levels': [500, 1000], 'lead_time_max': 12,
               'domain': [-5, 5, 40, 45]}
    action = asv.DownloadEcmwfData('Download ECMWF', options)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    date = datetime(yesterday.year, yesterday.month, yesterday.day, 0)
    assert action.run(date)

    local_dir = asv.build_date_dir_structure(str(tmp_path), date)
    run = date.strftime('%Y%m%d%H')
    z = read_grib(local_dir / f'CEP_Z_{run}00.grb')
    tcwv = read_grib(local_dir / f'CEP_TCWV_{run}00.grb')
    assert len(z) == 6 and len(tcwv) == 3
    assert {f['paramId'] for f in z} == {129}
    assert (z[0]['edition'], z[0]['Ni'], z[0]['Nj']) == (2, 41, 21)
    assert {f['paramId'] for f in tcwv} == {137}
    # Compression des données ouvertes conservée
    assert z[0]['packingType'] == 'grid_ccsds'
    # Géopotentiel à 500 hPa : environ 5000 à 6000 m (x 9.81)
    z500 = [f for f in z if f['level'] == 500][0]['values']
    assert 45000 < z500.mean() < 60000

    # Les fichiers existants ne sont pas téléchargés à nouveau
    assert action.run(date)
