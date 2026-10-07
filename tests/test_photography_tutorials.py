"""Recommendation integrity is separate from proof of a photographic claim."""
from copy import deepcopy
import json
from pathlib import Path

from tools.build_photography_atlas import build_payload
from tools.validate_photography_tutorials import validate_tutorials


def sample():
    tree = {"skills": [{"id": "s", "module_id": "m"}], "modules": [{"id": "m", "domain_id": "d"}]}
    sources = {"sources": [{"id": "source", "url": "https://example.org/lesson"}]}
    resource = {key: "Synthetic guidance" for key in (
        "title", "original_title", "author", "language", "trust_reason", "summary",
        "start_here", "study_task", "limitations")}
    resource.update(id="lesson", url="https://example.org/lesson", kind="article", access="free",
                    verification={"checked_at": "2026-10-08", "level": "full_text", "locator": "Synthetic section"},
                    source_id="source", skill_ids=["s"], domain_ids=["d"])
    return {"schema_version": 1, "resources": [resource]}, tree, sources


def test_companion_material_does_not_need_to_be_formal_skill_evidence():
    catalog, tree, sources = sample()
    item = catalog["resources"][0]
    item.update(kind="video", source_id=None)
    item["verification"]["level"] = "page_and_description"
    before = deepcopy((tree, sources))
    assert not validate_tutorials(catalog, tree, sources)
    assert (tree, sources) == before
    item["verification"]["level"] = "full_text"
    assert any("video must distinguish" in error for error in validate_tutorials(catalog, tree, sources))


def test_wrong_skill_mapping_or_misattributed_source_is_rejected():
    catalog, tree, sources = sample()
    item = catalog["resources"][0]
    item.update(skill_ids=["invented"], url="https://example.org/different-article")
    errors = validate_tutorials(catalog, tree, sources)
    assert any("known skill" in error for error in errors)
    assert any("source identity" in error for error in errors)


def test_private_links_and_duplicate_recommendations_are_rejected():
    catalog, tree, sources = sample()
    item = catalog["resources"][0]
    item.update(url="https://name:password@example.org/lesson", source_id=None)
    assert any("unsafe" in error for error in validate_tutorials(catalog, tree, sources))
    item["url"] = "https://example.org/lesson"
    catalog["resources"].append({**item, "id": "second"})
    assert any("duplicate tutorial URL" in error for error in validate_tutorials(catalog, tree, sources))


def test_shipped_reading_paths_and_tutorial_changes_do_not_rewrite_evidence(tmp_path):
    directory = Path(__file__).resolve().parents[1] / 'docs/research/photography-atlas'
    for name in ('SOURCE_MAP', 'SKILL_TREE', 'CONFLICTS', 'GAP_AUDIT', 'PROJECT_CHECKLISTS', 'TUTORIALS'):
        (tmp_path / f'{name}.json').write_bytes((directory / f'{name}.json').read_bytes())
    before = build_payload(tmp_path)
    sources = {item['id']: item for item in before['sources']}
    mapped = {ident for item in before['tutorials'] for ident in item['skill_ids']}
    for skill in before['skills']:
        if skill['id'] not in mapped:
            assert any(sources[item['source_id']]['access'] == 'full_text'
                       and sources[item['source_id']].get('eligible_for_skills') is not False
                       and item['locator'] and item['support'] for item in skill['evidence'])
    catalog_path = tmp_path / 'TUTORIALS.json'
    catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
    catalog['resources'][0]['start_here'] += ' Synthetic change to the study guide.'
    catalog_path.write_text(json.dumps(catalog), encoding='utf-8')
    after = build_payload(tmp_path)
    assert after['research_version'] != before['research_version']
    assert after['tutorials'] != before['tutorials']
    assert after['skills'] == before['skills']
    assert after['sources'] == before['sources']
