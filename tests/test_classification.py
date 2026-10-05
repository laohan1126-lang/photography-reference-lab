"""Queue regressions use synthetic pixels and a fake analyzer, not visual accuracy."""
import json
import time
from dataclasses import replace

from conftest import add_reference
from ref_lab.classification import ClassificationQueue, ClassificationResult, ClassificationWorker
from ref_lab.library_browser import AnnotationInput, BrowseFilters, LibraryBrowser
from ref_lab.providers import ProviderError


class Analyzer:
    producer_name = "synthetic-test"
    def __init__(self, callback=None):
        self.calls = []
        self.callback = callback
    def classify(self, image, sha, stop):
        self.calls.append((image, sha))
        if self.callback:
            self.callback()
        return ClassificationResult(asset_sha=sha, viewpoint="low_angle",
            framing="full_body", pose="standing", evidence="Synthetic test only.")


def keep(client, ref):
    response = client.patch(f"/api/references/{ref['id']}",
        json={"expected_revision": ref["revision"], "decision": "keep"})
    assert response.status_code == 200
    return response.json()


def queue(library):
    return ClassificationQueue(LibraryBrowser(library))


def test_keep_and_existing_backlog_classify_once_across_projects(client, project, library):
    ref = add_reference(client, project)
    q = queue(library)
    assert q.discover() == 0
    kept = keep(client, ref)
    assert q.discover() == 1
    other = client.post("/api/projects", json={"character": "Other"}).json()
    use = client.post(f"/api/projects/{other['id']}/references",
        json={"asset_sha": ref["asset_sha"]}).json()["reference"]
    keep(client, use)
    assert q.discover() == 0
    a = Analyzer()
    assert q.run_one(a)
    assert not q.run_one(a)
    assert len(a.calls) == 1 and a.calls[0][0]
    found = LibraryBrowser(library).browse(BrowseFilters(viewpoint="low_angle"))
    assert found["total"] == 1
    assert found["items"][0]["annotation"]["actor"] == "ai"
    assert library.reference(ref["id"]) == kept
    assert queue(library).discover() == 0


def test_manual_annotation_wins_during_model_call(client, project, library):
    ref = keep(client, add_reference(client, project))
    q = queue(library)
    q.discover()
    b = LibraryBrowser(library)
    a = Analyzer(lambda: b.annotate(ref["asset_sha"],
        AnnotationInput(expected_revision=0, viewpoint="high_angle")))
    q.run_one(a)
    item = b.browse(BrowseFilters())["items"][0]["annotation"]
    assert item["actor"] == "human" and item["viewpoint"] == "high_angle"
    assert q.status()["counts"]["superseded"] == 1
    assert q.discover() == 0


def test_existing_human_annotations_are_never_enqueued(client, project, library):
    ref = keep(client, add_reference(client, project))
    LibraryBrowser(library).annotate(ref["asset_sha"], AnnotationInput(expected_revision=0))
    q = queue(library)
    assert q.discover() == 0


def test_failed_job_is_visible_and_explicitly_retryable(client, project, library):
    keep(client, add_reference(client, project))
    q = queue(library)
    q.discover()
    class Broken:
        producer_name = "synthetic"
        def classify(self, *args):
            raise ProviderError("Synthetic provider unavailable")
    assert q.run_one(Broken())
    assert q.status()["counts"]["failed"] == 1
    assert not q.run_one(Analyzer())
    assert q.retry_failed() == 1
    q.run_one(Analyzer())
    assert q.status()["counts"]["succeeded"] == 1


def test_expired_claim_recovers_but_active_claim_is_not_stolen(client, project, library):
    keep(client, add_reference(client, project))
    q = queue(library)
    q.discover()
    job = q.claim()
    assert job and queue(library).claim() is None
    with library.db.transaction() as con:
        con.execute("UPDATE library_classification_jobs SET lease_until=0")
    assert queue(library).run_one(Analyzer())
    assert not q.finish(job, ClassificationResult(asset_sha=job["asset_sha"],
        viewpoint="eye_level", evidence="Stale synthetic result"), "synthetic")
    assert q.status()["counts"]["succeeded"] == 1


def test_removed_keep_drops_pending_work_but_active_inspiration_is_eligible(client, project, library):
    ref = keep(client, add_reference(client, project))
    q = queue(library)
    q.discover()
    client.patch(f"/api/references/{ref['id']}",
        json={"expected_revision": ref["revision"], "decision": "pending"})
    a = Analyzer()
    assert not q.run_one(a)
    assert not a.calls
    client.post("/api/inspirations", json={"asset_sha": ref["asset_sha"], "title": "Saved"})
    assert q.discover() == 1
    q.run_one(a)
    assert len(a.calls) == 1


