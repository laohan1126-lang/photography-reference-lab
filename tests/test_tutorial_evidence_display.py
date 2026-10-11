"""A/B/C/D teaching evidence: display contract and validator wiring, not pedagogy.

The browser fixtures below are synthetic strings. They prove that evidence renders as
four labelled layers, that an incomplete record stays marked unverified, and that text
never reaches the DOM as markup. They say nothing about real photography material.
"""
import copy
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from tools.validate_learning_gateways import validate_case_evidence, validate_gateways

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / 'docs/research/photography-atlas'
READER = ROOT / 'web/learning-gateways.js'

SOURCE = {'id': 'src-1', 'title': '示例来源', 'url': 'https://example.org/photography'}
OTHER_SOURCE = {'id': 'src-2', 'title': '另一个来源', 'url': 'https://other.example.org/page'}
CASE_URL = 'https://example.org/photography'
GATEWAY = {'id': 'demo', 'source_ids': ['src-1']}

DRIVER = """
const fs = require('fs');
global.window = {};
(0, eval)(fs.readFileSync(process.argv[2], 'utf8'));
const api = global.window.LearningGateways;
const fixtures = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
process.stdout.write(JSON.stringify(fixtures.map(f =>
  api.caseEvidenceHTML(f.item, f.gateway, new Map((f.sources || []).map(s => [s.id, s]))))));
"""


def render(tmp_path, evidence, case=None, sources=None, gateway=None):
    """Render one case through the reader's own helper in Node."""
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is required for the offline reader rendering check')
    driver, fixture = tmp_path / 'driver.js', tmp_path / 'fixture.json'
    driver.write_text(DRIVER, encoding='utf-8')
    item = {'id': 'case-1', 'url': CASE_URL, **(case or {})}
    if evidence is not None:
        item['evidence'] = evidence
    fixture.write_text(json.dumps([{'item': item,
                                   'gateway': gateway or GATEWAY,
                                   'sources': sources if sources is not None else [SOURCE]}]),
                       encoding='utf-8')
    # The reader speaks Chinese; Node's stdout must not be decoded with the Windows code page.
    done = subprocess.run([node, str(driver), str(READER), str(fixture)],
                          capture_output=True, text=True, encoding='utf-8')
    assert done.returncode == 0, f'reader render failed: {done.stderr}'
    return json.loads(done.stdout)[0]


def complete_evidence():
    return {
        'observation': {'text': '剑士右腿在前，膝盖压低，身体几乎正对镜头。'},
        'quote': {'text': '先决定你要读者看哪里，再决定镜头放多低。',
                  'language': 'zh', 'source_id': 'src-1', 'locator': '第 3 章 第 2 节',
                  'checked_at': '2026-10-10', 'verification': 'verbatim_checked'},
        'explanation': {'text': '透视消失点越低，地面占画面越多。', 'source_ids': ['src-1']},
        'advice': {'text': '下次用同一机位先拍一张站立版本，再对比。'},
    }


def test_complete_evidence_shows_four_named_layers(tmp_path):
    html = render(tmp_path, complete_evidence())
    for layer, label in (('observation', '画面观察'), ('quote', '作者原话'),
                         ('explanation', '专业解释'), ('advice', '项目建议')):
        assert f'data-evidence-layer="{layer}"' in html
        assert label in html
    assert 'data-evidence-state="verified"' in html
    assert '核验日期：2026-10-10' in html and '第 3 章 第 2 节' in html
    assert 'data-verified="true"' in html
    assert '不代表作者原话' in html


def test_case_without_evidence_keeps_the_previous_display(tmp_path):
    # Cases shipped before the evidence layers carry no field, null, or an empty block:
    # all three keep the old rendering, which is nothing at all.
    assert render(tmp_path, None) == ''
    assert render(tmp_path, {}) == ''
    assert render(tmp_path, {'observation': {'text': '只有观察层'}}).count(
        'data-evidence-layer="') == 4


@pytest.mark.parametrize('layer', ['observation', 'explanation', 'advice'])
def test_layers_quote_fields_stay_with_the_author(tmp_path, layer):
    evidence = complete_evidence()
    evidence[layer]['source_id'] = 'src-1'
    html = render(tmp_path, evidence)
    segment = html.split(f'data-evidence-layer="{layer}"')[1].split('data-evidence-layer="')[0]
    assert 'data-verified=' not in segment
    assert 'data-evidence-state="verified"' not in segment


