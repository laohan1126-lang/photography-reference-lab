from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from ref_lab import collection_postprocess
from ref_lab.agent_collection import AttemptFileLock
from tools import collect_verified as worker


def _image(folder: Path, name: str, color) -> tuple[Path, str]:
    path = folder / "images" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (640, 960), color).save(path, "PNG")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


class _History:
    known_shas = set()
    records = {}
    known_count = 0
    initial_count = 0
    ready = True
    errors = []
    library_keepers = {}
    attributed_run_dirs = []
    discovery_roots = []
    baseline_sha = ""

    def consider(self, path):
        raise AssertionError("pure search must not run perceptual history comparison")

    def close(self, **kwargs):
        pass


def test_download_target_callback_processes_each_returned_row_once(tmp_path):
    paths = []
    rows = []
    for index, color in enumerate(((40, 90, 140), (140, 90, 40)), 1):
        path, sha = _image(tmp_path, f"{index}.png", color)
        paths.append(path)
        rows.append({"asset_sha": sha, "original_path": str(path),
                     "page_url": "https://example.org/post", "image_url": f"https://example.org/{index}.png",
                     "width": 640, "height": 960, "source_text": "角色 cosplay", "image_index": index})
    delivered = []

    class Browser:
        supports_sort = False
        known_shas = set()
        known_sources = None
        incoming_dir = tmp_path / "incoming"
        return_failed = False
        return_error = None

        def start(self): pass
        def search(self, step):
            from urllib.parse import quote
            return {"url": "https://example.org/search?q=" + quote(step["query"]), "search": step["query"],
                    "visibleMain": "", "cards": [{"page": "https://example.org/post",
                                                    "text": "测试角色 cosplay"}]}
        def receive(self, card, step):
            callback = getattr(self, "_record_callback", None)
            for row in rows:
                delivered.append(row)
                if callback: callback(row)
            return rows
        def close(self): pass

    class Agent:
        producer = "synthetic"
        model = "synthetic"
        candidate_calls = 0
        references = []
        deadline = float("inf")

    job = {"id": "callback-job", "project_id": "project-callback", "collection_mode": "search",
           "download_target_count": 2, "target_count": 2,
           "project_snapshot": {"id": "project-callback", "character": "测试角色", "work": "", "costume": ""},
           "preferred_sources": ["xiaohongshu"], "search_attempt_started_at": worker.time.time()}
    summary, _ = worker.collect(job, Agent(), Browser(), tmp_path, history=_History(), search_only=True,
                                defer_postprocess=True)
    received = json.loads((tmp_path / "received.json").read_text("utf8"))
    assert delivered == rows
    assert [item["asset_sha"] for item in received] == [item["asset_sha"] for item in rows]
    assert all(item["original_path"] == str(path.resolve()) for item, path in zip(received, paths))
    assert summary["status"] == "completed"
    assert summary["download_target_reached"] is True
    assert summary["target_reached"] is False
    assert summary["counts"]["target_progress"] == 0
    assert not json.loads((tmp_path / "duplicates.json").read_text("utf8"))


def test_exact_library_reuse_does_not_consume_new_download_target(tmp_path):
    rows = []
    for index, color in enumerate(((80, 40, 120), (30, 130, 80)), 1):
        path, sha = _image(tmp_path, f"reuse-{index}.png", color)
        rows.append({"asset_sha": sha, "original_path": str(path),
                     "page_url": "https://example.org/post", "image_url": f"https://example.org/reuse-{index}.png",
                     "width": 640, "height": 960, "source_text": "其他项目 cosplay", "image_index": index})

    class Browser:
        supports_sort = False
        known_shas = set()
        known_sources = None
        incoming_dir = tmp_path / "incoming"
        return_failed = False
        return_error = None
        def start(self): pass
        def search(self, step):
            from urllib.parse import quote
            return {"url": "https://example.org/search?q=" + quote(step["query"]), "search": step["query"],
                    "visibleMain": "", "cards": [{"page": "https://example.org/post", "text": "角色 cosplay"}]}
        def receive(self, card, step):
            callback = getattr(self, "_record_callback", None)
            for row in rows:
                if callback: callback(row)
            return rows
        def close(self): pass

    class Agent:
        producer = model = "synthetic"
        candidate_calls = 0
        references = []
        deadline = float("inf")

    history = _History()
    history.library_keepers = {rows[0]["asset_sha"]: str(tmp_path / "other-project.png")}
    job = {"id": "reuse-job", "project_id": "project-reuse", "collection_mode": "search",
           "download_target_count": 1, "target_count": 1,
           "project_snapshot": {"id": "project-reuse", "character": "角色", "work": "", "costume": ""},
           "preferred_sources": ["xiaohongshu"]}
    summary, _ = worker.collect(job, Agent(), Browser(), tmp_path, history=history,
                                search_only=True, defer_postprocess=True)
    received = json.loads((tmp_path / "received.json").read_text("utf8"))
    assert len(received) == 2
    assert received[0]["original_reuse"]["reason"] == "same_bytes_library"
    assert summary["new_downloads"] == 1
    assert summary["counts"]["reused_originals"] == 1
    assert summary["status"] == "completed" and summary["download_target_reached"] is True


