"""Gateway contracts protect the research index and private, self-reported learning."""
from copy import deepcopy
import json
from pathlib import Path

from tools.build_photography_atlas import build_payload


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / 'docs/research/photography-atlas'


def test_three_teaching_paths_preserve_original_research_and_use_known_skills():
    data = build_payload(RESEARCH)
    assert len(data['gateways']) == 3
    assert len(data['skills']) == 247
    assert len(data['sources']) == 205
    assert len(data['tutorials']) == 46
    skill_ids = {s['id'] for s in data['skills']}
    assert len({g['method'] for g in data['gateways']}) == 3
    for gateway in data['gateways']:
        assert len(gateway['skill_ids']) > 1
        assert set(gateway['skill_ids']) <= skill_ids
        sections = {s['id']: s for s in gateway['sections']}
        assert set(sections) == {'problem', 'observe', 'principle', 'contrast', 'boundary', 'transfer', 'reflect', 'sources'}
        assert any(b['type'] == 'exercise' for b in sections['problem']['blocks'])
        assert any(b['type'] == 'exercise' for b in sections['transfer']['blocks'])
        assert any(b['type'] == 'reveal' for b in sections['transfer']['blocks'])
        assert all(c['review']['level'] == 'pixel_reviewed' for c in gateway['cases'])
        assert all(c['rights']['statement'] and c['rights']['url'] for c in gateway['cases'])


def test_gateway_validator_rejects_invented_mapping_unlicensed_embeds_and_unsafe_links():
    from tools.validate_learning_gateways import validate_gateways
    catalog = json.loads((RESEARCH / 'GATEWAYS.json').read_text(encoding='utf-8'))
    tree = json.loads((RESEARCH / 'SKILL_TREE.json').read_text(encoding='utf-8'))
    assert validate_gateways(catalog, tree) == []
    bad = deepcopy(catalog)
    bad['gateways'][0]['skill_ids'].append('invented-skill')
    assert any('skill' in e for e in validate_gateways(bad, tree))
    bad = deepcopy(catalog)
    case = bad['gateways'][0]['cases'][0]
    case['display'] = 'licensed_remote'
    case['rights']['allowed'] = False
    assert any('rights' in e for e in validate_gateways(bad, tree))
    bad = deepcopy(catalog)
    bad['sources'][0]['url'] = 'javascript:alert(1)'
    assert any('URL' in e for e in validate_gateways(bad, tree))
    bad = deepcopy(catalog)
    image = next(c for c in bad['gateways'][0]['cases'] if c['display'] == 'licensed_remote')
    image['src'] = 'https://example.org/licensed-but-not-allowed.jpg'
    assert any('page policy' in e for e in validate_gateways(bad, tree))


def test_gateway_content_changes_bundle_digest_without_changing_research(tmp_path):
    for name in ('SOURCE_MAP', 'SKILL_TREE', 'CONFLICTS', 'GAP_AUDIT', 'PROJECT_CHECKLISTS', 'TUTORIALS', 'GATEWAYS'):
        (tmp_path / f'{name}.json').write_bytes((RESEARCH / f'{name}.json').read_bytes())
    before = build_payload(tmp_path)
    path = tmp_path / 'GATEWAYS.json'
    catalog = json.loads(path.read_text(encoding='utf-8'))
    catalog['gateways'][0]['question'] += ' Synthetic test change.'
    path.write_text(json.dumps(catalog), encoding='utf-8')
    after = build_payload(tmp_path)
    assert before['research_version'] != after['research_version']
    assert before['skills'] == after['skills']
    assert before['sources'] == after['sources']
    assert before['tutorials'] == after['tutorials']
