from __future__ import annotations

import io
import json
import zipfile

from conftest import add_reference, image_bytes
from ref_lab.imports import import_candidates
from ref_lab.models import JobInput


def preflight_payload(ref, *, content_type="real_person_cosplay", identity_prediction="match"):
    return {
        "expected_revision": ref["revision"],
        "producer": "synthetic-regression-agent",
        "preflight": {
            "content_type": content_type,
            "identity_prediction": identity_prediction,
            "confidence": "high",
            "visual_evidence": ["Synthetic protocol fixture; this does not prove real vision accuracy."],
            "reason": "Regression verifies routing semantics only.",
        },
    }


def candidate_zip(job, *, schema_version=3, content_type="game_screenshot", identity_prediction="match", seed=44):
    candidate = {
        "id": f"candidate-{schema_version}-{seed}",
        "file": "images/one.png",
        "title": "search metadata is not image fact",
        "source": {"page_url": "https://example.com/post/1", "search_query": "王昭君 cosplay"},
        "discovery_intent": "exact_character",
        "discovery_reason": "Synthetic protocol test",
        "discovery_url": "https://example.com/search?q=wang",
    }
    if schema_version == 3:
        candidate["preflight"] = {
            "content_type": content_type,
            "identity_prediction": identity_prediction,
            "confidence": "high",
            "visual_evidence": ["Synthetic manifest evidence; not a live visual assessment."],
            "reason": "Regression verifies import filtering semantics.",
        }
    manifest = {
        "schema_version": schema_version,
        "job_id": job["id"],
        "batch_id": f"synthetic-v{schema_version}-{seed}",
        "candidates": [candidate],
        "execution_report": {
            "producer": "synthetic-regression-agent",
            "status": "completed",
            "summary": "Protocol regression only",
            "source_checks": [],
            "query_log": [],
            "gaps": [],
        },
    }
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("images/one.png", image_bytes(seed))
    return stream.getvalue()


def test_game_screenshot_preflight_is_filtered_but_recoverable(client, project):
    ref = add_reference(client, project)
    response = client.post(
        f"/api/references/{ref['id']}/preflight",
        json=preflight_payload(ref, content_type="game_screenshot"),
    )
    assert response.status_code == 200, response.text
    filtered = response.json()
    assert filtered["preflight_status"] == "filtered"
    assert filtered["preflight_filtered"] is True
    assert filtered["decision"] == "pending"

    assert client.get(f"/api/projects/{project['id']}/references").json()["total"] == 0
    filtered_view = client.get(f"/api/projects/{project['id']}/references?view_filtered=true").json()
    assert filtered_view["total"] == 1
    assert filtered_view["items"][0]["id"] == ref["id"]
    stats = client.get(f"/api/projects/{project['id']}/stats").json()
    assert stats["filtered"] == 1 and stats["visible"] == 0

    restored = client.post(
        f"/api/references/{ref['id']}/preflight-override",
        json={"expected_revision": filtered["revision"], "action": "restore"},
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["preflight_override"] is True
    assert client.get(f"/api/projects/{project['id']}/references").json()["total"] == 1


def test_identity_uncertain_is_not_forced_pass_and_mismatch_filters(client, project):
    uncertain = add_reference(client, project, seed=1)
    uncertain_result = client.post(
        f"/api/references/{uncertain['id']}/preflight",
        json=preflight_payload(uncertain, identity_prediction="uncertain"),
    )
    assert uncertain_result.status_code == 200, uncertain_result.text
    assert uncertain_result.json()["preflight_status"] == "uncertain"
    assert uncertain_result.json()["preflight_filtered"] is False

    mismatch = add_reference(client, project, seed=2)
    mismatch_result = client.post(
        f"/api/references/{mismatch['id']}/preflight",
        json=preflight_payload(mismatch, identity_prediction="mismatch"),
    )
    assert mismatch_result.status_code == 200, mismatch_result.text
    assert mismatch_result.json()["preflight_status"] == "filtered"
    assert mismatch_result.json()["preflight_filtered"] is True


def test_schema3_import_applies_visual_preflight_and_schema2_remains_unverified(project, library):
    job = library.create_job(project["id"], JobInput(kind="collection"))
    report = import_candidates(library, project["id"], candidate_zip(job), job["id"])
    assert report["errors"] == []
    ref = library.reference(report["reference_ids"][0])
    assert ref["preflight"]["content_type"] == "game_screenshot"
    assert ref["preflight_filtered"] is True
    assert library.references(project["id"])["total"] == 0
    assert library.references(project["id"], view_filtered=True)["total"] == 1

    second = library.create_job(project["id"], JobInput(kind="collection"))
    old = import_candidates(library, project["id"], candidate_zip(second, schema_version=2, seed=45), second["id"])
    assert old["errors"] == []
    old_ref = library.reference(old["reference_ids"][0])
    assert old_ref.get("preflight") is None
    assert old_ref.get("preflight_status") == "unreviewed"


def test_project_archive_hides_project_but_preserves_shared_assets_and_global_inspiration(client, project):
    ref = add_reference(client, project, seed=9)
    saved = client.post(
        f"/api/references/{ref['id']}/inspiration",
        json={"expected_revision": ref["revision"]},
    )
    assert saved.status_code == 200, saved.text

    other = client.post("/api/projects", json={"character": "另一个角色"}).json()
    reused = client.post(
        f"/api/projects/{other['id']}/references",
        json={"asset_sha": ref["asset_sha"], "title": "shared bytes"},
    )
    assert reused.status_code == 201, reused.text

    archived = client.request(
        "DELETE",
        f"/api/projects/{project['id']}",
        json={"expected_revision": project["revision"]},
    )
    assert archived.status_code == 200, archived.text
    archived_project = archived.json()
    assert archived_project["archived_at"]

    assert all(p["id"] != project["id"] for p in client.get("/api/projects").json())
    assert any(p["id"] == project["id"] for p in client.get("/api/projects?archived=true").json())
    assert client.get(f"/api/assets/{ref['asset_sha']}/original").status_code == 200
    assert client.get("/api/inspirations").json()["total"] == 1
    assert client.get(f"/api/projects/{other['id']}/references").json()["total"] == 1

    blocked_job = client.post(f"/api/projects/{project['id']}/jobs", json={"kind": "collection"})
    assert blocked_job.status_code == 409
    blocked_edit = client.patch(
        f"/api/references/{ref['id']}",
        json={"expected_revision": ref["revision"], "decision": "maybe"},
    )
    assert blocked_edit.status_code == 409

    restored = client.post(
        f"/api/projects/{project['id']}/restore",
        json={"expected_revision": archived_project["revision"]},
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["archived_at"] is None
    assert any(p["id"] == project["id"] for p in client.get("/api/projects").json())
