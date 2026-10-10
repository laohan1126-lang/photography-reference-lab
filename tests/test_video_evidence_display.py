"""Video evidence display boundaries.

The catalog, sources and screenshots below are SIMULATED fixtures written for this
file only. They prove that the shipped reader refuses unverifiable video claims;
they are not evidence that any real video was watched, heard or transcribed.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

WEB_JS = Path(__file__).resolve().parents[1] / 'web' / 'learning-gateways.js'
# Test-only closure export: the page never exposes these; the harness reads them to assert the boundary.
MARKER = 'return {init,links,close,openFromURL,onRouteChange:()=>{if(dialog?.open)close(false);},isOpen:()=>!!dialog?.open};'
PROBE = ('window.__probe = {evidenceTiming, evidenceIssues, evidenceVerdict, evidenceEntryHTML,'
         ' videoEvidenceHTML, videoKey, calendarDay, frameBinding, citedSources};\n' + MARKER)

HARNESS = """const fs = require('fs');
const vm = require('vm');
const payload = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const source = /*__SOURCE__*/;
function element() {
  return {innerHTML: '', hidden: false, scrollTop: 0, dataset: {}, open: false, style: {},
    addEventListener() {}, removeEventListener() {}, appendChild() {}, focus() {}, close() {}, showModal() {},
    querySelector() { return element(); }, querySelectorAll() { return []; },
    classList: {add() {}, remove() {}, toggle() {}, contains() { return false; }}};
}
const windowStub = {addEventListener() {}, location: {search: '', hash: ''}, scrollTo() {}, getComputedStyle() { return {}; }};
const documentStub = {getElementById() { return element(); }, createElement() { return element(); },
  querySelectorAll() { return []; }, addEventListener() {}, body: element()};
const context = vm.createContext({window: windowStub, document: documentStub, location: windowStub.location,
  sessionStorage: {getItem() { return null; }, setItem() {}, removeItem() {}}, URL: URL, console: console});
vm.runInContext(source, context, {filename: 'learning-gateways.js'});
const probe = windowStub.__probe;
if (!probe) throw new Error('test probe export is missing');
windowStub.LearningGateways.init(payload.atlas, {
  record() { return {}; }, revision() { return 0; }, canWrite() { return false; },
  async save() { return 0; }, navigate() {}, skillName() { return ''; }});
