import hashlib
import json

import pytest
from PIL import Image

import ref_lab.collection_history as collection_history
from ref_lab.collection_history import ImageHistory, historical_paths


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


def test_known_sha_is_an_exact_duplicate_before_lazy_fingerprints_finish(tmp_path):
    source = photo(tmp_path / 'source.png', (80, 40, 140))
    raw = source.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    stored = tmp_path / 'assets' / 'ab' / sha / 'original.png'
    stored.parent.mkdir(parents=True)
    stored.write_bytes(raw)
    history = ImageHistory([stored], cache_path=tmp_path / 'cache.json', lazy=True)
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
    original = photo(root / '.local' / 'older' / 'images' / 'one.png', (80, 90, 100))
    received(root / '.local' / 'older', original)
    ImageHistory([original], cache_path=root / '.local' / 'history-cache.json')
    current = root / '.local' / 'current'
    assert original.resolve() in historical_paths(root, current)

    photo(original, (200, 10, 160))
    with pytest.raises(ValueError, match='SHA changed'):
        historical_paths(root, current)


def test_explicit_history_roots_include_parent_and_performance_but_exclude_current_and_venv(tmp_path, monkeypatch):
    monkeypatch.delenv('LAB_DATA_DIR', raising=False)
    monkeypatch.delenv('LAB_COLLECTION_HISTORY_DIR', raising=False)
    daily = tmp_path / 'daily'
    worktree = daily / '.local' / 'worktrees' / 'finalization' / 'root'
    performance = daily / '.local' / 'worktrees' / 'performance' / 'root'
    parent_photo = photo(daily / '.local' / 'older-run' / 'images' / 'parent.png', (20, 80, 120))
    received(daily / '.local' / 'older-run', parent_photo)
    performance_photo = photo(performance / '.local' / 'supply-run' / 'images' / 'performance.png', (130, 80, 20))
    received(performance / '.local' / 'supply-run', performance_photo)
    current = worktree / '.local' / 'current-job'
    current_photo = photo(current / 'images' / 'current.png', (200, 40, 90))
    received(current, current_photo)
    venv_photo = photo(daily / '.local' / '.venv' / 'old-run' / 'images' / 'venv.png', (10, 220, 120))
    received(daily / '.local' / '.venv' / 'old-run', venv_photo)

    paths = set(historical_paths(worktree, current, history_roots=[daily, performance]))
    assert parent_photo.resolve() in paths
    assert performance_photo.resolve() in paths
    assert current_photo.resolve() not in paths
    assert venv_photo.resolve() not in paths


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


def test_isolated_adapter_environment_cannot_hide_explicit_daily_assets(tmp_path,monkeypatch):
    daily=tmp_path/'daily';worktree=daily/'.local/worktrees/task/root'
    worktree.mkdir(parents=True);(daily/'.local').mkdir(exist_ok=True)
    data=daily/'library'
    original=photo(data/'assets/ab/abcdef/original.png',(40,80,120))
    (daily/'.local/windows-runtime.json').write_text(json.dumps({'data_dir':str(data)}),encoding='utf-8-sig')
    scratch=worktree/'.local/adapter-scratch';scratch.mkdir(parents=True)
    monkeypatch.setenv('LAB_DATA_DIR',str(scratch))
    monkeypatch.setenv('LAB_COLLECTION_HISTORY_DIR',str(worktree/'.local/ui-data/assets'))
    assert original.resolve() in historical_paths(worktree,worktree/'.local/current',history_roots=[daily])
