"""Program regressions; synthetic pixels never prove photographic accuracy."""
import json
from ref_lab import collage
from ref_lab.collection_counts import compute
from ref_lab.collection_history import ImageHistory
from ref_lab.verified_collection import deterministic_plan
from tests.test_collage_split import _collage, _textured, _write_original
from tools.collect_verified import Browser, restore_history_index


def test_named_unknown_type_is_only_a_candidate(tmp_path):
    row = _write_original(tmp_path, _textured((800, 600), 1, (70, 80, 90)))
    row['relevance'] = {'tier': 'target_named'}
    record = collage.process_original(tmp_path, row)
    counts = compute(tmp_path, [row], {row['asset_sha']: record})
    assert counts['found'] == 1
    assert counts['usable_named'] == counts['usable_independent'] == 0


def test_successful_new_search_clears_previous_return_failure(tmp_path):
    browser = Browser(tmp_path)
    browser.return_failed = True
    browser.session = 'synthetic'
    browser.command = lambda *a, **k: '{}'
    browser.snapshot = lambda: {'cards': [{'page': 'https://www.pinterest.com/pin/1/'}]}
    browser.search({'source': 'pinterest', 'query': 'You Watanabe cosplay'})
    assert browser.return_failed is False


def test_trusted_names_preserve_original_and_languages():
    plan = deterministic_plan({'character': '渡边曜', 'work': 'Love Live! Sunshine!!'})
    records = {r['name']: r for r in plan.name_records}
    assert {'渡边曜', '渡辺曜', '渡辺 曜', 'You Watanabe', 'Watanabe You'} <= records.keys()
    assert records['渡边曜']['language'] == 'zh'
    assert records['渡辺曜']['language'] == 'ja'


def test_resume_keeps_shared_tile_business_identity(tmp_path):
    a = _write_original(tmp_path, _collage(2, 1, tile=(800, 600),
        bases=[(28, 30, 34), (222, 220, 214)]), name='a.png')
    a['relevance'] = {'tier': 'unconfirmed'}
    first = collage.process_original(tmp_path, a)
    history = ImageHistory([])
    try:
        restore_history_index(history, tmp_path, [a])
        b = _write_original(tmp_path, _collage(2, 1, tile=(800, 600),
            bases=[(28, 30, 34), (52, 150, 196)]), name='b.png')
        b['relevance'] = {'tier': 'target_named'}
        history.consider(__import__('pathlib').Path(b['original_path']))
        second = collage.process_original(tmp_path, b, history=history,
            known_shas={a['asset_sha'], b['asset_sha']})
        assert second['children'][0]['status'] == collage.DUPLICATE_RUN
        assert first['children'][0]['child_sha'] == second['children'][0]['child_sha']
    finally:
        history.close()