const results = payload.cases.map(item => {
  if (item.fn === 'timing') return probe.evidenceTiming(item.item, item.entry);
  if (item.fn === 'videoKey') return probe.videoKey(item.url);
  if (item.fn === 'html') {
    if (!item.item.video_evidence && Object.hasOwn(item, 'entry') && item.entry !== null) {
      item.item.video_evidence = {layers: Array.isArray(item.entry) ? item.entry : [item.entry]};
    }
    const html = probe.videoEvidenceHTML(item.item, item.item.url);
    return {html: html, verdicts: [...html.matchAll(/data-verdict="([a-z]+)"/g)].map(match => match[1])};
  }
  throw new Error('unknown probe: ' + item.fn);
});
console.log(JSON.stringify(results));
"""

CASE_VIDEO = 'https://www.youtube.com/watch?v=VidCaseAAA1'
CASE_AUTHOR = '案例作者'
SPEECH_RECORD_ID = 'speech-case-0020-0040'
SPEECH_TEXT = '先把距离拉开一点，再看背景。'
ATLAS = {
    'gateways': [{'id': 'fixture-gateway', 'kind': 'gateway', 'title': '夹具入口', 'author': CASE_AUTHOR,
                  'reading_depth': '入门', 'outcome': '', 'prior_knowledge': '', 'question': '',
                  'source_ids': [], 'skill_ids': [], 'sections': []}],
    'gateway_sources': [
        {'id': 'src-article', 'url': 'https://example.com/lighting-notes', 'title': '第三方笔记', 'author': '第三方作者'},
        {'id': 'src-same-video', 'url': 'https://youtu.be/VidCaseAAA1', 'title': '同一条视频的另一种地址', 'author': CASE_AUTHOR},
        {'id': 'src-insecure', 'url': 'http://example.com/insecure-notes', 'title': '非安全地址', 'author': '第三方作者'},
    ],
    'learning_content': {
        'sources': [{'id': 'content-video', 'url': CASE_VIDEO},
                    {'id': 'content-other', 'url': 'https://www.youtube.com/watch?v=OthVidBBB22'}],
        'speech_records': [],
        'media': [{'id': 'frame-case-0030', 'source_id': 'content-video', 'position': '00:30',
                   'caption': '人物与背景杆的前后关系'},
                  {'id': 'frame-other-0030', 'source_id': 'content-other', 'position': '00:30', 'caption': '另一条视频的截图'},
                  {'id': 'frame-case-late', 'source_id': 'content-video', 'position': '09:00', 'caption': '同一视频的靠后截图'}],
    },
}


def probe(tmp_path, cases, atlas=None):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is required to exercise the shipped reader inside a VM')
    source = WEB_JS.read_text(encoding='utf-8')
    assert MARKER in source, 'the module return moved; update the test-only probe export'
    payload = {'atlas': atlas or ATLAS, 'cases': cases}
    (tmp_path / 'payload.json').write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    (tmp_path / 'harness.js').write_text(
        HARNESS.replace('/*__SOURCE__*/', json.dumps(source.replace(MARKER, PROBE))), encoding='utf-8')
    result = subprocess.run([node, str(tmp_path / 'harness.js'), str(tmp_path / 'payload.json')],
                            capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def case(url=CASE_VIDEO, author=CASE_AUTHOR, playback=(0, 600)):
    return {'id': 'case-1', 'url': url, 'author': author,
            'playback': {'start': playback[0], 'end': playback[1]}}


def frame_entry(**overrides):
    return {'layer': 'A', 'text': '画面里能看见两人一前一后站着。', 'start': 20, 'end': 40,
            'media_id': 'frame-case-0030', 'verified_by': 'frames_reviewed', 'checked_at': '2026-10-10',
            **overrides}


def speech_entry(**overrides):
    return {'layer': 'B', 'text': SPEECH_TEXT, 'quote_kind': 'verbatim',
            'speaker': CASE_AUTHOR, 'attribution': 'clip_speech', 'start': 20, 'end': 40,
            'speech_record_id': SPEECH_RECORD_ID, 'verified_by': 'av_segment_check',
            'checked_at': '2026-10-10', **overrides}


def third_party_entry(**overrides):
    return {'layer': 'C', 'text': '透视变化主要来自拍摄距离而不是焦距。', 'source_ids': ['src-article'],
            'verification_scope': '正文第二段', 'verified_by': 'text_cross_check', 'checked_at': '2026-10-10',
            **overrides}


def verdicts(tmp_path, item, entry, atlas=None):
    if atlas is None and isinstance(entry, dict) and entry.get('layer') == 'B':
        atlas = atlas_with_speech(entry)
    return probe(tmp_path, [{'fn': 'html', 'item': item, 'entry': entry}], atlas)[0]['verdicts']


def atlas_with_speech(entry, **record_overrides):
    """Register a simulated transcript fixture; the digest records fixture integrity only."""
    atlas = json.loads(json.dumps(ATLAS))
    transcript = entry.get('original') if entry.get('quote_kind') == 'translation' else entry.get('text')
    transcript = transcript if isinstance(transcript, str) else ''
    record = {
        'id': SPEECH_RECORD_ID, 'source_id': 'content-video', 'url': CASE_VIDEO,
        'start': entry.get('start'), 'end': entry.get('end'), 'speaker': CASE_AUTHOR,
        'transcript': transcript,
        'fixture_sha256': hashlib.sha256(transcript.encode('utf-8')).hexdigest(),
        'verification_scope': '模拟音视频逐段核对，仅用于测试夹具', 'checked_at': '2026-10-10',
        'verified_by': entry.get('verified_by'), 'fixture_simulated': True,
    }
    record.update(record_overrides)
    atlas['learning_content']['speech_records'] = [record]
    return atlas


@pytest.mark.parametrize('case_url,entry_url,expected', [
    (CASE_VIDEO, CASE_VIDEO, True),
    (CASE_VIDEO, CASE_VIDEO + '&t=90', True),
    (CASE_VIDEO, CASE_VIDEO + '&t=30&list=PLabcdefgh', True),
    (CASE_VIDEO, CASE_VIDEO + '#t=30', True),
    (CASE_VIDEO, 'https://www.youtube.com/shorts/VidCaseAAA1?t=5', True),
    (CASE_VIDEO, 'https://youtu.be/VidCaseAAA1?t=5', True),
    (CASE_VIDEO, 'https://www.youtube.com/embed/VidCaseAAA1', True),
    (CASE_VIDEO, 'https://m.youtube.com/watch?v=VidCaseAAA1', True),
    (CASE_VIDEO, 'https://www.youtube.com/watch?v=OthVidBBB22', False),
    (CASE_VIDEO, 'https://www.youtube.com/watch?v=VidCaseAAA1X', False),
    (CASE_VIDEO, 'https://example.com/watch?v=VidCaseAAA1', False),
    (CASE_VIDEO, 'javascript:alert(1)', False),
    ('https://www.youtube.com/watch?v=REAL_A', 'https://www.youtube.com/watch?v=WRONG_B', False),
    ('https://www.youtube.com/watch?v=REAL_A', 'https://www.youtube.com/watch?v=REAL_A', False),
    ('javascript:alert(1)', CASE_VIDEO, False),
    ('https://www.bilibili.com/video/BV1od4y1n7Ag/', 'https://www.bilibili.com/video/BV1od4y1n7Ag/?t=60', True),
    ('https://www.bilibili.com/video/BV1od4y1n7Ag/', 'https://www.bilibili.com/video/BV1MD421L7VK/', False),
])
def test_timing_requires_the_same_identifiable_video(tmp_path, case_url, entry_url, expected):
    """Only ?t= and #fragment may differ; the video ID may never differ."""
    result = probe(tmp_path, [{'fn': 'timing', 'item': case(url=case_url),
                               'entry': {'start': 10, 'end': 30, 'url': entry_url}}])[0]
    assert result['ok'] is expected, result


