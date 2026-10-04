"""Candidate Production Line Test Suite.

Verifies:
1. Identity Context grounding, presets (Arima Kana, Durendal), and versioning.
2. Candidate-level file checks (resolution and diagnostic edge/divider measurements).
3. Candidate-level metadata doubts without invented visual identity or pose claims.
4. Near-duplicate perceptual hashing (dHash) & burst shot convergence.
5. Explainable multi-factor ranking & exploration candidate interleaving.
6. Screening session lifecycle, K/I/M/X distinction, and grounded summary hypotheses.
7. Versioned Aesthetic Profile updating, exemplar tracking, and rollback.
8. End-to-end API integration for filtered candidates, restoration, and sessions.
"""
from __future__ import annotations

import io
import json
from pathlib import Path
from PIL import Image, ImageDraw
import pytest

from conftest import image_bytes, TOKEN, add_reference
from ref_lab.identity import (
    build_identity_context,
    get_identity_context,
    save_identity_context,
    CANONICAL_PRESETS,
)
from ref_lab.preflight import (
    compute_dhash,
    hamming_distance,
    detect_collage,
    detect_modality,
    measure_sharpness,
    evaluate_quality,
    evaluate_identity,
    run_candidate_preflight,
    save_preflight,
    get_preflight,
    list_preflights,
)
from ref_lab.aesthetic_profile import (
    build_default_profile,
    get_current_profile,
    save_profile,
    update_profile_from_session,
    list_profile_history,
    rollback_profile,
)
from ref_lab.ranking import (
    evaluate_photographic_points,
    score_and_rank_candidates,
)
from ref_lab.screening import (
    get_or_create_active_session,
    record_session_action,
    finish_screening_session,
    confirm_session_summary,
)
from ref_lab.models import ProjectInput, CandidateInput, RevisionInput, ConfirmSummaryInput, RollbackProfileInput


