"""End-to-end requirement-driven opaque-box tests for search experience (R1-R5).

Exercises UI forms, candidate streaming, in-place retry resume generation,
error banners, CDP error classification, and production invariants.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from playwright.sync_api import expect

from conftest import add_reference, image_bytes
from test_ui_components import component_factory  # noqa: F401 - pytest fixture
from ref_lab import browser_recovery, collection_queue, collection_stages, service
from ref_lab.models import JobInput, ProjectInput


def _setup_candidate(run_root_dir: Path, job_id: str, seed: int = 1, file_ext: str = ".png") -> tuple[str, bytes, Path]:
    """Helper to create an authentic candidate image on disk and populate received.json."""
    raw = image_bytes(seed)
    sha = hashlib.sha256(raw).hexdigest()
    job_folder = run_root_dir / str(job_id) / "current"
    images_dir = job_folder / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    img_path = images_dir / f"{sha}{file_ext}"
    img_path.write_bytes(raw)

    received_row = {
        "asset_sha": sha,
        "original_path": str(img_path),
        "page_url": f"https://example.com/item/{seed}",
        "source": {"domain": "example.com", "rights": "editorial"},
        "acquired_at": 1700000000.0 + seed,
    }

    received_path = job_folder / "received.json"
    rows = []
    if received_path.exists():
        try:
            rows = json.loads(received_path.read_text(encoding="utf-8"))
        except Exception:
            rows = []
    rows.append(received_row)
    received_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return sha, raw, img_path


# ==============================================================================
# TIER 1: Core Feature Coverage (>= 5 tests)
# ==============================================================================

def test_tier1_ui_form_creation_and_search_mode_validation(client, monkeypatch):
    """Tier 1.1: UI form submission creates search job; verifies explicit mode requirement."""
    monkeypatch.setattr(collection_stages, "start_job", lambda lib, job_id: lib.job(job_id))

    # 1. Create project via public API
    proj_resp = client.post("/api/projects", json={
        "character": "绚濑绘里",
        "brief": "E2E搜图表单测试",
    })
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # 2. Creating collection job with omitted mode defaults to 'verified'
    default_job = client.post(f"/api/projects/{project_id}/jobs", json={
        "kind": "collection",
        "target_count": 6,
        "notes": "默认模式测试",
    })
    assert default_job.status_code == 201
    assert default_job.json()["collection_mode"] == "verified"

    # 3. Starting verified mode job via split start endpoint is rejected with 409
    start_default = client.post(f"/api/jobs/{default_job.json()['id']}/start")
    assert start_default.status_code == 409
    assert "该任务不是快速搜图" in start_default.json()["message"]

    # 4. Creating search collection job with explicit collection_mode='search'
    search_job = client.post(f"/api/projects/{project_id}/jobs", json={
        "kind": "collection",
        "collection_mode": "search",
        "target_count": 8,
        "notes": "快速搜图模式",
    })
    assert search_job.status_code == 201
    job_data = search_job.json()
    assert job_data["collection_mode"] == "search"
    assert job_data["target_count"] == 8

    # 5. Starting search mode job succeeds with 200
    start_search = client.post(f"/api/jobs/{job_data['id']}/start")
    assert start_search.status_code == 200
    assert start_search.json()["collection_mode"] == "search"


def test_tier1_candidate_image_streaming_endpoint(client, project, tmp_path, monkeypatch):
    """Tier 1.2: Candidate original image streaming endpoint delivers exact bytes and headers."""
    monkeypatch.setattr(collection_queue, "run_root", lambda: tmp_path / "collection-runs")

    # Create collection search job
    search_job = client.post(f"/api/projects/{project['id']}/jobs", json={
        "kind": "collection",
        "collection_mode": "search",
        "target_count": 4,
    }).json()

    # Populate candidate queue with authentic image
    sha, raw, _ = _setup_candidate(tmp_path / "collection-runs", search_job["id"], seed=101)

    # Request original streaming endpoint
    resp = client.get(f"/api/jobs/{search_job['id']}/candidates/{sha}/original")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert "no-store" in resp.headers["cache-control"]
    assert resp.content == raw
    assert hashlib.sha256(resp.content).hexdigest() == sha


def test_tier1_search_resume_generation_advancement(client, library, project, monkeypatch):
    """Tier 1.3: In-place retry of failed search advances search_resume_generation preserving budget."""
    # Prevent real background thread runner
    monkeypatch.setattr(collection_stages, "run_search_stage", lambda *args, **kwargs: None)

    # Create search job
    job = library.create_job(project["id"], JobInput(
        kind="collection", collection_mode="search", target_count=5
    ))
    job_id = job["id"]

    # Start first attempt then mark as blocked
    attempt1 = library.start_collection_attempt(job_id, job["revision"], "attempt-1", timeout=600)
    failed = library.update_search_stage(
        job_id, "attempt-1", "blocked",
        {"stop_reason": "browser_disconnected", "counts": {"found": 0}},
        "browser connection closed unexpectedly"
    )
    initial_gen = failed.get("search_resume_generation", 0)
    timeout_budget = failed["search_timeout_seconds"]

    # Trigger in-place retry via public API
    retry_resp = client.post(f"/api/jobs/{job_id}/search")
    assert retry_resp.status_code == 200

    # Verify updated job state
    retried_job = library.job(job_id)
    assert retried_job["id"] == job_id
    assert retried_job["search_resume_generation"] == initial_gen + 1
    assert retried_job["target_count"] == 5
    assert retried_job["search_timeout_seconds"] == timeout_budget


def test_tier1_error_banner_and_cdp_classification(component_factory):
    """Tier 1.4: Error banners render correct human-readable feedback for browser failures."""
    page = component_factory()

    def render(job):
        page.evaluate('''job => {
            candidateQueueDialog('err-job', job);
            renderCandidateQueue('err-job', {job, counts:{}, search:{}, review:{}, items:[]}, 'project');
        }''', job)

    base = {
        'id': 'err-job', 'project_id': 'project', 'status': 'blocked',
        'preparation_state': 'failed', 'search_state': 'blocked',
        'review_state': 'idle', 'can_retry_search': True, 'search_budget_exhausted': False
    }

    # Verify connection failure banner
    render({**base, 'last_error': 'browser start failed: connection refused'})
    expect(page.locator('#cq-status')).to_contain_text('浏览器连接失败')

    # Verify navigation timeout banner
    render({**base, 'last_error': 'navigation timeout'})
    expect(page.locator('#cq-status')).to_contain_text('页面导航失败')

    # Verify session extension timeout banner
    render({**base, 'last_error': 'session creation timed out waiting for extension'})
    expect(page.locator('#cq-status')).to_contain_text('无法创建采集窗口')

    # Verify renderer stall banner
    render({**base, 'last_error': 'Browser read Page.getFrameTree timed out: renderer is not answering'})
    expect(page.locator('#cq-status')).to_contain_text('浏览器控制暂时无响应')

    # Verify classify_bsk_error recognizes infrastructure codes and dead sessions
    dead_err = browser_recovery.classify_bsk_error("navigate", 1, "", "session not registered or already stopped")
    assert isinstance(dead_err, browser_recovery.BrowserInfrastructureError)
    assert getattr(dead_err, "is_session_dead", False) is True

    # Verify sanitization scrubs secrets
    sanitized = browser_recovery.sanitize_diagnostics("Authorization: Bearer secret-tok-1234")
    assert "secret-tok-1234" not in sanitized


def test_tier1_production_database_and_nico_job_invariants():
    """Tier 1.5: Verify Job 333d Nico Yazawa and asset count invariants in production sqlite."""
    db_path = Path("data/library.sqlite3")
    assert db_path.exists(), "Production database data/library.sqlite3 must exist"

    # Connect in read-only mode to prevent any modification
    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        cur = con.cursor()

        # Invariant 1: Job 333d31dec51f41b5a22d4ecc3b4d0270 (Nico Yazawa) intact
        cur.execute("SELECT id, project_id, kind, status, data FROM jobs WHERE id='333d31dec51f41b5a22d4ecc3b4d0270'")
        row = cur.fetchone()
        assert row is not None, "Job 333d Nico Yazawa must exist in jobs table"
        assert row[2] == "collection"
        assert row[3] == "blocked"

        job_data = json.loads(row[4])
        assert job_data.get("project_snapshot", {}).get("character") == "矢泽妮可"
        assert job_data.get("target_count") == 30

        # Invariant 2: Total assets >= 1,775
        cur.execute("SELECT count(*) FROM assets")
        count = cur.fetchone()[0]
        assert count >= 1775, f"Production assets must be >= 1,775, found {count}"
    finally:
        con.close()


# ==============================================================================
# TIER 2: Boundary & Error Conditions (>= 5 tests)
# ==============================================================================

def test_tier2_form_boundary_validation_missing_character(client):
    """Tier 2.1: Project creation with empty or missing character returns 422."""
    empty = client.post("/api/projects", json={"character": "", "brief": "缺少角色名"})
    assert empty.status_code == 422

    missing = client.post("/api/projects", json={"brief": "没有角色字段"})
    assert missing.status_code == 422


def test_tier2_streaming_nonexistent_sha_returns_422(client, project, tmp_path, monkeypatch):
    """Tier 2.2: Streaming non-existent or invalid candidate SHA returns 422."""
    monkeypatch.setattr(collection_queue, "run_root", lambda: tmp_path / "collection-runs")

    job = client.post(f"/api/projects/{project['id']}/jobs", json={
        "kind": "collection", "collection_mode": "search", "target_count": 2
    }).json()

    # 64-hex SHA that does not exist in candidate queue
    fake_sha = "0" * 64
    resp = client.get(f"/api/jobs/{job['id']}/candidates/{fake_sha}/original")
    assert resp.status_code == 422
    assert "not in the acquired candidate queue" in resp.json()["message"]

    # Invalid SHA format
    bad_format = client.get(f"/api/jobs/{job['id']}/candidates/invalid-sha-token/original")
    assert bad_format.status_code == 422
    assert "Invalid image SHA" in bad_format.json()["message"]


def test_tier2_streaming_tampered_bytes_fails_integrity(client, project, tmp_path, monkeypatch):
    """Tier 2.3: Modified candidate file on disk is detected and refused with 422."""
    monkeypatch.setattr(collection_queue, "run_root", lambda: tmp_path / "collection-runs")

    job = client.post(f"/api/projects/{project['id']}/jobs", json={
        "kind": "collection", "collection_mode": "search", "target_count": 2
    }).json()

    # Set up candidate with genuine SHA
    sha, _, img_path = _setup_candidate(tmp_path / "collection-runs", job["id"], seed=201)

    # Tamper with file on disk
    img_path.write_bytes(b"TAMPERED IMAGE DATA DIFFERENT FROM RECORDED SHA")

    # Request original bytes
    resp = client.get(f"/api/jobs/{job['id']}/candidates/{sha}/original")
    assert resp.status_code == 422
    assert "Original image bytes changed" in resp.json()["message"]


def test_tier2_streaming_non_collection_job_returns_409(client, library, project):
    """Tier 2.4: Attempting to stream candidates from non-collection job returns 409."""
    ref = add_reference(client, project, seed=99)
    client.patch(f"/api/references/{ref['id']}", json={"expected_revision": ref["revision"], "decision": "keep"})
    analysis_job = library.create_job(project["id"], JobInput(
        kind="analysis", reference_ids=[ref["id"]]
    ))
    fake_sha = "a" * 64
    resp = client.get(f"/api/jobs/{analysis_job['id']}/candidates/{fake_sha}/original")
    assert resp.status_code == 409
    assert "不是采集任务" in resp.json()["message"]


def test_tier2_cannot_search_on_cancelled_job(client, library, project):
    """Tier 2.5: Resuming or launching search on cancelled job returns 409."""
    job = library.create_job(project["id"], JobInput(
        kind="collection", collection_mode="search", target_count=3
    ))
    library.transition_job(job["id"], "cancelled", job["revision"], "User cancelled")

    resp = client.post(f"/api/jobs/{job['id']}/search")
    assert resp.status_code == 409
    assert "已取消的采集任务不能继续" in resp.json()["message"]


def test_tier2_browser_error_classification_boundaries():
    """Tier 2.6: Browser error classification across boundary strings and conditions."""
    # 1. Empty strings fallback to action_failed
    err = browser_recovery.classify_bsk_error("navigate", 1, "", "")
    assert isinstance(err, browser_recovery.BrowserInfrastructureError)
    assert err.code == "action_failed"

    # 2. Platform rate-limit / captcha / 403
    p_err = browser_recovery.classify_bsk_error("navigate", 1, '{"code": "rate_limited"}', "")
    assert isinstance(p_err, browser_recovery.PlatformRestrictionError)

    # 3. TimeoutExpired
    t_err = browser_recovery.classify_bsk_error("navigate", 1, '{"code": "timeout"}', "")
    assert isinstance(t_err, browser_recovery.BrowserInfrastructureError)
    assert getattr(t_err, "is_timeout", False) is True

    # 4. Dead session
    s_err = browser_recovery.classify_bsk_error("evaluate", 1, '{"code": "session_stopped"}', "")
    assert getattr(s_err, "is_session_dead", False) is True


# ==============================================================================
# TIER 3: Combinations & Multi-Step Workflows (>= 3 tests)
# ==============================================================================

def test_tier3_in_place_retry_preserves_candidates_and_advances_generation(client, library, project, tmp_path, monkeypatch):
    """Tier 3.1: Candidate queue items survive in-place search retry across generations."""
    monkeypatch.setattr(collection_queue, "run_root", lambda: tmp_path / "collection-runs")
    monkeypatch.setattr(collection_stages, "run_search_stage", lambda *args, **kwargs: None)

    job = library.create_job(project["id"], JobInput(
        kind="collection", collection_mode="search", target_count=5
    ))
    job_id = job["id"]

    # Ingest 2 candidates before failure
    sha1, raw1, _ = _setup_candidate(tmp_path / "collection-runs", job_id, seed=301)
    sha2, raw2, _ = _setup_candidate(tmp_path / "collection-runs", job_id, seed=302)

    # First attempt starts and fails
    library.start_collection_attempt(job_id, job["revision"], "attempt-a", timeout=300)
    failed = library.update_search_stage(
        job_id, "attempt-a", "blocked",
        {"stop_reason": "renderer_stall", "counts": {"found": 2}},
        "renderer became unresponsive"
    )
    assert failed.get("search_resume_generation", 0) == 0

    # In-place retry
    client.post(f"/api/jobs/{job_id}/search")
    retried = library.job(job_id)
    assert retried["search_resume_generation"] == 1

    # Verify both previously downloaded candidates remain accessible and intact
    c_resp = client.get(f"/api/jobs/{job_id}/candidates")
    assert c_resp.status_code == 200
    candidate_shas = [item["asset_sha"] for item in c_resp.json()["items"]]
    assert sha1 in candidate_shas
    assert sha2 in candidate_shas

    # Verify both can be streamed via /original
    stream1 = client.get(f"/api/jobs/{job_id}/candidates/{sha1}/original")
    assert stream1.status_code == 200
    assert stream1.content == raw1

    stream2 = client.get(f"/api/jobs/{job_id}/candidates/{sha2}/original")
    assert stream2.status_code == 200
    assert stream2.content == raw2


def test_tier3_candidate_human_decision_flow(client, library, project, tmp_path, monkeypatch):
    """Tier 3.2: Complete candidate workflow from image streaming to human decision recording."""
    monkeypatch.setattr(collection_queue, "run_root", lambda: tmp_path / "collection-runs")

    job = library.create_job(project["id"], JobInput(
        kind="collection", collection_mode="search", target_count=2
    ))
    job_id = job["id"]
    sha, _, _ = _setup_candidate(tmp_path / "collection-runs", job_id, seed=303)

    # 1. Stream image
    stream = client.get(f"/api/jobs/{job_id}/candidates/{sha}/original")
    assert stream.status_code == 200

    # 2. Human decides 'keep'
    dec_keep = client.post(f"/api/jobs/{job_id}/candidates/{sha}/decision", json={"decision": "keep"})
    assert dec_keep.status_code == 200

    # Verify decision reflected in candidate snapshot
    snapshot = collection_queue.snapshot(job_id)
    cand_item = next(i for i in snapshot["items"] if i["asset_sha"] == sha)
    assert cand_item.get("human_decision") == "keep"

    # 3. Human changes decision to 'reject'
    dec_reject = client.post(f"/api/jobs/{job_id}/candidates/{sha}/decision", json={"decision": "reject"})
    assert dec_reject.status_code == 200
    snapshot2 = collection_queue.snapshot(job_id)
    cand_item2 = next(i for i in snapshot2["items"] if i["asset_sha"] == sha)
    assert cand_item2.get("human_decision") == "reject"

    # 4. Invalid decision string rejected with 422
    dec_invalid = client.post(f"/api/jobs/{job_id}/candidates/{sha}/decision", json={"decision": "maybe"})
    assert dec_invalid.status_code == 422


def test_tier3_search_budget_exhaustion_vs_retry_ui_state(component_factory):
    """Tier 3.3: UI button toggle between retry search and budget replenish."""
    page = component_factory()

    def render(job):
        page.evaluate('''job => {
            candidateQueueDialog('budget-job', job);
            renderCandidateQueue('budget-job', {job, counts:{}, search:{}, review:{}, items:[]}, 'project');
        }''', job)

    base = {
        'id': 'budget-job', 'project_id': 'project', 'status': 'blocked',
        'preparation_state': 'failed', 'search_state': 'blocked', 'review_state': 'idle',
    }

    # State 1: Retryable error -> show retry, hide continue
    render({**base, 'can_retry_search': True, 'search_budget_exhausted': False, 'last_error': 'timeout'})
    expect(page.locator('#cq-retry-search')).to_be_visible()
    expect(page.locator('#cq-continue-search')).to_be_hidden()

    # State 2: Budget exhausted -> hide retry, show continue with text
    render({**base, 'can_retry_search': False, 'search_budget_exhausted': True})
    expect(page.locator('#cq-retry-search')).to_be_hidden()
    expect(page.locator('#cq-continue-search')).to_be_visible()
    expect(page.locator('#cq-continue-search')).to_have_text('预算耗尽 · 追加时间')


# ==============================================================================
# TIER 4: Real-World Character Search Workflows & Invariants (>= 2 tests)
# ==============================================================================

def test_tier4_character_search_workflow_simulation_eri_umi_nozomi(client, tmp_path, monkeypatch):
    """Tier 4.1: End-to-end character search simulation for Eli Ayase, Umi Sonoda, and Nozomi Tojo."""
    monkeypatch.setattr(collection_queue, "run_root", lambda: tmp_path / "collection-runs")

    characters = [
        {"name": "绚濑绘里", "work": "LoveLive!", "brief": "金发马尾学生会长"},
        {"name": "园田海未", "work": "LoveLive!", "brief": "深蓝长发大和抚子"},
        {"name": "东条希", "work": "LoveLive!", "brief": "紫色双马尾灵能力"},
    ]

    for index, char_info in enumerate(characters, 1):
        # 1. Project creation
        proj = client.post("/api/projects", json={
            "character": char_info["name"],
            "brief": f"{char_info['work']} - {char_info['brief']}",
        }).json()
        assert proj["character"] == char_info["name"]

        # 2. Search collection job creation
        job = client.post(f"/api/projects/{proj['id']}/jobs", json={
            "kind": "collection",
            "collection_mode": "search",
            "target_count": 6,
            "notes": f"{char_info['name']} 搜图任务",
        }).json()
        assert job["collection_mode"] == "search"
        assert job["target_count"] == 6

        # 3. Simulate candidate ingestion
        sha, raw, _ = _setup_candidate(tmp_path / "collection-runs", job["id"], seed=400 + index)

        # 4. Query candidate queue listing
        c_list = client.get(f"/api/jobs/{job['id']}/candidates")
        assert c_list.status_code == 200
        items = c_list.json()["items"]
        assert len(items) == 1
        assert items[0]["asset_sha"] == sha

        # 5. Stream candidate original image
        img_resp = client.get(f"/api/jobs/{job['id']}/candidates/{sha}/original")
        assert img_resp.status_code == 200
        assert img_resp.headers["content-type"] == "image/png"
        assert img_resp.content == raw
        assert hashlib.sha256(img_resp.content).hexdigest() == sha

        # 6. Human reviews and accepts candidate
        dec_resp = client.post(f"/api/jobs/{job['id']}/candidates/{sha}/decision", json={"decision": "keep"})
        assert dec_resp.status_code == 200


def test_tier4_production_database_and_nico_invariants_unmutated():
    """Tier 4.2: Comprehensive read-only invariant audit of Nico Yazawa, Eri Ayase, and asset storage."""
    db_file = Path("data/library.sqlite3")
    assert db_file.exists()

    uri = f"file:{db_file.resolve().as_posix()}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        cur = con.cursor()

        # Check Nico Yazawa Job 333d
        cur.execute("SELECT id, project_id, kind, status, data FROM jobs WHERE id='333d31dec51f41b5a22d4ecc3b4d0270'")
        nico = cur.fetchone()
        assert nico is not None, "Job 333d Nico Yazawa must exist"
        data_nico = json.loads(nico[4])
        assert data_nico.get("project_snapshot", {}).get("character") == "矢泽妮可"
        assert data_nico.get("target_count") == 30

        # Check Eri Ayase Job 5c9d
        cur.execute("SELECT id, project_id, kind, status, data FROM jobs WHERE id='5c9d0fb63700443bbe714df6d1a435eb'")
        eri = cur.fetchone()
        assert eri is not None, "Job 5c9d Eri Ayase must exist"
        data_eri = json.loads(eri[4])
        assert data_eri.get("project_snapshot", {}).get("character") == "绚濑绘里"

        # Check assets count
        cur.execute("SELECT count(*) FROM assets")
        asset_count = cur.fetchone()[0]
        assert asset_count >= 1775, f"Expected >= 1,775 assets, found {asset_count}"

        # Verify Job 5c9d collection run artifacts on filesystem exist and are untouched
        eri_run = Path(".local/collection-runs/5c9d0fb63700443bbe714df6d1a435eb/current/collector-state.json")
        assert eri_run.exists(), "Job 5c9d run artifacts must be preserved"
    finally:
        con.close()
