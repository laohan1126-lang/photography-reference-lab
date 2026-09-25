from __future__ import annotations

import hashlib
import io
import json
import zipfile
from PIL import Image
import pytest
from fastapi.testclient import TestClient
from ref_lab.config import Settings
from ref_lab.models import AnalysisResult, CandidateInput, ProjectInput, ReferenceEdit, Source, VisualReview
from ref_lab.policy import source_is_traceable
from ref_lab.security import COOKIE, valid_session, make_session
from ref_lab.service import Problem
from conftest import TOKEN, add_reference, card_data, image_bytes, ready_reference, review_data


def test_private_api_csrf_origin_and_host(app):
    with TestClient(app) as c:
        assert c.get("/api/projects").status_code == 401
        assert c.get("/api/assets/" + "a" * 64 + "/original").status_code == 401
        assert c.get("/health").status_code == 200
        assert c.get("/api/session").json()["authenticated"] is False
        assert c.get("/", headers={"host": "evil.example"}).status_code == 400
        response = c.post("/api/session", json={"token": TOKEN})
        assert "httponly" in response.headers["set-cookie"].lower()
        assert "samesite=strict" in response.headers["set-cookie"].lower()
        assert c.post("/api/projects", json={"character": "A"}).status_code == 403
        c.headers["X-Lab-CSRF"] = response.json()["csrf"]
        assert c.post("/api/projects", json={"character": "A"}, headers={"Origin": "https://evil.example"}).status_code == 403
        assert c.post("/api/projects", json={"character": "A"}).status_code == 201
        assert c.get("/api/projects").headers["cache-control"] == "private, no-store"
        assert c.get("/static/../.env").status_code == 404
        assert c.delete("/api/session").status_code == 200
        assert c.get("/api/projects").status_code == 401


def test_session_signature_and_login_rate_limit(app):
    session = make_session(TOKEN)
    assert valid_session(TOKEN, session)
    assert not valid_session(TOKEN, session + "tampered")
    assert not valid_session(TOKEN, "0.nonce.proof")
    with TestClient(app) as c:
        for _ in range(8): assert c.post("/api/session", json={"token": "wrong"}).status_code == 401
        assert c.post("/api/session", json={"token": TOKEN}).status_code == 429


@pytest.mark.parametrize("payload", [{}, {"character": "   "}, {"character": "A", "unexpected": True}])
def test_project_contract(client, payload):
    assert client.post("/api/projects", json=payload).status_code == 422


def test_original_bytes_derivatives_and_invalid_upload(client, project, library):
    data = image_bytes()
    asset = client.post("/api/assets", files={"file": ("wrong-extension.jpg", data, "image/jpeg")}).json()
    assert asset["id"] == hashlib.sha256(data).hexdigest()
    assert asset["ext"] == "png"
    assert client.get(f"/api/assets/{asset['id']}/original").content == data
    assert client.get(f"/api/assets/{asset['id']}/thumb").content != data
    assert library.assets.verify(asset)
    assert client.post("/api/assets", files={"file": ("bad.png", b"not an image", "image/png")}).status_code == 422
    assert client.get(f"/api/assets/{asset['id']}/../../library.sqlite3").status_code != 200


def test_exif_rotation_does_not_mutate_original(client):
    image = Image.new("RGB", (60, 100))
    exif = image.getexif(); exif[274] = 6
    stream = io.BytesIO(); image.save(stream, "JPEG", exif=exif)
    asset = client.post("/api/assets", files={"file": ("rotated.jpg", stream.getvalue(), "image/jpeg")}).json()
    assert (asset["width"], asset["height"]) == (100, 60)
    assert client.get(f"/api/assets/{asset['id']}/original").content == stream.getvalue()


