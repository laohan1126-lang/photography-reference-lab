"""Course delivery boundaries; these checks do not certify teaching quality."""
import copy
import json
from pathlib import Path

from tools.validate_learning_gateways import validate_gateways

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / 'docs/research/photography-atlas'


def test_course_media_requires_registered_bytes_and_matching_source():
    catalog = json.loads((RESEARCH / 'GATEWAYS.json').read_text(encoding='utf-8'))
    tree = json.loads((RESEARCH / 'SKILL_TREE.json').read_text(encoding='utf-8'))
    content = json.loads((RESEARCH / 'LEARNING_CONTENT.json').read_text(encoding='utf-8'))
    sample = copy.deepcopy(catalog)
    case = sample['gateways'][1]['cases'][0]
    source = next(s for s in content['sources'] if s['id'] == 'pilot-s2')
    sample['sources'].append({**source, 'id':'course-test-source',
                             'reading_depth':'test fixture', 'checked_at':'2026-10-10',
                             'locator':'fixture', 'support':'fixture', 'limitation':'fixture'})
    sample['gateways'][1]['source_ids'].append('course-test-source')
    case.update(display='note_media', url=source['url'], images=[{'media_id':'s2-knee-level'}])
    case.pop('src', None)
    assert validate_gateways(sample, tree, content) == []
    case['images'][0]['media_id'] = 'unregistered-frame'
    assert any('registered' in e for e in validate_gateways(sample, tree, content))
    case['images'][0]['media_id'] = 's2-knee-level'
    case['url'] = 'https://example.com/wrong-author'
    assert any('source' in e for e in validate_gateways(sample, tree, content))
    sample['gateways'][1]['source_ids'].append('missing-source')
    assert any('Unknown source mapping' in e for e in validate_gateways(sample, tree, content))
