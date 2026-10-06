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
        return ClassificationResult(asset_sha=sha, kind="cosplay_photo", viewpoint="low_angle",
            framing="full_body", pose="standing", evidence="Synthetic test only.")


def keep(client, ref):
    response = client.patch(f"/api/references/{ref['id']}",
        json={"expected_revision": ref["revision"], "decision": "keep"})
    assert response.status_code == 200
    return response.json()


def queue(library):
    return ClassificationQueue(LibraryBrowser(library))


def test_browsable_assets_classify_once_across_projects(client, project, library):
    ref = add_reference(client, project)
    q = queue(library)
    assert q.discover() == 1  # Pending pictures are searchable library members too.
    kept = keep(client, ref)
    assert q.discover() == 0
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
    assert q.discover() == 1  # Only the missing type remains, not the human facets.
    q.run_one(Analyzer())
    assert b.browse(BrowseFilters())["items"][0]["annotation"] == item
    assert q.discover() == 0


def test_complete_human_annotations_are_never_enqueued(client, project, library):
    ref = keep(client, add_reference(client, project))
    LibraryBrowser(library).annotate(ref["asset_sha"], AnnotationInput(expected_revision=0,kind="unknown",expected_kind_id=""))
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
    assert not q.finish(job, ClassificationResult(asset_sha=job["asset_sha"], kind="unknown",
        viewpoint="eye_level", evidence="Stale synthetic result"), "synthetic")
    assert q.status()["counts"]["succeeded"] == 1


def test_rejection_drops_pending_work_but_active_inspiration_is_eligible(client, project, library):
    ref = keep(client, add_reference(client, project))
    q = queue(library)
    q.discover()
    client.patch(f"/api/references/{ref['id']}",
        json={"expected_revision": ref["revision"], "decision": "reject"})
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
    result = ClassificationResult(asset_sha="a"*64, kind="unknown", evidence="Synthetic", pose="seated")
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

def test_runtime_worker_detects_pending_candidate_without_an_extra_button(settings):
    from fastapi.testclient import TestClient
    from ref_lab.api import create_app
    a = Analyzer()
    app = create_app(replace(settings, no_auth=True, auto_classify=True), classifier=a)
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"character":"Auto"}).json()
        ref = add_reference(client, project)
        time.sleep(0.1)
        deadline = time.monotonic() + 7
        while time.monotonic() < deadline:
            status = client.get(f"/api/library/assets/{ref['asset_sha']}/classification").json()
            if status["annotation"]["actor"] == "ai":
                break
            time.sleep(0.1)
        assert status["annotation"]["pose"] == "standing"
        assert len(a.calls) == 1

def test_auto_classification_populates_kind_and_pose_in_one_pass(client, project, library):
    ref = keep(client, add_reference(client, project))
    q = queue(library)
    q.discover()
    q.run_one(Analyzer())
    r = client.get("/api/library/assets", params={"kind":"cosplay_photo","pose":"standing"}).json()
    assert r["total"] == 1
    assert r["items"][0]["kind_actor"] == "ai"
    assert library.reference(ref["id"])["review"] is None
    assert library.reference(ref["id"])["card"] is None


def test_old_three_facet_result_is_completed_without_resetting_human_choices(client, project, library):
    from ref_lab.db import encode
    ref = keep(client, add_reference(client, project))
    q = queue(library)
    q.discover()
    q.run_one(Analyzer())
    with library.db.transaction() as con:
        con.execute("DELETE FROM asset_observations WHERE asset_sha=?", (ref["asset_sha"],))
    assert q.discover() == 1
    q.run_one(Analyzer())
    assert client.get("/api/library/assets",params={"kind":"cosplay_photo","pose":"standing"}).json()["total"] == 1
    assert q.discover() == 0


def test_manual_facets_get_missing_type_without_being_replaced(client, project, library):
    ref = keep(client, add_reference(client, project))
    b = LibraryBrowser(library)
    saved = b.annotate(ref["asset_sha"], AnnotationInput(expected_revision=0,pose="seated"))
    q = queue(library)
    assert q.discover() == 1
    q.run_one(Analyzer())
    item = b.browse(BrowseFilters(kind="cosplay_photo",pose="seated"))["items"][0]
    assert item["annotation"] == saved and item["kind_actor"] == "ai"
    assert q.discover() == 0


def test_human_type_overrides_later_ai_type_and_unknown_is_not_cosplay(client, project, library):
    from conftest import review_data
    ref = keep(client, add_reference(client, project))
    r=client.post(f"/api/references/{ref['id']}/review",json={
        "expected_revision":ref["revision"],"review":review_data(ref["asset_sha"],kind="illustration")})
    assert r.status_code == 200
    q = queue(library); q.discover(); q.run_one(Analyzer())
    assert client.get("/api/library/assets",params={"pose":"standing","kind":"cosplay_photo"}).json()["total"] == 0
    assert client.get("/api/library/assets",params={"pose":"standing","kind":"illustration"}).json()["total"] == 1


def test_type_correction_can_return_to_a_previous_value_and_detect_conflicts(client, project, library):
    ref=add_reference(client, project)
    url=f"/api/library/assets/{ref['asset_sha']}"
    stale=client.get(url+'/classification').json()['annotation']
    for kind in ('cosplay_photo','illustration','cosplay_photo'):
        before=client.get(url+'/classification').json()['annotation']
        r=client.put(url+'/annotation',json={'expected_revision':before['revision'],'kind':kind,
            'expected_kind_id':before['kind_observation_id'] or ''})
        assert r.status_code==200, r.text
        assert client.get(url+'/classification').json()['annotation']['kind']==kind
    current=client.get(url+'/classification').json()['annotation']
    r=client.put(url+'/annotation',json={'expected_revision':current['revision'],'kind':'generated','expected_kind_id':''})
    assert r.status_code==409


def test_hidden_assets_are_not_sent_for_classification(client, project, library):
    ref=add_reference(client,project)
    client.patch(f"/api/references/{ref['id']}",json={'expected_revision':ref['revision'],'decision':'reject'})
    assert queue(library).discover()==0
    assert client.get('/api/library/assets').json()['unclassified']==0


def test_bad_single_image_does_not_stop_other_images_but_provider_outage_does(client, project, library):
    from ref_lab.classification import ClassificationUnavailable
    add_reference(client,project,seed=201)
    add_reference(client,project,seed=202)
    q=queue(library); q.discover()
    class BadImage(Analyzer):
        def classify(self,*args):
            raise ProviderError("Bad single-image output")
    q.run_one(BadImage())
    assert q.status()["counts"]["failed"]==1
    q.run_one(Analyzer())
    assert q.status()["counts"]["succeeded"]==1
    q.retry_failed()
    class Offline(Analyzer):
        def classify(self,*args):
            raise ClassificationUnavailable("Provider offline")
    q.run_one(Offline())
    assert q.status()["counts"]["blocked"]==1
    assert q.retry_failed()==1
    q.run_one(Analyzer())
    assert q.status()["counts"]["succeeded"]==2