@pytest.mark.parametrize('break_quote', [
    {'verification': []},
    {'verification': {'state': 'verbatim_checked'}},
    {'verification': 'checked'},
    {'verification': None},
    {'locator': ''},
    {'language': '   '},
    {'checked_at': '2026-13'},
    {'checked_at': '2026-13-40'},
    {'checked_at': '2026-02-29'},
    {'checked_at': ''},
    {'source_id': 'src-2'},
    {'source_id': 'not-in-this-gateway'},
    {'text': ''},
    {'text': '   '},
])
def test_incomplete_quote_never_claims_a_checked_original(tmp_path, break_quote):
    evidence = complete_evidence()
    evidence['quote'].update(break_quote)
    html = render(tmp_path, evidence)
    assert 'data-evidence-layer="quote"' in html
    assert 'data-verified="false"' in html and '未核验' in html
    assert 'data-verified="true"' not in html and '已核对原文' not in html


@pytest.mark.parametrize('checked_at', ['2026-10-10', '2028-02-29', '2024-02-29'])
def test_a_real_calendar_day_still_counts_as_a_checking_date(tmp_path, checked_at):
    evidence = complete_evidence()
    evidence['quote']['checked_at'] = checked_at
    html = render(tmp_path, evidence)
    assert 'data-verified="true"' in html
    assert f'核验日期：{checked_at}' in html


def test_an_empty_quote_never_shows_a_checked_original_next_to_the_missing_words(tmp_path):
    # The four layers stay on screen, but "未提供作者原话" and "已核对原文" cannot both appear.
    evidence = complete_evidence()
    evidence['quote']['text'] = ''
    html = render(tmp_path, evidence)
    assert '未提供作者原话' in html
    assert '已核对原文' not in html and 'data-verified="true"' not in html
    assert 'data-evidence-state="unverified"' in html


def test_two_unsafe_urls_that_both_fail_are_not_a_matching_page(tmp_path):
    unsafe = {'id': 'src-1', 'title': '脚本来源', 'url': 'javascript:alert(1)'}
    html = render(tmp_path, complete_evidence(), case={'url': 'javascript:alert(1)'}, sources=[unsafe])
    assert 'data-verified="false"' in html
    assert 'data-evidence-state="verified"' not in html
    assert 'href="javascript' not in html and 'href=""' not in html


def test_another_gateways_source_cannot_become_this_authors_verification(tmp_path):
    evidence = complete_evidence()
    evidence['quote']['source_id'] = 'src-2'
    html = render(tmp_path, evidence, sources=[SOURCE, OTHER_SOURCE])
    assert 'data-verified="false"' in html
    assert 'other.example.org' not in html


@pytest.mark.parametrize('evidence', [
    {'quote': '逐字原文'},
    {'advice': []},
    {'observation': None, 'quote': 3, 'explanation': '解释', 'advice': True},
    {'unknown_layer': {'text': 'x'}},
    {'explanation': {'text': '解释', 'source_ids': ['src-2']}},
])
def test_malformed_evidence_stays_conservative_and_does_not_crash(tmp_path, evidence):
    html = render(tmp_path, evidence, sources=[SOURCE])
    assert 'data-evidence-state="unverified"' in html or 'data-evidence-state="unreadable"' in html
    assert 'data-verified="true"' not in html
    assert 'data-evidence-layer="quote"' in html
    if evidence.get('explanation'):
        assert '缺少可核对的来源' in html


def test_explanation_never_inherits_another_gateways_source(tmp_path):
    evidence = complete_evidence()
    evidence['explanation']['source_ids'] = ['src-2']
    html = render(tmp_path, evidence, sources=[SOURCE, OTHER_SOURCE])
    assert 'other.example.org' not in html
    assert '缺少可核对的来源' in html


def test_evidence_text_is_never_markup_or_a_script_url(tmp_path):
    evidence = complete_evidence()
    payload = '<img src=x onerror="alert(1)"> javascript:alert(2) </blockquote><script>alert(3)</script>'
    for layer, value in evidence.items():
        evidence[layer] = {**value, 'text': payload}
    evidence['quote'].update(verification='verbatim_checked', source_id='javascript:alert(1)')
    html = render(tmp_path, evidence)
    # Escaped text may still spell the words; what must not exist is live markup or an attribute URL.
    assert '<img' not in html and '<script' not in html
    # The reader owns one genuine quote element. The hostile closing tag must stay
    # escaped rather than creating an extra close; banning our own close is not XSS.
    assert html.count('<blockquote ') == html.count('</blockquote>') == 1
    assert '&lt;/blockquote&gt;' in html
    assert 'href="javascript' not in html and 'src="javascript' not in html
    assert 'data-verified="false"' in html
    assert '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;' in html
    assert '&lt;script&gt;' in html


