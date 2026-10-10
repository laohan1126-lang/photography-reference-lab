"""Quality Gate Loop Orchestrator.

Orchestrates two tiers of independent inspection, computes gate decision
(PASS / REVISE / BLOCKED), manages rework iterations (max 2 cycles),
and exports machine-readable rework packages and admission receipts.
"""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
from typing import Optional

from ref_lab.evidence_gate.checker import ProgrammaticChecker
from ref_lab.evidence_gate.models import (
    AdmissionReceipt,
    AuditIssue,
    GateDecision,
    ResearchEvidencePackage,
    ReworkPackage,
)
from ref_lab.evidence_gate.semantic_audit import SemanticAuditor


class QualityGateLoop:
    """Core Quality Gate Loop controller enforcing evidence rigor before admission."""

    def __init__(
        self,
        media_root: Optional[Path] = None,
        max_cycles: int = 2,
    ):
        self.media_root = media_root
        self.max_cycles = max_cycles
        self.programmatic_checker = ProgrammaticChecker(media_root=media_root)
        self.semantic_auditor = SemanticAuditor()

    def evaluate(
        self,
        package: ResearchEvidencePackage,
        cycle: int = 1,
    ) -> tuple[GateDecision, Optional[AdmissionReceipt], Optional[ReworkPackage]]:
        """Run full 2-tier inspection and return decision with corresponding payload."""
        # Run Tier 1 Programmatic Fact Checking
        tier_1_issues = self.programmatic_checker.audit(package)

        # Run Tier 2 Independent Semantic Audit
        tier_2_issues = self.semantic_auditor.audit(package)

        all_issues = tier_1_issues + tier_2_issues
        error_issues = [i for i in all_issues if i.severity == "ERROR"]

        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Case 1: PASS
        if not error_issues:
            manifest_hash = package.compute_fingerprint()
            receipt = AdmissionReceipt(
                receipt_id=f"rcpt_{package.package_id}_{manifest_hash[:10]}",
                package_id=package.package_id,
                verified_at=now_str,
                decision="PASS",
                total_claims_verified=len(package.claims),
                approved_manifest_hash=manifest_hash,
                scope="photography_course_curriculum",
            )
            return "PASS", receipt, None

        # Case 2: Determine REVISE vs BLOCKED
        affected_claims = sorted(list({i.claim_id for i in error_issues if i.claim_id}))

        # Fatal non-reworkable conditions:
        fatal_unrecoverable = any(
            i.issue_code in ("MEDIA_UNACCESSIBLE", "UNREAD_SOURCE_CITATION") for i in error_issues
        )

        if fatal_unrecoverable:
            decision: GateDecision = "BLOCKED"
            summary = (
                f"Gate evaluation BLOCKED at cycle {cycle}: Unaccessible media or unread source. "
                f"Cannot make claims on inaccessible evidence."
            )
        elif cycle >= self.max_cycles:
            decision = "BLOCKED"
            summary = (
                f"Gate evaluation BLOCKED: Reached maximum rework cycle limit ({self.max_cycles}). "
                f"{len(error_issues)} error(s) remain uncorrected."
            )
        else:
            decision = "REVISE"
            summary = (
                f"Gate evaluation REVISE at cycle {cycle}/{self.max_cycles}: Found {len(error_issues)} "
                f"fact/semantic error(s) across {len(affected_claims)} claim(s)."
            )

        remediation_guidance = [f"[{i.issue_code}] ({i.claim_id or 'GENERAL'}): {i.remediation}" for i in error_issues]

        rework_package = ReworkPackage(
            package_id=package.package_id,
            cycle=cycle,
            max_cycles=self.max_cycles,
            decision=decision,
            issues=all_issues,
            affected_claim_ids=affected_claims,
            summary=summary,
            remediation_guidance=remediation_guidance,
        )

        return decision, None, rework_package

    def export_artifacts(
        self,
        decision: GateDecision,
        receipt: Optional[AdmissionReceipt],
        rework_package: Optional[ReworkPackage],
        output_dir: Path,
    ) -> dict[str, Path]:
        """Save machine-readable gate artifacts to destination directory."""
        output_dir.mkdir(parents=True, exist_ok=True)
        results: dict[str, Path] = {}

        if decision == "PASS" and receipt:
            path = output_dir / "ADMISSION_RECEIPT.json"
            path.write_text(receipt.model_dump_json(indent=2), encoding="utf-8")
            results["receipt"] = path
        elif rework_package:
            path = output_dir / "REWORK_PACKAGE.json"
            path.write_text(rework_package.model_dump_json(indent=2), encoding="utf-8")
            results["rework_package"] = path

        return results
