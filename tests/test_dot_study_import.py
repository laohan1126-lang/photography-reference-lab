"""Independent study candidates preserve provenance and human review boundaries."""
from __future__ import annotations

import io
import json
import sqlite3

import pytest
from PIL import Image

from ref_lab.db import Database, SCHEMA
from ref_lab.migrations import CATALOG_SCHEMA, V3_SCHEMA
from ref_lab.service import Problem
from tools.import_dot_drive_batch import candidate_data
from conftest import image_bytes


def dot_record(number="P366"):
    return {"编号": number, "Drive文件ID": "drive-image-123", "图片文件名": number + ".jpg",
            "主题": "合成测试参考", "公开出处": "https://example.org/post/1",
            "Google Drive 图片": "https://drive.google.com/file/d/example/view",
            "助手判断": "手位和背景线条值得核对", "现场借鉴": "轻扶道具",
            "摄影署名": "测试摄影者", "用户反馈": {"状态": "尚无对应用户反馈"},
            "作者与来源使用限制": ["仅私有测试用途"]}


def test_v3_upgrade_adds_independent_queue_and_preserves_rows(tmp_path):
    path = tmp_path / "library.sqlite3"
    with sqlite3.connect(path) as con:
        con.executescript(SCHEMA + CATALOG_SCHEMA + V3_SCHEMA)
        con.execute("INSERT INTO projects VALUES(?,?)", ("old-project", '{"character":"王昭君"}'))
        con.execute("PRAGMA user_version=3")
    db = Database(path)
    with db.read() as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 4
        assert con.execute("SELECT data FROM projects WHERE id='old-project'").fetchone()[0] == '{"character":"王昭君"}'
        assert con.execute("SELECT COUNT(*) FROM study_candidates").fetchone()[0] == 0
    assert db.migration_report["from"] == 3 and db.migration_report["to"] == 4
    assert db.migration_report["backup"]


def test_study_candidate_is_pending_and_rerun_preserves_human_choice(client, library):
    asset = library.ingest_asset(image_bytes())
    item = candidate_data(dot_record(), asset["id"], None)
    assert library.add_study_candidate(item)["created"]
    assert client.get("/api/inspirations").json()["total"] == 0
    listing = client.get("/api/study-candidates?topic=动作").json()
    assert listing["total"] == 1 and listing["items"][0]["status"] == "pending"
    assert listing["items"][0]["topic_origin"].startswith("Dot 文案")
    noted = client.patch("/api/study-candidates/dot:P366", json={"expected_revision": 1, "human_note": "先记下要比较手位"})
    assert noted.status_code == 200
    assert noted.json()["status"] == "pending" and noted.json()["decision_origin"] == "unreviewed"
    updated = client.patch("/api/study-candidates/dot:P366", json={
        "expected_revision": 2, "status": "priority", "human_note": "我只想学手位"})
    assert updated.status_code == 200
    assert updated.json()["revision"] == 3 and updated.json()["decision_origin"] == "human"
    assert client.patch("/api/study-candidates/dot:P366", json={
        "expected_revision": 1, "status": "skip"}).status_code == 409
    assert not library.add_study_candidate(candidate_data(dot_record(), asset["id"], None))["created"]
    changed_source = candidate_data(dot_record(), asset["id"], None)
    changed_source["compat_file_id"] = "unexpected-other-drive-file"
    with pytest.raises(Problem):
        library.add_study_candidate(changed_source)
    kept = client.get("/api/study-candidates/dot:P366").json()
    assert kept["status"] == "priority" and kept["human_note"] == "我只想学手位"
    assert client.get("/api/study-candidates?status=priority&q=P366").json()["total"] == 1
    assert client.get("/api/inspirations").json()["total"] == 0


def test_unified_library_keeps_study_only_assets_out_of_classification(library):
    from ref_lab.classification import ClassificationQueue
    from ref_lab.library_browser import LibraryBrowser
    from ref_lab.service import Library

    asset = library.ingest_asset(image_bytes(84))
    library.add_study_candidate(candidate_data(dot_record(), asset['id'], None))
    queue = ClassificationQueue(LibraryBrowser(library))
    assert queue.discover() == 0
    tables = ('projects', 'assets', 'refs', 'inspirations', 'study_candidates', 'events')
    with library.db.read() as con:
        before = {table: [tuple(row) for row in con.execute(f'SELECT * FROM {table} ORDER BY rowid')]
                  for table in tables}
    reopened = Library(library.settings, repair_untrusted_preflights=True)
    with reopened.db.read() as con:
        after = {table: [tuple(row) for row in con.execute(f'SELECT * FROM {table} ORDER BY rowid')]
                 for table in tables}
    assert after == before
    assert reopened.study_candidate('dot:P366')['status'] == 'pending'


def test_study_reasons_are_independent_human_choices_with_revision(client, library):
    asset = library.ingest_asset(image_bytes())
    library.add_study_candidate(candidate_data(dot_record(), asset["id"], None))
    selected = client.patch("/api/study-candidates/dot:P366", json={
        "expected_revision": 1, "study_reasons": ["composition", "pose"]})
    assert selected.status_code == 200
    assert selected.json()["study_reasons"] == ["composition", "pose"]
    assert selected.json()["status"] == "pending"
    assert selected.json()["decision_origin"] == "unreviewed"
    assert selected.json()["reason_origin"] == "human"
    assert client.get("/api/study-candidates/dot:P366").json()["study_reasons"] == ["composition", "pose"]
    assert not library.add_study_candidate(candidate_data(dot_record(), asset["id"], None))["created"]
    assert library.study_candidate("dot:P366")["study_reasons"] == ["composition", "pose"]
    assert client.patch("/api/study-candidates/dot:P366", json={
        "expected_revision": 1, "study_reasons": ["lighting"]}).status_code == 409
    assert client.patch("/api/study-candidates/dot:P366", json={
        "expected_revision": 2, "study_reasons": ["unknown"]}).status_code == 422
    noted = client.patch("/api/study-candidates/dot:P366", json={
        "expected_revision": 2, "human_note": "只学走位"})
    assert noted.status_code == 200 and noted.json()["study_reasons"] == ["composition", "pose"]
    cleared = client.patch("/api/study-candidates/dot:P366", json={
        "expected_revision": 3, "study_reasons": []})
    assert cleared.status_code == 200 and cleared.json()["study_reasons"] == []
    assert library.study_candidate("dot:P366")["human_note"] == "只学走位"
    assert client.get("/api/inspirations").json()["total"] == 0


def test_avif_received_bytes_remain_original(client, library):
    stream = io.BytesIO()
    Image.new("RGB", (64, 48), (70, 100, 130)).save(stream, format="AVIF")
    original = stream.getvalue()
    asset = library.ingest_asset(original, "example.avif")
    assert asset["ext"] == "avif" and asset["mime"] == "image/avif"
    assert library.assets.path(asset).read_bytes() == original
    response = client.get(f"/api/assets/{asset['id']}/original")
    assert response.status_code == 200 and response.content == original
