"""Validate atlas provenance/structure; not a substitute for source or taste review."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
RELEVANCE = {"core", "important", "advanced", "optional"}
BASES = {"professional_consensus", "photographer_method", "project_adaptation"}
STATUSES = {"unassessed", "unstarted", "learning", "practicing", "field_verified", "mastered"}
SKILL_FIELDS = {"id", "module_id", "skill_name", "capability", "why_it_matters",
                "prerequisites", "failure_modes", "practice", "acceptance", "evidence",
                "visual_examples", "relevance", "status", "confidence", "basis", "practice_basis"}


def public_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        url = urlsplit(value)
        return (url.scheme in {"http", "https"} and bool(url.hostname)
                and not url.username and not url.password
                and url.hostname not in {"localhost", "127.0.0.1", "::1"}
                and not any(key in url.query.lower() for key in
                            ("awsaccesskeyid=", "signature=", "access_token=", "api_key=")))
    except ValueError:
        return False


def validate_atlas(source_map: dict, tree: dict) -> dict:
    errors, warnings = [], []

    def index(records, kind):
        found = {}
        for item in records:
            ident = item.get("id") if isinstance(item, dict) else None
            if not isinstance(ident, str) or not ident:
                errors.append(f"{kind}: missing string id")
            elif ident in found:
                errors.append(f"{kind}: duplicate id {ident}")
            else:
                found[ident] = item
        return found

    sources = index(source_map.get("sources", []), "source")
    domains = index(tree.get("domains", []), "domain")
    modules = index(tree.get("modules", []), "module")
    skills = index(tree.get("skills", []), "skill")
    if not domains or not modules or not skills:
        errors.append("tree: domains, modules and skills must all be present")
    for ident, source in sources.items():
        if not public_url(source.get("url")):
            errors.append(f"{ident}: unsafe or missing public source URL")
        if not source.get("independence_key"):
            errors.append(f"{ident}: missing original-author independence key")
        if not source.get("read_depth"):
            errors.append(f"{ident}: missing actual reading depth")

    placements = Counter()
    module_placements = Counter()
    for ident, domain in domains.items():
        if not domain.get("name") or not domain.get("module_ids"):
            errors.append(f"{ident}: domain needs a name and nonempty modules")
        for mid in domain.get("module_ids", []):
            module_placements[mid] += 1
            if mid not in modules or modules[mid].get("domain_id") != ident:
                errors.append(f"{ident}: invalid module relationship {mid}")
    for ident, module in modules.items():
        if module.get("domain_id") not in domains or module_placements[ident] != 1:
            errors.append(f"{ident}: module must belong to exactly one domain")
        if not module.get("name") or not module.get("skill_ids"):
            errors.append(f"{ident}: module needs a name and nonempty skills")
        for sid in module.get("skill_ids", []):
            placements[sid] += 1
            if sid not in skills or skills[sid].get("module_id") != ident:
                errors.append(f"{ident}: invalid skill relationship {sid}")

    for ident, skill in skills.items():
        missing = SKILL_FIELDS.difference(skill)
        if missing:
            errors.append(f"{ident}: missing fields {sorted(missing)}")
        if placements[ident] != 1 or skill.get("module_id") not in modules:
            errors.append(f"{ident}: skill must belong to exactly one module")
        for key in ("skill_name", "capability", "why_it_matters", "practice"):
            if not isinstance(skill.get(key), str) or not skill[key].strip():
                errors.append(f"{ident}: missing observable {key}")
        for key in ("failure_modes", "acceptance"):
            if not isinstance(skill.get(key), list) or not skill[key] or not all(
                    isinstance(x, str) and x.strip() for x in skill[key]):
                errors.append(f"{ident}: {key} must contain observable text checks")
        for key in ("prerequisites", "visual_examples", "evidence"):
            if not isinstance(skill.get(key), list):
                errors.append(f"{ident}: {key} must be a list")
        if skill.get("status") != "unassessed":
            errors.append(f"{ident}: canonical personal status must start unassessed")
        if skill.get("relevance") not in RELEVANCE or skill.get("basis") not in BASES:
            errors.append(f"{ident}: invalid relevance or claim basis")
        if skill.get("practice_basis") not in {"project_designed", "source_exercise"}:
            errors.append(f"{ident}: missing exercise attribution")
        if skill.get("confidence") not in {"high", "medium", "low"}:
            errors.append(f"{ident}: invalid confidence")
        direct_authors = set()
        for evidence in skill.get("evidence", []):
            sid = evidence.get("source_id")
            source = sources.get(sid)
            if source is None:
                errors.append(f"{ident}: unknown evidence source {sid}")
                continue
            if not evidence.get("locator") or not evidence.get("support"):
                errors.append(f"{ident}: evidence needs locator and actual support {sid}")
            if source.get("access") in {"index_only", "blocked"} or not source.get("eligible_for_skills", True):
                errors.append(f"{ident}: discovery-only source used as skill evidence {sid}")
            if evidence.get("scope") not in {"direct", "adapted"}:
                errors.append(f"{ident}: evidence scope must be explicit {sid}")
            if (source.get("access") == "full_text" and source.get("tier") in {"A", "B"}
                    and evidence.get("scope") == "direct" and source.get("eligible_for_skills", True)):
                direct_authors.add(source["independence_key"])
        if not direct_authors:
            errors.append(f"{ident}: no directly read professional evidence")
        if skill.get("confidence") == "high" and len(direct_authors) < 2:
            errors.append(f"{ident}: high confidence requires independent direct professional sources")
        if skill.get("basis") == "professional_consensus" and len(direct_authors) < 2:
            errors.append(f"{ident}: claimed source consensus needs independent supporting authors")
        if skill.get("confidence") == "low":
            warnings.append(f"{ident}: low confidence requires further research")
        for dep in skill.get("prerequisites", []):
            if dep not in skills or dep == ident:
                errors.append(f"{ident}: invalid prerequisite {dep}")
        for example in skill.get("visual_examples", []):
            if example.get("source_id") not in sources or not public_url(example.get("url")):
                errors.append(f"{ident}: invalid linked professional example")

    visited, visiting = set(), set()

    def visit(ident):
        if ident in visiting:
            errors.append(f"{ident}: cyclic prerequisite relationship")
            return
        if ident in visited or ident not in skills:
            return
        visiting.add(ident)
        for dep in skills[ident].get("prerequisites", []):
            visit(dep)
        visiting.remove(ident)
        visited.add(ident)

    for ident in skills:
        visit(ident)
    return {"errors": errors, "warnings": warnings,
            "counts": {"sources": len(sources), "domains": len(domains), "modules": len(modules),
                       "skills": len(skills), "confidence": dict(Counter(s.get("confidence") for s in skills.values()))},
            "scope": "Structural/provenance integrity only; does not verify teaching claims or personal mastery."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / "docs/research/photography-atlas")
    args = parser.parse_args()
    sources = json.loads((args.directory / "SOURCE_MAP.json").read_text(encoding="utf-8"))
    tree = json.loads((args.directory / "SKILL_TREE.json").read_text(encoding="utf-8"))
    report = validate_atlas(sources, tree)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
