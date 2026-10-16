import json

import pytest

import atmoswing_vigicrues as asv


@pytest.fixture
def local_files(tmp_path):
    """Exports locaux : JSON réussi, JSON en erreur, et fichier non JSON."""
    files = {
        'ok.json': json.dumps({'status': 0, 'data': 'résultats'}),
        'error.json': json.dumps({'status': 200, 'data': None}),
        'other.json': json.dumps(['sans', 'statut']),
        'forecast.nc': 'données netcdf',
    }
    paths = {}
    for name, content in files.items():
        path = tmp_path / name
        path.write_text(content, encoding='utf-8')
        paths[name] = str(path)
    return paths


def size(path):
    with open(path, 'rb') as f:
        return len(f.read())


def test_successful_export_with_same_size_is_kept(local_files):
    path = local_files['ok.json']
    assert not asv.Dissemination._must_replace(path, size(path))


def test_successful_export_replaces_different_remote_copy(local_files):
    path = local_files['ok.json']
    assert asv.Dissemination._must_replace(path, size(path) - 10)


def test_successful_export_replaces_remote_copy_of_unknown_size(local_files):
    assert asv.Dissemination._must_replace(local_files['ok.json'], None)


def test_export_with_error_is_always_replaced(local_files):
    path = local_files['error.json']
    assert asv.Dissemination._must_replace(path, size(path))


@pytest.mark.parametrize('name', ['forecast.nc', 'other.json'])
def test_files_without_status_are_never_replaced(local_files, name):
    assert not asv.Dissemination._must_replace(local_files[name], None)
    assert not asv.Dissemination._must_replace(local_files[name], 1)
