import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

import ref_lab.collection_history as collection_history
from ref_lab.collection_history import ImageHistory, collect_history_scope
from conftest import library_db


def photo(path, color):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new('RGB', (96, 128), color).save(path, format='PNG')
    return path


def received(run, original):
    run.mkdir(parents=True, exist_ok=True)
    (run / 'received.json').write_text(json.dumps([{
        'original_path': str(original),
        'asset_sha': hashlib.sha256(original.read_bytes()).hexdigest(),
    }]), encoding='utf8')


def sha_of(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_known_sha_is_an_exact_duplicate_before_lazy_fingerprints_finish(tmp_path):
    source = photo(tmp_path / 'source.png', (80, 40, 140))
    raw = source.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    stored = tmp_path / 'assets' / 'ab' / sha / 'original.png'
    stored.parent.mkdir(parents=True)
    stored.write_bytes(raw)
    history = ImageHistory([stored], cache_path=tmp_path / 'cache.json', lazy=True,
                           library_keepers={sha: stored})
    try:
        assert history.known_count == 1
        duplicate = history.match(source)
        assert duplicate == {'duplicate_of': sha, 'reason': 'same_bytes'}
    finally:
        history.close(wait=True, timeout=5)


def test_cached_history_matches_uncached_and_hot_scan_skips_decode(tmp_path, monkeypatch):
    first = photo(tmp_path / 'history' / 'first.png', (60, 100, 140))
    second = photo(tmp_path / 'history' / 'second.png', (170, 100, 35))
    paths = [first, second]
    cache = tmp_path / '.local' / 'history-cache.json'
    uncached = ImageHistory(paths)
    cold = ImageHistory(paths, cache_path=cache)
    assert cold.records == uncached.records
    payload = json.loads(cache.read_text(encoding='utf8'))
    assert payload['schema_version'] == collection_history.CACHE_SCHEMA_VERSION
    assert any(str(first.resolve()) == key for key in payload['files'])
    assert all(len(entry['sha']) == 64 for entry in payload['files'].values())

    reencoded = tmp_path / 'reencoded.jpg'
    with Image.open(first) as image:
        image.save(reencoded, quality=95)
    unique = photo(tmp_path / 'unique.png', (245, 5, 245))
    with monkeypatch.context() as patch:
        patch.setattr(collection_history.Image, 'open', lambda *a, **k: pytest.fail('warm cache decoded an unchanged original'))
        hot = ImageHistory(paths, cache_path=cache)
    assert hot.records == uncached.records

    rows = [first, reencoded, unique]
    results = []
    for path in rows:
        expected = uncached.consider(path)
        assert cold.consider(path) == expected
        assert hot.consider(path) == expected
        assert cold.records == hot.records == uncached.records
        results.append(expected)
    assert [row['reason'] if row else None for row in results] == ['same_bytes', 'near_duplicate', None]


def test_corrupt_cache_falls_back_to_decode_and_rebuilds(tmp_path, monkeypatch):
    original = photo(tmp_path / 'original.png', (40, 80, 120))
    cache = tmp_path / 'cache.json'
    cache.write_text('{broken', encoding='utf8')
    expected = ImageHistory([original])
    open_image = collection_history.Image.open
    calls = 0

    def counted_open(*args, **kwargs):
        nonlocal calls
        calls += 1
        return open_image(*args, **kwargs)

    monkeypatch.setattr(collection_history.Image, 'open', counted_open)
    repaired = ImageHistory([original], cache_path=cache)
    assert calls == 1
    assert repaired.records == expected.records
    assert json.loads(cache.read_text(encoding='utf8'))['schema_version'] == collection_history.CACHE_SCHEMA_VERSION

    with monkeypatch.context() as patch:
        patch.setattr(collection_history.Image, 'open', lambda *a, **k: pytest.fail('repaired cache was not reused'))
        assert ImageHistory([original], cache_path=cache).records == expected.records


def test_changed_original_bytes_invalidate_cache_by_sha(tmp_path):
    original = photo(tmp_path / 'original.png', (20, 60, 100))
    cache = tmp_path / 'cache.json'
    initial = ImageHistory([original], cache_path=cache)
    old_sha = next(iter(initial.records))

    photo(original, (230, 30, 210))
    expected = ImageHistory([original])
    changed = ImageHistory([original], cache_path=cache)
    assert next(iter(changed.records)) != old_sha
    assert changed.records == expected.records


def test_history_received_sha_binding_is_still_enforced_with_a_cache(tmp_path):
    root = tmp_path
    original = photo(root / '.local' / 'collection-runs' / 'job-a' / 'current' / 'images' / 'one.png', (80, 90, 100))
    received(root / '.local' / 'collection-runs' / 'job-a' / 'current', original)
    ImageHistory([original], cache_path=root / '.local' / 'history-cache.json')
    library_db(root / 'data', jobs=[('job-a', 'proj-a')])
    current = root / '.local' / 'current'
    scope = collect_history_scope(root, current, 'proj-a')
    assert original.resolve() in {Path(p).resolve() for p in scope.paths}

    photo(original, (200, 10, 160))
    with pytest.raises(ValueError, match='SHA changed'):
        collect_history_scope(root, current, 'proj-a')


def test_run_without_library_attribution_is_never_in_scope(tmp_path):
    root = tmp_path
    original = photo(root / '.local' / 'older' / 'images' / 'one.png', (80, 90, 100))
    received(root / '.local' / 'older', original)
    # An ad-hoc directory outside the collection-run shapes is never scanned:
    # bounded discovery cannot be widened into a whole-.local walk.
    unattributed = []
    scope = collect_history_scope(root, root / '.local' / 'current', 'proj-a', unattributed=unattributed)
    assert scope.paths == []
    assert unattributed == []
    assert (root / '.local' / 'older' / 'received.json').exists()


def test_archived_diagnostic_run_stays_in_its_project_duplicate_history(tmp_path):
    """Archiving a batch for evidence must not remove its received images from
    its own project's duplicate history: the same bytes may not be re-counted
    as new later."""
    root = tmp_path
    job = 'job-diag-1'
    archived_run = root / '.local' / 'backups' / 'snapshot-1' / job / 'current'
    archived = photo(archived_run / 'images' / 'one.png', (80, 90, 100))
    received(archived_run, archived)
    library_db(root / 'data', jobs=[(job, 'proj-a')])
    current = root / '.local' / 'current-job'
    scope = collect_history_scope(root, current, 'proj-a')
    assert archived.resolve() in {Path(p).resolve() for p in scope.paths}


def test_other_project_run_is_out_of_this_project_similar_scope(tmp_path):
    root = tmp_path
    mine = photo(root / '.local' / 'collection-runs' / 'job-a' / 'current' / 'images' / 'mine.png', (80, 90, 100))
    other = photo(root / '.local' / 'collection-runs' / 'job-b' / 'current' / 'images' / 'other.png', (10, 200, 30))
    received(root / '.local' / 'collection-runs' / 'job-a' / 'current', mine)
    received(root / '.local' / 'collection-runs' / 'job-b' / 'current', other)
    library_db(root / 'data', jobs=[('job-a', 'proj-a'), ('job-b', 'proj-b')])
    scope = collect_history_scope(root, root / '.local' / 'current', 'proj-a')
    assert mine.resolve() in {Path(p).resolve() for p in scope.paths}
    assert other.resolve() not in {Path(p).resolve() for p in scope.paths}
    # Same character name in another project does not merge scopes: only the
    # library-wide exact index covers the other run.
    assert sha_of(other) in scope.library_keepers


def test_failed_or_unimported_batches_of_this_project_stay_in_scope(tmp_path):
    root = tmp_path
    job = 'job-failed'
    run = root / '.local' / 'collection-runs' / job / 'current'
    original = photo(run / 'images' / 'kept.png', (90, 90, 200))
    received(run, original)
    library_db(root / 'data', jobs=[(job, 'proj-a')])
    scope = collect_history_scope(root, root / '.local' / 'current', 'proj-a')
    assert original.resolve() in {Path(p).resolve() for p in scope.paths}


def test_unattributed_runs_are_reported_and_kept_out_of_scope(tmp_path):
    root = tmp_path
    stray = photo(root / '.local' / 'collection-runs' / 'test-a22-probe' / 'current' / 'images' / 'probe.png', (200, 10, 10))
    received(root / '.local' / 'collection-runs' / 'test-a22-probe' / 'current', stray)
    job = 'job-a'
    mine = photo(root / '.local' / 'collection-runs' / job / 'current' / 'images' / 'mine.png', (5, 5, 200))
    received(root / '.local' / 'collection-runs' / job / 'current', mine)
    library_db(root / 'data', jobs=[(job, 'proj-a')])
    unattributed = []
    scope = collect_history_scope(root, root / '.local' / 'current', 'proj-a', unattributed=unattributed)
    assert stray.resolve() not in {Path(p).resolve() for p in scope.paths}
    assert mine.resolve() in {Path(p).resolve() for p in scope.paths}
    assert len(unattributed) == 1
    assert 'test-a22-probe' in unattributed[0]['run']
    assert (stray.parent.parent / 'received.json').exists()  # original record kept, not deleted
    assert sha_of(stray) not in scope.library_keepers  # never indexed for reuse either


def asset_copy(path, color):
    """Create an image and place it under its content-addressed store path."""
    source = photo(path.parent.parent.parent / 'staging' / (path.stem + '.png'), color)
    sha = sha_of(source)
    target = path.parent.parent / sha / 'original.png'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())
    return target


