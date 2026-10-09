from __future__ import annotations

from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from ref_lab.api import create_app
from ref_lab.config import Settings
from tools.build_photography_atlas import build_payload
from tools.validate_learning_content import validate_learning_content


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "docs/research/photography-atlas"
CONTENT_PATH = RESEARCH / "LEARNING_CONTENT.json"
HEIGHT_SKILL = "perspective-skill-height-proportion-diagnosis"
OPTICAL_SKILL = "perspective-skill-optical-vs-perspective"
TOKEN = "test-only-access-token-not-a-live-credential-123"


def _catalogue() -> dict:
    return json.loads(CONTENT_PATH.read_text(encoding="utf-8"))


def _tree() -> dict:
    return json.loads((RESEARCH / "SKILL_TREE.json").read_text(encoding="utf-8"))


def test_pilot_catalogue_integrates_notes_training_sources_and_all_real_frames():
    payload = build_payload(RESEARCH)
    content = payload["learning_content"]
    notes, trainings = content["notes"], content["trainings"]
    note_ids = {note["id"] for note in notes}
    skill_ids = {skill["id"] for skill in payload["skills"]}
    source_ids = {source["id"] for source in content["sources"]}

    assert len(notes) == 4
    assert len(trainings) == 3
    assert len(content["sources"]) == 4
    assert len(content["media"]) == 13
    assert notes[0]["skill_ids"] == [HEIGHT_SKILL, OPTICAL_SKILL]
    assert all(note["skill_ids"] == [HEIGHT_SKILL] for note in notes[1:])
    assert all(note["citations"] for note in notes)
    assert all(set(note["skill_ids"]) <= skill_ids for note in notes)
    assert all(training["note_ids"] and set(training["note_ids"]) <= note_ids
               for training in trainings)
    assert all(training["basis"] == "project_designed" for training in trainings)
    assert all(citation["source_id"] in source_ids
               for note in notes for citation in note["citations"])
    assert {media["id"] for media in content["media"]} == {
        "s1-close", "s1-recede", "s1-background-near", "s1-background-far",
        "s2-face-heights", "s2-lower-chest", "s2-knee-level", "s2-above-eye-warning",
        "s4-double-chin", "s4-side-upward", "s4-front-caption",
        "s3-stone-foreground", "s3-flower-pose",
    }
    for media in content["media"]:
        assert media["filename"] in {f"{media['sha256']}.jpg", f"{media['sha256']}.png"}
        assert media["source_id"] in source_ids
        assert len(media["sha256"]) == 64


def test_builder_keeps_legacy_research_input_without_optional_learning_content(tmp_path: Path):
    for name in ("SOURCE_MAP", "SKILL_TREE", "CONFLICTS", "GAP_AUDIT",
                 "PROJECT_CHECKLISTS", "TUTORIALS", "GATEWAYS"):
        source = RESEARCH / f"{name}.json"
        if source.is_file():
            (tmp_path / source.name).write_bytes(source.read_bytes())

    payload = build_payload(tmp_path)

    assert len(payload["skills"]) == 247
    assert payload["learning_content"] == {
        "schema_version": 1, "notes": [], "trainings": [], "sources": [], "media": [],
    }


def test_content_validator_rejects_unknown_skills_sources_media_and_training_notes():
    catalog, tree = _catalogue(), _tree()
    assert validate_learning_content(catalog, tree) == []

    cases = []
    bad = deepcopy(catalog)
    bad["notes"][0]["skill_ids"].append("invented-skill")
    cases.append(bad)
    bad = deepcopy(catalog)
    bad["notes"][0]["citations"][0]["source_id"] = "invented-source"
    cases.append(bad)
    bad = deepcopy(catalog)
    bad["media"][0]["filename"] = "..\\outside.jpg"
    cases.append(bad)
    bad = deepcopy(catalog)
    bad["trainings"][0]["note_ids"] = ["invented-note"]
    cases.append(bad)
    bad = deepcopy(catalog)
    bad["notes"][1]["id"] = bad["notes"][0]["id"]
    cases.append(bad)

    for invalid in cases:
        assert validate_learning_content(invalid, tree)


def test_content_validator_accepts_exact_hash_named_png_media():
    catalog, tree = _catalogue(), _tree()
    png_media = catalog["media"][8]
    png_media["filename"] = f"{png_media['sha256']}.png"

    assert validate_learning_content(catalog, tree) == []


def test_content_catalog_changes_bundle_digest_without_rewriting_research(tmp_path: Path):
    for name in ("SOURCE_MAP", "SKILL_TREE", "CONFLICTS", "GAP_AUDIT", "PROJECT_CHECKLISTS",
                 "TUTORIALS", "GATEWAYS", "LEARNING_CONTENT"):
        source = RESEARCH / f"{name}.json"
        if source.is_file():
            (tmp_path / source.name).write_bytes(source.read_bytes())
    before = build_payload(tmp_path)
    assert before["learning_content"]["notes"]

    path = tmp_path / "LEARNING_CONTENT.json"
    catalog = json.loads(path.read_text(encoding="utf-8"))
    catalog["notes"][0]["lead"] += " 更新后的短句。"
    path.write_text(json.dumps(catalog, ensure_ascii=False), encoding="utf-8")
    after = build_payload(tmp_path)

    assert before["research_version"] != after["research_version"]
    for key in ("domains", "modules", "skills", "sources", "tutorials", "gateways"):
        assert before[key] == after[key]


