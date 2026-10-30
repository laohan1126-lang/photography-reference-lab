"""Rejected continuations must be read-only, including real HTTP handlers."""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from ref_lab import collection_queue, collection_stages, service
from ref_lab.api import create_app
from ref_lab.collection_history import HistoryIntegrityBlocked, collect_history_scope
from ref_lab.config import Settings
from ref_lab.models import JobInput, ProjectInput
from tests.conftest import TOKEN, image_bytes, library_db


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    # Keep Windows task-package paths short, even under a long pytest node name.
    root = tmp_path.parent / ("g" + uuid4().hex[:6])
    root.mkdir()
    monkeypatch.setattr(service, "__file__", str(root / "ref_lab/service.py"))
    monkeypatch.setattr(collection_queue, "ROOT", root)
    monkeypatch.setenv("LAB_DATA_DIR", str(root / "data"))
    monkeypatch.setenv("LAB_COLLECTION_HISTORY_ROOTS", "[]")
    monkeypatch.delenv("LAB_COLLECTION_HISTORY_DIR", raising=False)
    app = create_app(Settings(root / "data", TOKEN, public_origin="http://testserver"))
    with TestClient(app) as client:
        client.headers["X-Lab-CSRF"] = client.post("/api/session", json={"token": TOKEN}).json()["csrf"]
        library = app.state.library
        project = library.create_project(ProjectInput(character="王昭君"))
        job = library.create_job(project["id"], JobInput(kind="collection", collection_mode="search", target_count=2))
        attempt_id = "prep-" + job["id"]
        library.begin_job_preparation(job["id"], attempt_id, {"pid": os.getpid(), "phase": "test"})
        job = library.prepare_job(job["id"], attempt_id)
        yield root, library, client, job


def snapshot(root, library):
    with library.db.read() as con:
        names = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        tables = {name: [tuple(row) for row in con.execute('SELECT * FROM "' + name + '" ORDER BY rowid')]
                  for name in names}
    # SQLite WAL bookkeeping is not business state; every row and other file is.
    files = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in root.rglob("*") if p.is_file() and not p.name.startswith("library.sqlite3")}
    dirs = sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_dir())
    return {"tables": tables, "files": files, "dirs": dirs}


def damage(root, job, kind):
    goal_dir = root / ".local/goals" / job["goal_id"]
    goal_path = goal_dir / "goal.json"
    goal = json.loads(goal_path.read_text("utf8"))
    baseline_path = goal_dir / "baseline.json"
    baseline = json.loads(baseline_path.read_text("utf8"))
    if kind == "unbound":
        for value in (goal, baseline):
            value.pop("project_id")
            value.pop("dedup_scope_version")
    elif kind == "wrong_project":
        goal["project_id"] = baseline["project_id"] = "another-project"
    elif kind == "bad_baseline":
        baseline_path.write_bytes(b"broken baseline")
        return
    elif kind == "invalid_baseline":
        baseline = []
    elif kind == "bad_goal":
        goal_path.write_bytes(b"{")
        return
    elif kind == "bad_run_goal":
        run_goal = collection_queue.run_directory(job["id"]) / "goal.json"
        existing = json.loads(run_goal.read_text("utf8"))
        existing["project_id"] = "another-project"
        collection_queue.write_json(run_goal, existing)
        return
    elif kind == "bad_run_baseline":
        (collection_queue.run_directory(job["id"]) / "baseline.json").write_bytes(b"broken run baseline")
        return
    raw = json.dumps(baseline).encode("utf8")
    baseline_path.write_bytes(raw)
    goal["baseline_sha"] = hashlib.sha256(raw).hexdigest()
    collection_queue.write_json(goal_path, goal)


@pytest.mark.parametrize("kind", ["unbound", "wrong_project", "bad_baseline", "invalid_baseline", "bad_goal",
                                  "bad_run_goal", "bad_run_baseline"])
@pytest.mark.parametrize("entry", ["http_extend", "http_replenish", "extend", "replenish", "artifacts"])
def test_invalid_goal_rejected_before_any_write(isolated, kind, entry):
    root, library, client, job = isolated
    folder, _, _ = collection_stages._artifacts(library, job["id"])
    collection_queue.write_json(folder / "received.json", [{"asset_sha": "a" * 64, "original_path": "historical"}])
    collection_queue.write_json(folder / "receipt.json", {"status": "historical", "count": 1})
    damage(root, job, kind)
    before = snapshot(root, library)
    if entry.startswith("http_"):
        payload = {"extra_target": 1} if entry == "http_extend" else {"additional_seconds": 60}
        response = client.post(f"/api/jobs/{job['id']}/search/continue", json=payload)
        assert response.status_code == 409, response.text
    else:
        with pytest.raises(service.Problem) as failure:
            if entry == "extend":
                library.extend_search(job["id"], 1)
            elif entry == "replenish":
                library.replenish_search(job["id"], 60)
            else:
                collection_stages._artifacts(library, job["id"])
        assert failure.value.status == 409
    assert snapshot(root, library) == before


OFFLINE_ADAPTER = '''
import json, sys
from pathlib import Path
task = Path(sys.argv[1])
folder = task.parent.parent
job = json.loads((task.parent / 'job.json').read_text('utf8'))['job']
rows = json.loads((folder / 'received.json').read_text('utf8'))
summary = {'version': 1, 'status': 'partial', 'stop_reason': 'offline_recovery_fixture',
           'target': job['target_count'] + job.get('search_extra_target', 0),
           'counts': {'found': len(rows), 'target_confirmed': 0},
           'elapsed_seconds': 0.01, 'model_calls': 0, 'tokens': 0,
           'adapter': 'offline-preserve-received-no-browser-no-model'}
(folder / 'search-summary.json').write_text(json.dumps(summary), encoding='utf8')
'''