def test_library_references_join_the_project_scope_but_others_do_not(tmp_path):
    root = tmp_path
    mine = asset_copy(root / 'data' / 'assets' / 'aa' / 'placeholder' / 'original.png', (120, 40, 90))
    other = asset_copy(root / 'data' / 'assets' / 'bb' / 'placeholder' / 'original.png', (200, 200, 5))
    mine_sha = sha_of(mine)
    other_sha = sha_of(other)
    library_db(root / 'data', refs=[('proj-a', mine_sha), ('proj-b', other_sha)])
    scope = collect_history_scope(root, root / '.local' / 'current', 'proj-a')
    resolved = {Path(p).resolve() for p in scope.paths}
    assert mine.resolve() in resolved
    assert other.resolve() not in resolved
    assert other_sha in scope.library_keepers


def test_similar_scope_requires_a_project_identity(tmp_path):
    root = tmp_path
    with pytest.raises(collection_history.HistoryIntegrityBlocked):
        collect_history_scope(root, root / '.local' / 'current', '')


def test_exact_library_hit_is_reuse_not_duplicate(tmp_path):
    keeper = photo(tmp_path / 'data' / 'assets' / 'cc' / ('c' * 64) / 'original.png', (45, 140, 200))
    sha = sha_of(keeper)
    candidate = tmp_path / 'candidate.png'
    candidate.write_bytes(keeper.read_bytes())
    history = ImageHistory([], cache_path=tmp_path / 'cache.json', library_keepers={sha: keeper})
    try:
        duplicate = history.consider(candidate)
        assert duplicate == {'duplicate_of': sha, 'reason': 'same_bytes_library', 'reuse': True,
                             'keeper_path': str(keeper.resolve())}
        # After reuse the bytes belong to this project: a second copy is a repeat.
        second = tmp_path / 'second.png'
        second.write_bytes(keeper.read_bytes())
        repeat = history.consider(second)
        assert repeat == {'duplicate_of': sha, 'reason': 'same_bytes'}
        assert sha in history.known_shas
    finally:
        history.close(wait=True, timeout=5)


