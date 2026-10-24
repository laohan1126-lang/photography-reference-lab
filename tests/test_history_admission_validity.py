"""F1: an admission receipt counts only under the rules that produced it.

The crop matcher was corrected, so a receipt written under the old rules can
no longer prove that an image is not a repeat. The receipt has to say which
algorithm produced it, and a Goal whose frozen baseline predates the current
rules has to report that honestly instead of failing the request.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from ref_lab import collage
from ref_lab.collection_counts import compute
from ref_lab.collection_history import DEDUP_SCOPE_VERSION, FINGERPRINT_ALGORITHM_VERSION
from tests.photo_type_fixture import synthetic_type
from tests.test_collage_split import _textured, _write_original

OLD_ALGORITHM_VERSION = FINGERPRINT_ALGORITHM_VERSION - 1
PROJECT_ID = 'proj-a'


@pytest.fixture(autouse=True)
def _no_production_data(monkeypatch):
    """A synthetic fixture must never read the exported production library."""
    monkeypatch.delenv('LAB_DATA_DIR', raising=False)
    monkeypatch.delenv('LAB_COLLECTION_HISTORY_DIR', raising=False)


def _fingerprint(sha):
    return {'asset_sha': sha, 'path': '/nowhere/old.png', 'ratio': 1.0, 'dhash': '0' * 16,
            'sample': '0' * 384, 'pixels': '00' * (128 * 128 * 3)}


def _bound(baseline, project_id=PROJECT_ID):
    """The project duplicate-scope binding every frozen baseline carries."""
    baseline['project_id'] = project_id
    baseline['dedup_scope_version'] = DEDUP_SCOPE_VERSION
    return baseline


def _goal_run(folder, *, algorithm_version=FINGERPRINT_ALGORITHM_VERSION, project_id=PROJECT_ID):
    """A Goal-bound run with one named original and its type receipt."""
    row = _write_original(folder, _textured((800, 600), 21, (70, 90, 120)))
    row['acquired_at'] = 1000.0
    record = collage.process_original(folder, row)
    synthetic_type(folder, row)
    baseline = _bound({'goal_id': 'goal-1', 'target': 1, 'started_at': 0.0,
                       'items': [{'sha': 'b' * 64, 'path': str(folder / 'old.png'),
                                  'fingerprint': _fingerprint('b' * 64)}],
                       'fingerprint_algorithm_version': algorithm_version}, project_id)
    raw = json.dumps(baseline).encode('utf8')
    (folder / 'baseline.json').write_bytes(raw)
    goal = {'goal_id': 'goal-1', 'target': 1, 'started_at': 0.0,
            'project_id': project_id, 'dedup_scope_version': DEDUP_SCOPE_VERSION,
            'baseline_sha': hashlib.sha256(raw).hexdigest(), 'baseline_shas': ['b' * 64]}
    (folder / 'goal.json').write_text(json.dumps(goal), encoding='utf8')
    return row, record, goal


def _receipt(folder, row, goal, algorithm_version):
    ledger = json.loads((folder / 'photo-types.json').read_text(encoding='utf8'))
    ledger['items'][row['asset_sha']]['history_check'] = {
        'state': 'clear', 'baseline_sha': goal['baseline_sha'],
        'algorithm_version': algorithm_version}
    (folder / 'photo-types.json').write_text(json.dumps(ledger), encoding='utf8')


def test_receipt_written_under_the_current_rules_counts(tmp_path):
    row, record, goal = _goal_run(tmp_path)
    _receipt(tmp_path, row, goal, FINGERPRINT_ALGORITHM_VERSION)
    counts = compute(tmp_path, [row], {row['asset_sha']: record})
    assert counts['usable_independent'] == counts['usable_named'] == 1
    assert counts['history_pending'] == 0


def test_old_clear_receipt_is_not_inherited(tmp_path):
    """A 'clear' written by the previous algorithm cannot be inherited."""
    row, record, goal = _goal_run(tmp_path)
    _receipt(tmp_path, row, goal, OLD_ALGORITHM_VERSION)
    counts = compute(tmp_path, [row], {row['asset_sha']: record})
    assert counts['usable_independent'] == 0
    assert counts['history_pending'] == 1


def test_stale_goal_baseline_is_reported_as_pending_not_as_a_crash(tmp_path):
    row, record, goal = _goal_run(tmp_path, algorithm_version=OLD_ALGORITHM_VERSION)
    _receipt(tmp_path, row, goal, FINGERPRINT_ALGORITHM_VERSION)
    counts = compute(tmp_path, [row], {row['asset_sha']: record})
    assert counts['usable_independent'] == 0
    assert counts['history_pending'] == 1


def test_launching_a_stage_on_a_stale_baseline_is_a_clean_conflict(tmp_path, monkeypatch):
    """A Goal frozen under the old rules may not start a stage silently."""
    from ref_lab import collection_queue, collection_stages
    from ref_lab.service import Problem

    monkeypatch.setattr(collection_queue, 'ROOT', tmp_path)
    monkeypatch.setattr(collection_stages, '_prepare_task', lambda *a, **k: None)
    goal_dir = tmp_path / '.local' / 'goals' / 'goal-1'
    goal_dir.mkdir(parents=True)
    # No project duplicate-scope binding: a pre-boundary whole-library baseline.
    baseline = {'goal_id': 'goal-1', 'target': 1, 'started_at': 0.0,
                'items': [{'sha': 'b' * 64, 'path': str(tmp_path / 'old.png'),
                           'fingerprint': _fingerprint('b' * 64)}],
                'fingerprint_algorithm_version': OLD_ALGORITHM_VERSION}
    raw = json.dumps(baseline).encode('utf8')
    (goal_dir / 'baseline.json').write_bytes(raw)
    (goal_dir / 'goal.json').write_text(json.dumps({
        'goal_id': 'goal-1', 'target': 1, 'started_at': 0.0,
        'baseline_sha': hashlib.sha256(raw).hexdigest(), 'baseline_shas': ['b' * 64]}),
                                         encoding='utf8')

    class _StubLibrary:
        def job(self, job_id):
            return {'id': job_id, 'project_id': PROJECT_ID, 'goal_id': 'goal-1', 'target_count': 1,
                    'search_extra_target': 0}

    with pytest.raises(Problem) as failure:
        collection_stages._artifacts(_StubLibrary(), 'job-1')
    assert failure.value.status == 409
    assert '版本' in failure.value.message
    assert failure.value.details.get('code') == 'goal_scope_binding_invalid'


def test_launching_a_stage_on_an_unbound_baseline_cannot_restore_whole_library_scope(tmp_path, monkeypatch):
    """A baseline frozen before the project boundary (current algorithm, no
    binding) must not silently continue as a whole-library scope."""
    from ref_lab import collection_queue, collection_stages
    from ref_lab.service import Problem

    monkeypatch.setattr(collection_queue, 'ROOT', tmp_path)
    monkeypatch.setattr(collection_stages, '_prepare_task', lambda *a, **k: None)
    goal_dir = tmp_path / '.local' / 'goals' / 'goal-1'
    goal_dir.mkdir(parents=True)
    baseline = {'goal_id': 'goal-1', 'target': 1, 'started_at': 0.0,
                'items': [{'sha': 'b' * 64, 'path': str(tmp_path / 'old.png'),
                           'fingerprint': _fingerprint('b' * 64)}],
                'fingerprint_algorithm_version': FINGERPRINT_ALGORITHM_VERSION}
    raw = json.dumps(baseline).encode('utf8')
    (goal_dir / 'baseline.json').write_bytes(raw)
    (goal_dir / 'goal.json').write_text(json.dumps({
        'goal_id': 'goal-1', 'target': 1, 'started_at': 0.0,
        'baseline_sha': hashlib.sha256(raw).hexdigest(), 'baseline_shas': ['b' * 64]}),
                                         encoding='utf8')

    class _StubLibrary:
        def job(self, job_id):
            return {'id': job_id, 'project_id': PROJECT_ID, 'goal_id': 'goal-1', 'target_count': 1,
                    'search_extra_target': 0}

    with pytest.raises(Problem) as failure:
        collection_stages._artifacts(_StubLibrary(), 'job-1')
    assert failure.value.status == 409
    assert failure.value.details.get('code') == 'goal_scope_binding_invalid'


def test_launching_a_stage_on_another_projects_baseline_is_refused(tmp_path, monkeypatch):
    from ref_lab import collection_queue, collection_stages
    from ref_lab.service import Problem

    monkeypatch.setattr(collection_queue, 'ROOT', tmp_path)
    monkeypatch.setattr(collection_stages, '_prepare_task', lambda *a, **k: None)
    goal_dir = tmp_path / '.local' / 'goals' / 'goal-1'
    goal_dir.mkdir(parents=True)
    baseline = _bound({'goal_id': 'goal-1', 'target': 1, 'started_at': 0.0,
                       'items': [{'sha': 'b' * 64, 'path': str(tmp_path / 'old.png'),
                                  'fingerprint': _fingerprint('b' * 64)}],
                       'fingerprint_algorithm_version': FINGERPRINT_ALGORITHM_VERSION},
                      project_id='proj-other')
    raw = json.dumps(baseline).encode('utf8')
    (goal_dir / 'baseline.json').write_bytes(raw)
    (goal_dir / 'goal.json').write_text(json.dumps({
        'goal_id': 'goal-1', 'target': 1, 'started_at': 0.0, 'project_id': 'proj-other',
        'dedup_scope_version': DEDUP_SCOPE_VERSION,
        'baseline_sha': hashlib.sha256(raw).hexdigest(), 'baseline_shas': ['b' * 64]}),
                                         encoding='utf8')

    class _StubLibrary:
        def job(self, job_id):
            return {'id': job_id, 'project_id': PROJECT_ID, 'goal_id': 'goal-1', 'target_count': 1,
                    'search_extra_target': 0}

    with pytest.raises(Problem) as failure:
        collection_stages._artifacts(_StubLibrary(), 'job-1')
    assert failure.value.status == 409
    assert failure.value.details.get('code') == 'goal_scope_binding_invalid'


def test_launching_a_stage_on_a_tampered_baseline_is_not_called_a_version_upgrade(tmp_path, monkeypatch):
    """A baseline that does not match its Goal is a validation failure."""
    from ref_lab import collection_queue, collection_stages
    from ref_lab.service import Problem

    monkeypatch.setattr(collection_queue, 'ROOT', tmp_path)
    monkeypatch.setattr(collection_stages, '_prepare_task', lambda *a, **k: None)
    goal_dir = tmp_path / '.local' / 'goals' / 'goal-1'
    goal_dir.mkdir(parents=True)
    baseline = {'goal_id': 'goal-1', 'target': 1, 'started_at': 0.0,
                'items': [{'sha': 'b' * 64, 'path': str(tmp_path / 'old.png'),
                           'fingerprint': _fingerprint('b' * 64)}],
                'fingerprint_algorithm_version': FINGERPRINT_ALGORITHM_VERSION}
    raw = json.dumps(baseline).encode('utf8')
    (goal_dir / 'baseline.json').write_bytes(raw)
    # The Goal claims a different SHA set than the baseline it froze.
    (goal_dir / 'goal.json').write_text(json.dumps({
        'goal_id': 'goal-1', 'target': 1, 'started_at': 0.0,
        'baseline_sha': hashlib.sha256(raw).hexdigest(), 'baseline_shas': ['c' * 64]}),
                                         encoding='utf8')

    class _StubLibrary:
        def job(self, job_id):
            return {'id': job_id, 'project_id': PROJECT_ID, 'goal_id': 'goal-1', 'target_count': 1,
                    'search_extra_target': 0}

    with pytest.raises(Problem) as failure:
        collection_stages._artifacts(_StubLibrary(), 'job-1')
    assert failure.value.status == 409
    assert '版本' not in failure.value.message, 'a tampered baseline is not a version upgrade'
    assert not failure.value.details or failure.value.details.get('code') != 'goal_scope_binding_invalid'


def test_a_stage_on_a_current_baseline_still_prepares_the_task_package(tmp_path, monkeypatch):
    from ref_lab import collection_queue, collection_stages

    monkeypatch.setattr(collection_queue, 'ROOT', tmp_path)
    monkeypatch.setattr(collection_stages, '_prepare_task', lambda *a, **k: None)
    goal_dir = tmp_path / '.local' / 'goals' / 'goal-1'
    goal_dir.mkdir(parents=True)
    baseline = _bound({'goal_id': 'goal-1', 'target': 1, 'started_at': 0.0,
                       'items': [{'sha': 'b' * 64, 'path': str(tmp_path / 'old.png'),
                                  'fingerprint': _fingerprint('b' * 64)}],
                       'fingerprint_algorithm_version': FINGERPRINT_ALGORITHM_VERSION})
    raw = json.dumps(baseline).encode('utf8')
    (goal_dir / 'baseline.json').write_bytes(raw)
    (goal_dir / 'goal.json').write_text(json.dumps({
        'goal_id': 'goal-1', 'target': 1, 'started_at': 0.0, 'project_id': PROJECT_ID,
        'dedup_scope_version': DEDUP_SCOPE_VERSION,
        'baseline_sha': hashlib.sha256(raw).hexdigest(), 'baseline_shas': ['b' * 64]}),
                                         encoding='utf8')

    class _StubLibrary:
        def job(self, job_id):
            return {'id': job_id, 'project_id': PROJECT_ID, 'goal_id': 'goal-1', 'target_count': 1,
                    'search_extra_target': 0}

    folder, task_dir, task_file = collection_stages._artifacts(_StubLibrary(), 'job-1')
    assert (folder / 'baseline.json').is_file()
    assert (folder / 'goal.json').is_file()
    assert task_dir.name == 'task' and task_file.name == 'AGENT_TASK.md'


def test_goal_baseline_rejects_the_whole_library_era_without_touching_it(tmp_path):
    """The frozen files of a pre-boundary baseline stay untouched on disk."""
    import hashlib
    import json
    from ref_lab.collection_history import BaselineNeedsUpgrade, goal_baseline

    baseline = {'goal_id': 'goal-1', 'target': 1, 'started_at': 0.0,
                'items': [{'sha': 'b' * 64, 'path': str(tmp_path / 'old.png'),
                           'fingerprint': _fingerprint('b' * 64)}],
                'fingerprint_algorithm_version': FINGERPRINT_ALGORITHM_VERSION}
    raw = json.dumps(baseline).encode('utf8')
    (tmp_path / 'baseline.json').write_bytes(raw)
    goal = {'goal_id': 'goal-1', 'baseline_sha': hashlib.sha256(raw).hexdigest(),
            'baseline_shas': ['b' * 64]}
    (tmp_path / 'goal.json').write_text(json.dumps(goal), encoding='utf8')
    with pytest.raises(BaselineNeedsUpgrade, match='dedup_scope_version'):
        goal_baseline(tmp_path, goal)
    assert (tmp_path / 'baseline.json').read_bytes() == raw
    assert json.loads((tmp_path / 'goal.json').read_text(encoding='utf8')) == goal