def test_dedupe_and_cross_project_reuse(client, project, library):
    first = add_reference(client, project)
    second = client.post(f"/api/projects/{project['id']}/references", json={"asset_sha": first["asset_sha"]}).json()
    assert second["created"] is False
    assert second["reference"]["id"] == first["id"]
    other = client.post("/api/projects", json={"character": "另一个角色"}).json()
    reused = client.post(f"/api/projects/{other['id']}/references", json={"asset_sha": first["asset_sha"]}).json()
    assert reused["created"] is True
    assert reused["reference"]["id"] != first["id"]
    assert len(list(library.assets.root.rglob("original.*"))) == 1


def test_optimistic_concurrency_and_no_positive_defaults(client, project):
    ref = add_reference(client, project)
    changed = client.patch(f"/api/references/{ref['id']}", json={"expected_revision": ref["revision"], "decision": "keep"}).json()
    assert changed["state"] == "needs_review"
    assert changed["card"] is None and changed["review"] is None and not changed["field_ready"]
    assert client.patch(f"/api/references/{ref['id']}", json={"expected_revision": ref["revision"], "decision": "reject"}).status_code == 409
    assert client.post(f"/api/references/{ref['id']}/review", json={"expected_revision": changed["revision"], "review": review_data("a" * 64)}).status_code == 409


@pytest.mark.parametrize("kind", ["equipment", "location", "illustration", "collage", "generated", "unknown"])
def test_wrong_image_kinds_never_become_field_cards(client, project, kind):
    ref = add_reference(client, project)
    ref = client.patch(f"/api/references/{ref['id']}", json={"expected_revision": ref["revision"], "decision": "keep"}).json()
    data = {"expected_revision": ref["revision"], "producer": "synthetic-fixture-reviewer", "result": {"review": review_data(ref["asset_sha"], kind=kind), "card": card_data()}}
    result = client.post(f"/api/references/{ref['id']}/analysis", json=data)
    assert result.status_code == 200
    ref = result.json()
    assert ref["card"] is None and not ref["field_ready"]
    assert "wrong_kind" in [r["code"] for r in ref["blockers"]]
    assert client.post(f"/api/references/{ref['id']}/accept", json={"expected_revision": ref["revision"]}).status_code == 409
    assert client.post(f"/api/references/{ref['id']}/card", json={"expected_revision": ref["revision"], "card": card_data()}).status_code == 409


@pytest.mark.parametrize("field,code", [("visible_person", "no_person"), ("pose_readable", "pose_unreadable"), ("single_image", "collage"), ("sufficiently_clear", "unclear")])
def test_individual_visual_gates(client, project, field, code):
    ref = ready_reference(client, project)
    changed = client.post(f"/api/references/{ref['id']}/review", json={"expected_revision": ref["revision"], "review": review_data(ref["asset_sha"], **{field: False})}).json()
    assert code in [x["code"] for x in changed["blockers"]]
    assert not changed["field_ready"]


def test_uncertainty_and_cross_domain_require_explicit_approval(client, project):
    ref = ready_reference(client, project)
    ref = client.post(f"/api/references/{ref['id']}/review", json={"expected_revision": ref["revision"], "review": review_data(ref["asset_sha"], kind="portrait_photo", character_match="adapted")}).json()
    assert "adaptation_unapproved" in [x["code"] for x in ref["blockers"]]
    ref = client.patch(f"/api/references/{ref['id']}", json={"expected_revision": ref["revision"], "allow_cross_domain": True}).json()
    assert client.post(f"/api/references/{ref['id']}/accept", json={"expected_revision": ref["revision"]}).status_code == 200
    ref = client.get(f"/api/references/{ref['id']}").json()
    ref = client.post(f"/api/references/{ref['id']}/review", json={"expected_revision": ref["revision"], "review": review_data(ref["asset_sha"], critical_uncertainties=["Hands are obscured"])}).json()
    assert "uncertain" in [x["code"] for x in ref["blockers"]]
    assert client.post(f"/api/references/{ref['id']}/accept", json={"expected_revision": ref["revision"]}).status_code == 409