def test_non_youtube_sites_keep_identity_bearing_parameters(tmp_path):
    keys = probe(tmp_path, [{'fn': 'videoKey', 'url': f'https://example.com/watch?id={value}'}
                            for value in (7, 8)])
    assert keys[0] != keys[1]
    same = probe(tmp_path, [{'fn': 'videoKey', 'url': 'https://example.com/watch?id=7&t=10&start=20#t=5'},
                            {'fn': 'videoKey', 'url': 'https://example.com/watch?id=7&t=99'}])
    assert same[0] == same[1] == 'example.com/watch?id=7'


def test_case_without_safe_video_identity_never_shows_verified(tmp_path):
    html = probe(tmp_path, [{'fn': 'html', 'item': case(url='javascript:alert(1)'),
                             'entry': frame_entry(url='javascript:alert(1)')}])[0]
    assert html['verdicts'] == ['unverified']
    assert 'alert(1)' not in html['html'] and 'href="javascript' not in html['html']
    assert '<span class="evidence-verdict">已核验' not in html['html']


@pytest.mark.parametrize('entry', [
    frame_entry(),
    frame_entry(url='https://youtu.be/VidCaseAAA1?t=5'),
], ids=['same_video', 'same_video_other_form'])
def test_registered_frame_media_can_be_checked(tmp_path, entry):
    assert verdicts(tmp_path, case(), entry) == ['verified']


@pytest.mark.parametrize('entry', [
    frame_entry(media_id=''),
    frame_entry(media_id='frame-that-was-never-registered'),
    frame_entry(media_id='frame-other-0030'),
    frame_entry(media_id='frame-case-late'),
    frame_entry(start=60, end=90),
    frame_entry(verified_by='clip_watched'),
    frame_entry(url='https://www.youtube.com/watch?v=OthVidBBB22'),
    frame_entry(checked_at='2026-99-99'),
    frame_entry(checked_at='2026-02-30'),
    frame_entry(checked_at='2026-10-10T08:00:00Z'),
    frame_entry(checked_at='昨天'),
    frame_entry(checked_at=''),
    frame_entry(verified=False),
    frame_entry(status='unverified'),
    frame_entry(simulated=True),
], ids=['no_media_id', 'unregistered_media', 'media_from_other_video', 'frame_outside_clip', 'clip_outside_clip',
        'watched_without_source', 'other_video', 'impossible_month', 'impossible_day', 'timestamp', 'prose_date',
        'empty_date', 'explicitly_unverified', 'marked_unverified', 'simulated_entry'])