def test_deferred_pure_search_never_constructs_embedded_workers(tmp_path, monkeypatch):
    from ref_lab import collage, photo_types
    from ref_lab.collection_history import DEDUP_SCOPE_VERSION, FINGERPRINT_ALGORITHM_VERSION

    baseline = {"goal_id": "real-goal", "fingerprint_algorithm_version": FINGERPRINT_ALGORITHM_VERSION,
                "project_id": "project-worker-guard", "dedup_scope_version": DEDUP_SCOPE_VERSION, "items": []}
    raw_baseline = json.dumps(baseline).encode()
    baseline_sha = hashlib.sha256(raw_baseline).hexdigest()
    (tmp_path / "baseline.json").write_bytes(raw_baseline)
    (tmp_path / "goal.json").write_text(json.dumps({
        "goal_id": "real-goal", "baseline_sha": baseline_sha, "baseline_shas": [], "started_at": 0.0,
        "target": 1, "project_id": "project-worker-guard", "dedup_scope_version": DEDUP_SCOPE_VERSION}), "utf8")
    path, sha = _image(tmp_path, "guarded.png", (10, 70, 130))
    row = {"asset_sha": sha, "original_path": str(path), "page_url": "https://example.org/post",
           "image_url": "https://example.org/guarded.png", "width": 640, "height": 960,
           "source_text": "角色 cosplay", "image_index": 1}

    class Browser:
        supports_sort = False
        known_shas = set(); known_sources = None; incoming_dir = tmp_path / "incoming"
        return_failed = False; return_error = None
        def start(self): pass
        def search(self, step):
            from urllib.parse import quote
            return {"url": "https://example.org/search?q=" + quote(step["query"]), "search": step["query"],
                    "visibleMain": "", "cards": [{"page": "https://example.org/post", "text": "角色 cosplay"}]}
        def receive(self, card, step): return [row]
        def close(self): pass

    class Agent:
        producer = model = "synthetic"; candidate_calls = 0; references = []; deadline = float("inf")

    def forbidden(*args, **kwargs):
        raise AssertionError("deferred Search constructed an embedded post-process worker")
    monkeypatch.setattr(photo_types, "PhotoTypeWorker", forbidden)
    monkeypatch.setattr(collage, "CollageWorker", forbidden)
    history = _History(); history.baseline_sha = baseline_sha
    job = {"id": "worker-guard", "project_id": "project-worker-guard", "goal_id": "real-goal",
           "collection_mode": "search", "download_target_count": 1, "target_count": 1,
           "project_snapshot": {"id": "project-worker-guard", "character": "角色", "work": "", "costume": ""},
           "preferred_sources": ["xiaohongshu"]}
    summary, _ = worker.collect(job, Agent(), Browser(), tmp_path, history=history,
                                search_only=True, defer_postprocess=True)
    assert summary["status"] == "completed" and summary["new_downloads"] == 1


