"""Synthetic integrity cases, not photography correctness or visual accuracy evidence."""
from copy import deepcopy
from pathlib import Path
import json

import pytest

from tools.validate_photography_atlas import public_url, validate_atlas
from tools.build_photography_atlas import build_payload, normalized_conflicts, serialized


@pytest.fixture
def atlas():
    sources = {"sources": [{"id": ident, "url": f"https://example.org/{ident}", "independence_key": author,
                            "read_depth": "Synthetic read-depth fixture", "access": "full_text", "tier": "A"}
                           for ident, author in [("s1", "teacher-one"), ("s2", "teacher-two")]]}
    skill = {"id": "one", "module_id": "m", "skill_name": "Synthetic control", "capability": "Compare one variable",
             "why_it_matters": "Detect a synthetic failure", "prerequisites": [], "failure_modes": ["Observable error"],
             "practice": "Repeat a controlled comparison", "acceptance": ["Explain the difference"],
             "evidence": [{"source_id": s, "locator": "Synthetic section", "support": "Synthetic claim", "scope": "direct"}
                          for s in ["s1", "s2"]], "visual_examples": [], "relevance": "core", "status": "unassessed",
             "confidence": "high", "basis": "professional_consensus", "practice_basis": "project_designed"}
    tree = {"domains": [{"id": "d", "name": "Synthetic domain", "module_ids": ["m"]}],
            "modules": [{"id": "m", "domain_id": "d", "name": "Synthetic module", "skill_ids": ["one"]}],
            "skills": [skill]}
    return sources, tree


def test_complete_hierarchy_and_independent_evidence(atlas):
    report = validate_atlas(*atlas)
    assert report["errors"] == []
    assert report["counts"]["skills"] == 1


def test_two_pages_by_one_teacher_do_not_triangulate(atlas):
    sources, tree = atlas
    sources["sources"][1]["independence_key"] = "teacher-one"
    assert any("high confidence" in error for error in validate_atlas(sources, tree)["errors"])


@pytest.mark.parametrize("access", ["blocked", "index_only"])
def test_discovery_lead_cannot_support_a_formal_skill(atlas, access):
    sources, tree = atlas
    sources["sources"][0]["access"] = access
    assert any("discovery-only" in error for error in validate_atlas(sources, tree)["errors"])


def test_unknown_citation_and_duplicate_placement_fail(atlas):
    sources, tree = atlas
    tree["skills"][0]["evidence"][0]["source_id"] = "not-read"
    tree["modules"][0]["skill_ids"].append("one")
    errors = validate_atlas(sources, tree)["errors"]
    assert any("unknown evidence" in x for x in errors)
    assert any("exactly one module" in x for x in errors)


def test_assessment_is_not_prepopulated_from_source_research(atlas):
    sources, tree = atlas
    tree["skills"][0]["status"] = "mastered"
    assert any("start unassessed" in x for x in validate_atlas(sources, tree)["errors"])


def test_missing_training_acceptance_is_not_atomic(atlas):
    sources, tree = atlas
    tree["skills"][0]["acceptance"] = []
    assert any("observable text checks" in x for x in validate_atlas(sources, tree)["errors"])


def test_prerequisite_cycle_detected(atlas):
    sources, tree = atlas
    two = deepcopy(tree["skills"][0])
    two.update(id="two", prerequisites=["one"])
    tree["skills"][0]["prerequisites"] = ["two"]
    tree["skills"].append(two)
    tree["modules"][0]["skill_ids"].append("two")
    assert any("cyclic prerequisite" in x for x in validate_atlas(sources, tree)["errors"])


@pytest.mark.parametrize("url", ["javascript:alert(1)", "https://user:secret@example.org", "http://localhost/a",
                                 "https://example.org?AWSAccessKeyId=private"])
def test_source_links_do_not_export_credentials_or_local_urls(url):
    assert not public_url(url)


def test_research_bundle_is_reproducible_and_never_mutates_inputs(atlas, tmp_path):
    sources, tree = atlas
    inputs = {"SOURCE_MAP": sources, "SKILL_TREE": tree, "CONFLICTS": {"conflicts": []},
              "GAP_AUDIT": {"remaining_gaps": ["Synthetic unresolved gap"]}}
    for name, data in inputs.items():
        (tmp_path / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    one, two = build_payload(tmp_path), build_payload(tmp_path)
    assert serialized(one) == serialized(two)
    assert one["gaps"] == ["Synthetic unresolved gap"]
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before
    inputs["SKILL_TREE"]["skills"][0]["practice"] = "Changed project experiment"
    (tmp_path / "SKILL_TREE.json").write_text(json.dumps(inputs["SKILL_TREE"]), encoding="utf-8")
    assert build_payload(tmp_path)["research_version"] != one["research_version"]


def test_shipped_research_retains_two_audits_reverse_paths_and_visible_unknowns():
    directory = Path(__file__).resolve().parents[1] / "docs/research/photography-atlas"
    payload = build_payload(directory)
    ids = {s["id"] for s in payload["skills"]}
    gaps = {g["id"] for g in payload["gaps"]}
    audit = json.loads((directory / "GAP_AUDIT.json").read_text(encoding="utf-8"))
    assert len(audit["rounds"]) >= 2
    assert len(payload["problem_index"]) == 10
    for problem in payload["problem_index"]:
        assert problem["skill_ids"] and set(problem["skill_ids"]) <= ids
        assert set(problem["gap_ids"]) <= gaps
    dagger = next(p for p in payload["problem_index"] if "匕首" in p["problem"])
    assert "cosplay-short-dagger-orientation" in dagger["gap_ids"]
    assert all(s["status"] == "unassessed" for s in payload["skills"])
    shipped = directory.parents[2] / "web/learning-atlas.json"
    assert shipped.read_text(encoding="utf-8") == serialized(payload)


def test_conflict_positions_keep_multiple_sources_and_explicit_skill_scope(atlas):
    sources, tree = atlas
    records = [{'skill_ids': ['one'], 'record': {
        'topic': 'Synthetic conditional difference',
        'positions': [{'summary': 'Two independently attributed methods', 'source_ids': ['s1', 's2']}],
    }}]
    result = normalized_conflicts(records, sources, tree['skills'])
    assert result[0]['skill_ids'] == ['one']
    assert result[0]['source_ids'] == ['s1', 's2']
    assert result[0]['positions'][0]['source_ids'] == ['s1', 's2']
    records[0]['skill_ids'] = ['unknown']
    with pytest.raises(ValueError, match='conflict skill'):
        normalized_conflicts(records, sources, tree['skills'])
