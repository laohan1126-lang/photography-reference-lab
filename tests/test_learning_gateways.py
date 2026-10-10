"""Gateway contracts protect the research index and private, self-reported learning."""
from copy import deepcopy
import json
from pathlib import Path

from tools.build_photography_atlas import build_payload


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / 'docs/research/photography-atlas'


def test_three_teaching_paths_preserve_original_research_and_use_known_skills():
    data = build_payload(RESEARCH)
    assert len([g for g in data['gateways'] if g.get('kind') != 'course']) == 3
    assert len([g for g in data['gateways'] if g.get('kind') == 'course']) == 1
    assert len(data['skills']) == 247
    assert len(data['sources']) == 205
    assert len(data['tutorials']) == 46
    skill_ids = {s['id'] for s in data['skills']}
    assert len({g['method'] for g in data['gateways']}) == 4
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
    assert validate_gateways(catalog, tree, json.loads((RESEARCH / 'LEARNING_CONTENT.json').read_text(encoding='utf-8'))) == []
    bad = deepcopy(catalog)
    bad['gateways'][0]['skill_ids'].append('invented-skill')
    assert any('skill' in e for e in validate_gateways(bad, tree, json.loads((RESEARCH / 'LEARNING_CONTENT.json').read_text(encoding='utf-8'))))
    bad = deepcopy(catalog)
    case = bad['gateways'][0]['cases'][0]
    case['display'] = 'licensed_remote'
    case['rights']['allowed'] = False
    assert any('rights' in e for e in validate_gateways(bad, tree, json.loads((RESEARCH / 'LEARNING_CONTENT.json').read_text(encoding='utf-8'))))
    bad = deepcopy(catalog)
    bad['sources'][0]['url'] = 'javascript:alert(1)'
    assert any('URL' in e for e in validate_gateways(bad, tree, json.loads((RESEARCH / 'LEARNING_CONTENT.json').read_text(encoding='utf-8'))))
    bad = deepcopy(catalog)
    image = next(c for c in bad['gateways'][0]['cases'] if c['display'] == 'licensed_remote')
    image['src'] = 'https://example.org/licensed-but-not-allowed.jpg'
    assert any('page policy' in e for e in validate_gateways(bad, tree, json.loads((RESEARCH / 'LEARNING_CONTENT.json').read_text(encoding='utf-8'))))


def test_source_case_images_are_exact_registered_originals_with_truthful_rights_and_provenance():
    from ref_lab.learning_media import SOURCE_CASE_MEDIA

    catalog = json.loads((RESEARCH / 'GATEWAYS.json').read_text(encoding='utf-8'))
    case_entries = {case['id']: (gateway, case) for gateway in catalog['gateways'] for case in gateway['cases']}
    source_cases = {case_id: entry for case_id, entry in case_entries.items()
                    if entry[1].get('display') == 'source_remote'}
    assert set(source_cases) == set(SOURCE_CASE_MEDIA)
    assert len(SOURCE_CASE_MEDIA) == 13
    assert sum(len(urls) for urls in SOURCE_CASE_MEDIA.values()) == 15

    for case_id, urls in SOURCE_CASE_MEDIA.items():
        gateway, case = source_cases[case_id]
        assert case['rights']['allowed'] is False
        assert len(case['images']) == len(urls)
        assert tuple(image['src'] for image in case['images']) == urls
        for image in case['images']:
            assert image['src'].startswith('https://')
            assert type(image['width']) is int and image['width'] > 0
            assert type(image['height']) is int and image['height'] > 0
            assert image['alt'].strip()
            if case_id == 'hobby-ambient-sequence':
                assert image['label'].strip()
        summary = case['source_summary']
        assert summary['text'].strip()
        assert summary['locator'].strip()
        assert summary['source_id'] in gateway['source_ids']
        source = next(source for source in catalog['sources'] if source['id'] == summary['source_id'])
        assert source['url'] == case['url']
        assert summary['checked_at'].strip()
    assert [image['label'] for image in source_cases['hobby-ambient-sequence'][1]['images']] == [
        '01 环境光基准 · Shade', '02 压低环境曝光 · Dark', '03 加入人物与背景闪光 · Final']

    # The three previously licensed Commons examples retain their independent permission records.
    licensed = [case for _, case in case_entries.values() if case.get('display') == 'licensed_remote']
    assert len(licensed) == 3
    assert all(case['rights']['allowed'] is True and case['rights'].get('license') for case in licensed)


def test_gateway_validator_rejects_unregistered_or_cross_case_source_media():
    from tools.validate_learning_gateways import validate_gateways
    catalog = json.loads((RESEARCH / 'GATEWAYS.json').read_text(encoding='utf-8'))
    tree = json.loads((RESEARCH / 'SKILL_TREE.json').read_text(encoding='utf-8'))
    cases = {case['id']: case for gateway in catalog['gateways'] for case in gateway['cases']}

    bad = deepcopy(catalog)
    case = next(c for g in bad['gateways'] for c in g['cases'] if c['id'] == 'marsh-before')
    case['images'][0]['src'] = 'https://images.example.invalid/not-the-registered-source.jpg'
    assert any('source media' in error.lower() or 'image' in error.lower()
               for error in validate_gateways(bad, tree, json.loads((RESEARCH / 'LEARNING_CONTENT.json').read_text(encoding='utf-8'))))

    bad = deepcopy(catalog)
    cases = {case['id']: case for gateway in bad['gateways'] for case in gateway['cases']}
    cases['marsh-before']['images'][0]['src'] = cases['marsh-after']['images'][0]['src']
    assert any('source media' in error.lower() or 'image' in error.lower()
               for error in validate_gateways(bad, tree, json.loads((RESEARCH / 'LEARNING_CONTENT.json').read_text(encoding='utf-8'))))

    bad = deepcopy(catalog)
    case = next(c for g in bad['gateways'] for c in g['cases'] if c['id'] == 'hobby-ambient-sequence')
    case['source_summary']['source_id'] = 'unrelated-source'
    assert any('summary' in error.lower() or 'source' in error.lower()
               for error in validate_gateways(bad, tree, json.loads((RESEARCH / 'LEARNING_CONTENT.json').read_text(encoding='utf-8'))))


def test_gateway_content_changes_bundle_digest_without_changing_research(tmp_path):
    for name in ('SOURCE_MAP', 'SKILL_TREE', 'CONFLICTS', 'GAP_AUDIT', 'PROJECT_CHECKLISTS', 'TUTORIALS', 'GATEWAYS', 'LEARNING_CONTENT'):
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