def _postprocess_fixture(tmp_path, monkeypatch, *, type_blocked=False):
    path, sha = _image(tmp_path, "one.png", (20, 80, 140))
    row = {"asset_sha": sha, "original_path": str(path), "page_url": "https://example.org/post",
           "image_url": "https://example.org/image.png", "width": 640, "height": 960}
    (tmp_path / "received.json").write_text(json.dumps([row]), "utf8")
    (tmp_path / "goal.json").write_text(json.dumps({"baseline_sha": "a" * 64}), "utf8")
    (tmp_path / "search-summary.json").write_text(json.dumps({"status": "completed"}), "utf8")
    calls = []

    class Collage:
        def __init__(self, *args, **kwargs):
            self._queue = SimpleNamespace(unfinished_tasks=0)
            self.errors = []
        def enqueue(self, row): self._queue.unfinished_tasks = 1
        def drain(self, timeout=None):
            calls.append(("collage", timeout))
            self._queue.unfinished_tasks = 0
        def close(self, timeout=None): pass
        def summary(self): return {"originals": 1}

    class Types:
        def __init__(self, *args, **kwargs):
            self.pending = SimpleNamespace(unfinished_tasks=1)
            self.blocked = False
            self.block_reason = ""
            self.stop = SimpleNamespace(set=lambda: None)
        def enqueue(self, record): self.pending.unfinished_tasks = 1
        def drain(self, timeout=None):
            calls.append(("types", timeout))
            self.pending.unfinished_tasks = 0
            self.blocked = type_blocked
            self.block_reason = "model_unavailable" if type_blocked else ""
        def close(self, timeout=None): pass

    monkeypatch.setattr(collection_postprocess, "CollageWorker", Collage)
    monkeypatch.setattr("ref_lab.photo_types.PhotoTypeWorker", Types)
    monkeypatch.setattr("tools.collect_verified._history_for_search",
                        lambda folder, project_id: _History())
    job = {"project_id": "project", "target_count": 1}
    return job, calls


def test_postprocess_waits_for_type_queue_and_marks_blocked_receipts(tmp_path, monkeypatch):
    job, calls = _postprocess_fixture(tmp_path, monkeypatch)
    state = collection_postprocess.run_postprocess_job(job, tmp_path)
    assert state["phase"] == "complete"
    assert any(name == "types" and timeout is not None and timeout > 0 for name, timeout in calls)

    other = tmp_path / "blocked"
    other.mkdir()
    job2, _ = _postprocess_fixture(other, monkeypatch, type_blocked=True)
    blocked = collection_postprocess.run_postprocess_job(job2, other)
    assert blocked["phase"] == "blocked"
    assert blocked["reason"] == "model_unavailable"


def test_duplicate_postprocess_lock_does_not_overwrite_owner_state(tmp_path):
    state_path = tmp_path / "postprocess.json"
    original = {"phase": "running", "owner": {"pid": 1234}, "reason": "still_owned"}
    state_path.write_text(json.dumps(original), "utf8")
    lock = AttemptFileLock(tmp_path / "postprocess.lock")
    assert lock.acquire()
    try:
        result = collection_postprocess.run_postprocess_job({"target_count": 1}, tmp_path)
    finally:
        lock.release()
    assert result["lock_contended"] is True
    assert json.loads(state_path.read_text("utf8")) == original


def test_background_retry_waits_for_its_own_search_receipt(tmp_path, monkeypatch):
    job, calls = _postprocess_fixture(tmp_path, monkeypatch)
    job['search_attempt_started_at'] = 20.0
    read_json = collection_postprocess.collection_queue.read_json
    polls = []

    def read_receipt(path, default):
        if Path(path).name == 'search-summary.json':
            polls.append(len(calls))
            return {'status': 'completed', 'finished_at': 10.0 if len(polls) < 5 else 30.0}
        return read_json(path, default)

    monkeypatch.setattr(collection_postprocess.collection_queue, 'read_json', read_receipt)
    result = collection_postprocess.run_postprocess_job(job, tmp_path)
    assert result['phase'] == 'complete'
    assert len(polls) >= 5
    assert polls[:5] == [0, 0, 0, 0, 0]
    assert any(name == 'types' for name, _ in calls)


def test_manager_receipt_cannot_infer_success():
    assert collection_postprocess.manager_receipt_state(1, {"phase": "complete"})["state"] == "blocked"
    assert collection_postprocess.manager_receipt_state(0, {})["reason"] == "postprocess_receipt_missing"
    assert collection_postprocess.manager_receipt_state(0, {"phase": "blocked", "reason": "budget"}) == {
        "state": "blocked", "phase": "blocked", "reason": "budget", "exit_code": 0}
    assert collection_postprocess.manager_receipt_state(0, {"phase": "complete"})["state"] == "complete"