def exercise_valid_recovery(root, library, client, job, raw, monkeypatch):
    """Real handler + stage + subprocess; fixture only reports offline progress."""
    folder, _, _ = collection_stages._artifacts(library, job['id'])
    sha = hashlib.sha256(raw).hexdigest()
    original = folder / 'images' / (sha + '.png')
    original.parent.mkdir()
    original.write_bytes(raw)
    with Image.open(io.BytesIO(raw)) as image:
        width, height = image.size
    collection_queue.write_json(folder / 'received.json', [{
        'asset_sha': sha, 'original_path': str(original.resolve()),
        'page_url': 'https://example.org/offline-existing',
        'image_url': 'https://example.org/offline-existing.png',
        'acquired_at': time.time(), 'width': width, 'height': height}])
    collection_queue.write_json(folder / 'receipt.json', {'status': 'historical', 'count': 1})
    preserved = {p: p.read_bytes() for p in (original, folder / 'received.json', folder / 'receipt.json')}
    library.extend_search(job['id'], 1)
    with library.db.transaction() as con:
        current = library.job(job['id'])
        current['search_stop_reason'] = 'time_budget_exhausted'
        library._save_job(con, current, 'test.budget_exhausted', {}, 'worker')
    adapter = root / 'offline_adapter.py'
    adapter.write_text(OFFLINE_ADAPTER, encoding='utf8')
    monkeypatch.setenv('LAB_COLLECTION_COMMAND', json.dumps([
        sys.executable, '-B', '-X', 'utf8', str(adapter), '{task_file}', '{result_file}']))
    evidence = []
    for payload in ({'additional_seconds': 60}, {'extra_target': 1}):
        previous = library.job(job['id'])
        response = client.post(f"/api/jobs/{job['id']}/search/continue", json=payload)
        assert response.status_code == 200, response.text
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            after = library.job(job['id'])
            if after.get('search_state') != 'running' and not any(k[0] == job['id'] for k in collection_stages._RUNNING):
                break
            time.sleep(.05)
        else:
            raise AssertionError('offline adapter did not finish')
        assert after['search_state'] == 'partial', after
        assert after['search_resume_generation'] == previous['search_resume_generation'] + 1
        assert after['target_count'] == 2
        assert after['search_extra_target'] == previous['search_extra_target'] + payload.get('extra_target', 0)
        assert after['search_timeout_seconds'] > previous['search_timeout_seconds']
        assert after['search_counts']['found'] == 1
        view = client.get(f"/api/jobs/{job['id']}/candidates").json()
        assert view['counts']['found'] == 1
        assert all(p.read_bytes() == before for p, before in preserved.items())
        goal = json.loads((folder / 'goal.json').read_text('utf8'))
        assert goal['target'] == after['target_count'] + after['search_extra_target']
        evidence.append({'request': payload, 'http': response.status_code,
                         'target_count': after['target_count'], 'search_extra_target': after['search_extra_target'],
                         'found': view['counts']['found'], 'generation': after['search_resume_generation'],
                         'original_sha': sha, 'received_receipt_original_unchanged': True,
                         'summary': json.loads((folder / 'search-summary.json').read_text('utf8'))})
    return evidence


def test_valid_nonempty_goal_keeps_original_and_extra_targets(isolated, monkeypatch):
    root, library, client, job = isolated
    exercise_valid_recovery(root, library, client, job, image_bytes(), monkeypatch)


def test_invalid_goal_does_not_even_prepare_a_new_task(isolated, monkeypatch):
    root, library, _, job = isolated
    damage(root, job, "unbound")
    before = snapshot(root, library)
    calls = []
    monkeypatch.setattr(collection_stages, "_prepare_task", lambda *args: calls.append(args))
    with pytest.raises(service.Problem):
        collection_stages._artifacts(library, job["id"])
    assert calls == []
    assert snapshot(root, library) == before


@pytest.mark.parametrize("metadata,reference_sha", [("{", None), ("[]", None), ("null", None),
                                                   ('"invalid"', None), ("{}", "not-a-sha")])
def test_malformed_reference_metadata_blocks_instead_of_shrinking_history(tmp_path, monkeypatch, metadata, reference_sha):
    monkeypatch.delenv("LAB_COLLECTION_HISTORY_DIR", raising=False)
    monkeypatch.delenv("LAB_DATA_DIR", raising=False)
    raw = image_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    root = tmp_path.parent / ("r" + uuid4().hex[:6])
    data = root / "data"
    original = data / "assets" / sha[:2] / sha / "original.png"
    original.parent.mkdir(parents=True)
    original.write_bytes(raw)
    db = library_db(data, refs=[("project-a", sha)])
    import sqlite3
    with sqlite3.connect(db) as con:
        con.execute("INSERT INTO assets VALUES(?,?)", (sha, json.dumps({'id': sha})))
    assert str(original.resolve()) in map(str, collect_history_scope(root, root / '.local/current', 'project-a').paths)
    with sqlite3.connect(db) as con:
        con.execute("UPDATE refs SET data=?,asset_sha=?", (metadata, reference_sha or sha))
    with pytest.raises(HistoryIntegrityBlocked, match="reference.*metadata"):
        collect_history_scope(root, root / ".local/current", "project-a")
    assert original.read_bytes() == raw