def test_frame_evidence_without_traceable_media_stays_unverified(tmp_path, entry):
    assert verdicts(tmp_path, case(), entry) == ['unverified']


def test_frame_check_line_explains_itself_in_chinese(tmp_path):
    html = probe(tmp_path, [{'fn': 'html', 'item': case(), 'entry': frame_entry()}])[0]['html']
    assert '画面来源：已登记截图 · 取自 00:30' in html
    assert '逐帧查看已登记的画面截图' in html and '核验于 2026-10-10' in html
    for internal in ('frames_reviewed', 'media_id', 'verified_by', 'checked_at', 'clip_speech', 'gateway_sources'):
        assert internal not in html


@pytest.mark.parametrize('entry', [
    speech_entry(),
    speech_entry(verified_by='subtitle_segment_check'),
], ids=['av_check', 'subtitle_check'])
def test_author_speech_can_be_checked(tmp_path, entry):
    assert verdicts(tmp_path, case(), entry) == ['verified']


@pytest.mark.parametrize('entry', [
    speech_entry(attribution=''),
    speech_entry(attribution='frames_reviewed'),
    speech_entry(attribution='third_party'),
    speech_entry(speaker=''),
    speech_entry(speaker='路过的观众'),
    speech_entry(quote_kind='paraphrase'),
    speech_entry(quote_kind=''),
    speech_entry(verified_by='frames_reviewed'),
    speech_entry(verified_by='clip_watched'),
    speech_entry(verified_by='made_up_method'),
    speech_entry(checked_at='2026-99-99'),
    speech_entry(verified=False),
    speech_entry(status='unverified'),
    speech_entry(simulated=True),
], ids=['no_attribution', 'frames_attribution', 'other_attribution', 'no_speaker', 'unrelated_speaker',
        'paraphrase', 'no_quote_kind', 'frames_method', 'watch_method', 'unknown_method', 'impossible_date',
        'explicitly_unverified', 'marked_unverified', 'simulated_entry'])
def test_speech_evidence_needs_clip_speech_and_the_registered_author(tmp_path, entry):
    assert verdicts(tmp_path, case(), entry) == ['unverified']


def test_translated_speech_still_needs_the_original_line(tmp_path):
    assert verdicts(tmp_path, case(), speech_entry(quote_kind='translation', original='Move back first.')) == ['verified']
    assert verdicts(tmp_path, case(), speech_entry(quote_kind='translation', original='')) == ['unverified']


@pytest.mark.parametrize('record_overrides', [
    {'transcript': '另一段转录原文'},
    {'start': 19, 'end': 40},
    {'source_id': 'content-other', 'url': 'https://www.youtube.com/watch?v=OthVidBBB22'},
    {'source_id': 'source-not-registered', 'url': ''},
], ids=['wrong_transcript', 'wrong_time', 'other_video_source', 'unregistered_source'])
def test_speech_requires_matching_registered_transcript_content_and_binding(tmp_path, record_overrides):
    entry = speech_entry()
    atlas = atlas_with_speech(entry, **record_overrides)
    assert verdicts(tmp_path, case(), entry, atlas) == ['unverified']


@pytest.mark.parametrize('record_overrides', [
    {'simulated': True},
    {'verified': False},
    {'status': 'unverified'},
], ids=['simulated_record', 'explicitly_unverified_record', 'marked_unverified_record'])
def test_untrusted_registry_status_cannot_verify_author_speech(tmp_path, record_overrides):
    entry = speech_entry()
    atlas = atlas_with_speech(entry, **record_overrides)
    assert verdicts(tmp_path, case(), entry, atlas) == ['unverified']


@pytest.mark.parametrize('entry', [third_party_entry()], ids=['independent'])
def test_third_party_prose_can_be_checked(tmp_path, entry):
    assert verdicts(tmp_path, case(), entry) == ['verified']


def test_independent_source_mixed_with_self_reference_stays_unverified(tmp_path):
    entry = third_party_entry(source_ids=['src-article', 'src-same-video'])
    assert verdicts(tmp_path, case(), entry) == ['unverified']