def _jpeg() -> bytes:
    image = Image.new("RGB", (8, 8), (30, 80, 120))
    output = io.BytesIO()
    image.save(output, format="JPEG")
    return output.getvalue()


def _png() -> bytes:
    image = Image.new("RGB", (8, 8), (120, 80, 30))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_note_media_route_requires_auth_and_serves_only_hash_checked_catalogue_files(tmp_path: Path):
    web = tmp_path / "web"
    web.mkdir()
    body = _jpeg()
    digest = hashlib.sha256(body).hexdigest()
    media = {"id": "fixture-frame", "filename": f"{digest}.jpg", "sha256": digest}
    atlas_path = web / "learning-atlas.json"
    atlas_path.write_text(
        json.dumps({"learning_content": {"media": [media]}}), encoding="utf-8")
    media_dir = tmp_path / ".local" / "learning-note-media"
    media_dir.mkdir(parents=True)
    path = media_dir / media["filename"]
    path.write_bytes(body)

    app = create_app(Settings(tmp_path / "data", TOKEN, public_origin="http://testserver", web_dir=web))
    with TestClient(app) as client:
        assert client.get("/api/learning-note-media/fixture-frame").status_code == 401
        session = client.post("/api/session", json={"token": TOKEN})
        assert session.status_code == 200
        assert client.get("/api/learning-note-media/unlisted").status_code == 404
        response = client.get("/api/learning-note-media/fixture-frame")
        assert response.status_code == 200
        assert response.content == body
        assert response.headers["content-type"].startswith("image/jpeg")

        atlas_path.write_text(
            json.dumps({"learning_content": {"media": [{**media, "filename": "../outside.jpg"}]}}),
            encoding="utf-8")
        assert client.get("/api/learning-note-media/fixture-frame").status_code == 404
        atlas_path.write_text(json.dumps({"learning_content": {"media": [media]}}), encoding="utf-8")
        path.write_bytes(b"tampered bytes")
        assert client.get("/api/learning-note-media/fixture-frame").status_code == 404
        path.unlink()
        assert client.get("/api/learning-note-media/fixture-frame").status_code == 404


def test_note_media_route_rejects_symlinked_file_even_when_target_hash_matches(tmp_path: Path):
    web = tmp_path / "web"
    web.mkdir()
    body = _jpeg()
    digest = hashlib.sha256(body).hexdigest()
    media = {"id": "fixture-frame", "filename": f"{digest}.jpg", "sha256": digest}
    (web / "learning-atlas.json").write_text(
        json.dumps({"learning_content": {"media": [media]}}), encoding="utf-8")
    media_dir = tmp_path / ".local" / "learning-note-media"
    media_dir.mkdir(parents=True)
    outside = tmp_path / "outside.jpg"
    outside.write_bytes(body)
    link = media_dir / media["filename"]
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        import pytest
        pytest.skip("symlink creation is unavailable in this Windows environment")

    app = create_app(Settings(tmp_path / "data", TOKEN, public_origin="http://testserver", web_dir=web))
    with TestClient(app) as client:
        client.post("/api/session", json={"token": TOKEN})
        assert client.get("/api/learning-note-media/fixture-frame").status_code == 404


def test_note_media_route_serves_hash_named_png_and_rejects_suffix_or_magic_mismatch(tmp_path: Path):
    web = tmp_path / "web"
    web.mkdir()
    body = _png()
    digest = hashlib.sha256(body).hexdigest()
    media = {"id": "fixture-frame", "filename": f"{digest}.png", "sha256": digest}
    atlas_path = web / "learning-atlas.json"
    atlas_path.write_text(
        json.dumps({"learning_content": {"media": [media]}}), encoding="utf-8")
    media_dir = tmp_path / ".local" / "learning-note-media"
    media_dir.mkdir(parents=True)
    (media_dir / media["filename"]).write_bytes(body)

    app = create_app(Settings(tmp_path / "data", TOKEN, public_origin="http://testserver", web_dir=web))
    with TestClient(app) as client:
        client.post("/api/session", json={"token": TOKEN})
        response = client.get("/api/learning-note-media/fixture-frame")
        assert response.status_code == 200
        assert response.content == body
        assert response.headers["content-type"].startswith("image/png")

        wrong_suffix = {**media, "filename": f"{digest}.jpg"}
        (media_dir / wrong_suffix["filename"]).write_bytes(body)
        atlas_path.write_text(
            json.dumps({"learning_content": {"media": [wrong_suffix]}}), encoding="utf-8")
        assert client.get("/api/learning-note-media/fixture-frame").status_code == 404

        jpeg = _jpeg()
        jpeg_digest = hashlib.sha256(jpeg).hexdigest()
        fake_png = {"id": "fixture-frame", "filename": f"{jpeg_digest}.png", "sha256": jpeg_digest}
        atlas_path.write_text(
            json.dumps({"learning_content": {"media": [fake_png]}}), encoding="utf-8")
        (media_dir / fake_png["filename"]).write_bytes(jpeg)
        assert client.get("/api/learning-note-media/fixture-frame").status_code == 404