def test_live_import_survives_postprocess_process_start_failure(tmp_path, monkeypatch):
    folder = tmp_path / "job"
    folder.mkdir()
    (folder / "received.json").write_text("[]", "utf8")
    monkeypatch.setattr(collection_postprocess.collection_queue, "run_directory", lambda job_id: folder)
    calls = []

    class Library:
        def job(self, job_id): return {"status": "running", "search_state": "running"}
        def import_search_candidates(self, job_id):
            calls.append(job_id)
            return {"created": 0, "errors": 0}

    def fail_start(*args, **kwargs):
        raise OSError("synthetic postprocess start failure")
    monkeypatch.setattr(collection_postprocess.subprocess, "Popen", fail_start)
    manager = collection_postprocess.PostprocessManager(Library(), "job")
    manager.start()
    deadline = worker.time.monotonic() + 2
    while len(calls) < 1 and worker.time.monotonic() < deadline: worker.time.sleep(.01)
    (folder / "received.json").write_text("[{\"asset_sha\":\"a\"}]")
    while len(calls) < 2 and worker.time.monotonic() < deadline: worker.time.sleep(.01)
    try:
        assert len(calls) >= 2
        state = json.loads((folder / "postprocess-manager.json").read_text("utf8"))
        assert state["state"] == "running" and state["postprocess_state"] == "blocked"
    finally:
        manager.stop()


def test_restart_history_excludes_current_job_refs_and_keeps_human_choice(tmp_path, monkeypatch):
    from ref_lab import collage
    from ref_lab.config import Settings
    from ref_lab.models import CandidateInput, JobInput, ProjectInput, ReferenceEdit
    from ref_lab.service import Library

    root = tmp_path / "root"
    data_dir = root / ".local"
    data_dir.mkdir(parents=True)
    monkeypatch.setattr(worker, "ROOT", root)
    monkeypatch.setattr(worker.subprocess, "check_output", lambda *args, **kwargs: ".git")
    library = Library(Settings(data_dir=data_dir, token="x" * 32, no_auth=True))
    project = library.create_project(ProjectInput(character="重启用例"))
    job = library.create_job(project["id"], JobInput(kind="collection", collection_mode="search", target_count=10))
    folder = data_dir / "collection-runs" / job["id"] / "current"
    (folder / "images").mkdir(parents=True)
    (folder / "derived").mkdir()
    rows = []
    refs = []
    originals = []
    for index in range(10):
        image = Image.new("RGB", (640, 960), (20 + index, 60, 120))
        from io import BytesIO
        stream = BytesIO(); image.save(stream, "PNG"); raw = stream.getvalue()
        asset = library.ingest_asset(raw, f"{index}.png")
        ref = library.add_candidate(project["id"], CandidateInput(
            asset_sha=asset["id"], title=f"current {index}", job_id=job["id"]) )["reference"]
        refs.append(ref)
        path = folder / "images" / f"{asset['id']}.png"
        originals.append((path, raw))
        rows.append({"asset_sha": asset["id"], "original_path": str(path),
                     "page_url": f"https://example.org/{index}", "image_url": f"https://example.org/{index}.png",
                     "search_query": "重启用例", "acquired_at": worker.time.time()})
    (folder / "images").mkdir(parents=True, exist_ok=True)
    for path, raw in originals:
        path.write_bytes(raw)
    child_stream = __import__("io").BytesIO()
    Image.new("RGB", (640, 960), (220, 40, 60)).save(child_stream, "PNG")
    child_raw = child_stream.getvalue()
    child = library.ingest_asset(child_raw, "derived.png")
    derived_path = folder / "derived" / f"{child['id']}.png"
    derived_path.write_bytes(child_raw)
    (folder / "derived.json").write_text(json.dumps({"version": 1, "items": {rows[0]["asset_sha"]: {
        "parent_sha": rows[0]["asset_sha"], "algorithm_version": collage.ALGORITHM_VERSION,
        "status": collage.STATUS_SPLIT_OK, "children": [{
            "parent_sha": rows[0]["asset_sha"], "child_sha": child["id"], "status": collage.VALID,
            "path": str(derived_path), "size": [640, 960]}]
    }}}), "utf8")
    library.add_candidate(project["id"], CandidateInput(
        asset_sha=child["id"], title="current derived", job_id=job["id"], discovery_intent="exact_character"))
    (folder / "received.json").write_text(json.dumps(rows), "utf8")
    kept = library.edit_reference(refs[0]["id"], ReferenceEdit(expected_revision=refs[0]["revision"], decision="keep"))

    history = worker._history_for_search(folder, project["id"])
    try:
        assert all(row["asset_sha"] not in history.records for row in rows)
        assert all(row["asset_sha"] not in history.known_shas for row in rows)
        assert child["id"] not in history.records
        assert child["id"] not in history.known_shas
    finally:
        history.close(wait=False, timeout=1)
    assert library.reference(kept["id"])["decision"] == "keep"