def test_reading_helper_is_exported_for_the_offline_regression():
    assert re.search(r'return \{[^}]*\bcaseEvidenceHTML\b', READER.read_text(encoding='utf-8'))


def _catalog_with_source_case():
    catalog = json.loads((RESEARCH / 'GATEWAYS.json').read_text(encoding='utf-8'))
    tree = json.loads((RESEARCH / 'SKILL_TREE.json').read_text(encoding='utf-8'))
    content = json.loads((RESEARCH / 'LEARNING_CONTENT.json').read_text(encoding='utf-8'))
    sample = copy.deepcopy(catalog)
    for gateway in sample['gateways']:
        for case in gateway['cases']:
            if case.get('display') == 'source_remote' and case.get('source_summary'):
                return sample, tree, content, gateway, case
    pytest.skip('no source_remote case in the shipped catalog')


def _shipped_evidence(case):
    summary = case['source_summary']
    return {
        'observation': {'text': '合成观察：主体在画面里的位置与姿态。'},
        'quote': {'text': '合成引文：只用于契约测试。', 'language': 'zh',
                  'source_id': summary['source_id'], 'locator': summary['locator'],
                  'checked_at': summary['checked_at'], 'verification': 'verbatim_checked'},
        'explanation': {'text': '合成解释：用于校验证据契约。', 'source_ids': [summary['source_id']]},
        'advice': {'text': '合成建议：用于校验建议层的显示。'},
    }


def test_a_complete_evidence_record_passes_the_gateway_validator():
    sample, tree, content, _, case = _catalog_with_source_case()
    case['evidence'] = _shipped_evidence(case)
    assert validate_gateways(sample, tree, content) == []


@pytest.mark.parametrize('layer,change,expected', [
    ('quote', {'verification': []}, 'quote verification'),
    ('quote', {'verification': 'checked'}, 'quote verification'),
    ('quote', {'verification': 'verbatim_checked', 'locator': ''}, 'locator'),
    ('quote', {'verification': 'verbatim_checked', 'language': ''}, 'locator'),
    ('quote', {'verification': 'verbatim_checked', 'checked_at': 'yesterday'}, 'checking date'),
    ('quote', {'verification': 'verbatim_checked', 'checked_at': '2026-13-40'}, 'checking date'),
    ('quote', {'verification': 'verbatim_checked', 'source_id': 'not-a-source'}, 'known source'),
    ('quote', {'verification': 'verbatim_checked', 'source_id': None}, 'known source'),
    ('explanation', {'source_ids': ['not-a-source']}, 'explanation source'),
    ('explanation', {'source_ids': 'src-1'}, 'explanation sources'),
    ('explanation', {'source_id': 'src-1'}, 'cannot claim the author wording'),
    ('advice', {'checked_at': '10-10-2026'}, 'Invalid case evidence advice date'),
    ('observation', {'text': '   '}, 'Missing case evidence observation text'),
    ('observation', {'locator': '第 1 页'}, 'Unknown case evidence observation fields'),
    ('nope', {'text': 'x'}, 'Unknown case evidence layer'),
])
def test_incomplete_evidence_is_reported_not_accepted(layer, change, expected):
    sample, tree, content, _, case = _catalog_with_source_case()
    evidence = _shipped_evidence(case)
    # An unknown layer has no template to update; it still has to reach the validator.
    evidence[layer] = {**(evidence.get(layer) or {}), **change}
    case['evidence'] = evidence
    errors = validate_gateways(sample, tree, content)
    assert any(expected in error for error in errors), errors


def test_another_case_source_cannot_be_promoted_to_a_verified_quote():
    sample, tree, content, gateway, case = _catalog_with_source_case()
    registry = {source['id']: source for source in sample['sources']}
    evidence = _shipped_evidence(case)
    own = evidence['quote']['source_id']
    borrowed = next((source_id for source_id in gateway['source_ids']
                     if source_id != own and registry[source_id]['url'] != case['url']), None)
    if not borrowed:
        pytest.skip('this gateway has no second source with a different page to borrow')
    evidence['quote']['source_id'] = borrowed
    case['evidence'] = evidence
    errors = validate_gateways(sample, tree, content)
    assert any('not this case page' in error and case['id'] in error and borrowed in error
               for error in errors), errors


@pytest.mark.parametrize('verification', [[], {}, None, 'checked', 1])
def test_unhashable_verification_is_reported_without_raising(verification):
    sources = {'src-1': SOURCE}
    errors = validate_case_evidence(
        {'quote': {'text': '原文', 'verification': verification}},
        'case-1', {'src-1'}, sources, CASE_URL)
    assert errors and 'quote verification' in errors[0]


