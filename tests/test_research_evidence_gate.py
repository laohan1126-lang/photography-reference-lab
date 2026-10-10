"""Red team automated test suite for Research Evidence Quality Gate Loop.

Covers all 6 historical failure patterns and verified golden samples:
1. Equipment contradiction (Canon R5 vs Sony A7R)
2. Hallucinated quote ("剑像小棍子")
3. Mismatched travel vlog URL (Manny Ortiz Kolkata Vlog I6sdXDIjo50)
4. Screenshot timestamp mismatch
5. Timeline anachronism (2024 video citing late-2025 gear)
6. Speculative pseudoscience (embryonic reflex & fabricated 90/10 ratio)
7. Timestamp out of bounds
8. Unaccessible source media leads to BLOCKED
9. Authentic verified golden claims achieve PASS and produce AdmissionReceipt
10. Rework cycle progression: cycle 1 -> REVISE, cycle 2 -> BLOCKED
11. Neutralization of self-attested verified=true
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from ref_lab.evidence_gate.loop import QualityGateLoop
from ref_lab.evidence_gate.models import (
    ClaimRecord,
    ClaimedNumber,
    MediaArtifactRecord,
    ResearchEvidencePackage,
    SourceMetadata,
    TimestampSpan,
)


def make_valid_base_package() -> ResearchEvidencePackage:
    """Creates a clean, valid evidence package based on calibrated XiaoYanJun research."""
    source = SourceMetadata(
        url="https://www.bilibili.com/video/BV1MD421L7VK/",
        platform="bilibili",
        author="小言Jun",
        title="【第一视角】挑战最细节动作引导摄影师",
        published_date="2024-03-24",
        duration_seconds=340.0,
        known_equipment=["Canon EOS R5", "RF 50mm f/1.8 STM"],
        is_tutorial_confirmed=True,
    )
    media = MediaArtifactRecord(
        local_path="scratch/BV1MD421L7VK/video.mp4",
        sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        media_type="video",
        status="ACCESSIBLE",
    )
    claim = ClaimRecord(
        claim_id="claim-1.1",
        statement="小言Jun 在漫展走廊使用的是 Canon EOS R5 + RF 50mm f/1.8 STM 镜头，全程 f/2.8 光圈，三灯系统。",
        category="B",
        source_url="https://www.bilibili.com/video/BV1MD421L7VK/",
        time_spans=[
            TimestampSpan(
                start_seconds=0.0,
                end_seconds=15.0,
                formatted_time="00:00-00:15",
                screenshot_timestamp_seconds=5.0,
            )
        ],
        supporting_evidence="视频简介文本直写：'设备：佳能r5+rf501.8 光圈全程2.8 三灯阵，一个逆光 一个面光 一个顶光'。画面可见机身与三灯设置。",
        verbatim_quote="设备：佳能r5+rf501.8 光圈全程2.8 三灯阵",
        equipment_tags=["Canon EOS R5", "RF 50mm f/1.8 STM"],
        unknown_conditions=["无法确认具体闪光灯品牌型号"],
    )
    return ResearchEvidencePackage(
        package_id="pkg_calibration_test",
        topic="人像摄影动作引导与设备配置",
        author="Antigravity Researcher",
        created_at="2026-10-10T12:00:00Z",
        sources=[source],
        media_artifacts=[media],
        claims=[claim],
    )


def test_redteam_sony_a7r_contradiction():
    """Red team 1: Canon R5 falsely reported as Sony A7R."""
    pkg = make_valid_base_package()
    pkg.claims[0].equipment_tags = ["Sony A7R IV", "35mm 定焦"]
    pkg.claims[0].statement = "小言Jun 使用 Sony A7R IV 搭配 35mm 定焦镜头进行拍摄。"

    gate = QualityGateLoop()
    decision, receipt, rework = gate.evaluate(pkg, cycle=1)

    assert decision == "REVISE"
    assert rework is not None
    assert any(i.issue_code == "EQUIPMENT_CONTRADICTION" for i in rework.issues)
    contradiction_issue = next(i for i in rework.issues if i.issue_code == "EQUIPMENT_CONTRADICTION")
    assert "Sony A7R IV" in contradiction_issue.message
    assert "claim-1.1" in rework.affected_claim_ids


def test_redteam_hallucinated_little_stick_dialogue():
    """Red team 2: Fabricated dialogue claiming photographer sighed 'sword looks like a little stick'."""
    pkg = make_valid_base_package()
    fake_claim = ClaimRecord(
        claim_id="claim-1.2-fake",
        statement="摄影师叹气说：你看剑根本看不出来，像个小棍子，必须换手持剑。",
        category="B",
        source_url="https://www.bilibili.com/video/BV1MD421L7VK/",
        time_spans=[
            TimestampSpan(
                start_seconds=105.0,
                end_seconds=134.0,
                formatted_time="01:45-02:14",
                screenshot_timestamp_seconds=115.0,
            )
        ],
        supporting_evidence="视频 01:45-02:14 段落摄影师对白。",
        verbatim_quote="你看剑根本看不出来，像个小棍子",
    )
    pkg.claims = [fake_claim]

    gate = QualityGateLoop()
    decision, receipt, rework = gate.evaluate(pkg, cycle=1)

    assert decision == "REVISE"
    assert rework is not None
    assert any(i.issue_code == "VERBATIM_HALLUCINATION" for i in rework.issues)
    hallucination_issue = next(i for i in rework.issues if i.issue_code == "VERBATIM_HALLUCINATION")
    assert "像个小棍子" in hallucination_issue.message


def test_redteam_manny_vlog_url_mismatch():
    """Red team 3: Manny Ortiz Kolkata Street Photo Vlog cited as posing tutorial."""
    pkg = make_valid_base_package()
    bad_source = SourceMetadata(
        url="https://www.youtube.com/watch?v=I6sdXDIjo50",
        platform="youtube",
        author="Manny Ortiz",
        title="Posing and Portrait Masterclass",  # Falsely titled
        duration_seconds=600.0,
    )
    pkg.sources.append(bad_source)
    pkg.claims[0].source_url = bad_source.url

    gate = QualityGateLoop()
    decision, receipt, rework = gate.evaluate(pkg, cycle=1)

    assert decision == "REVISE"
    assert rework is not None
    assert any(i.issue_code == "URL_MISMATCH_VLOG" for i in rework.issues)


def test_redteam_screenshot_timestamp_mismatch():
    """Red team 4: Screenshot timestamp (04:30 = 270s) out of sync with interval (01:45-02:14 = 105-134s)."""
    pkg = make_valid_base_package()
    pkg.claims[0].time_spans = [
        TimestampSpan(
            start_seconds=105.0,
            end_seconds=134.0,
            formatted_time="01:45-02:14",
            screenshot_timestamp_seconds=270.0,  # 04:30, completely mismatched!
        )
    ]

    gate = QualityGateLoop()
    decision, receipt, rework = gate.evaluate(pkg, cycle=1)

    assert decision == "REVISE"
    assert rework is not None
    assert any(i.issue_code == "SCREENSHOT_TIMESTAMP_MISMATCH" for i in rework.issues)


def test_redteam_timeline_anachronism():
    """Red team 5: 2024 video citing equipment released in late 2025."""
    pkg = make_valid_base_package()
    # Video published on 2024-03-24, but claims to use Sony A7 V (released late 2025)
    pkg.claims[0].equipment_tags = ["Sony A7 V"]
    pkg.claims[0].statement = "小言Jun 在 2024年3月视频中使用 Sony A7 V 拍摄。"

    gate = QualityGateLoop()
    decision, receipt, rework = gate.evaluate(pkg, cycle=1)

    assert decision == "REVISE"
    assert rework is not None
    assert any(i.issue_code == "TIMELINE_ANACHRONISM" for i in rework.issues)


def test_redteam_pseudoscience_and_pseudo_precision():
    """Red team 6: Embryonic startle reflex hypothesis and ungrounded 90/10 ratio."""
    pkg = make_valid_base_package()
    speculative_claim = ClaimRecord(
        claim_id="claim-1.4-pseudo",
        statement="模特肌肉紧绷源自胎儿期防御性惊跳反射，将剑尖下插地面作为物理三角支点使身体承重从 90/10 变成 60/40。",
        category="C",
        source_url="https://www.bilibili.com/video/BV1MD421L7VK/",
        supporting_evidence="观察视频中的动作推断得出。",
    )
    pkg.claims = [speculative_claim]

    gate = QualityGateLoop()
    decision, receipt, rework = gate.evaluate(pkg, cycle=1)

    assert decision == "REVISE"
    assert rework is not None
    assert any(i.issue_code == "PSEUDOSCIENCE_OVERGENERALIZATION" for i in rework.issues)
    assert any(i.issue_code == "UNVERIFIED_PSEUDO_PRECISION" for i in rework.issues)


def test_redteam_timestamp_out_of_bounds():
    """Red team 7: Timestamp exceeds total video duration."""
    pkg = make_valid_base_package()
    pkg.claims[0].time_spans = [
        TimestampSpan(
            start_seconds=400.0,
            end_seconds=450.0,  # Duration is 340s
            formatted_time="06:40-07:30",
        )
    ]

    gate = QualityGateLoop()
    decision, receipt, rework = gate.evaluate(pkg, cycle=1)

    assert decision == "REVISE"
    assert rework is not None
    assert any(i.issue_code == "TIMESTAMP_OUT_OF_BOUNDS" for i in rework.issues)


def test_redteam_unaccessible_media_blocks():
    """Red team 8: Unaccessible media immediately blocks gate."""
    pkg = make_valid_base_package()
    pkg.media_artifacts[0].status = "UNACCESSIBLE"

    gate = QualityGateLoop()
    decision, receipt, rework = gate.evaluate(pkg, cycle=1)

    assert decision == "BLOCKED"
    assert rework is not None
    assert any(i.issue_code == "MEDIA_UNACCESSIBLE" for i in rework.issues)


def test_rework_loop_cycle_limit():
    """Red team 9: Exceeding max rework cycles (2) changes REVISE to BLOCKED."""
    pkg = make_valid_base_package()
    pkg.claims[0].statement = "小言Jun 使用 Sony A7R IV 拍摄。"
    pkg.claims[0].equipment_tags = ["Sony A7R IV"]

    gate = QualityGateLoop(max_cycles=2)

    # Cycle 1: REVISE
    decision_1, receipt_1, rework_1 = gate.evaluate(pkg, cycle=1)
    assert decision_1 == "REVISE"
    assert rework_1.cycle == 1

    # Cycle 2: BLOCKED
    decision_2, receipt_2, rework_2 = gate.evaluate(pkg, cycle=2)
    assert decision_2 == "BLOCKED"
    assert rework_2.cycle == 2
    assert "Reached maximum rework cycle limit" in rework_2.summary


def test_self_attested_verified_neutralized():
    """Red team 10: Researcher self-attesting verified=true does not bypass errors."""
    pkg = make_valid_base_package()
    pkg.claims[0].self_attested_verified = True
    pkg.claims[0].statement = "小言Jun 叹气说像个小棍子。"
    pkg.claims[0].verbatim_quote = "像个小棍子"

    gate = QualityGateLoop()
    decision, receipt, rework = gate.evaluate(pkg, cycle=1)

    assert decision == "REVISE"
    assert any(i.issue_code == "SELF_ATTESTATION_IGNORED" for i in rework.issues)
    assert any(i.issue_code == "VERBATIM_HALLUCINATION" for i in rework.issues)


def test_golden_sample_passes_and_issues_receipt():
    """Positive test: Calibrated and verified claims pass and generate AdmissionReceipt."""
    source_xy = SourceMetadata(
        url="https://www.bilibili.com/video/BV1MD421L7VK/",
        platform="bilibili",
        author="小言Jun",
        title="【第一视角】挑战最细节动作引导摄影师",
        published_date="2024-03-24",
        duration_seconds=340.0,
        known_equipment=["Canon EOS R5", "RF 50mm f/1.8 STM"],
    )
    source_lhy = SourceMetadata(
        url="https://www.bilibili.com/video/BV1imaN6tEc8/",
        platform="bilibili",
        author="林海音Haiyin",
        title="拍照不会摆姿势？这几个技巧让你秒变拍照达人！",
        published_date="2024-05-18",
        duration_seconds=312.0,
        known_equipment=["Canon EOS R5", "RF 50mm f/1.2 L"],
    )

    claims = [
        # XiaoYanJun 1.1 Equipment
        ClaimRecord(
            claim_id="claim-1.1",
            statement="小言Jun 在漫展走廊使用的是 Canon EOS R5 + RF 50mm f/1.8 STM 镜头，全程 f/2.8 光圈，三灯系统。",
            category="B",
            source_url="https://www.bilibili.com/video/BV1MD421L7VK/",
            time_spans=[TimestampSpan(start_seconds=0.0, end_seconds=15.0, formatted_time="00:00-00:15")],
            supporting_evidence="视频简介作者直写：'设备：佳能r5+rf501.8 光圈全程2.8 三灯阵，一个逆光 一个面光 一个顶光'。",
            equipment_tags=["Canon EOS R5", "RF 50mm f/1.8 STM"],
        ),
        # XiaoYanJun 1.2 Hand Switch to Prevent Occlusion
        ClaimRecord(
            claim_id="claim-1.2",
            statement="摄影师指示模特双手持剑/鞘对调并撑出手臂，是为了解决一只手完全遮挡另一只手的问题。",
            category="B",
            source_url="https://www.bilibili.com/video/BV1MD421L7VK/",
            time_spans=[TimestampSpan(start_seconds=105.0, end_seconds=134.0, formatted_time="01:45-02:14")],
            supporting_evidence="时间码 02:08-02:14 摄影师原话与音频逐字一致。",
            verbatim_quote="因为这样一只手，你把那只手完全挡完了！",
        ),
        # XiaoYanJun 1.3 Sword Angle
        ClaimRecord(
            claim_id="claim-1.3",
            statement="摄影师口令强调'剑斜脸别斜'，以避免武器直冲镜头透视短缩并保持视线警惕感。",
            category="B",
            source_url="https://www.bilibili.com/video/BV1MD421L7VK/",
            time_spans=[TimestampSpan(start_seconds=73.0, end_seconds=85.0, formatted_time="01:13-01:25")],
            supporting_evidence="时间码 01:18-01:22 摄影师口令：'不是，你剑斜，你脸别斜，剑斜一点点，好，上来，好！'。",
            verbatim_quote="不是，你剑斜，你脸别斜，剑斜一点点",
        ),
        # Lin Haiyin 2.1 Dynamic Movement
        ClaimRecord(
            claim_id="claim-2.1",
            statement="对于缺乏摆姿经验的被摄者，摄影师指示其在走动和回眸过程中进行抓拍比僵止静拍更自然。",
            category="B",
            source_url="https://www.bilibili.com/video/BV1imaN6tEc8/",
            time_spans=[TimestampSpan(start_seconds=162.0, end_seconds=180.0, formatted_time="02:42-03:00")],
            supporting_evidence="时间码 02:46-02:58 林海音原声自述动起来抓拍原则。",
            verbatim_quote="那不太会摆姿势的人呢，我们可以先让他动起来：往前走几步，回头看一看",
        ),
    ]

    golden_package = ResearchEvidencePackage(
        package_id="pkg_golden_curriculum_admission",
        topic="人像摆姿真实引导实证教学",
        author="Antigravity Grounded Researcher",
        created_at="2026-10-10T12:00:00Z",
        sources=[source_xy, source_lhy],
        media_artifacts=[
            MediaArtifactRecord(
                local_path="scratch/BV1MD421L7VK/video.mp4",
                sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                media_type="video",
                status="ACCESSIBLE",
            ),
            MediaArtifactRecord(
                local_path="scratch/BV1imaN6tEc8/video.mp4",
                sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                media_type="video",
                status="ACCESSIBLE",
            ),
        ],
        claims=claims,
    )

    gate = QualityGateLoop()
    decision, receipt, rework = gate.evaluate(golden_package, cycle=1)

    assert decision == "PASS"
    assert receipt is not None
    assert rework is None
    assert receipt.decision == "PASS"
    assert receipt.total_claims_verified == 4
    assert receipt.scope == "photography_course_curriculum"
    assert receipt.approved_manifest_hash == golden_package.compute_fingerprint()
