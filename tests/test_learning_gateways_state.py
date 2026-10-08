from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ref_lab.learning_state import router


def _client(web: Path, data: Path) -> TestClient:
    app = FastAPI()
    app.include_router(router(web, data))
    return TestClient(app)


def _atlas(web: Path, *, gateways: list[dict] | None = None) -> None:
    web.mkdir(parents=True, exist_ok=True)
    atlas = {
        "schema_version": 1, "research_version": "test", "domains": [], "modules": [],
        "skills": [{"id": "post-color"}],
    }
    if gateways is not None:
        atlas["gateways"] = gateways
    (web / "learning-atlas.json").write_text(json.dumps(atlas), encoding="utf-8")


def _body(**overrides):
    return {
        "expected_revision": 0,
        "stage": "unseen",
        "answers": {"observation": "线条交点", "comparison": "改变机位", "transfer": "换一张图", "confusion": ""},
        "revealed": ["observation", "comparison"],
        "last_section": "observe",
        **overrides,
    }


def test_legacy_atlas_and_state_keep_the_original_skill_response_shape(tmp_path: Path):
    web, data = tmp_path / "web", tmp_path / "data"
    _atlas(web)
    with _client(web, data) as client:
        response = client.get("/api/learning-state")
        assert response.status_code == 200
        assert response.json() == {"revision": 0, "skills": {}}


def test_gateway_put_roundtrips_filtered_state_and_preserves_skill_photo_and_unknown_records(tmp_path: Path):
    web, data = tmp_path / "web", tmp_path / "data"
    _atlas(web, gateways=[{"id": "gateway-a", "title": "A"}])
    state_path = data / "learning" / "learning-state.json"
    state_path.parent.mkdir(parents=True)
    photo_bytes = b"original-photo-bytes"
    state_path.write_text(json.dumps({
        "revision": 4,
        "skills": {"post-color": {
            "status": "practicing", "notes": "保留旧笔记", "logs": [{"id": "l1", "text": "原日志"}],
            "photos": [{"id": "p1", "src": "/api/learning-photos/a.png", "caption": "old photo"}],
        }, "removed-skill": {"notes": "hidden"}},
        "gateways": {"removed-gateway": {"stage": "field", "answers": {}, "revealed": [], "last_section": "reflect"}},
    }), encoding="utf-8")
    (data / "learning" / "photos").mkdir()
    (data / "learning" / "photos" / "a.png").write_bytes(photo_bytes)

    with _client(web, data) as client:
        before = client.get("/api/learning-state").json()
        assert before["revision"] == 4
        assert before["skills"]["post-color"]["notes"] == "保留旧笔记"
        assert before["gateways"] == {}

        response = client.put("/api/learning-gateways/gateway-a", json=_body(expected_revision=4))
        assert response.status_code == 200, response.text
        saved = response.json()
        assert saved["revision"] == 5
        assert saved["skills"]["post-color"] == before["skills"]["post-color"]
        assert saved["gateways"]["gateway-a"] == {key: value for key, value in _body(expected_revision=4).items() if key != "expected_revision"}
        assert "removed-gateway" not in saved["gateways"]
        assert "removed-skill" not in saved["skills"]

    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert "removed-gateway" in persisted["gateways"]
    assert (data / "learning" / "photos" / "a.png").read_bytes() == photo_bytes


def test_gateway_rejects_unknown_ids_and_invalid_or_oversized_inputs_without_mutation(tmp_path: Path):
    web, data = tmp_path / "web", tmp_path / "data"
    _atlas(web, gateways=[{"id": "gateway-a"}])
    with _client(web, data) as client:
        assert client.put("/api/learning-gateways/nope", json=_body()).status_code == 404
        invalid = [
            _body(stage="mastered"),
            _body(answers={"other": "x"}),
            _body(answers={"observation": 4}),
            _body(answers={"observation": "x" * 8001}),
            _body(revealed=["observation", "observation"]),
            _body(revealed=["confusion"]),
            _body(last_section="unknown"),
            _body(unapproved=True),
            {"expected_revision": 0},
            _body(expected_revision=True),
        ]
        for body in invalid:
            response = client.put("/api/learning-gateways/gateway-a", json=body)
            assert response.status_code == 422, (body, response.text)
        assert client.get("/api/learning-state").json() == {"revision": 0, "skills": {}, "gateways": {}}


def test_skill_and_gateway_writes_share_revision_and_racing_lock(tmp_path: Path):
    web, data = tmp_path / "web", tmp_path / "data"
    _atlas(web, gateways=[{"id": "gateway-a"}])
    clients = [_client(web, data), _client(web, data)]
    try:
        def save(args):
            client, kind = args
            if kind == "gateway":
                return client.put("/api/learning-gateways/gateway-a", json=_body()).status_code
            return client.put("/api/learning-state/post-color", json={"expected_revision": 0, "notes": "skill"}).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(save, [(clients[0], "gateway"), (clients[1], "skill")]))
        assert sorted(statuses) == [200, 409]
        state = clients[0].get("/api/learning-state").json()
        assert state["revision"] == 1
        assert bool(state["gateways"]) != bool(state["skills"])
    finally:
        for client in clients:
            client.close()


def test_malformed_persisted_gateway_and_bad_gateway_whitelist_fail_closed(tmp_path: Path):
    web, data = tmp_path / "web", tmp_path / "data"
    _atlas(web, gateways=[{"id": "gateway-a"}])
    state_path = data / "learning" / "learning-state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(json.dumps({"revision": 1, "skills": {}, "gateways": {
        "gateway-a": {"stage": "invented", "answers": {}, "revealed": [], "last_section": "observe"},
    }}), encoding="utf-8")
    with _client(web, data) as client:
        assert client.get("/api/learning-state").status_code == 503

    _atlas(web, gateways=[{"id": "gateway-a"}, {"id": "gateway-a"}])
    with _client(web, tmp_path / "other-data") as client:
        assert client.get("/api/learning-state").status_code == 503