@pytest.mark.parametrize("url", ["https://i.pinimg.com/736x/image.jpg", "https://www.pinterest.com/search/pins/?q=cos", "https://example.com/", ""])
def test_search_and_cdn_are_not_original_post_evidence(url):
    assert not source_is_traceable({"page_url": url, "source_confirmed": True, "rights": "unknown"})


@pytest.mark.parametrize("url", ["javascript:alert(1)", "https://user:pass@example.com/a", "https://example.com/?access_token=secret"])
def test_unsafe_provenance_urls_rejected(url):
    with pytest.raises(ValueError): Source(page_url=url)


def test_ready_pack_and_invalidated_acceptance(client, project, library):
    ref = ready_reference(client, project)
    assert ref["field_ready"] and ref["state"] == "ready"
    response = client.post(f"/api/projects/{project['id']}/pack", json={"reference_ids": [ref["id"]], "mode": "field"})
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        exported = manifest["references"][0]
        assert hashlib.sha256(archive.read(exported["offline_original"])).hexdigest() == ref["asset_sha"]
        html = archive.read("index.html").decode()
        assert '__DATA__' not in html and 'fetch(' not in html
    assert not list((library.settings.data_dir / "exports").glob("*.zip"))
    updated = client.patch(f"/api/references/{ref['id']}", json={"expected_revision": ref["revision"], "decision": "reject"}).json()
    assert updated["state"] == "rejected" and not updated["field_ready"]
    assert client.post(f"/api/projects/{project['id']}/pack", json={"reference_ids": [ref["id"]]}).status_code == 409


def test_replace_revokes_decision_review_card_and_source(client, project):
    ref = ready_reference(client, project)
    changed = client.post(f"/api/references/{ref['id']}/replace", data={"expected_revision": ref["revision"]}, files={"file": ("new.png", image_bytes(4), "image/png")}).json()
    assert changed["asset_sha"] != ref["asset_sha"]
    assert changed["decision"] == "pending"
    assert changed["review"] is None and changed["card"] is None
    assert not changed["source"]["source_confirmed"]
    assert client.get(f"/api/assets/{ref['asset_sha']}/original").status_code == 200


def test_context_change_invalidates_card(client, project):
    ref = ready_reference(client, project)
    updated_project = {k: project[k] for k in ("character", "work", "costume", "brief", "gear")}
    updated_project.update(brief="不同场景和要求", expected_revision=project["revision"])
    assert client.put(f"/api/projects/{project['id']}", json=updated_project).status_code == 200
    changed = client.get(f"/api/references/{ref['id']}").json()
    assert "stale_context" in [x["code"] for x in changed["blockers"]]
    assert not changed["field_ready"] and changed["revision"] > ref["revision"]
    assert client.post(f"/api/references/{ref['id']}/accept", json={"expected_revision": changed["revision"]}).status_code == 409


def test_reflection_preserves_approval(client, project):
    ref = ready_reference(client, project)
    response = client.post(f"/api/references/{ref['id']}/reflection", json={"expected_revision": ref["revision"], "tried": True, "worked": "口令好用"})
    assert response.status_code == 200
    assert response.json()["field_ready"]
    assert response.json()["reflections"][0]["worked"] == "口令好用"


def test_pagination_and_parameterized_search(client, project, library):
    for index in range(125): library.add_candidate(project["id"], CandidateInput(title=f"reference {index}", import_key=f"row-{index}"))
    page = client.get(f"/api/projects/{project['id']}/references?limit=60&offset=120").json()
    assert page["total"] == 125 and len(page["items"]) == 5
    assert client.get(f"/api/projects/{project['id']}/references", params={"q": "' OR 1=1 --"}).json()["total"] == 0
    assert client.get(f"/api/projects/{project['id']}/references?limit=0").status_code == 422


def test_field_integrity_rejects_modified_local_file(client, project, library):
    ref = ready_reference(client, project)
    library.assets.path(ref["asset"]).write_bytes(b"corrupt")
    assert client.post(f"/api/projects/{project['id']}/pack", json={"reference_ids": [ref["id"]]}).status_code == 409