def test_reject_during_analysis_does_not_publish_result(client, project, library):
    ref = keep(client, add_reference(client, project))
    q = queue(library)
    q.discover()
    def reject():
        client.patch(f"/api/references/{ref['id']}",
            json={"expected_revision": ref["revision"], "decision": "reject"})
    q.run_one(Analyzer(reject))
    with library.db.read() as con:
        assert con.execute("SELECT count(*) FROM library_annotations").fetchone()[0] == 0


def test_worker_starts_and_stops_with_application(settings):
    from fastapi.testclient import TestClient
    from ref_lab.api import create_app
    app = create_app(replace(settings, auto_classify=True), classifier=Analyzer())
    worker = app.state.classification_worker
    with TestClient(app):
        assert worker.thread.is_alive()
    assert not worker.thread.is_alive()


def test_status_endpoint_reports_disabled_without_claiming_model_execution(client):
    status = client.get("/api/library/classification").json()
    assert status["enabled"] is False
    assert status["counts"].get("succeeded", 0) == 0

def test_corrupt_original_never_reaches_model(client, project, library):
    ref = keep(client, add_reference(client, project))
    q = queue(library)
    q.discover()
    library.assets.path(library.asset(ref["asset_sha"])).write_bytes(b"changed")
    a = Analyzer()
    q.run_one(a)
    assert not a.calls
    assert q.status()["counts"]["failed"] == 1


def test_image_read_receipt_and_schema_are_required(tmp_path):
    import pytest
    from ref_lab.classification import parse_vision_stream
    path = tmp_path / "image.jpg"
    result = ClassificationResult(asset_sha="a"*64, evidence="Synthetic", pose="seated")
    done = {"event": "result", "result": {"status": "SUCCESS", "response": result.model_dump_json()}}
    with pytest.raises(ProviderError):
        parse_vision_stream(json.dumps(done), path)
    opened = {"event": "step_update", "step_update": {"tool_name": "view_file", "state": "DONE",
        "tool_info": {"parameters": {"AbsolutePath": str(path)}}}}
    stream = json.dumps(opened)+"\n"+json.dumps(done)
    assert parse_vision_stream(stream, path).pose == "seated"
    with pytest.raises(ProviderError):
        parse_vision_stream(stream, tmp_path/"other.jpg")
    done["result"]["response"] = json.dumps({**result.model_dump(), "pose": "invented"})
    with pytest.raises(ProviderError):
        parse_vision_stream(json.dumps(opened)+"\n"+json.dumps(done), path)


def test_late_failure_does_not_overwrite_new_attempt(client, project, library):
    keep(client, add_reference(client, project))
    q = queue(library)
    q.discover()
    def replace_attempt():
        with library.db.transaction() as con:
            con.execute("UPDATE library_classification_jobs SET attempt='new-owner',status='running'")
        raise ProviderError("Old failure")
    q.run_one(Analyzer(replace_attempt))
    assert q.status()["counts"]["running"] == 1


def test_worker_pauses_on_failure_and_stops_promptly(client, project, library):
    import threading
    ref = keep(client, add_reference(client, project))
    started = threading.Event()
    class Blocking:
        producer_name = "synthetic"
        def classify(self, image, sha, stop):
            started.set()
            stop.wait(10)
            raise InterruptedError()
    q = queue(library)
    worker = ClassificationWorker(q, Blocking())
    worker.start()
    assert started.wait(5)
    worker.stop()
    assert not worker.thread.is_alive()
    assert q.status()["counts"]["pending"] == 1

def test_runtime_worker_detects_new_keep_without_an_extra_button(settings):
    from fastapi.testclient import TestClient
    from ref_lab.api import create_app
    a = Analyzer()
    app = create_app(replace(settings, no_auth=True, auto_classify=True), classifier=a)
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"character":"Auto"}).json()
        ref = add_reference(client, project)
        time.sleep(0.1)
        assert not a.calls
        keep(client, ref)
        deadline = time.monotonic() + 7
        while time.monotonic() < deadline:
            status = client.get(f"/api/library/assets/{ref['asset_sha']}/classification").json()
            if status["annotation"]["actor"] == "ai":
                break
            time.sleep(0.1)
        assert status["annotation"]["pose"] == "standing"
        assert len(a.calls) == 1