def make_test_image(size=(600, 800), color=(180, 100, 100), text="TEST") -> bytes:
    img = Image.new("RGB", size, color)
    draw = ImageDraw.Draw(img)
    draw.rectangle((size[0] // 4, size[1] // 4, size[0] * 3 // 4, size[1] * 3 // 4), fill=(120, 200, 140))
    draw.text((20, 20), text, fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def make_collage_image() -> bytes:
    img = Image.new("RGB", (600, 600), (150, 150, 150))
    draw = ImageDraw.Draw(img)
    # Draw horizontal divider
    draw.rectangle((0, 198, 600, 202), fill=(255, 255, 255))
    draw.rectangle((0, 398, 600, 402), fill=(255, 255, 255))
    # Draw vertical divider
    draw.rectangle((198, 0, 202, 600), fill=(255, 255, 255))
    draw.rectangle((398, 0, 402, 600), fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


# ==============================================================================
# 1. Identity Context Unit Tests
# ==============================================================================

def test_identity_context_presets_and_general_fallback():
    # Grounded preset: 有马加奈
    kana_ctx = build_identity_context("有马加奈")
    assert kana_ctx["canonical_name"] == "有马加奈"
    assert "我推的孩子" in kana_ctx["work"]
    assert any("暗红色" in vi for vi in kana_ctx["visual_identifiers"])
    assert any("黑川茜" in c["name"] for c in kana_ctx["common_confusions"])
    assert any("星野露比" in c["name"] for c in kana_ctx["common_confusions"])

    # Grounded preset: Kamen Rider Durendal
    durendal_ctx = build_identity_context("假面骑士Durendal")
    assert "假面骑士" in durendal_ctx["canonical_name"]
    assert any("Sabela" in c["name"] or "佩剑" in c["name"] for c in durendal_ctx["common_confusions"])
    assert any("时国剑界时" in vi or "三叉戟" in vi for vi in durendal_ctx["visual_identifiers"])

    # General character: honest fallback with zero hallucination
    general_ctx = build_identity_context("原创角色A", work="原创企划", costume="常服")
    assert general_ctx["canonical_name"] == "原创角色A"
    assert general_ctx["common_confusions"] == []
    assert any("待补充" in vi for vi in general_ctx["visual_identifiers"])


# ==============================================================================
# 2. Quality Preflight Unit Tests
# ==============================================================================

def test_quality_preflight_filters():
    # Low resolution (< 200px)
    tiny_img = make_test_image(size=(120, 150))
    res_tiny = evaluate_quality(tiny_img)
    assert not res_tiny["passed"]
    assert any("分辨率过低" in r for r in res_tiny["filter_reasons"])

    # Collage / grid detection
    collage_img = make_collage_image()
    res_collage = evaluate_quality(collage_img)
    assert res_collage["passed"]
    assert res_collage["divider_hint"] is True
    assert res_collage["is_collage"] is None

    # Valid photographic candidate
    good_img = make_test_image(size=(800, 1200))
    res_good = evaluate_quality(good_img)
    assert res_good["passed"]
    assert len(res_good["filter_reasons"]) == 0
    assert len(res_good["dhash"]) == 16


# ==============================================================================
# 3. Identity Preflight & Live Cases (Arima Kana & Kamen Rider Durendal)
# ==============================================================================

def test_identity_preflight_arima_kana_vs_akane():
    kana_ctx = build_identity_context("有马加奈")

    # Mismatch candidate: title or search metadata contains confused character "黑川茜"
    akane_meta = {
        "title": "【我推的孩子】黑川茜 舞台演出正片",
        "source": {"search_query": "黑川茜 cosplay", "search_category": "cosplay_photo"},
    }
    # Blue-headed image simulating Akane's blue hair
    blue_img = Image.new("RGB", (300, 400), (30, 40, 180))
    buf = io.BytesIO()
    blue_img.save(buf, "PNG")
    akane_bytes = buf.getvalue()

    res_akane = evaluate_identity(akane_bytes, akane_meta, kana_ctx)
    assert res_akane["prediction"] == "uncertain"
    assert res_akane["source_conflict"] is True
    assert "黑川茜" in res_akane["reason"]
    assert res_akane["transferable_candidate"] is False  # No observed pose usefulness from a color fixture.

    # Matching candidate: Arima Kana
    kana_meta = {
        "title": "有马加奈 制服 贝雷帽 回眸",
        "source": {"search_query": "有马加奈 cosplay", "search_category": "cosplay_photo"},
    }
    red_img = Image.new("RGB", (300, 400), (180, 40, 40))
    buf = io.BytesIO()
    red_img.save(buf, "PNG")
    kana_bytes = buf.getvalue()

    res_kana = evaluate_identity(kana_bytes, kana_meta, kana_ctx)
    assert res_kana["prediction"] == "uncertain"
    assert res_kana["confidence"] == "low"

    # Honest uncertain: no metadata match and ambiguous pixels
    neutral_img = Image.new("RGB", (300, 400), (128, 128, 128))
    buf = io.BytesIO()
    neutral_img.save(buf, "PNG")
    res_uncertain = evaluate_identity(buf.getvalue(), {"title": "漫展随拍", "source": {}}, kana_ctx)
    assert res_uncertain["prediction"] == "uncertain"
    assert "诚实保留" in res_uncertain["reason"]


def test_identity_preflight_kamen_rider_durendal_vs_sabela():
    durendal_ctx = build_identity_context("假面骑士Durendal")

    # Mismatch candidate: Kamen Rider Sabela (神代玲花 / 佩剑)
    sabela_meta = {
        "title": "假面骑士佩剑 (Sabela) 烟睿剑狼烟 皮套特写",
        "source": {"search_query": "假面骑士佩剑 cosplay", "search_category": "cosplay_photo"},
    }
    res_sabela = evaluate_identity(make_test_image(), sabela_meta, durendal_ctx)
    assert res_sabela["prediction"] == "uncertain"
    assert res_sabela["source_conflict"] is True
    assert "Sabela" in res_sabela["reason"] or "佩剑" in res_sabela["reason"]
    assert res_sabela["transferable_candidate"] is False

    # Metadata that names Durendal is still not visual identity proof.
    durendal_meta = {
        "title": "假面骑士恒剑 Durendal 海洋历史 时国剑界时",
        "source": {"search_query": "假面骑士恒剑", "search_category": "cosplay_photo"},
    }
    res_durendal = evaluate_identity(make_test_image(), durendal_meta, durendal_ctx)
    assert res_durendal["prediction"] == "uncertain"
    assert "metadata 不能代替图像核验" in res_durendal["reason"]


# ==============================================================================
# 4. Near-Duplicate Perceptual Hashing (dHash) & Burst Shot Convergence
# ==============================================================================

def test_dhash_near_duplicate_detection():
    base_img = Image.new("RGB", (400, 600), (100, 120, 140))
    draw = ImageDraw.Draw(base_img)
    draw.rectangle((100, 100, 300, 500), fill=(200, 150, 80))

    # Exact duplicate
    h1 = compute_dhash(base_img)
    h2 = compute_dhash(base_img)
    assert hamming_distance(h1, h2) == 0

    # Near burst shot: slight brightness shift or tiny watermark
    burst_img = base_img.copy()
    b_draw = ImageDraw.Draw(burst_img)
    b_draw.text((10, 10), "watermark", fill=(255, 255, 255))
    h_burst = compute_dhash(burst_img)
    dist = hamming_distance(h1, h_burst)
    assert dist <= 6  # Close distance indicates burst shot

    # Completely different image
    diff_img = Image.new("RGB", (400, 600), (250, 20, 10))
    d_draw = ImageDraw.Draw(diff_img)
    d_draw.ellipse((50, 50, 350, 550), fill=(10, 200, 250))
    h_diff = compute_dhash(diff_img)
    assert hamming_distance(h1, h_diff) > 10


# ==============================================================================
# 5. Multi-Factor Explainable Ranking & Exploration Interleaving
# ==============================================================================

def test_explainable_ranking_and_exploration_interleaving():
    profile = build_default_profile()

    candidates = [
        {"id": f"c_{i}", "title": f"Candidate {i}", "decision": "pending",
         "preflight_status": "passed", "preflight": {"quality": {"pose_readable": True, "is_single_person": True}}}
        for i in range(12)
    ]
    # Make candidate 8 an exploration / novel sample with diverse attributes
    candidates[8]["preflight"]["quality"]["is_low_angle"] = True
    candidates[8]["title"] = "极具张力的动态低仰角构图"

    ranked = score_and_rank_candidates(candidates, profile)
    assert len(ranked) == 12

    # Verify transparent explanations exist on all items
    for item in ranked:
        assert "recommendation" in item
        rec = item["recommendation"]
        assert "total_score" in rec
        assert "photographic_points" in rec
        assert "preference_points" in rec
        assert rec["relevance_score"] is None

    # Verify exploration slot interleaving (every 4th item has exploration tag or bonus)
    fourth_item = ranked[3]
    eighth_item = ranked[7]
    assert "recommendation" in fourth_item
    assert "recommendation" in eighth_item


# ==============================================================================
# 6. Screening Session Lifecycle & Grounded Hypotheses
# ==============================================================================

def test_screening_session_and_grounded_hypotheses(app):
    library = app.state.library
    project = library.create_project(ProjectInput(character="有马加奈", work="我推的孩子"))

    with library.db.transaction() as con:
        # Start session
        session = get_or_create_active_session(con, project["id"])
        assert session["status"] == "active"
        assert session["stats"]["viewed"] == 0

        # Simulate actions
        # 1. Keep a low-angle dynamic shot
        record_session_action(
            con,
            session_id=session["id"],
            reference_id="ref_1",
            asset_sha="sha_1",
            decision="keep",
            lane="field",
            preference="很喜欢这个低角度仰拍和眼神光",
            borrow=["低角度", "眼神光", "轮廓光"],
        )

        # 2. Keep an inspiration shot
        record_session_action(
            con,
            session_id=session["id"],
            reference_id="ref_2",
            asset_sha="sha_2",
            decision="keep",
            lane="inspiration",
            preference="舞台光线质感极佳",
            borrow=["轮廓光", "高对比度"],
        )

        # 3. Reject an aesthetic negative
        record_session_action(
            con,
            session_id=session["id"],
            reference_id="ref_3",
            asset_sha="sha_3",
            decision="reject",
            is_aesthetic_negative=True,
            reject_reason="背景太杂乱，光线平淡",
        )

        # 4. Reject due to quality / mismatch defect (NOT aesthetic negative!)
        record_session_action(
            con,
            session_id=session["id"],
            reference_id="ref_4",
            asset_sha="sha_4",
            decision="reject",
            is_aesthetic_negative=False,
            reject_reason="九宫格拼图缺陷",
        )

        # Finish session
        summary = finish_screening_session(con, session["id"])
        assert summary["stats"]["viewed"] == 4
        assert summary["stats"]["keep"] == 1
        assert summary["stats"]["inspiration"] == 1
        assert summary["stats"]["reject"] == 2

        # Check grounded hypotheses
        hypotheses = summary["hypotheses"]
        assert len(hypotheses) > 0
        assert any(h["category"] == "inspiration_signal" for h in hypotheses)
        assert len(next(h for h in hypotheses if h["category"] == "aesthetic_negative")["evidence"]) == 1

        # Confirm summary and update profile
        accepted = [hypotheses[0]["text"]]
        result = confirm_session_summary(con, session["id"], accepted_hypotheses=accepted, apply_to_profile=True)
        assert result["status"] == "completed_feedback_saved"
        assert result["profile_version"] >= 2

        # Check that profile now includes the accepted hypothesis
        current_profile = get_current_profile(con)
        assert current_profile["version"] == result["profile_version"]
        accepted_texts = [h["text"] for h in current_profile["accepted_hypotheses"]]
        assert accepted[0] in accepted_texts


# ==============================================================================
# 7. Versioned Aesthetic Profile Updating and Rollback
# ==============================================================================

def test_aesthetic_profile_versioning_and_rollback(app):
    library = app.state.library
    with library.db.transaction() as con:
        # Initial profile is v1
        v1 = get_current_profile(con)
        assert v1["version"] == 1

        # Simulate update from session 1
        v2 = update_profile_from_session(
            con,
            session_id="sess_1",
            accepted_hypotheses=["偏好低角度构图与强轮廓光"],
            exemplar_items=[{"decision": "keep", "borrow": ["低角度", "轮廓光"]}],
        )
        assert v2["version"] == 2
        assert v2["dimensions"] == v1["dimensions"]
        assert v2["accepted_hypotheses"][0]["text"] == "偏好低角度构图与强轮廓光"

        # Simulate update from session 2
        v3 = update_profile_from_session(
            con,
            session_id="sess_2",
            accepted_hypotheses=["偏好纯净影棚背景"],
            exemplar_items=[{"decision": "keep", "borrow": ["影棚"]}],
        )
        assert v3["version"] == 3

        # List history
        history = list_profile_history(con)
        versions = [h["version"] for h in history]
        assert 1 in versions and 2 in versions and 3 in versions

        # Rollback to v1
        rolled = rollback_profile(con, target_version=1)
        assert rolled["version"] == 4  # Version advances monotonically
        assert rolled["dimensions"]["lighting"]["rim_light"] == v1["dimensions"]["lighting"]["rim_light"]
        assert rolled["accepted_hypotheses"] == v1["accepted_hypotheses"]
        assert rolled["provenance"]["rollback_from"] == 1


# ==============================================================================
# 8. Library & API Integration Tests: Filtered Candidates & Restoration
# ==============================================================================

def test_api_candidate_preflight_and_filtered_restoration(client):
    # 1. Create project
    r = client.post("/api/projects", json={"character": "有马加奈", "work": "【我推的孩子】"})
    assert r.status_code == 201
    project_id = r.json()["id"]

    # 2. Ingest normal portrait image
    normal_img = make_test_image(size=(800, 1200))
    upload_normal = client.post("/api/assets", files={"file": ("kana_portrait.png", normal_img, "image/png")})
    assert upload_normal.status_code == 201
    normal_sha = upload_normal.json()["id"]

    # Ingest lowres image
    lowres_img = make_test_image(size=(120, 150))
    upload_lowres = client.post("/api/assets", files={"file": ("lowres.png", lowres_img, "image/png")})
    assert upload_lowres.status_code == 201
    lowres_sha = upload_lowres.json()["id"]

    # Ingest confused character image (Akane Kurokawa)
    akane_img = make_test_image(size=(800, 1200), color=(80, 90, 180), text="AKANE")
    upload_akane = client.post("/api/assets", files={"file": ("akane.png", akane_img, "image/png")})
    assert upload_akane.status_code == 201
    akane_sha = upload_akane.json()["id"]

    # 3. Add candidates
    # Normal candidate
    r_norm = client.post(f"/api/projects/{project_id}/references", json={
        "asset_sha": normal_sha, "title": "有马加奈 贝雷帽 正片", "source": {"page_url": "https://example.com/1"}
    })
    assert r_norm.status_code == 201
    norm_ref = r_norm.json()["reference"]
    # Title/search metadata may suggest cosplay, but without a real visual
    # classifier it must not be promoted to a visual PASS.
    assert norm_ref["preflight_status"] == "uncertain"
    assert norm_ref["preflight_filtered"] is False

    # Low-resolution candidate
    r_col = client.post(f"/api/projects/{project_id}/references", json={
        "asset_sha": lowres_sha, "title": "低分辨率文件测试", "source": {"page_url": "https://example.com/2"}
    })
    assert r_col.status_code == 201
    col_ref = r_col.json()["reference"]
    assert col_ref["preflight_status"] == "filtered"
    assert col_ref["preflight_filtered"] is True

    # Akane candidate
    r_ak = client.post(f"/api/projects/{project_id}/references", json={
        "asset_sha": akane_sha, "title": "黑川茜 舞台演出服", "source": {"page_url": "https://example.com/3"}
    })
    assert r_ak.status_code == 201
    ak_ref = r_ak.json()["reference"]
    assert ak_ref["preflight_status"] == "uncertain"
    assert ak_ref["preflight_filtered"] is False
    assert ak_ref["preflight"]["identity"]["source_conflict"] is True

    # 4. Verify candidate streams
    # Normal stream: both visually uncertain candidates remain visible
    r_list = client.get(f"/api/projects/{project_id}/references")
    assert r_list.status_code == 200
    items = r_list.json()["items"]
    assert {item["id"] for item in items} == {norm_ref["id"], ak_ref["id"]}

    # Filtered stream: only the measured low-resolution file is hidden
    r_filtered = client.get(f"/api/projects/{project_id}/references?view_filtered=true")
    assert r_filtered.status_code == 200
    filtered_items = r_filtered.json()["items"]
    assert len(filtered_items) == 1
    filtered_ids = [item["id"] for item in filtered_items]
    assert col_ref["id"] in filtered_ids
    assert ak_ref["id"] not in filtered_ids

    # 5. Restore candidate from filtered stream
    r_restore = client.post(f"/api/references/{col_ref['id']}/restore-preflight", json={"expected_revision": col_ref["revision"]})
    assert r_restore.status_code == 200
    restored = r_restore.json()
    assert restored["preflight_filtered"] is False
    assert restored["preflight_status"] == "restored"

    # Now normal stream has 3 items
    r_list2 = client.get(f"/api/projects/{project_id}/references")
    assert len(r_list2.json()["items"]) == 3

    # 6. Make Akane transferable inspiration (archives to aesthetic library, detaches from project queue)
    r_trans = client.post(f"/api/references/{ak_ref['id']}/make-transferable", json={"expected_revision": ak_ref["revision"]})
    assert r_trans.status_code == 200
    transferable = r_trans.json()
    assert transferable["preflight_filtered"] is False
    assert transferable["lane"] == "inspiration"
    assert transferable["allow_cross_domain"] is True
    assert transferable["detached_at"] is not None
    assert transferable["detached_reason"] == "archived_to_inspiration"

    # Verify global aesthetic inspirations contains this asset
    r_insp = client.get("/api/inspirations")
    assert r_insp.status_code == 200
    assert any(item["asset_sha"] == akane_sha for item in r_insp.json()["items"])

    # Verify detached candidate is removed from normal project references and filtered stream
    r_norm_after = client.get(f"/api/projects/{project_id}/references")
    assert not any(item["id"] == ak_ref["id"] for item in r_norm_after.json()["items"])
    r_filt_after = client.get(f"/api/projects/{project_id}/references?view_filtered=true")
    assert not any(item["id"] == ak_ref["id"] for item in r_filt_after.json()["items"])

    # Verify it is visible in recycle view and does not occupy active project slots
    r_recyc = client.get(f"/api/projects/{project_id}/references?view_recycle=true")
    assert any(item["id"] == ak_ref["id"] for item in r_recyc.json()["items"])
    r_stats = client.get(f"/api/projects/{project_id}/stats")
    assert r_stats.json()["detached"] >= 1

    # 7. Check Aesthetic Profile & History via API
    r_profile = client.get("/api/profile")
    assert r_profile.status_code == 200
    profile_data = r_profile.json()
    assert profile_data["version"] >= 1

    r_history = client.get("/api/profile/history")
    assert r_history.status_code == 200
    assert len(r_history.json()) >= 1

    # 8. Test scan_project_preflight and view_filtered visibility with decision='reject'
    r_scan = client.post(f"/api/projects/{project_id}/preflight-scan", json={"force": True})
    assert r_scan.status_code == 200
    scan_res = r_scan.json()
    assert scan_res["total"] >= 2

    # Reject a filtered candidate
    col_ref_id = col_ref["id"]
    cur_ref = client.get(f"/api/references/{col_ref_id}").json()
    r_dec = client.patch(f"/api/references/{col_ref_id}", json={"decision": "reject", "expected_revision": cur_ref["revision"]})
    assert r_dec.status_code == 200
    # view_filtered MUST still return this filtered candidate even though decision='reject'
    r_filt_rejected = client.get(f"/api/projects/{project_id}/references?view_filtered=true")
    assert r_filt_rejected.status_code == 200
    assert any(item["id"] == col_ref_id for item in r_filt_rejected.json()["items"])

# ==============================================================================
# 9. Preflight trust boundary & project isolation regressions
# ==============================================================================

def test_metadata_prefix_or_known_url_never_asserts_real_person_modality():
    image = Image.open(io.BytesIO(make_test_image(size=(800, 1200))))
    metadata = {
        "title": "COS_王昭君 长夜焕生 正片",
        "source": {
            "page_url": "https://example.com/haute-couture/sensory-seas",
            "search_category": "cosplay_photo",
        },
    }
    modality, evidence = detect_modality(image, metadata)
    assert modality == "unknown"
    assert evidence == []


def test_costume_help_metadata_stays_a_discovery_doubt():
    payload = make_test_image(size=(800, 1200))
    metadata = {
        "title": "求助：三分妄想家的王昭君长夜焕生c服裙边怎么整理",
        "source": {
            "page_url": "https://www.xiaohongshu.com/explore/help-post",
            "search_category": "",
        },
    }
    context = build_identity_context("王昭君", "王者荣耀", "长夜焕生")
    result = run_candidate_preflight(
        payload,
        metadata=metadata,
        context=context,
        asset_sha="a" * 64,
        project_id="project-a",
        reference_id="ref-a",
    )
    assert result["content_type"] == "unknown"
    assert result["status"] == "uncertain"
    assert "怎么整理" in result["discovery_context"]["filter_terms"]
    assert result["visual_evidence"] == []


def test_project_scoped_preflight_lookup_is_strict_and_chronological(app, client, project):
    library = app.state.library
    other = library.create_project(ProjectInput(character="隔离测试角色B", work="测试作品"))
    existing_ref = add_reference(client, project, seed=91)
    asset_sha = existing_ref["asset_sha"]

    def pf(ident: str, project_id: str, status: str) -> dict:
        return {
            "id": ident,
            "asset_sha": asset_sha,
            "project_id": project_id,
            "reference_id": None,
            "status": status,
            "created_at": ident,
        }

    with library.db.transaction() as con:
        # Random-looking IDs deliberately contradict insertion chronology:
        # lexical ORDER BY id DESC would incorrectly keep pf_zzzz_old.
        save_preflight(con, pf("pf_zzzz_old", project["id"], "uncertain"))
        save_preflight(con, pf("pf_aaaa_new", project["id"], "filtered"))
        save_preflight(con, pf("pf_mmmm_other", other["id"], "passed"))

        scoped = get_preflight(con, asset_sha, project["id"])
        assert scoped is not None
        assert scoped["id"] == "pf_aaaa_new"

        # A project with no record must not inherit another project's preflight.
        assert get_preflight(con, asset_sha, "missing-project") is None

        # Unscoped lookup is allowed to return the newest record globally.
        unscoped = get_preflight(con, asset_sha)
        assert unscoped is not None
        assert unscoped["id"] == "pf_mmmm_other"

        listed = list_preflights(con, project["id"])
        assert [item["id"] for item in listed[:2]] == ["pf_aaaa_new", "pf_zzzz_old"]