def test_exact_library_reuse_verifies_keeper_bytes(tmp_path):
    keeper = photo(tmp_path / 'data' / 'assets' / 'dd' / ('d' * 64) / 'original.png', (45, 140, 200))
    sha = sha_of(keeper)
    candidate = tmp_path / 'candidate.png'
    candidate.write_bytes(keeper.read_bytes())
    # A keeper whose bytes no longer match its content address is not reuse.
    photo(keeper, (250, 250, 250))
    history = ImageHistory([], cache_path=tmp_path / 'cache.json', library_keepers={sha: keeper})
    try:
        assert history.consider(candidate) is None
    finally:
        history.close(wait=True, timeout=5)


def test_project_exact_bytes_still_block_when_also_in_the_library(tmp_path):
    keeper = photo(tmp_path / 'data' / 'assets' / 'ee' / ('e' * 64) / 'original.png', (45, 140, 200))
    sha = sha_of(keeper)
    candidate = tmp_path / 'candidate.png'
    candidate.write_bytes(keeper.read_bytes())
    history = ImageHistory([keeper], cache_path=tmp_path / 'cache.json', library_keepers={sha: keeper})
    try:
        duplicate = history.consider(candidate)
        assert duplicate == {'duplicate_of': sha, 'reason': 'same_bytes'}
    finally:
        history.close(wait=True, timeout=5)