@pytest.mark.parametrize('entry', [
    third_party_entry(source_ids=['src-same-video']),
    third_party_entry(source_ids=[]),
    third_party_entry(source_ids=['src-not-registered']),
    third_party_entry(source_ids=['src-insecure']),
    third_party_entry(verification_scope=''),
    third_party_entry(verification_scope='   '),
    third_party_entry(verified_by='frames_reviewed'),
    third_party_entry(verified_by='clip_watched'),
    third_party_entry(checked_at='2026-99-99'),
    third_party_entry(verified=False),
    third_party_entry(status='unverified'),
    third_party_entry(simulated=True),
], ids=['self_reference', 'no_sources', 'unregistered_source', 'insecure_source', 'no_scope', 'blank_scope',
        'frames_method', 'watch_method', 'impossible_date', 'explicitly_unverified', 'marked_unverified',
        'simulated_entry'])
def test_third_party_prose_needs_a_safe_independent_scoped_source(tmp_path, entry):
    assert verdicts(tmp_path, case(), entry) == ['unverified']


def test_self_reference_names_the_same_video_however_it_is_spelled(tmp_path):
    html = probe(tmp_path, [{'fn': 'html', 'item': case(), 'entry': third_party_entry(source_ids=['src-same-video'])}])[0]
    assert html['verdicts'] == ['unverified']
    assert '不能当作独立第三方依据' in html['html']


def test_simulated_catalog_never_verifies_anything(tmp_path):
    atlas = json.loads(json.dumps(ATLAS))
    atlas['gateways'][0]['cases'] = []
    entries = [{'layers': [frame_entry(), speech_entry(), third_party_entry()]}]
    atlas['cases'] = entries
    item = dict(case(), video_evidence={'simulated': True, 'layers': entries[0]['layers']})
    html = probe(tmp_path, [{'fn': 'html', 'item': item, 'entry': None}], atlas)[0]
    assert html['verdicts'] == ['unverified', 'unverified', 'unverified']
    assert '模拟夹具' in html['html']
    assert '<span class="evidence-verdict">已核验' not in html['html']


def test_legacy_self_claims_never_promote_evidence(tmp_path):
    entry = {'layer': 'A', 'text': '画面里能看见两人一前一后站着。', 'start': 20, 'end': 40,
             'verified': True, 'status': 'verified'}
    html = probe(tmp_path, [{'fn': 'html', 'item': case(), 'entry': entry}])[0]
    assert html['verdicts'] == ['unverified']
    assert '<span class="evidence-verdict">已核验（仅限所列片段与核验方式）' not in html['html']
    assert '自称已核验的字段都不算核对过' in html['html']


def test_missing_text_is_insufficient_rather_than_unverified(tmp_path):
    html = probe(tmp_path, [{'fn': 'html', 'item': case(), 'entry': frame_entry(text='   ')}])[0]
    assert html['verdicts'] == ['insufficient']
    assert '没有可读的证据正文' in html['html']


def test_unreadable_layer_and_object_cannot_claim_verification(tmp_path):
    unreadable = {'layer': 'Z', 'text': '未知层级', 'verified': True, 'status': 'verified'}
    malformed_quote = {'layer': 'B', 'text': '异常 quote_kind', 'quote_kind': {'toString': None}}
    suggestion = {'layer': 'D', 'text': '可在实拍中另行验证。'}
    result = probe(tmp_path, [{'fn': 'html', 'item': case(),
                               'entry': [unreadable, 'not-an-object', [], malformed_quote, suggestion]}])[0]
    assert result['verdicts'] == ['insufficient', 'insufficient', 'insufficient', 'unverified', 'suggestion']


def test_injected_markup_stays_text_in_both_body_and_meta(tmp_path):
    payload = '<script>alert(1)</script><img src=x onerror=alert(2)>'
    entry = frame_entry(text=payload, verification_scope=payload, speaker=payload)
    html = probe(tmp_path, [{'fn': 'html', 'item': case(author=payload), 'entry': entry}])[0]['html']
    assert '<script>' not in html and '</script>' not in html
    assert '<img src=x onerror=' not in html and '<img src=x' not in html
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in html
    speech = probe(tmp_path, [{'fn': 'html', 'item': case(), 'entry': speech_entry(speaker=payload)}])[0]['html']
    assert '<script>' not in speech and '与本案例登记的作者对不上' in speech
