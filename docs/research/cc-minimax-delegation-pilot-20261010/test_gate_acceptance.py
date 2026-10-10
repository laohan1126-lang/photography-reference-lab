"""Codex-owned behavioral acceptance; immutable during external CC development.

Fixtures contain real nonempty temporary bytes, not authentic course observations.
"""
from hashlib import sha256

import pytest

from ref_lab.evidence_gate.loop import QualityGateLoop
from ref_lab.evidence_gate.models import (
    ClaimRecord, MediaArtifactRecord, ResearchEvidencePackage,
    SourceMetadata, TimestampSpan,
)


def package_with_real_media(tmp_path):
    path = tmp_path / "fixture.txt"
    content = b"Structural fixture: subject raises a hand at second one.\n"
    path.write_bytes(content)
    assert path.is_file() and path.stat().st_size > 0
    source = SourceMetadata(
        url="https://example.com/structural-fixture", platform="local",
        author="Fixture author", title="Structural test fixture", duration_seconds=10,
    )
    return ResearchEvidencePackage(
        package_id="codex-independent-fixture", topic="Structural acceptance",
        author="Codex acceptance", created_at="2026-10-10T00:00:00Z",
        sources=[source],
        media_artifacts=[MediaArtifactRecord(
            local_path=str(path), sha256=sha256(content).hexdigest(),
            media_type="transcript", status="ACCESSIBLE", file_size_bytes=len(content),
        )],
        claims=[ClaimRecord(
            claim_id="fixture-hand", statement="The fixture subject raises a hand.",
            category="A", source_url=source.url,
            time_spans=[TimestampSpan(start_seconds=1, end_seconds=2)],
            supporting_evidence=f"Structural fixture bytes in {path}",
        )],
    )


def assert_rejected_without_receipt(package, tmp_path):
    for cycle in (1, 2):
        gate = QualityGateLoop()
        decision, receipt, rework = gate.evaluate(package, cycle=cycle)
        assert decision in {"REVISE", "BLOCKED"}, f"unexpected admission: {decision}"
        assert receipt is None, "rejected evidence must have no admission receipt"
        assert rework is not None
        assert any(issue.severity == "ERROR" for issue in rework.issues)
        output = tmp_path / f"export-{cycle}"
        artifacts = gate.export_artifacts(decision, receipt, rework, output)
        assert "receipt" not in artifacts
        assert not (output / "ADMISSION_RECEIPT.json").exists()


def test_a_accessible_missing_file_rejected(tmp_path):
    package = package_with_real_media(tmp_path)
    package.media_artifacts[0].local_path = str(tmp_path / "never-created.txt")
    assert not (tmp_path / "never-created.txt").exists()
    assert_rejected_without_receipt(package, tmp_path)


def test_b_real_file_wrong_hash_rejected(tmp_path):
    package = package_with_real_media(tmp_path)
    wrong_digest = sha256(b"different actual nonempty content").hexdigest()
    assert wrong_digest != package.media_artifacts[0].sha256
    package.media_artifacts[0].sha256 = wrong_digest
    assert_rejected_without_receipt(package, tmp_path)


def test_c_real_nonempty_matching_file_admitted(tmp_path):
    package = package_with_real_media(tmp_path)
    gate = QualityGateLoop()
    decision, receipt, rework = gate.evaluate(package)
    assert decision == "PASS", rework
    assert receipt is not None and receipt.total_claims_verified == 1
    assert receipt.approved_manifest_hash == package.compute_fingerprint()
    assert rework is None
    artifacts = gate.export_artifacts(decision, receipt, rework, tmp_path / "export")
    assert artifacts["receipt"].is_file()


@pytest.mark.parametrize("keep_sources", [False, True], ids=["all-empty", "sources-only"])
def test_d_empty_research_not_admitted(tmp_path, keep_sources):
    package = package_with_real_media(tmp_path)
    package.claims = []
    package.media_artifacts = []
    if not keep_sources:
        package.sources = []
    assert_rejected_without_receipt(package, tmp_path)