def test_near_duplicate_and_unique_results_are_unchanged(tmp_path):
    original = photo(tmp_path / 'history' / 'one.png', (60, 100, 140))
    reencoded = tmp_path / 'reencoded.jpg'
    with Image.open(original) as image:
        image.save(reencoded, quality=95)
    unique = photo(tmp_path / 'unique.png', (245, 5, 245))
    history = ImageHistory([original], cache_path=tmp_path / 'cache.json')
    try:
        assert history.consider(reencoded)['reason'] == 'near_duplicate'
        assert history.consider(unique) is None
    finally:
        history.close(wait=True, timeout=5)


def test_cache_write_failure_does_not_change_duplicate_results(tmp_path, monkeypatch):
    original = photo(tmp_path / 'original.png', (40, 80, 120))
    expected = ImageHistory([original])
    cache = tmp_path / '.local' / 'cache.json'

    def fail_replace(*args, **kwargs):
        raise OSError('read-only cache')

    monkeypatch.setattr(collection_history.os, 'replace', fail_replace)
    actual = ImageHistory([original], cache_path=cache)
    assert actual.records == expected.records
    assert not cache.exists()
    assert not list(cache.parent.glob('.*.tmp'))


def test_scope_report_counts_are_bound_to_the_project(tmp_path):
    root = tmp_path
    job = 'job-a'
    mine = photo(root / '.local' / 'collection-runs' / job / 'current' / 'images' / 'mine.png', (90, 90, 200))
    received(root / '.local' / 'collection-runs' / job / 'current', mine)
    other = photo(root / '.local' / 'collection-runs' / 'job-b' / 'current' / 'images' / 'other.png', (200, 100, 100))
    received(root / '.local' / 'collection-runs' / 'job-b' / 'current', other)
    library_db(root / 'data', jobs=[(job, 'proj-a'), ('job-b', 'proj-b')])
    scope = collect_history_scope(root, root / '.local' / 'current', 'proj-a')
    assert scope.report['project_id'] == 'proj-a'
    assert scope.report['runs']['project_runs'] == 1
    assert scope.report['runs']['attributed'] == 2
    assert scope.report['runs']['unattributed'] == 0
    assert scope.report['perceptual_paths'] == len(scope.paths)


def test_current_run_is_excluded_from_its_own_scope(tmp_path):
    root = tmp_path
    job = 'job-a'
    current = root / '.local' / 'collection-runs' / job / 'current'
    mine = photo(current / 'images' / 'mine.png', (90, 90, 200))
    received(current, mine)
    library_db(root / 'data', jobs=[(job, 'proj-a')])
    scope = collect_history_scope(root, current, 'proj-a')
    assert mine.resolve() not in {Path(p).resolve() for p in scope.paths}


