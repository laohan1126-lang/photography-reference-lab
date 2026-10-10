"""Tier 1: Programmatic Fact Checker.

Audits structured evidence for deterministic facts:
0. Presence of substantive research (empty / sources-only packages assert nothing)
1. URL authenticity and blacklist/vlog mismatch
2. Timestamp bounds vs video duration
3. Screenshot timestamp concordance
4. Cross-document and intra-document equipment contradiction
5. Equipment release timeline anachronisms
6. Unverified pseudo-exact numbers (e.g., 90/10, 30°-60°)
7. Media artifact presence on disk, hash integrity, and unread sources
   (declared ACCESSIBLE media must exist, be readable, and match its SHA256)
8. Neutralization of self-attested verification
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Optional

from ref_lab.evidence_gate.models import (
    AuditIssue,
    ClaimRecord,
    MediaArtifactRecord,
    ResearchEvidencePackage,
    SourceMetadata,
)

# Known mismatched URLs: Travel Vlogs falsely cited as photography posing tutorials
KNOWN_MISMATCHED_URLS: dict[str, str] = {
    "https://www.youtube.com/watch?v=I6sdXDIjo50": "Manny Ortiz Kolkata Street Photo Vlog (travel footage, not posing tutorial)",
    "http://www.youtube.com/watch?v=I6sdXDIjo50": "Manny Ortiz Kolkata Street Photo Vlog (travel footage, not posing tutorial)",
    "https://youtu.be/I6sdXDIjo50": "Manny Ortiz Kolkata Street Photo Vlog (travel footage, not posing tutorial)",
    "I6sdXDIjo50": "Manny Ortiz Kolkata Street Photo Vlog (travel footage, not posing tutorial)",
}

# Known hardware launch dates (YYYY-MM)
EQUIPMENT_RELEASE_DATES: dict[str, str] = {
    "sony a7 v": "2025-11",
    "sony a7v": "2025-11",
    "sony a7m5": "2025-11",
    "canon r5 mark ii": "2024-08",
    "canon r5m2": "2024-08",
    "canon eos r5 mark ii": "2024-08",
    "canon eos r6 mark iii": "2025-11",
    "canon r5": "2020-07",
    "canon eos r5": "2020-07",
    "sony a7 iv": "2021-12",
    "sony a7r v": "2022-11",
    "sony a7r iv": "2019-09",
}

# Regex for pseudo-exact numbers lacking empirical measurement
PSEUDO_RATIO_PATTERN = re.compile(r"\b(\d{2}/\d{2})\b")
PSEUDO_ANGLE_PATTERN = re.compile(r"(\d+°\s*[-~至到]\s*\d+°|\b\d+度\s*[-~至到]\s*\d+度)")


class ProgrammaticChecker:
    """Executes Tier 1 programmatic fact checks on a ResearchEvidencePackage."""

    def __init__(self, media_root: Optional[Path] = None):
        self.media_root = media_root

    def audit(self, package: ResearchEvidencePackage) -> list[AuditIssue]:
        issues: list[AuditIssue] = []
        source_map: dict[str, SourceMetadata] = {s.url: s for s in package.sources}
        artifact_map: dict[str, MediaArtifactRecord] = {a.local_path: a for a in package.media_artifacts}

        # 0. Substantive-research floor.
        # A package with no claims asserts nothing, so every downstream per-claim loop below
        # would contribute zero issues and the loop would treat "nothing wrong" as PASS and
        # mint a receipt with total_claims_verified=0. Source metadata alone is likewise not
        # research: it describes where to look without recording a single verified assertion.
        issues.extend(self._check_substantive_research_present(package))

        # 1. Check sources & URLs
        for source in package.sources:
            issues.extend(self._check_source_url(source))

        # 2. Check media artifacts
        issues.extend(self._check_media_artifacts(package.media_artifacts))

        # 3. Check claims
        for claim in package.claims:
            source = source_map.get(claim.source_url)
            issues.extend(self._check_claim(claim, source, package))

        # 4. Check cross-document consistency
        issues.extend(self._check_cross_document_consistency(package))

        return issues

    @staticmethod
    def _check_substantive_research_present(package: ResearchEvidencePackage) -> list[AuditIssue]:
        """Reject packages that assert nothing, whether fully empty or sources-only."""
        if package.claims:
            return []

        if not package.sources and not package.media_artifacts:
            message = (
                "Evidence package is empty: it declares no sources, no media artifacts and no "
                "claims, so there is no research to audit and nothing to admit."
            )
            actual: object = {"sources": 0, "media_artifacts": 0, "claims": 0}
            remediation = (
                "Deliver actual researched claims backed by declared source metadata and media."
            )
        else:
            message = (
                f"Evidence package declares {len(package.sources)} source(s) and "
                f"{len(package.media_artifacts)} media artifact(s) but zero claims. Source metadata "
                "alone is not substantive research: no assertion has actually been made."
            )
            actual = {
                "sources": len(package.sources),
                "media_artifacts": len(package.media_artifacts),
                "claims": 0,
            }
            remediation = (
                "Extract and record the claims the cited sources support, each with a claim_id, "
                "statement and supporting evidence."
            )

        return [
            AuditIssue(
                tier="TIER_1_PROGRAMMATIC",
                issue_code="EMPTY_RESEARCH_EVIDENCE",
                severity="ERROR",
                field="claims",
                message=message,
                actual_value=actual,
                expected_or_conflict="At least one substantiated claim record",
                remediation=remediation,
            )
        ]

    def _check_source_url(self, source: SourceMetadata) -> list[AuditIssue]:
        issues: list[AuditIssue] = []
        for bad_url, reason in KNOWN_MISMATCHED_URLS.items():
            if bad_url in source.url:
                issues.append(
                    AuditIssue(
                        tier="TIER_1_PROGRAMMATIC",
                        issue_code="URL_MISMATCH_VLOG",
                        severity="ERROR",
                        field="url",
                        message=f"Cited source is a known travel/street vlog, not posing instruction: {reason}",
                        actual_value=source.url,
                        expected_or_conflict="Valid posing instruction tutorial URL",
                        remediation="Remove or replace this source with a genuine posing tutorial.",
                    )
                )
        return issues

    def _check_media_artifacts(self, artifacts: list[MediaArtifactRecord]) -> list[AuditIssue]:
        issues: list[AuditIssue] = []
        for artifact in artifacts:
            if artifact.status == "UNACCESSIBLE":
                issues.append(
                    AuditIssue(
                        tier="TIER_1_PROGRAMMATIC",
                        issue_code="MEDIA_UNACCESSIBLE",
                        severity="ERROR",
                        field="status",
                        message=f"Media artifact is marked UNACCESSIBLE: {artifact.local_path}",
                        actual_value=artifact.status,
                        expected_or_conflict="ACCESSIBLE",
                        remediation="Ensure original media is downloaded and accessible before making claims.",
                    )
                )
            elif artifact.status == "NOT_DOWNLOADED":
                issues.append(
                    AuditIssue(
                        tier="TIER_1_PROGRAMMATIC",
                        issue_code="MEDIA_NOT_DOWNLOADED",
                        severity="ERROR",
                        field="status",
                        message=f"Media artifact is not downloaded: {artifact.local_path}",
                        actual_value=artifact.status,
                        expected_or_conflict="ACCESSIBLE",
                        remediation="Download media and verify checksum.",
                    )
                )
            elif artifact.status == "ACCESSIBLE":
                # A declared-ACCESSIBLE artifact must be verifiable on disk: the file has to exist,
                # be a regular readable file, and hash to the declared SHA256. Silence here would
                # let an unverifiable artifact pass the gate and receive an admission receipt.
                issues.extend(self._check_accessible_media(artifact))
        return issues

    @staticmethod
    def _compute_sha256(local_file: Path) -> str:
        """Stream a file through SHA256 so large media does not need to be fully buffered."""
        digest = hashlib.sha256()
        with local_file.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _check_accessible_media(self, artifact: MediaArtifactRecord) -> list[AuditIssue]:
        """Verify existence, readability and SHA256 integrity of a declared-accessible artifact."""
        issues: list[AuditIssue] = []
        local_file = Path(artifact.local_path)

        if not local_file.exists():
            issues.append(
                AuditIssue(
                    tier="TIER_1_PROGRAMMATIC",
                    issue_code="MEDIA_FILE_MISSING",
                    severity="ERROR",
                    field="local_path",
                    message=(
                        f"Media artifact is declared ACCESSIBLE but the local file does not exist: "
                        f"{artifact.local_path}"
                    ),
                    actual_value=str(local_file),
                    expected_or_conflict="Existing local media file at the declared path",
                    remediation="Download the original media to the declared path, or correct the path declaration.",
                )
            )
            return issues

        if not local_file.is_file():
            issues.append(
                AuditIssue(
                    tier="TIER_1_PROGRAMMATIC",
                    issue_code="MEDIA_UNREADABLE",
                    severity="ERROR",
                    field="local_path",
                    message=(
                        f"Media artifact path is not a regular file and cannot be hashed: "
                        f"{artifact.local_path}"
                    ),
                    actual_value=str(local_file),
                    expected_or_conflict="Regular readable media file",
                    remediation="Point local_path at the actual media file instead of a directory or device path.",
                )
            )
            return issues

        try:
            computed_sha = self._compute_sha256(local_file)
        except OSError as exc:
            issues.append(
                AuditIssue(
                    tier="TIER_1_PROGRAMMATIC",
                    issue_code="MEDIA_UNREADABLE",
                    severity="ERROR",
                    field="local_path",
                    message=f"Local media could not be read for hashing: {artifact.local_path} ({exc})",
                    actual_value=f"{type(exc).__name__}: {exc}",
                    expected_or_conflict="Readable local media file",
                    remediation="Restore read permissions on the media file before making claims from it.",
                )
            )
            return issues

        if computed_sha.lower() != artifact.sha256.lower():
            issues.append(
                AuditIssue(
                    tier="TIER_1_PROGRAMMATIC",
                    issue_code="MEDIA_HASH_MISMATCH",
                    severity="ERROR",
                    field="sha256",
                    message=f"Local media SHA256 mismatch for {artifact.local_path}",
                    actual_value=computed_sha,
                    expected_or_conflict=artifact.sha256,
                    remediation="Re-verify local media file integrity.",
                )
            )
        return issues

    def _check_claim(
        self, claim: ClaimRecord, source: Optional[SourceMetadata], package: ResearchEvidencePackage
    ) -> list[AuditIssue]:
        issues: list[AuditIssue] = []

        # Check self-attestation attempt
        if claim.self_attested_verified is True:
            issues.append(
                AuditIssue(
                    tier="TIER_1_PROGRAMMATIC",
                    issue_code="SELF_ATTESTATION_IGNORED",
                    severity="WARNING",
                    claim_id=claim.claim_id,
                    field="self_attested_verified",
                    message="Claim researcher marked verified=true; self-attestation is ignored by the Quality Gate.",
                    actual_value=True,
                    expected_or_conflict=None,
                    remediation="Verification must be established through independent gate checks.",
                )
            )

        if not source:
            issues.append(
                AuditIssue(
                    tier="TIER_1_PROGRAMMATIC",
                    issue_code="SOURCE_METADATA_MISSING",
                    severity="ERROR",
                    claim_id=claim.claim_id,
                    field="source_url",
                    message=f"Claim cites source_url '{claim.source_url}' which is not in package sources.",
                    actual_value=claim.source_url,
                    expected_or_conflict="Declared source URL",
                    remediation="Include source metadata for cited URL.",
                )
            )
            return issues

        # Check if source media was accessible
        source_artifacts = [a for a in package.media_artifacts if a.local_path in claim.supporting_evidence or claim.source_url in a.local_path]
        if any(a.status in ("UNACCESSIBLE", "NOT_DOWNLOADED") for a in source_artifacts):
            issues.append(
                AuditIssue(
                    tier="TIER_1_PROGRAMMATIC",
                    issue_code="UNREAD_SOURCE_CITATION",
                    severity="ERROR",
                    claim_id=claim.claim_id,
                    field="supporting_evidence",
                    message="Claim relies on source whose media artifact is UNACCESSIBLE or NOT_DOWNLOADED.",
                    actual_value="UNACCESSIBLE",
                    expected_or_conflict="ACCESSIBLE",
                    remediation="Access and inspect original media before making factual claims.",
                )
            )

        # Check timestamps vs duration
        for span in claim.time_spans:
            if span.end_seconds > source.duration_seconds:
                issues.append(
                    AuditIssue(
                        tier="TIER_1_PROGRAMMATIC",
                        issue_code="TIMESTAMP_OUT_OF_BOUNDS",
                        severity="ERROR",
                        claim_id=claim.claim_id,
                        field="time_spans",
                        message=f"Claim timestamp end {span.end_seconds}s exceeds video duration {source.duration_seconds}s.",
                        actual_value=span.end_seconds,
                        expected_or_conflict=source.duration_seconds,
                        remediation=f"Correct timestamp to fall within 0.0s - {source.duration_seconds}s.",
                    )
                )

            # Check screenshot alignment
            if span.screenshot_timestamp_seconds is not None:
                tolerance = 5.0  # seconds
                if (
                    span.screenshot_timestamp_seconds < span.start_seconds - tolerance
                    or span.screenshot_timestamp_seconds > span.end_seconds + tolerance
                ):
                    issues.append(
                        AuditIssue(
                            tier="TIER_1_PROGRAMMATIC",
                            issue_code="SCREENSHOT_TIMESTAMP_MISMATCH",
                            severity="ERROR",
                            claim_id=claim.claim_id,
                            field="screenshot_timestamp_seconds",
                            message=(
                                f"Screenshot timestamp {span.screenshot_timestamp_seconds}s does not match "
                                f"claimed interval [{span.start_seconds}s, {span.end_seconds}s]."
                            ),
                            actual_value=span.screenshot_timestamp_seconds,
                            expected_or_conflict=f"[{span.start_seconds}s, {span.end_seconds}s]",
                            remediation="Align screenshot timestamp with cited claim interval.",
                        )
                    )

        # Check equipment consistency
        issues.extend(self._check_equipment_for_claim(claim, source))

        # Check timeline anachronism
        issues.extend(self._check_timeline_anachronism(claim, source))

        # Check unverified pseudo-exact numbers
        issues.extend(self._check_pseudo_exact_numbers(claim))

        return issues

    def _check_equipment_for_claim(self, claim: ClaimRecord, source: SourceMetadata) -> list[AuditIssue]:
        issues: list[AuditIssue] = []
        # If source has known equipment (e.g. Canon EOS R5), check if claim alleges contradictory gear
        canon_known = any("canon" in eq.lower() for eq in source.known_equipment)
        if canon_known:
            for eq_tag in claim.equipment_tags:
                if any(sony in eq_tag.lower() for sony in ["sony a7", "sony a7r", "sony"]):
                    issues.append(
                        AuditIssue(
                            tier="TIER_1_PROGRAMMATIC",
                            issue_code="EQUIPMENT_CONTRADICTION",
                            severity="ERROR",
                            claim_id=claim.claim_id,
                            field="equipment_tags",
                            message=(
                                f"Claim cites equipment '{eq_tag}' which directly contradicts author source gear "
                                f"{source.known_equipment}."
                            ),
                            actual_value=eq_tag,
                            expected_or_conflict=source.known_equipment,
                            remediation="Correct equipment citation to match author's authentic gear.",
                        )
                    )
        return issues

    def _check_timeline_anachronism(self, claim: ClaimRecord, source: SourceMetadata) -> list[AuditIssue]:
        issues: list[AuditIssue] = []
        if not source.published_date:
            return issues

        # Check each equipment mentioned in tags or statement
        combined_text = f"{' '.join(claim.equipment_tags)} {claim.statement}".lower()
        for gear_name, release_date in EQUIPMENT_RELEASE_DATES.items():
            if gear_name in combined_text:
                if source.published_date < release_date:
                    issues.append(
                        AuditIssue(
                            tier="TIER_1_PROGRAMMATIC",
                            issue_code="TIMELINE_ANACHRONISM",
                            severity="ERROR",
                            claim_id=claim.claim_id,
                            field="equipment_tags",
                            message=(
                                f"Timeline conflict: video published on {source.published_date} claims equipment "
                                f"'{gear_name}' released later on {release_date}."
                            ),
                            actual_value=f"{source.published_date} vs {release_date}",
                            expected_or_conflict=f"Equipment released before {source.published_date}",
                            remediation="Remove anachronistic equipment citation.",
                        )
                    )
        return issues

    def _check_pseudo_exact_numbers(self, claim: ClaimRecord) -> list[AuditIssue]:
        issues: list[AuditIssue] = []

        # Check explicit claimed_numbers
        for cn in claim.claimed_numbers:
            if not cn.has_empirical_basis:
                issues.append(
                    AuditIssue(
                        tier="TIER_1_PROGRAMMATIC",
                        issue_code="UNVERIFIED_PSEUDO_PRECISION",
                        severity="ERROR",
                        claim_id=claim.claim_id,
                        field="claimed_numbers",
                        message=f"Claim asserts exact numerical value '{cn.value}' without empirical basis.",
                        actual_value=cn.value,
                        expected_or_conflict="Empirical measurement or verified specification",
                        remediation="Remove pseudo-exact numbers or provide verified empirical measurement.",
                    )
                )

        # Regex check on statement for ratios like 90/10, 60/40
        ratio_matches = PSEUDO_RATIO_PATTERN.findall(claim.statement)
        for m in ratio_matches:
            # If not explicitly justified in supporting_evidence
            if not any(basis in claim.supporting_evidence.lower() for basis in ["测力", "力传感器", "实测", "力学实验"]):
                issues.append(
                    AuditIssue(
                        tier="TIER_1_PROGRAMMATIC",
                        issue_code="UNVERIFIED_PSEUDO_PRECISION",
                        severity="ERROR",
                        claim_id=claim.claim_id,
                        field="statement",
                        message=f"Statement asserts ungrounded ratio '{m}' without empirical force/sensor basis.",
                        actual_value=m,
                        expected_or_conflict="Empirical measurement basis",
                        remediation="Remove fabricated ratios like 90/10 or 60/40 unless backed by physical sensor data.",
                    )
                )

        # Regex check for rigid angles like 30°-60°
        angle_matches = PSEUDO_ANGLE_PATTERN.findall(claim.statement)
        for m in angle_matches:
            if claim.category in ("A", "B", "C") and "测角仪" not in claim.supporting_evidence:
                issues.append(
                    AuditIssue(
                        tier="TIER_1_PROGRAMMATIC",
                        issue_code="UNVERIFIED_PSEUDO_PRECISION",
                        severity="ERROR",
                        claim_id=claim.claim_id,
                        field="statement",
                        message=f"Statement asserts rigid angular range '{m}' as universal rule without empirical basis.",
                        actual_value=m,
                        expected_or_conflict="Contextual guidance or empirical measurement",
                        remediation="Do not state speculative angle ranges as mandatory physical laws.",
                    )
                )

        return issues

    def _check_cross_document_consistency(self, package: ResearchEvidencePackage) -> list[AuditIssue]:
        issues: list[AuditIssue] = []
        ctx = package.cross_document_context
        # Check if external documents claim contradictory equipment for any source
        for source in package.sources:
            if "BV1MD421L7VK" in source.url:
                # If external document has conflicting equipment
                external_equipment = ctx.get("external_documents", {}).get("BV1MD421L7VK", {}).get("equipment")
                if external_equipment and any(s in str(external_equipment).lower() for s in ["sony", "a7r"]):
                    issues.append(
                        AuditIssue(
                            tier="TIER_1_PROGRAMMATIC",
                            issue_code="CROSS_DOCUMENT_EQUIPMENT_CONTRADICTION",
                            severity="ERROR",
                            field="cross_document_context",
                            message=(
                                f"External document reports equipment '{external_equipment}' for BV1MD421L7VK, "
                                f"contradicting author's genuine gear {source.known_equipment}."
                            ),
                            actual_value=external_equipment,
                            expected_or_conflict=source.known_equipment,
                            remediation="Harmonize cross-document records with author's verified Canon R5 gear.",
                        )
                    )
        return issues
