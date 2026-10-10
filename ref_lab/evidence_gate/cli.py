"""Command line interface for Research Evidence Quality Gate Loop."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ref_lab.evidence_gate.loop import QualityGateLoop
from ref_lab.evidence_gate.models import ResearchEvidencePackage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audits research evidence packages against two-tier quality gate."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        required=True,
        help="Path to JSON file containing ResearchEvidencePackage",
    )
    parser.add_argument(
        "--cycle",
        "-c",
        type=int,
        default=1,
        help="Current rework iteration cycle (1-based, default 1)",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=2,
        help="Maximum allowed rework cycles before BLOCKED (default 2)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=None,
        help="Directory to save ADMISSION_RECEIPT.json or REWORK_PACKAGE.json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(json.dumps({"error": f"Input file not found: {args.input}"}))
        return 2

    try:
        content = json.loads(args.input.read_text(encoding="utf-8"))
        package = ResearchEvidencePackage.model_validate(content)
    except Exception as exc:
        print(json.dumps({"error": f"Invalid ResearchEvidencePackage schema: {exc}"}))
        return 2

    gate = QualityGateLoop(max_cycles=args.max_cycles)
    decision, receipt, rework_package = gate.evaluate(package, cycle=args.cycle)

    output_dir = args.output_dir or args.input.parent
    saved_files = gate.export_artifacts(decision, receipt, rework_package, output_dir)

    result_summary = {
        "decision": decision,
        "cycle": args.cycle,
        "max_cycles": args.max_cycles,
        "saved_artifacts": {k: str(v) for k, v in saved_files.items()},
    }

    if decision == "PASS" and receipt:
        result_summary["receipt_id"] = receipt.receipt_id
        result_summary["total_claims_verified"] = receipt.total_claims_verified
        result_summary["manifest_hash"] = receipt.approved_manifest_hash
        print(json.dumps(result_summary, indent=2, ensure_ascii=False))
        return 0

    if rework_package:
        result_summary["summary"] = rework_package.summary
        result_summary["affected_claims"] = rework_package.affected_claim_ids
        result_summary["issue_count"] = len(rework_package.issues)
        result_summary["remediation_guidance"] = rework_package.remediation_guidance
        print(json.dumps(result_summary, indent=2, ensure_ascii=False))
        return 1 if decision == "REVISE" else 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