def test_a_complete_quote_record_is_accepted_by_the_helper():
    errors = validate_case_evidence(
        {'quote': {'text': '原文', 'language': 'zh', 'source_id': 'src-1',
                   'locator': '第 3 章', 'checked_at': '2026-10-10',
                   'verification': 'verbatim_checked'}},
        'case-1', {'src-1'}, {'src-1': SOURCE}, CASE_URL)
    assert errors == []


def test_matching_is_required_against_this_case_page():
    errors = validate_case_evidence(
        {'quote': {'text': '原文', 'language': 'zh', 'source_id': 'src-1',
                   'locator': '第 3 章', 'checked_at': '2026-10-10',
                   'verification': 'verbatim_checked'}},
        'case-1', {'src-1'}, {'src-1': SOURCE}, 'https://example.org/photography/gallery')
    assert any('not this case page' in error for error in errors), errors


def test_absent_evidence_stays_valid():
    assert validate_case_evidence(None, 'case-1', set(), {}, CASE_URL) == []


def _checked_quote(**overrides):
    quote = {'text': '原文', 'language': 'zh', 'source_id': 'src-1', 'locator': '第 3 章',
             'checked_at': '2026-10-10', 'verification': 'verbatim_checked'}
    quote.update(overrides)
    return quote


@pytest.mark.parametrize('checked_at', ['2026-13-40', '2026-02-29', '2025-02-29',
                                        '2026-04-31', '2026-00-10', '2026-10-00', '2026-1-01'])
def test_a_shaped_but_impossible_day_is_not_a_checking_date(checked_at):
    errors = validate_case_evidence({'quote': _checked_quote(checked_at=checked_at)},
                                    'case-1', {'src-1'}, {'src-1': SOURCE}, CASE_URL)
    assert any('checking date' in error for error in errors), errors


@pytest.mark.parametrize('checked_at', ['2026-10-10', '2028-02-29', '2024-02-29', '2026-12-31'])
def test_a_real_calendar_day_is_accepted_as_a_checking_date(checked_at):
    assert validate_case_evidence({'quote': _checked_quote(checked_at=checked_at)},
                                   'case-1', {'src-1'}, {'src-1': SOURCE}, CASE_URL) == []


@pytest.mark.parametrize('layer,change,expected', [
    ('advice', {'checked_at': '2026-02-30'}, 'Invalid case evidence advice date'),
    ('observation', {'checked_at': '2026-13-40'}, 'Invalid case evidence observation date'),
    ('explanation', {'checked_at': '2026-10-32'}, 'Invalid case evidence explanation date'),
])
def test_other_layers_reject_impossible_days_too(layer, change, expected):
    evidence = {'advice': {'text': '建议', 'checked_at': '2026-10-10'},
                'observation': {'text': '观察', 'checked_at': '2026-10-10'},
                'explanation': {'text': '解释', 'source_ids': ['src-1'], 'checked_at': '2026-10-10'}}
    evidence[layer].update(change)
    errors = validate_case_evidence(evidence, 'case-1', {'src-1'}, {'src-1': SOURCE}, CASE_URL)
    assert any(expected in error for error in errors), errors


@pytest.mark.parametrize('case_url', ['javascript:alert(1)', 'http://example.org/photography',
                                      'https://user@example.org/photography', '', None])
def test_a_verified_quote_needs_a_readable_case_page(case_url):
    errors = validate_case_evidence({'quote': _checked_quote()}, 'case-1', {'src-1'},
                                    {'src-1': SOURCE}, case_url)
    assert any('public case page' in error for error in errors), errors


@pytest.mark.parametrize('source_url', ['javascript:alert(1)', 'http://example.org/photography',
                                        'https://127.0.0.1/photography', ''])
def test_a_verified_quote_needs_a_readable_source_page(source_url):
    errors = validate_case_evidence({'quote': _checked_quote()}, 'case-1', {'src-1'},
                                    {'src-1': {**SOURCE, 'url': source_url}}, CASE_URL)
    assert any('public source page' in error or 'known source' in error for error in errors), errors


@pytest.mark.parametrize('text', ['', '   ', None, 3])
def test_a_verified_quote_needs_the_quoted_words_itself(text):
    errors = validate_case_evidence({'quote': _checked_quote(text=text)}, 'case-1', {'src-1'},
                                    {'src-1': SOURCE}, CASE_URL)
    assert any('quoted words' in error for error in errors), errors
