"""Search/Review stage contract tests. Synthetic adapters only, no live network.

These tests exercise the actual FastAPI handlers and subprocess transport while
the adapter itself is a deterministic local stand-in. They are not evidence of
live browsing or visual accuracy.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import pytest
from PIL import Image

from ref_lab import collection_queue
from ref_lab.models import JobInput
from ref_lab.verified_collection import CollectionVision, NamePlan, scope_sha
from tools import collect_verified as worker


def make_image(path: Path, color, size=(640, 960)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, format="PNG")
    return path


def wait_until(predicate, *, timeout=25.0, interval=0.1):
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    raise AssertionError("timed out waiting for stage state")


FAKE_ADAPTER = r'''
import json, os, sys, time, zipfile
from pathlib import Path
from PIL import Image

args = sys.argv[1:]
task_file = Path(args[0]); result_file = Path(args[1])
folder = task_file.parent.parent
search_only = '--search-only' in args
review_only = '--review-only' in args
wait_search = '--wait-search' in args
(folder / 'images').mkdir(parents=True, exist_ok=True)


def read(path, default):
    try: return json.loads(Path(path).read_text('utf8'))
    except (OSError, ValueError): return default


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')


def make_photo(index):
    path = folder / 'images' / ('fake-%s-%s.png' % (index, os.getpid()))
    Image.new('RGB', (640, 960), (40 + index * 30, 90, 140)).save(path, format='PNG')
    raw = path.read_bytes()
    return {'asset_sha': __import__('hashlib').sha256(raw).hexdigest(),
            'original_path': str(path.resolve()),
            'page_url': 'https://example.org/post/%s' % index,
            'image_url': 'https://example.org/image/%s.png' % index,
            'width': 640, 'height': 960, 'search_query': 'synthetic query',
            'discovery_url': 'https://example.org/search?q=synthetic'}


if search_only:
    sleep = float(os.environ.get('FAKE_SEARCH_SLEEP', '0'))
    if sleep: time.sleep(sleep)
    received = read(folder / 'received.json', [])
    have = {row['asset_sha'] for row in received}
    partial = os.environ.get('FAKE_SEARCH_PARTIAL') == '1'
    for index in range(1 if partial else 2):
        row = make_photo(index + len(have))
        if row['asset_sha'] not in have:
            received.append(row); have.add(row['asset_sha'])
    write(folder / 'received.json', received)
    if os.environ.get('FAKE_SEARCH_PARTIAL_SUMMARY') == '1':
        write(folder / 'search-summary.json', {
            'version': 1, 'status': 'partial', 'stop_reason': 'target_partial',
            'target': 2, 'target_reached': False,
            'counts': {'found': len(received), 'duplicates': 0, 'errors': 0,
                       'usable_named': len(received), 'target_confirmed': len(received)},
            'elapsed_seconds': 0.01, 'first_received_seconds': 0.01,
            'queries': [], 'source_checks': [], 'searches': {}, 'errors': [],
            'model_calls': 0, 'tokens': 0})
        raise SystemExit(0)
    if partial:
        raise SystemExit(1)
    write(folder / 'search-summary.json', {
        'version': 1, 'status': 'completed', 'stop_reason': 'target_reached',
        'target': 2, 'counts': {'found': len(received), 'duplicates': 0, 'errors': 0},
        'elapsed_seconds': 0.01, 'first_received_seconds': 0.01,
        'queries': [], 'source_checks': [], 'searches': {}, 'errors': [],
        'model_calls': 0, 'tokens': 0})
    raise SystemExit(0)

if review_only:
    if wait_search:
        deadline = time.time() + 20
        while not (folder / 'received.json').exists():
            if time.time() > deadline: raise SystemExit(2)
            time.sleep(0.05)
    release = os.environ.get('FAKE_REVIEW_RELEASE', '')
    write(folder / 'review-state.json', {'phase': 'reference_prepare', 'started_at': time.time()})
    if release:
        deadline = time.time() + 20
        while not Path(release).exists():
            if time.time() > deadline: raise SystemExit(3)
            time.sleep(0.05)
    received = read(folder / 'received.json', [])
    task = read(folder / 'task' / 'job.json', {})
    job_id = task.get('id') or task.get('job', {}).get('id') or 'fake-job'
    block_first = os.environ.get('FAKE_REVIEW_BLOCK_ONE') == '1'
    items = {}
    for index, row in enumerate(received):
        sha = row['asset_sha']
        if block_first and index == 0:
            items[sha] = {'asset_sha': sha, 'status': 'blocked', 'accepted': False,
                          'decision': 'REVIEW_BLOCKED', 'error': 'synthetic vision timeout',
                          'attempts': 1, 'completed_at': time.time()}
        else:
            value = {'asset_sha': sha, 'context_sha': task.get('context_sha', ''),
                     'kind': 'cosplay_photo', 'identity': 'match', 'costume': 'not_required',
                     'confidence': 'high',
                     'kind_evidence': ['synthetic single frame'],
                     'identity_evidence': ['synthetic fixture evidence'],
                     'costume_evidence': [],
                     'photography_usable': 'yes',
                     'photography_evidence': ['synthetic composition evidence'],
                     'reason': 'synthetic acceptance fixture',
                     'reference_comparisons': []}
            items[sha] = {'asset_sha': sha, 'status': 'accepted', 'accepted': True,
                          'decision': 'CONFIRMED', 'review': value, 'references': [],
                          'attempts': 1, 'completed_at': time.time()}
    write(folder / 'review-audit.json', {'version': 1, 'context_sha': task.get('context_sha', ''),
                                         'items': items})
    accepted = [row for row in received if items[row['asset_sha']]['status'] == 'accepted']
    write(folder / 'review-summary.json', {
        'version': 1, 'status': 'completed' if len(accepted) == len(received) else 'partial',
        'stop_reason': 'review_complete', 'target': 2,
        'counts': {'found': len(received), 'accepted': len(accepted),
                   'rejected': 0, 'blocked': len(received) - len(accepted),
                   'pending': 0, 'human_keep': 0, 'human_reject': 0},
        'accepted_candidates': len(accepted), 'elapsed_seconds': 0.01,
        'model_calls': 0, 'tokens': 0})
    manifest = {'schema_version': 3, 'job_id': job_id, 'batch_id': 'fake-batch',
                'candidates': [], 'execution_report': {
                    'producer': 'fake-adapter', 'status': 'completed' if len(accepted) == len(received) else 'blocked',
                    'summary': 'synthetic stage fixture', 'source_checks': [], 'query_log': [], 'gaps': []}}
    for row in accepted:
        manifest['candidates'].append({
            'id': 'verified-' + row['asset_sha'][:20],
            'file': 'images/' + Path(row['original_path']).name,
            'title': 'synthetic candidate',
            'source': {'page_url': row['page_url'], 'image_url': row['image_url'],
                       'search_query': row.get('search_query', '')},
            'preflight': {'content_type': 'real_person_cosplay', 'identity_prediction': 'match',
                          'confidence': 'high', 'visual_evidence': ['synthetic fixture'],
                          'reason': 'synthetic stage fixture'}})
    with zipfile.ZipFile(result_file, 'w') as archive:
        archive.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False))
        for row in accepted:
            path = Path(row['original_path'])
            archive.writestr('images/' + path.name, path.read_bytes())
    raise SystemExit(0)
raise SystemExit(4)
'''


def adapter(tmp_path, monkeypatch):
    script = tmp_path / "fake_adapter.py"
    script.write_text(FAKE_ADAPTER, encoding="utf8")
    command = [sys.executable, str(script), "{task_file}", "{result_file}"]
    monkeypatch.setenv("LAB_COLLECTION_COMMAND", json.dumps(command))
    return script


def isolate_queue(tmp_path, monkeypatch):
    root = tmp_path
    # Keep the synthetic task-package path short; the Windows adapter path is
    # otherwise near MAX_PATH in a deep pytest temp directory.
    monkeypatch.setattr(collection_queue, "run_directory", lambda job_id: root / "q")
    return root


def create_job(client, project, mode="search_review", target=2):
    response = client.post(f"/api/projects/{project['id']}/jobs",
                           json={"kind": "collection", "target_count": target,
                                 "collection_mode": mode, "notes": "synthetic stage test"})
    assert response.status_code == 201, response.text
    return response.json()


def stages(client, job_id):
    response = client.get(f"/api/jobs/{job_id}/candidates")
    assert response.status_code == 200, response.text
    return response.json()


def test_search_only_cli_writes_summary_without_a_model_budget_or_result_zip(tmp_path, monkeypatch):
    root = tmp_path / "cli-root"
    run = root / ".local" / "collection-runs" / "cli-job" / "current"
    run.mkdir(parents=True)
    task_dir = root / "task"
    task_dir.mkdir()
    job = {"id": "cli-job", "project_snapshot": {"character": "测试角色甲", "work": "", "costume": "", "brief": ""},
           "target_count": 1, "preferred_sources": ["xiaohongshu"], "notes": ""}
    (task_dir / "job.json").write_text(json.dumps({"job": job}), encoding="utf8")
    (task_dir / "AGENT_TASK.md").write_text("synthetic task", encoding="utf8")
    image = make_image(run / "images" / "one.png", (30, 100, 140))

    class Browser:
        def __init__(self, folder): self.folder = folder
        def start(self): pass
        def search(self, step):
            from urllib.parse import quote
            return {"url": "https://example.org/search?q=" + quote(step["query"]), "search": step["query"],
                    "visibleMain": "", "cards": [{"page": "https://example.org/post", "text": "测试角色甲 cosplay"}]}
        def receive(self, card, step):
            return [{"asset_sha": hashlib.sha256(image.read_bytes()).hexdigest(),
                     "original_path": str(image), "page_url": "https://example.org/post",
                     "image_url": "https://example.org/image.png", "width": 640, "height": 960}]
        def close(self): pass

    class Agent:
        producer = "synthetic-cli-search"
        model = "synthetic"
        candidate_calls = vision_cli_calls = 0
        references = []
        deadline = float("inf")
        def __init__(self, *args, **kwargs):
            assert kwargs.get("runtime_budget") is False
        def plan(self, project): raise AssertionError("CLI search must not call the name model")
        def prepare(self, project, plan): raise AssertionError("CLI search must not prepare references")
        def review(self, path, project): raise AssertionError("CLI search must not call vision")

    class History:
        records = {}
        initial_count = 0
        known_count = 0
        ready = True
        errors = []
        def consider(self, path): return None
        def close(self, **kwargs): pass

    monkeypatch.setattr(worker, "ROOT", root)
    monkeypatch.setattr(worker, "AntigravityCollectionAgent", Agent)
    monkeypatch.setattr(worker, "Browser", Browser)
    monkeypatch.setattr(worker, "_history_for_search", lambda folder: History())
    monkeypatch.setattr(worker, "_write_run_info", lambda *args, **kwargs: None)
    monkeypatch.setattr(sys, "argv", ["collect_verified.py", str(task_dir / "AGENT_TASK.md"), str(run / "result.zip"), "--search-only"])
    worker.main()
    summary = json.loads((run / "search-summary.json").read_text("utf8"))
    assert summary["status"] == "partial" and summary["counts"]["found"] == 1
    assert summary["counts"]["usable_named"] == 0  # no actual type observation
    assert summary["model_calls"] == 0
    assert not (run / "runtime-budget.json").exists()
    assert not (run / "result.zip").exists()
    assert json.loads((run / "received.json").read_text("utf8"))


def test_search_only_persists_candidates_without_any_model_or_reference_call(tmp_path):
    image = make_image(tmp_path / "images" / "one.png", (40, 120, 160))

    class Browser:
        def start(self): self.started = True
        def search(self, step):
            from urllib.parse import quote
            return {"url": "https://example.org/search?q=" + quote(step["query"]), "search": step["query"],
                    "visibleMain": "", "cards": [{"page": "https://example.org/post", "text": "测试角色甲 cosplay"}]}
        def receive(self, card, step):
            return [{"asset_sha": hashlib.sha256(image.read_bytes()).hexdigest(),
                     "original_path": str(image), "page_url": "https://example.org/post",
                     "image_url": "https://example.org/image.png", "width": 640, "height": 960}]
        def close(self): self.closed = True

    class Agent:
        producer = "synthetic-search-only"
        model = "synthetic"
        candidate_calls = 0
        vision_cli_calls = 0
        references = []
        deadline = float("inf")
        def __init__(self): self.plan_calls = self.prepare_calls = self.review_calls = 0
        def plan(self, project): self.plan_calls += 1; return NamePlan(names=[project["character"]])
        def prepare(self, project, plan): self.prepare_calls += 1; raise AssertionError("Search must not prepare references")
        def review(self, path, project): self.review_calls += 1; raise AssertionError("Search must not run vision")

    agent = Agent()
    task = {"id": "search-only-fixture", "project_snapshot": {"character": "测试角色甲", "work": "", "costume": "", "brief": ""},
            "target_count": 2, "preferred_sources": ["xiaohongshu"]}
    summary, images = worker.collect(task, agent, Browser(), tmp_path, search_only=True)
    assert agent.plan_calls == agent.prepare_calls == agent.review_calls == 0
    assert summary["status"] == "partial" and summary["counts"]["found"] == 1
    assert summary["counts"]["target_confirmed"] == 1 and summary["target_reached"] is False
    assert summary["model_calls"] == 0 and summary["tokens"] == 0
    assert images == {}
    received = json.loads((tmp_path / "received.json").read_text("utf8"))
    assert len(received) == 1 and received[0]["asset_sha"] == hashlib.sha256(image.read_bytes()).hexdigest()
    assert (tmp_path / "public" / "search-index.html").exists()
    assert not (tmp_path / "manifest.json").exists()


class FakeReviewAgent:
    producer = "synthetic-review-only"
    model = "synthetic"
    candidate_calls = 0
    vision_cli_calls = 0
    candidate_limit = 20
    deadline = float("inf")
    def __init__(self, *, fail_first=False):
        self.references = []
        self.review_calls = 0
        self.fail_first = fail_first
    def plan(self, project): return NamePlan(names=[project["character"]])
    def prepare(self, project, plan):
        self.references = [
            {"asset_sha": "d" * 64, "path": str(Path(__file__)), "page_url": "https://example.org/ref",
             "label": "synthetic reference", "authority": "official_licensed_manufacturer"}]
    def review(self, path, project):
        self.review_calls += 1
        sha = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        if self.fail_first and self.review_calls == 1:
            raise worker.AgentUnavailable("synthetic vision timeout")
        return CollectionVision(asset_sha=sha, context_sha=scope_sha(project), kind="cosplay_photo",
                                identity="match", costume="not_required", confidence="high",
                                kind_evidence=["synthetic single frame"],
                                identity_evidence=["synthetic fixture evidence"],
                                costume_evidence=[], photography_usable="yes",
                                photography_evidence=["synthetic composition evidence"],
                                reason="synthetic acceptance fixture",
                                reference_comparisons=[{"reference_sha": "d" * 64, "assessment": "supports",
                                                        "scope": "identity",
                                                        "supporting_features": ["synthetic silhouette", "synthetic accessory"],
                                                        "conflicting_features": []}])


def seed_search_rows(folder, count=2):
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for index in range(count):
        path = make_image(folder / "images" / f"seed-{index}.png", (60 + index * 40, 90, 140))
        rows.append({"asset_sha": hashlib.sha256(path.read_bytes()).hexdigest(),
                     "original_path": str(path.resolve()), "page_url": f"https://example.org/post/{index}",
                     "image_url": f"https://example.org/image/{index}.png", "width": 640, "height": 960,
                     "search_query": "synthetic", "discovery_url": "https://example.org/search"})
    (folder / "received.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf8")
    (folder / "search-summary.json").write_text(json.dumps({
        "version": 1, "status": "completed", "stop_reason": "target_reached",
        "target": count, "counts": {"found": count, "duplicates": 0, "errors": 0},
        "elapsed_seconds": 0.01, "model_calls": 0, "tokens": 0}), encoding="utf8")
    task = {"id": "seed-job", "project_snapshot": {"character": "测试角色甲", "work": "", "costume": "", "brief": ""},
            "target_count": count, "preferred_sources": ["xiaohongshu"]}
    from ref_lab.collection_checkpoint import job_binding
    (folder / "collector-state.json").write_text(json.dumps({
        "version": 1, "binding": job_binding(task, "synthetic"), "batch_id": "seed-batch",
        "received": rows, "audit": [], "queries": [], "checks": {}, "pages": [], "page_attempts": {},
        "duplicates": [], "collisions": [], "gaps": [], "searches": {}, "details": 0, "windows": 0,
        "first_usable": None, "search_complete": True}, ensure_ascii=False), encoding="utf8")
    return task, rows


def test_review_is_idempotent_and_does_not_repeat_completed_judgments(tmp_path):
    task, rows = seed_search_rows(tmp_path, 2)
    agent = FakeReviewAgent()
    manifest, images, summary = worker.review_candidates(task, agent, tmp_path, history=None)
    assert agent.review_calls == 2 and len(manifest["candidates"]) == 2 and len(images) == 2
    assert summary["counts"]["accepted"] == 2
    # A second launch (as after a server restart) must not call vision again.
    agent2 = FakeReviewAgent()
    manifest2, images2, summary2 = worker.review_candidates(task, agent2, tmp_path, history=None)
    assert agent2.review_calls == 0
    assert manifest2["candidates"] == manifest["candidates"] and images2 == images
    assert all((tmp_path / "images" / Path(row["original_path"]).name).read_bytes() ==
               (tmp_path / "images" / Path(row["original_path"]).name).read_bytes() for row in rows)


def test_review_failure_keeps_candidate_originals_and_marks_only_that_image_blocked(tmp_path):
    task, rows = seed_search_rows(tmp_path, 2)
    agent = FakeReviewAgent(fail_first=True)
    manifest, images, summary = worker.review_candidates(task, agent, tmp_path, history=None)
    assert len(manifest["candidates"]) == 1
    assert summary["counts"]["accepted"] == 1 and summary["counts"]["blocked"] == 1
    assert len(rows) == 2 and all(Path(row["original_path"]).is_file() for row in rows)
    audit = json.loads((tmp_path / "review-audit.json").read_text("utf8"))["items"]
    assert sorted(item["status"] for item in audit.values()) == ["accepted", "blocked"]


def test_blocked_review_retries_only_unfinished_images(tmp_path):
    task, rows = seed_search_rows(tmp_path, 2)
    first = FakeReviewAgent(fail_first=True)
    worker.review_candidates(task, first, tmp_path, history=None)
    second = FakeReviewAgent()
    manifest, _, summary = worker.review_candidates(task, second, tmp_path, history=None)
    assert first.review_calls == 2
    assert second.review_calls == 1
    assert len(manifest["candidates"]) == 2
    assert summary["counts"]["accepted"] == 2


def test_human_decision_is_not_overwritten_by_ai_review(tmp_path, monkeypatch):
    task, rows = seed_search_rows(tmp_path, 2)
    monkeypatch.setattr(collection_queue, "run_directory", lambda job_id: tmp_path)
    collection_queue.write_json(collection_queue.decide_path(tmp_path),
                                {"version": 1, "items": {rows[0]["asset_sha"]: {"decision": "keep", "at": time.time()}}})
    agent = FakeReviewAgent()
    worker.review_candidates(task, agent, tmp_path, history=None)
    assert agent.review_calls == 1
    snapshot = collection_queue.snapshot("seed-job")
    statuses = {item["asset_sha"]: item["status"] for item in snapshot["items"]}
    assert statuses[rows[0]["asset_sha"]] == "human_keep"
    assert statuses[rows[1]["asset_sha"]] == "accepted"


def test_cancelling_review_does_not_stop_search_or_delete_candidates(
        tmp_path, library, project, client, monkeypatch):
    isolate_queue(tmp_path, monkeypatch)
    adapter(tmp_path, monkeypatch)
    monkeypatch.setenv("FAKE_SEARCH_SLEEP", "1")
    job = create_job(client, project, "search_review", 2)
    assert client.post(f"/api/jobs/{job['id']}/start").status_code == 200
    wait_until(lambda: library.job(job["id"])["review_state"] == "running", timeout=10)
    cancel = client.post(f"/api/jobs/{job['id']}/review/cancel")
    assert cancel.status_code == 200, cancel.text
    assert cancel.json()["review_state"] == "cancelled"
    wait_until(lambda: library.job(job["id"])["search_state"] == "completed", timeout=20)
    body = stages(client, job["id"])
    assert body["counts"]["found"] >= 2
    assert body["counts"]["accepted"] == 0
    assert library.job(job["id"])["review_state"] == "cancelled"


def test_human_reject_after_ai_accept_is_excluded_from_the_formal_package(tmp_path):
    task, rows = seed_search_rows(tmp_path, 2)
    agent = FakeReviewAgent()
    manifest, images, _ = worker.review_candidates(task, agent, tmp_path, history=None)
    result_path = tmp_path / "review-result.zip"
    worker.write_result(result_path, manifest, images)
    collection_queue.write_json(collection_queue.decide_path(tmp_path), {
        "version": 1, "items": {rows[0]["asset_sha"]: {"decision": "reject", "at": time.time()}}})
    agent2 = FakeReviewAgent()
    manifest2, images2, summary2 = worker.review_candidates(task, agent2, tmp_path, history=None)
    assert agent2.review_calls == 0
    assert len(manifest2["candidates"]) == 1
    assert manifest2["candidates"][0]["id"] == "verified-" + rows[1]["asset_sha"][:20]
    assert summary2["counts"]["human_reject"] == 1
    from ref_lab.agent_collection import _read_result
    previous = _read_result(result_path, task["id"])
    worker.write_result(result_path, manifest2, images2, previous_result=previous,
                        allow_omitted={"verified-" + rows[0]["asset_sha"][:20]})
    assert len(json.loads(__import__("zipfile").ZipFile(result_path).read("manifest.json"))["candidates"]) == 1
    assert Path(rows[0]["original_path"]).is_file()


def test_vision_error_marks_only_that_candidate_blocked_and_keeps_originals(
        tmp_path, library, project, client, monkeypatch):
    isolate_queue(tmp_path, monkeypatch)
    adapter(tmp_path, monkeypatch)
    monkeypatch.setenv("FAKE_REVIEW_BLOCK_ONE", "1")
    job = create_job(client, project, "search_review", 2)
    assert client.post(f"/api/jobs/{job['id']}/start").status_code == 200
    wait_until(lambda: library.job(job["id"])["search_state"] == "completed", timeout=20)
    wait_until(lambda: library.job(job["id"])["review_state"] in {"completed", "partial", "blocked"}, timeout=20)
    wait_until(lambda: library.job(job["id"]).get("review_imported_ids"), timeout=20)
    body = stages(client, job["id"])
    assert body["counts"]["found"] >= 2
    assert body["counts"]["accepted"] >= 1
    assert body["counts"]["blocked"] >= 1
    assert all((tmp_path / "q" / "images").glob("*.png"))
    final = library.job(job["id"])
    assert len(final["review_imported_ids"]) == body["counts"]["accepted"]
    assert final["search_state"] == "completed"


def test_partial_search_exit_keeps_originals_and_a_second_search_continues_the_same_job(
        tmp_path, library, project, client, monkeypatch):
    isolate_queue(tmp_path, monkeypatch)
    adapter(tmp_path, monkeypatch)
    # First adapter pass writes one original and exits non-zero without a summary.
    monkeypatch.setenv("FAKE_SEARCH_PARTIAL", "1")
    job = create_job(client, project, "search", 2)
    assert client.post(f"/api/jobs/{job['id']}/search").status_code == 200
    wait_until(lambda: library.job(job["id"])["search_state"] == "blocked", timeout=20)
    body = stages(client, job["id"])
    assert body["counts"]["found"] == 1
    # Resume the same job: another attempt may append, but the first original survives.
    monkeypatch.delenv("FAKE_SEARCH_PARTIAL", raising=False)
    from ref_lab import collection_stages
    wait_until(lambda: (job["id"], "search") not in collection_stages._RUNNING, timeout=10)
    assert client.post(f"/api/jobs/{job['id']}/search").status_code == 200
    wait_until(lambda: library.job(job["id"])["search_state"] == "completed", timeout=20)
    body = stages(client, job["id"])
    assert body["counts"]["found"] >= 2
    originals = [item["asset_sha"] for item in body["items"]]
    assert len(originals) == len(set(originals))
    for item in body["items"]:
        _, raw = collection_queue.original_bytes(job["id"], item["asset_sha"])
        assert hashlib.sha256(raw).hexdigest() == item["asset_sha"]


def test_partial_search_summary_is_accepted_as_the_stage_receipt(
        tmp_path, library, project, client, monkeypatch):
    """A finished search that fell short writes status=partial; the service must
    keep that receipt instead of reporting a missing summary."""
    isolate_queue(tmp_path, monkeypatch)
    adapter(tmp_path, monkeypatch)
    monkeypatch.setenv("FAKE_SEARCH_PARTIAL_SUMMARY", "1")
    monkeypatch.setenv("FAKE_SEARCH_PARTIAL", "1")     # one original, target not reached
    job = create_job(client, project, "search", 2)
    assert client.post(f"/api/jobs/{job['id']}/search").status_code == 200
    wait_until(lambda: library.job(job["id"])["search_state"] in {"partial", "blocked"}, timeout=20)
    current = library.job(job["id"])
    assert current["search_state"] == "partial"
    assert current["search_stop_reason"] == "target_partial"
    assert current["search_counts"]["found"] == 1
    assert current["search_counts"]["usable_named"] == 1
    body = stages(client, job["id"])
    assert body["counts"]["found"] == 1


def test_stage_endpoints_keep_search_complete_while_review_is_blocked(
        tmp_path, library, project, client, monkeypatch):
    isolate_queue(tmp_path, monkeypatch)
    adapter(tmp_path, monkeypatch)
    release = tmp_path / "release-review"
    monkeypatch.setenv("FAKE_REVIEW_RELEASE", str(release))
    job = create_job(client, project, "search_review", 2)
    assert client.post(f"/api/jobs/{job['id']}/start").status_code == 200
    wait_until(lambda: library.job(job["id"])["search_state"] == "completed", timeout=20)
    current = library.job(job["id"])
    assert current["review_state"] == "running"
    body = stages(client, job["id"])
    assert body["counts"]["found"] >= 2
    assert current["search_stop_reason"] == "target_reached"
    release.write_text("release", encoding="utf8")
    wait_until(lambda: library.job(job["id"])["review_state"] in {"completed", "partial", "blocked"}, timeout=20)
    wait_until(lambda: library.job(job["id"]).get("review_imported_ids"), timeout=20)
    final = library.job(job["id"])
    assert final["search_state"] == "completed"
    assert final["review_state"] in {"completed", "partial"}
    body = stages(client, job["id"])
    assert body["counts"]["found"] >= 2
    assert body["counts"]["accepted"] >= 2
    assert final["review_imported_ids"]


def test_queue_survives_a_new_server_process_and_human_decision(tmp_path, library, project, client, monkeypatch):
    isolate_queue(tmp_path, monkeypatch)
    adapter(tmp_path, monkeypatch)
    job = create_job(client, project, "search", 2)
    assert client.post(f"/api/jobs/{job['id']}/search").status_code == 200
    wait_until(lambda: library.job(job["id"])["search_state"] == "completed", timeout=20)
    body = stages(client, job["id"])
    assert body["counts"]["found"] >= 2
    sha = body["items"][0]["asset_sha"]
    decision = client.post(f"/api/jobs/{job['id']}/candidates/{sha}/decision", json={"decision": "reject"})
    assert decision.status_code == 200, decision.text
    assert decision.json()["items"][0]["status"] == "human_reject"
    # A fresh app over the same data directory must still see the original and decision.
    from ref_lab.api import create_app
    from fastapi.testclient import TestClient
    from conftest import TOKEN
    with TestClient(create_app(library.settings)) as fresh:
        auth = fresh.post("/api/session", json={"token": TOKEN})
        assert auth.status_code == 200, auth.text
        fresh.headers["X-Lab-CSRF"] = auth.json()["csrf"]
        body2 = fresh.get(f"/api/jobs/{job['id']}/candidates").json()
        assert body2["counts"]["found"] == body["counts"]["found"]
        assert any(item["asset_sha"] == sha and item["status"] == "human_reject" for item in body2["items"])
