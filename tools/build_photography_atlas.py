"""Build the learning payload from independently preserved research, without inventing content."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.validate_photography_atlas import ROOT, validate_atlas
from tools.validate_photography_tutorials import validate_tutorials
from tools.validate_learning_gateways import validate_gateways


def normalized_conflicts(records: list, source_map: dict, skills: list) -> list:
    aliases = source_map.get("aliases", {})
    sources = {s["id"]: s for s in source_map["sources"]}
    skill_ids = {s['id'] for s in skills}
    result = []
    for index, item in enumerate(records):
        record = item.get("record", item)
        related = item.get('skill_ids', record.get('skill_ids'))
        if (not isinstance(related, list) or not related
                or any(not isinstance(sid, str) or sid not in skill_ids for sid in related)
                or len(related) != len(set(related))):
            raise ValueError('Invalid conflict skill mapping: ' + str(record.get('topic', index)))
        positions = []
        ids = list(record.get("source_ids", record.get("sources", [])))
        for position in record.get("positions", []):
            if isinstance(position, str):
                positions.append({"text": position})
            else:
                position_ids = list(position.get('source_ids', []))
                if position.get('source_id'):
                    position_ids.append(position['source_id'])
                position_ids = list(dict.fromkeys(aliases.get(sid, sid) for sid in position_ids))
                positions.append({"source_id": position_ids[0] if len(position_ids) == 1 else None,
                                  "source_ids": position_ids,
                                  "text": position.get("position", position.get("summary", ""))})
                ids.extend(position_ids)
        ids = list(dict.fromkeys(aliases.get(s, s) for s in ids if isinstance(s, str)))
        result.append({**item, "id": f"conflict-{index + 1}", "title": record.get("topic", "条件差异"),
                       "skill_ids": related,
                       "description": record.get("description", record.get("detail", "")),
                       "positions": positions, "resolution": record.get("resolution", record.get("handling", "")),
                       "source_ids": [s for s in ids if s in sources],
                       "eligible_source_ids": [s for s in ids if sources.get(s, {}).get("eligible_for_skills")],
                       "limitation": "保留方法与条件差异；目录、摘要和未观看材料的观点仅作为研究线索。"})
    return result


def build_payload(directory: Path) -> dict:
    inputs = {name: json.loads((directory / f"{name}.json").read_text(encoding="utf-8"))
              for name in ("SOURCE_MAP", "SKILL_TREE", "CONFLICTS", "GAP_AUDIT")}
    checklists = directory / "PROJECT_CHECKLISTS.json"
    if checklists.is_file():
        inputs["PROJECT_CHECKLISTS"] = json.loads(checklists.read_text(encoding="utf-8"))
    tutorials = directory / "TUTORIALS.json"
    if tutorials.is_file():
        inputs["TUTORIALS"] = json.loads(tutorials.read_text(encoding="utf-8"))
    gateways = directory / "GATEWAYS.json"
    if gateways.is_file():
        inputs["GATEWAYS"] = json.loads(gateways.read_text(encoding="utf-8"))
    source_map, tree = inputs["SOURCE_MAP"], inputs["SKILL_TREE"]
    result = validate_atlas(source_map, tree)
    if result["errors"]:
        raise ValueError("Atlas integrity failed: " + "; ".join(result["errors"][:20]))
    tutorial_catalog = inputs.get("TUTORIALS", {"schema_version": 1, "resources": []})
    tutorial_errors = validate_tutorials(tutorial_catalog, tree, source_map)
    if tutorial_errors:
        raise ValueError("Tutorial integrity failed: " + "; ".join(tutorial_errors[:20]))
    gateway_catalog = inputs.get("GATEWAYS", {"schema_version": 1, "gateways": [], "sources": []})
    gateway_errors = validate_gateways(gateway_catalog, tree)
    if gateway_errors:
        raise ValueError("Gateway integrity failed: " + "; ".join(gateway_errors[:20]))
    digest = hashlib.sha256(json.dumps(inputs, ensure_ascii=False, sort_keys=True,
                                      separators=(",", ":")).encode("utf-8")).hexdigest()
    return {"schema_version": 1, "research_version": digest,
            "meta": tree.get("meta", {}),
            "domains": tree["domains"], "modules": tree["modules"], "skills": tree["skills"],
            "sources": source_map["sources"], "conflicts": normalized_conflicts(inputs["CONFLICTS"].get("conflicts", []), source_map, tree['skills']),
            "gaps": inputs["GAP_AUDIT"].get("remaining_gaps", []),
            "problem_index": inputs["GAP_AUDIT"].get("problem_index", []),
            "project_checklists": inputs.get("PROJECT_CHECKLISTS", {}).get("checklists", []),
            "tutorials": tutorial_catalog["resources"],
            "gateways": gateway_catalog["gateways"], "gateway_sources": gateway_catalog["sources"],
            "research_scope": "Source-backed skills; practice thresholds are project-designed unless attributed otherwise."}


def serialized(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / "docs/research/photography-atlas")
    parser.add_argument("--output", type=Path, default=ROOT / "web/learning-atlas.json")
    parser.add_argument("--write", action="store_true", help="Write the validated bundle; default is read-only.")
    parser.add_argument("--check", action="store_true", help="Fail if the shipped bundle differs from canonical research.")
    args = parser.parse_args()
    payload = build_payload(args.directory)
    content = serialized(payload)
    if args.check and (not args.output.is_file() or args.output.read_text(encoding="utf-8") != content):
        print("FAIL: shipped learning bundle differs from canonical research")
        return 1
    if args.write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
    print(json.dumps({"status": "PASS" if args.check else "WRITTEN" if args.write else "DRY_RUN",
                      "domains": len(payload["domains"]), "modules": len(payload["modules"]),
                      "skills": len(payload["skills"]), "sources": len(payload["sources"]),
                      "research_version": payload["research_version"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
