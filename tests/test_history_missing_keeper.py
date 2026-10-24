'''F3: a missing historical original has to be proven, not assumed.

The duplicate cleanup removed the redundant copies of archived runs and kept
the canonical asset in the library. A history scope that only saw an emptied
``images`` directory used to skip the whole run and declare the bytes covered.
Every missing byte set now has to resolve to a keeper whose SHA and
decodability are proven, and a run without one blocks the project's duplicate
scope instead of reporting a complete duplicate check.
'''
from __future__ import annotations

import hashlib
import json

import pytest
from PIL import Image

from ref_lab.collection_history import (HistoricalBytesMissing, HistoryIntegrityBlocked,
                                        collect_history_scope)
from conftest import library_db


@pytest.fixture(autouse=True)
def _no_production_data(monkeypatch):
    """A synthetic fixture must never read the exported production library."""
    monkeypatch.delenv('LAB_DATA_DIR', raising=False)
    monkeypatch.delenv('LAB_COLLECTION_HISTORY_DIR', raising=False)


def photo(path, color=(80, 90, 100), size=(96, 128)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new('RGB', size, color).save(path, format='PNG')
    return path


def sha_of(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_with_rows(run, rows):
    run.mkdir(parents=True, exist_ok=True)
    (run / 'received.json').write_text(json.dumps(rows), encoding='utf8')


def keeper(root, path, sha=None):
    # Store the canonical copy of these bytes in the library asset store.
    sha = sha or sha_of(path)
    target = root / 'data' / 'assets' / sha[:2] / sha / 'original.png'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(path.read_bytes())
    return target.resolve()


def attributed(root, job='old', project='proj-a'):
    library_db(root / 'data', jobs=[(job, project)])


def scope(root, current=None, *, project='proj-a', skipped=None, history_roots=()):
    return collect_history_scope(root, current or root / '.local' / 'current', project,
                                 history_roots=history_roots, skipped=skipped)


def test_missing_original_resolves_to_keeper(tmp_path):
    root = tmp_path / 'root'
    source = photo(root / 'source.png', (40, 80, 120))
    sha = sha_of(source)
    kept = keeper(root, source, sha)
    source.unlink()
    run = root / '.local' / 'collection-runs' / 'old'
    run_with_rows(run, [{'original_path': str(run / 'images' / (sha + '.png')),
                         'asset_sha': sha}])
    attributed(root)
    skipped = []
    paths = set(scope(root, skipped=skipped).paths)
    assert kept in paths, 'the retained copy is the history for those bytes'
    assert len(skipped) == 1
    assert 'verified keeper' in skipped[0]['reason']
    assert skipped[0]['received_rows'] == 1


def test_missing_original_without_keeper_blocks(tmp_path):
    root = tmp_path / 'root'
    source = photo(root / 'source.png', (40, 80, 120))
    sha = sha_of(source)
    source.unlink()
    run = root / '.local' / 'collection-runs' / 'old'
    run_with_rows(run, [{'original_path': str(run / 'images' / (sha + '.png')),
                         'asset_sha': sha}])
    attributed(root)
    with pytest.raises(HistoricalBytesMissing):
        scope(root, skipped=[])


def test_emptied_run_still_processes_other_rows(tmp_path):
    root = tmp_path / 'root'
    gone = photo(root / 'gone.png', (40, 80, 120))
    gone_sha = sha_of(gone)
    gone_keeper = keeper(root, gone, gone_sha)
    gone.unlink()
    run = root / '.local' / 'collection-runs' / 'old'
    kept_source = photo(run / 'images' / 'kept.png', (200, 30, 90))
    kept = keeper(root, kept_source)
    run_with_rows(run, [{'original_path': str(run / 'images' / (gone_sha + '.png')),
                         'asset_sha': gone_sha},
                        {'original_path': str(kept_source), 'asset_sha': sha_of(kept_source)}])
    attributed(root)
    paths = set(scope(root, skipped=[]).paths)
    assert gone_keeper in paths
    assert kept_source.resolve() in paths, 'the surviving row of the run is still history'


def test_missing_child_without_keeper_blocks(tmp_path):
    root = tmp_path / 'root'
    tile = photo(root / 'tile.png', (240, 20, 20), (64, 64))
    tile_sha = sha_of(tile)
    run = root / '.local' / 'collection-runs' / 'old'
    parent = photo(run / 'images' / 'parent.png', (10, 120, 60))
    parent_sha = sha_of(parent)
    run_with_rows(run, [{'original_path': str(parent), 'asset_sha': parent_sha}])
    (run / 'derived.json').write_text(json.dumps({'items': {parent_sha: {
        'parent_sha': parent_sha, 'status': 'split_ok',
        'children': [{'child_sha': tile_sha, 'path': str(run / 'derived' / (tile_sha + '.png')),
                      'status': 'valid'}]}}}), encoding='utf8')
    tile.unlink()
    attributed(root)
    with pytest.raises(HistoricalBytesMissing):
        scope(root, skipped=[])


def test_missing_child_resolves_to_keeper(tmp_path):
    root = tmp_path / 'root'
    tile = photo(root / 'tile.png', (240, 20, 20), (64, 64))
    tile_sha = sha_of(tile)
    kept = keeper(root, tile, tile_sha)
    run = root / '.local' / 'collection-runs' / 'old'
    parent = photo(run / 'images' / 'parent.png', (10, 120, 60))
    parent_sha = sha_of(parent)
    run_with_rows(run, [{'original_path': str(parent), 'asset_sha': parent_sha}])
    (run / 'derived.json').write_text(json.dumps({'items': {parent_sha: {
        'parent_sha': parent_sha, 'status': 'split_ok',
        'children': [{'child_sha': tile_sha, 'path': str(run / 'derived' / (tile_sha + '.png')),
                      'status': 'valid'}]}}}), encoding='utf8')
    tile.unlink()
    attributed(root)
    assert kept in set(scope(root, skipped=[]).paths)


def test_a_corrupt_keeper_blocks(tmp_path):
    root = tmp_path / 'root'
    source = photo(root / 'source.png', (40, 80, 120))
    sha = sha_of(source)
    keeper(root, source, sha)
    source.unlink()
    kept = root / 'data' / 'assets' / sha[:2] / sha / 'original.png'
    kept.write_bytes(b'not the image anymore')
    run = root / '.local' / 'collection-runs' / 'old'
    run_with_rows(run, [{'original_path': str(run / 'images' / (sha + '.png')),
                         'asset_sha': sha}])
    attributed(root)
    with pytest.raises(HistoryIntegrityBlocked, match='No verifiable keeper'):
        scope(root, skipped=[])


def test_current_run_and_fixtures_stay_out(tmp_path):
    root = tmp_path / 'root'
    current = root / '.local' / 'collection-runs' / 'current'
    current_photo = photo(current / 'images' / 'current.png', (200, 40, 90))
    run_with_rows(current, [{'original_path': str(current_photo), 'asset_sha': sha_of(current_photo)}])
    fixture = photo(root / '.local' / 'fixtures' / 'run' / 'images' / 'synthetic.png', (9, 9, 9))
    run_with_rows(root / '.local' / 'fixtures' / 'run',
                  [{'original_path': str(fixture), 'asset_sha': sha_of(fixture)}])
    attributed(root, job='current')
    paths = set(scope(root, current=current, skipped=[]).paths)
    assert current_photo.resolve() not in paths
    assert fixture.resolve() not in paths


def test_archived_run_under_backups_stays(tmp_path):
    root = tmp_path / 'root'
    archived_run = root / '.local' / 'backups' / 'snapshot' / 'job-diag' / 'current'
    archived = photo(archived_run / 'images' / 'one.png', (80, 90, 100))
    run_with_rows(archived_run, [{'original_path': str(archived), 'asset_sha': sha_of(archived)}])
    attributed(root, job='job-diag')
    paths = set(scope(root, skipped=[]).paths)
    assert archived.resolve() in paths


def test_keeper_in_a_later_history_root_is_found(tmp_path):
    '''The keeper may live in any authorized root, not only the first one.'''
    primary = tmp_path / 'primary'
    secondary = tmp_path / 'secondary'
    source = photo(primary / 'source.png', (40, 80, 120))
    sha = sha_of(source)
    kept = keeper(secondary, source, sha)
    source.unlink()
    run = primary / '.local' / 'collection-runs' / 'old'
    run_with_rows(run, [{'original_path': str(run / 'images' / (sha + '.png')),
                         'asset_sha': sha}])
    attributed(primary)
    paths = set(scope(primary, history_roots=[secondary], skipped=[]).paths)
    assert kept in paths, 'the later root proves the missing bytes'


def test_child_keeper_in_a_later_history_root_is_found(tmp_path):
    '''A missing tile is proven by the same rule, in any authorized root.'''
    primary = tmp_path / 'primary'
    secondary = tmp_path / 'secondary'
    tile = photo(primary / 'tile.png', (240, 20, 20), (64, 64))
    tile_sha = sha_of(tile)
    kept = keeper(secondary, tile, tile_sha)
    run = primary / '.local' / 'collection-runs' / 'old'
    parent = photo(run / 'images' / 'parent.png', (10, 120, 60))
    parent_sha = sha_of(parent)
    run_with_rows(run, [{'original_path': str(parent), 'asset_sha': parent_sha}])
    (run / 'derived.json').write_text(json.dumps({'items': {parent_sha: {
        'parent_sha': parent_sha, 'status': 'split_ok',
        'children': [{'child_sha': tile_sha, 'path': str(run / 'derived' / (tile_sha + '.png')),
                      'status': 'valid'}]}}}), encoding='utf8')
    tile.unlink()
    attributed(primary)
    paths = set(scope(primary, history_roots=[secondary], skipped=[]).paths)
    assert kept in paths