def test_explicit_history_roots_are_attributed_by_their_own_library(tmp_path, monkeypatch):
    monkeypatch.delenv('LAB_DATA_DIR', raising=False)
    monkeypatch.delenv('LAB_COLLECTION_HISTORY_DIR', raising=False)
    daily = tmp_path / 'daily'
    worktree = daily / '.local' / 'worktrees' / 'finalization' / 'root'
    performance = daily / '.local' / 'worktrees' / 'performance' / 'root'
    parent_photo = photo(daily / '.local' / 'collection-runs' / 'job-parent' / 'current' / 'images' / 'parent.png', (20, 80, 120))
    received(daily / '.local' / 'collection-runs' / 'job-parent' / 'current', parent_photo)
    performance_photo = photo(performance / '.local' / 'collection-runs' / 'job-perf' / 'current' / 'images' / 'performance.png', (130, 80, 20))
    received(performance / '.local' / 'collection-runs' / 'job-perf' / 'current', performance_photo)
    current = worktree / '.local' / 'current-job'
    current_photo = photo(current / 'images' / 'current.png', (200, 40, 90))
    received(current, current_photo)
    # A synthetic directory outside the collection-run shapes is never even
    # scanned; a probe directory under collection-runs is reported, not used.
    fixture_photo = photo(daily / '.local' / 'fixtures' / 'fixture-run' / 'images' / 'synthetic.png', (200, 200, 40))
    received(daily / '.local' / 'fixtures' / 'fixture-run', fixture_photo)
    probe_photo = photo(daily / '.local' / 'collection-runs' / 'pytest-probe-x' / 'current' / 'images' / 'probe.png', (250, 10, 10))
    received(daily / '.local' / 'collection-runs' / 'pytest-probe-x' / 'current', probe_photo)

    library_db(daily / 'data', jobs=[('job-parent', 'proj-a')])
    library_db(performance / 'data', jobs=[('job-perf', 'proj-a')])
    unattributed = []
    scope = collect_history_scope(worktree, current, 'proj-a',
                                  history_roots=[daily, performance], unattributed=unattributed)
    resolved = {Path(p).resolve() for p in scope.paths}
    assert parent_photo.resolve() in resolved
    assert performance_photo.resolve() in resolved
    assert current_photo.resolve() not in resolved
    assert fixture_photo.resolve() not in resolved
    assert probe_photo.resolve() not in resolved
    assert 'pytest-probe-x' in unattributed[0]['run']
    assert len([entry for entry in unattributed if 'pytest-probe-x' in entry['run']]) == 1


def test_isolated_adapter_environment_cannot_hide_the_real_library(tmp_path, monkeypatch):
    daily = tmp_path / 'daily'
    worktree = daily / '.local' / 'worktrees' / 'task' / 'root'
    worktree.mkdir(parents=True)
    (daily / '.local').mkdir(exist_ok=True)
    data = daily / 'library'
    original = asset_copy(data / 'assets' / 'ab' / 'placeholder' / 'original.png', (40, 80, 120))
    sha = sha_of(original)
    (daily / '.local' / 'windows-runtime.json').write_text(json.dumps({'data_dir': str(data)}), encoding='utf-8-sig')
    # The collector's redirected runtime data directory still owns the project
    # references; the canonical root only supplies retained asset bytes.
    library_db(worktree / '.local' / 'ui-data', refs=[('proj-a', sha)])
    scratch = worktree / '.local' / 'adapter-scratch'
    scratch.mkdir(parents=True)
    monkeypatch.setenv('LAB_DATA_DIR', str(scratch))
    monkeypatch.setenv('LAB_COLLECTION_HISTORY_DIR', str(worktree / '.local' / 'ui-data' / 'assets'))
    scope = collect_history_scope(worktree, worktree / '.local' / 'current', 'proj-a', history_roots=[daily])
    assert original.resolve() in {Path(p).resolve() for p in scope.paths}
