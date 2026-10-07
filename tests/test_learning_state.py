from __future__ import annotations

import io
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from ref_lab.learning_state import MAX_PHOTO_BYTES, router


def _client(web: Path, data: Path) -> TestClient:
    app = FastAPI()
    app.include_router(router(web, data))
    return TestClient(app)


def _atlas(web: Path, ids: list[str] | None = None) -> None:
    web.mkdir(parents=True, exist_ok=True)
    (web / "learning-atlas.json").write_text(json.dumps({
        "schema_version": 1, "research_version": "test", "domains": [], "modules": [],
        "skills": [{"id": item} for item in (ids or ["post-color", "post-skin"])],
    }), encoding="utf-8")


def _png() -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (9, 7), (72, 113, 150)).save(stream, format="PNG")
    return stream.getvalue()


def test_default_is_empty_and_unknown_skill_is_rejected(tmp_path: Path):
    web = tmp_path / "web"
    _atlas(web)
    with _client(web, tmp_path / "data") as client:
        assert client.get("/api/learning-state").json() == {"revision": 0, "skills": {}}
        response = client.put("/api/learning-state/not-allowlisted", json={"expected_revision": 0, "weak": True})
        assert response.status_code == 404
        assert client.get("/api/learning-state").json() == {"revision": 0, "skills": {}}


def test_atlas_missing_or_bad_fails_closed(tmp_path: Path):
    web, data = tmp_path / "web", tmp_path / "data"
    with _client(web, data) as client:
        assert client.get("/api/learning-state").status_code == 503
        web.mkdir()
        (web / "learning-atlas.json").write_text('{"skills":[]}', encoding="utf-8")
        assert client.get("/api/learning-state").status_code == 503


def test_profile_is_strict_persistent_and_never_auto_promoted(tmp_path: Path):
    web, data = tmp_path / "web", tmp_path / "data"
    _atlas(web)
    first = _client(web, data)
    second = _client(web, data)
    with first, second:
        saved = first.put("/api/learning-state/post-color", json={"expected_revision": 0, "weak": True})
        assert saved.status_code == 200
        result = saved.json()
        assert result["revision"] == 1
        assert result["skills"]["post-color"]["status"] == "unassessed"
        assert result["skills"]["post-color"]["weak"] is True
        assert "post-skin" not in result["skills"]
        assert second.get("/api/learning-state").json() == result
        stale = second.put("/api/learning-state/post-color", json={"expected_revision": 0, "notes": "旧内容"})
        assert stale.status_code == 409
        assert first.get("/api/learning-state").json() == result
        assert first.put("/api/learning-state/post-color", json={"expected_revision": 1, "status": "invented"}).status_code == 422
        assert first.put("/api/learning-state/post-color", json={"expected_revision": 1, "weak": 1}).status_code == 422
        assert first.put("/api/learning-state/post-color", json={"expected_revision": 1, "weak": False, "other": 1}).status_code == 422


def test_routers_for_same_path_share_lock_and_racing_stale_write_conflicts(tmp_path: Path):
    web, data = tmp_path / "web", tmp_path / "data"
    _atlas(web)
    clients = [_client(web, data), _client(web, data)]
    try:
        def save(client: TestClient, key: str):
            return client.put("/api/learning-state/post-color", json={"expected_revision": 0, key: True}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(lambda args: save(*args), [(clients[0], "weak"), (clients[1], "focus")]))
        assert sorted(statuses) == [200, 409]
        assert clients[0].get("/api/learning-state").json()["revision"] == 1
    finally:
        for client in clients:
            client.close()


def test_logs_are_append_only_revisioned_and_photo_links_must_exist(tmp_path: Path):
    web, data = tmp_path / "web", tmp_path / "data"
    _atlas(web)
    with _client(web, data) as client:
        bad_ref = client.post("/api/learning-state/post-skin/logs", json={
            "expected_revision": 0, "text": "观察", "photo_ids": ["missing"]})
        assert bad_ref.status_code == 422
        response = client.post("/api/learning-state/post-skin/logs", json={"expected_revision": 0, "text": "  对比两张肤色  "})
        assert response.status_code == 201
        state = response.json()
        assert state["revision"] == 1
        log = state["skills"]["post-skin"]["logs"][0]
        assert log["text"] == "对比两张肤色"
        assert log["created_at"] and log["id"]
        assert client.post("/api/learning-state/post-skin/logs", json={"expected_revision": 0, "text": "过时"}).status_code == 409


def test_photo_preserves_bytes_validates_image_and_rejects_path_guessing(tmp_path: Path):
    web, data = tmp_path / "web", tmp_path / "data"
    _atlas(web)
    raw = _png()
    with _client(web, data) as client:
        response = client.post("/api/learning-state/post-skin/photos", data={"expected_revision": "0", "caption": "边缘对照"},
                               files={"file": ("ignored.png", raw, "image/png")})
        assert response.status_code == 201, response.text
        result = response.json()
        photo = result["skills"]["post-skin"]["photos"][0]
        assert photo["caption"] == "边缘对照"
        assert photo["src"].startswith("/api/learning-photos/")
        filename = photo["src"].rsplit("/", 1)[1]
        stored = data / "learning" / "photos" / filename
        assert stored.read_bytes() == raw
        fetched = client.get(photo["src"])
        assert fetched.status_code == 200 and fetched.content == raw
        assert fetched.headers["cache-control"] == "private, no-store"
        assert client.get("/api/learning-photos/../../secret.png").status_code == 404
        bad = client.post("/api/learning-state/post-skin/photos", data={"expected_revision": "1"},
                          files={"file": ("x.svg", b"<svg/>", "image/svg+xml")})
        assert bad.status_code == 415
        oversized = client.post("/api/learning-state/post-skin/photos", data={"expected_revision": "1"},
                                files={"file": ("big.png", b"x" * (MAX_PHOTO_BYTES + 1), "image/png")})
        assert oversized.status_code == 413
        assert client.get("/api/learning-state").json()["revision"] == 1
