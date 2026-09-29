from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import zipfile

from PIL import Image

from ref_lab.agent_collection import run_collection_attempt
from ref_lab.models import JobInput
from ref_lab.preflight import detect_modality, evaluate_identity
from ref_lab.service import Library
from ref_lab.db import encode
from ref_lab.identity import build_identity_context
from conftest import image_bytes, add_reference
from tools.collect_adapter import (
    _is_note_url,
    build_policy,
    build_queries,
    compute_dhash,
    hamming_distance,
    result_metadata_allowed,
    validate_downloaded_image,
)


def test_request_notes_change_queries_and_add_negative_filters():
    job = {
        "queries": ["王昭君 cosplay 摄影", "王昭君 长夜焕生 cosplay 摄影"],
        "notes": "只找该皮肤的COS正片；不要游戏截图，不要插画",
        "project_snapshot": {"character": "王昭君", "work": "王者荣耀", "costume": "长夜焕生"},
    }
    policy = build_policy(job)
    queries = build_queries(job)
    assert policy["require_cosplay"] is True
    assert policy["require_costume"] is True
    assert all("长夜焕生" in q for q in queries)
    assert all("-游戏截图" in q and "-插画" in q and "-皮肤特效" in q for q in queries)
    assert any("只找该皮肤的COS正片" in q for q in queries)

    browser_queries = build_queries(job, for_browser=True)
    assert all("-" not in q for q in browser_queries)
    assert any("王昭君 长夜焕生" in q for q in browser_queries)


def test_search_query_cos_does_not_make_game_result_eligible():
    policy = build_policy({
        "notes": "只找该皮肤的COS正片",
        "project_snapshot": {"character": "王昭君", "work": "王者荣耀", "costume": "长夜焕生"},
    })
    game = {
        "t": "王者荣耀王昭君FMVP皮肤长夜焕生特效设计介绍",
        "desc": "新皮肤技能特效展示与游戏画面",
        "purl": "https://example.com/game/skin-demo",
    }
    allowed, reason = result_metadata_allowed(game, policy)
    assert allowed is False
    assert reason.startswith("negative_type:")

    # The query itself intentionally contains cosplay; it is not passed to the
    # result classifier and therefore cannot rescue unrelated metadata.
    valid = {
        "t": "王昭君 长夜焕生 COS 正片返图",
        "desc": "coser 棚拍摄影",
        "purl": "https://example.com/cosplay/post-1",
    }
    assert result_metadata_allowed(valid, policy)[0] is True


def test_specific_skin_and_cosplay_are_hard_requirements():
    policy = build_policy({
        "notes": "仅找该皮肤COS正片",
        "project_snapshot": {"character": "王昭君", "work": "王者荣耀", "costume": "长夜焕生"},
    })
    wrong_skin = {
        "t": "王昭君 凤凰于飞 cosplay 正片",
        "desc": "王昭君 coser 摄影",
        "purl": "https://example.com/cosplay/phoenix",
    }
    assert result_metadata_allowed(wrong_skin, policy) == (False, "missing_costume")

    no_cosplay = {
        "t": "王昭君 长夜焕生 皮肤资料",
        "desc": "角色资料",
        "purl": "https://example.com/wiki",
    }
    allowed, reason = result_metadata_allowed(no_cosplay, policy)
    assert allowed is False
    assert reason in {"missing_cosplay_evidence"} or reason.startswith("negative_type:")


def test_social_platform_cosplay_matching():
    policy = build_policy({
        "notes": "只找同皮肤cos正片",
        "project_snapshot": {"character": "王昭君", "work": "王者荣耀", "costume": "长夜焕生"},
    })
    # Social card with character alias and author
    card1 = {
        "t": "长夜焕生•昭君",
        "author": "📷刘肉丸丸",
        "purl": "https://www.xiaohongshu.com/explore/sample1",
    }
    assert result_metadata_allowed(card1, policy)[0] is True

    # Social card with costume and cosplay author
    card2 = {
        "t": "宁波还能拍到这么好看的长夜焕生！",
        "author": "像素猫cos自拍摄影",
        "purl": "https://www.xiaohongshu.com/explore/sample2",
    }
    assert result_metadata_allowed(card2, policy)[0] is True

    # A voice-line title is not accepted merely because it appeared in the
    # requested Xiaohongshu search.  It must be resolved from visible detail
    # metadata/tags before becoming eligible.
    card_voiceline = {
        "t": "长风万里，生生不息",
        "author": "小兔子落落",
        "purl": "https://www.xiaohongshu.com/explore/sample_voiceline",
    }
    allowed, reason = result_metadata_allowed(card_voiceline, policy)
    assert allowed is False
    assert reason.startswith("needs_detail_evidence:")

    resolved_voiceline = {
        **card_voiceline,
        "full_text": "#王者荣耀 #王昭君长夜焕生 #cos正片 长风万里，生生不息",
    }
    assert result_metadata_allowed(resolved_voiceline, policy)[0] is True

    # Costume brand names are not intrinsically noise.  A clearly labelled
    # cosplay/photo post must remain eligible even if the costume maker is named.
    branded_cosplay = {
        "t": "三分妄想 王昭君长夜焕生 COS 正片返图",
        "author": "小兔子落落",
        "purl": "https://www.xiaohongshu.com/explore/sample_brand",
    }
    assert result_metadata_allowed(branded_cosplay, policy)[0] is True

    # The real regression: a costume-help/text post is not a photography
    # reference even though it names the exact character/skin and a known brand.
    help_post = {
        "t": "求助：三分妄想家的王昭君长夜焕生c服裙边怎么整理",
        "author": "路人甲",
        "purl": "https://www.xiaohongshu.com/explore/sample_help",
    }
    allowed, reason = result_metadata_allowed(help_post, policy)
    assert allowed is False
    assert reason.startswith("negative_type:")

    unrelated_social = {
        "t": "今天随手记",
        "author": "路人乙",
        "purl": "https://www.xiaohongshu.com/explore/sample_unrelated",
    }
    allowed, reason = result_metadata_allowed(unrelated_social, policy)
    assert allowed is False
    assert reason.startswith("needs_detail_evidence:")

    # Social card with skirt/corset negative marker rejected
    card_skirt = {
        "t": "喵怎么会做裙撑不要命啦",
        "author": "小兔子落落",
        "purl": "https://www.xiaohongshu.com/explore/sample_skirt",
    }
    allowed, reason = result_metadata_allowed(card_skirt, policy)
    assert allowed is False
    assert reason.startswith("negative_type:")

    # Social card with shop review negative marker rejected
    card_shop = {
        "t": "女神们长夜焕生哪家好",
        "author": "路人甲",
        "purl": "https://www.xiaohongshu.com/explore/sample_shop",
    }
    allowed, reason = result_metadata_allowed(card_shop, policy)
    assert allowed is False
    assert reason.startswith("negative_type:")

    # Social card with negative marker still rejected
    card3 = {
        "t": "长夜焕生昭君游戏截图特效展示",
        "author": "游戏攻略菌",
        "purl": "https://www.xiaohongshu.com/explore/sample3",
    }
    allowed, reason = result_metadata_allowed(card3, policy)
    assert allowed is False
    assert reason.startswith("negative_type:")


def test_download_validation_and_within_run_perceptual_hash():
    first = image_bytes(seed=17, size=(800, 1200))
    second = image_bytes(seed=17, size=(800, 1200))
    policy = {"portrait_only": False}
    ok1, ext1, dh1 = validate_downloaded_image(first, policy)
    ok2, ext2, dh2 = validate_downloaded_image(second, policy)
    assert ok1 and ok2 and ext1 == ext2 == "png"
    assert dh1 == dh2
    assert hamming_distance(dh1, dh2) == 0

    with Image.open(io.BytesIO(first)) as image:
        assert compute_dhash(image) == dh1


def test_deterministic_preflight_does_not_promote_query_metadata_to_visual_pass():
    image = Image.open(io.BytesIO(image_bytes(seed=22, size=(800, 1200))))
    metadata = {
        "title": "王昭君 长夜焕生 cosplay 摄影",
        "source": {
            "page_url": "https://example.com/post",
            "search_query": "王昭君 长夜焕生 cos 正片",
            "search_category": "",
        },
    }
    modality, evidence = detect_modality(image, metadata)
    assert modality == "unknown"
    assert any("不能据此宣称真人实拍" in x for x in evidence)

    context = build_identity_context("王昭君", "王者荣耀", "长夜焕生")
    identity = evaluate_identity(first := image_bytes(seed=22, size=(800, 1200)), metadata, context)
    assert identity["prediction"] == "uncertain"
    assert "metadata" in identity["reason"] or "标题/检索上下文" in identity["reason"]


def test_game_effect_metadata_is_filtered_even_when_query_is_cosplay():
    image = Image.open(io.BytesIO(image_bytes(seed=23, size=(1200, 700))))
    metadata = {
        "title": "王昭君FMVP皮肤长夜焕生特效设计介绍",
        "source": {
            "page_url": "https://example.com/game",
            "search_query": "王昭君 长夜焕生 cos 正片",
            "search_category": "",
        },
    }
    modality, _ = detect_modality(image, metadata)
    assert modality == "game_screenshot"


def test_collect_adapter_transport_uses_schema2_without_fake_preflight(library, project, monkeypatch, tmp_path):
    job = library.create_job(project["id"], JobInput(
        kind="collection",
        notes="只找该皮肤的COS正片",
        target_count=2,
    ))
    adapter_script = Path(__file__).resolve().parent.parent / "tools" / "collect_adapter.py"
    assert adapter_script.is_file()

    wrapper = tmp_path / "mock_adapter.py"
    img1 = image_bytes(seed=1, size=(800, 1200))
    img2 = image_bytes(seed=2, size=(900, 1200))
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "img1.png").write_bytes(img1)
    (cache_dir / "img2.png").write_bytes(img2)

    repo_root = str(adapter_script.parent.parent).replace("\\", "/")
    if repo_root.startswith("D:"):
        repo_root = "/mnt/d" + repo_root[2:]
    elif repo_root.startswith("C:"):
        repo_root = "/mnt/c" + repo_root[2:]

    wrapper.write_text(f"""import json, sys, zipfile
from pathlib import Path
task_dir = Path(sys.argv[1]).parent
job = json.loads((task_dir / 'job.json').read_text(encoding='utf-8'))['job']
manifest = {{
  'schema_version': 2,
  'job_id': job['id'],
  'batch_id': 'strict-search-test',
  'candidates': [
    {{'id':'one','file':'images/img1.png','title':'王昭君 长夜焕生 COS 正片',
      'source':{{'page_url':'https://example.com/1','image_url':'https://example.com/i1','search_query':'strict','rights':'unknown','source_confirmed':False}},
      'discovery_intent':'exact_character','discovery_reason':'strict search only','discovery_url':'https://example.com/search','notes':''}},
    {{'id':'two','file':'images/img2.png','title':'王昭君 长夜焕生 COS 返图',
      'source':{{'page_url':'https://example.com/2','image_url':'https://example.com/i2','search_query':'strict','rights':'unknown','source_confirmed':False}},
      'discovery_intent':'exact_character','discovery_reason':'strict search only','discovery_url':'https://example.com/search','notes':''}}
  ],
  'execution_report': {{
    'producer':'local_collection_adapter_search_only','status':'completed',
    'summary':'strict search; no visual model','source_checks':[],'query_log':[],'gaps':[]
  }}
}}
with zipfile.ZipFile(sys.argv[2], 'w') as z:
    z.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False))
    z.writestr('images/img1.png', Path(r'{cache_dir / "img1.png"}').read_bytes())
    z.writestr('images/img2.png', Path(r'{cache_dir / "img2.png"}').read_bytes())
""", encoding="utf-8")

    monkeypatch.setenv("LAB_COLLECTION_COMMAND", json.dumps([
        sys.executable, str(wrapper), "{task_file}", "{result_file}"
    ]))
    monkeypatch.setenv("LAB_COLLECTION_TIMEOUT_SECONDS", "10")

    result = run_collection_attempt(library, job["id"])
    assert result["status"] == "succeeded"
    assert len(result["imported_ids"]) == 2
    for ident in result["imported_ids"]:
        ref = library.reference(ident)
        assert ref["preflight"] is None
        assert ref["preflight_status"] == "unreviewed"
        assert ref["decision"] == "pending"


def test_startup_repairs_known_fake_local_adapter_preflight(client, project, library):
    ref = add_reference(client, project, seed=77)
    with library.db.transaction() as con:
        row = con.execute("SELECT data FROM refs WHERE id=?", (ref["id"],)).fetchone()
        data = json.loads(row[0])
        data["title"] = "王昭君FMVP皮肤长夜焕生特效设计介绍"
        data["source"]["search_query"] = "王昭君 长夜焕生 cos 正片"
        data["preflight"] = {
            "producer": "local_collection_adapter",
            "content_type": "real_person_cosplay",
            "identity_prediction": "match",
            "confidence": "medium",
            "visual_evidence": ["真人实拍", "符合检索词"],
            "reason": "metadata-only false positive",
            "status": "passed",
            "status_reason": "身份与质量预检均通过",
        }
        data["preflight_status"] = "passed"
        data["preflight_filtered"] = False
        con.execute("UPDATE refs SET data=? WHERE id=?", (encode(data), ref["id"]))

    repaired_library = Library(library.settings)
    repaired = repaired_library.reference(ref["id"])
    assert repaired["preflight"]["producer"] == "vision-preflight-gate"
    assert repaired["preflight"]["content_type"] == "game_screenshot"
    assert repaired["preflight_status"] == "filtered"
    assert repaired["preflight_filtered"] is True
    assert repaired["invalidated_preflights"][-1]["producer"] == "local_collection_adapter"
    assert repaired["decision"] == ref["decision"]


def test_target_query_cannot_mask_explicit_confusion_character():
    metadata = {
        "title": "小乔 cosplay 正片",
        "source": {
            "page_url": "https://example.com/xiaoqiao-cos",
            "title": "小乔 COS",
            "search_query": "王昭君 长夜焕生 cos 正片",
            "search_category": "",
        },
    }
    context = build_identity_context("王昭君", "王者荣耀", "长夜焕生")
    result = evaluate_identity(image_bytes(seed=88, size=(800, 1200)), metadata, context)
    assert result["prediction"] == "mismatch"
    assert "小乔" in result["reason"]


def test_xhs_note_url_recognises_both_link_forms_but_not_the_search_page():
    """Live failure (2026-09-29): the search page links every note twice.

    The tokenless `/explore/<id>` anchor is what the collector used to pick, and
    opening it renders Xiaohongshu's 404 "当前笔记暂时无法浏览", so every
    voice-line-titled cosplay card came back with empty detail evidence and was
    dropped.  Detail evidence must accept the token-bearing link form too,
    while still refusing the aggregate keyword search page.
    """
    assert _is_note_url("https://www.xiaohongshu.com/explore/6a8937bb000000003a02d574")
    assert _is_note_url(
        "https://www.xiaohongshu.com/search_result/6a8937bb000000003a02d574"
        "?xsec_token=ABwwTLyycSTrO5-0kSYw3X4oaRf-UJeyYe_YiiZthglYw=&xsec_source=pc_feed"
    )
    # The aggregate search page must never validate an individual card.
    assert not _is_note_url(
        "https://www.xiaohongshu.com/search_result?keyword=%E7%8E%8B%E6%98%AD%E5%90%9B&type=51"
    )
    assert not _is_note_url("https://www.pinterest.com/search/pins/?q=wzj")
    assert not _is_note_url("")


def test_xhs_extract_js_prefers_the_token_bearing_note_link():
    """The card extractor must prefer the xsec_token anchor it previously skipped."""
    import re
    source = (Path(__file__).resolve().parent.parent / "tools" / "collect_adapter.py").read_text(encoding="utf-8")
    match = re.search(r"const link = item\.querySelector\((.*?)\);", source, re.S)
    assert match, "extract_js link selection not found"
    selectors = match.group(1)
    assert 'a[href*="xsec_token"]' in selectors
    assert selectors.index('xsec_token') < selectors.index('/explore/')


def _fake_run(responses):
    """subprocess.run stub keyed by the bsk binary being invoked."""
    def run(cmd, *args, **kwargs):
        binary = cmd[0]
        if binary not in responses:
            raise FileNotFoundError(binary)
        reply = responses[binary]
        if isinstance(reply, Exception):
            raise reply
        return type("R", (), {"stdout": json.dumps(reply, ensure_ascii=False), "returncode": 0})()
    return run


def test_browserskill_selection_prefers_a_binary_that_reaches_the_browser(monkeypatch, tmp_path):
    """Live failure (2026-09-29): `which("bsk")` found a WSL bsk with no daemon.

    That binary exists and reports its version fine, but it cannot see the
    Windows browser, so selecting it dropped the whole run into a silent Bing
    fallback.  The binary that actually reaches Edge must win.
    """
    import tools.collect_adapter as ca

    dead = str(tmp_path / "bsk")
    live = str(tmp_path / "bsk.exe")
    # Presence is all isfile can tell us, so both files must really exist.
    for path in (dead, live):
        Path(path).write_text("", encoding="utf-8")

    monkeypatch.setattr(ca.shutil, "which", lambda n: {"bsk": dead, "bsk.exe": live}.get(n))
    monkeypatch.setattr(ca.os.path, "isfile", lambda p: p in {dead, live})
    monkeypatch.setattr(ca.subprocess, "run", _fake_run({
        dead: [],                                                   # present, no browser
        live: [{"instance_id": "9d3f232a", "browser_name": "edge"}],
    }))

    assert ca.select_browserskill({}) == (live, "9d3f232a")


def test_browserskill_selection_keeps_probing_after_an_unusable_candidate(monkeypatch, tmp_path):
    import tools.collect_adapter as ca

    dead = "/wsl/bin/bsk"
    broken = "/wsl/bin/bsk-crash"
    live = "/mnt/c/Users/Dell/.local/bin/bsk.exe"
    monkeypatch.setattr(ca, "bsk_candidates", lambda: [dead, broken, live])
    monkeypatch.setattr(ca.subprocess, "run", _fake_run({
        dead: [],
        broken: OSError("daemon IPC unavailable"),
        live: [{"instance_id": "edge-1", "browser_name": "edge"}],
    }))

    assert ca.select_browserskill({}) == (live, "edge-1")


def test_browserskill_selection_returns_nothing_when_every_candidate_is_unusable(monkeypatch):
    import tools.collect_adapter as ca

    only = ["/wsl/bin/bsk"]
    monkeypatch.setattr(ca, "bsk_candidates", lambda: only)
    monkeypatch.setattr(ca.subprocess, "run", _fake_run({"/wsl/bin/bsk": []}))

    assert ca.select_browserskill({}) == (None, None)


def test_no_usable_browserskill_must_not_silently_use_bing(tmp_path):
    """No live browser and no --allow-bing-fallback => blocked, zero candidates."""
    import tools.collect_adapter as ca
    import zipfile

    dead = "/wsl/bin/bsk"
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    (task_dir / "job.json").write_text(json.dumps({
        "job": {"id": "job-1", "target_count": 2,
                "notes": "只找王昭君长夜焕生这个皮肤的真人COS正片",
                "project_snapshot": {"character": "王昭君", "work": "王者荣耀", "costume": "长夜焕生"}},
    }, ensure_ascii=False), encoding="utf-8")
    result_file = tmp_path / "result.zip"

    def _no_browser(_env, *_a, **_k):
        return None, None
    ca.select_browserskill = _no_browser
    ca.nudge_extension = lambda *_a, **_k: (None, None)
    ca.bsk_candidates = lambda: [dead]
    called = []
    ca.fetch_bing_candidates = lambda *a, **k: called.append(True) or ([], {}, [])

    sys.argv = ["collect_adapter.py", str(task_dir / "job.json"), str(result_file)]
    ca.main()

    assert called == [], "Bing must not be used without an explicit opt-in"
    with zipfile.ZipFile(result_file) as archive:
        manifest = json.loads(archive.read("manifest.json"))
    report = manifest["execution_report"]
    assert report["status"] == "blocked"
    assert manifest["candidates"] == []
    assert "BrowserSkill" in report["summary"]
    assert any("BrowserSkill" in gap for gap in report["gaps"])


def test_bing_fallback_requires_explicit_opt_in(tmp_path):
    import tools.collect_adapter as ca
    import zipfile

    task_dir = tmp_path / "task"
    task_dir.mkdir()
    (task_dir / "job.json").write_text(json.dumps({
        "job": {"id": "job-2", "target_count": 1, "notes": "cos 正片",
                "project_snapshot": {"character": "王昭君", "work": "王者荣耀", "costume": "长夜焕生"}},
    }, ensure_ascii=False), encoding="utf-8")
    result_file = tmp_path / "result.zip"

    ca.select_browserskill = lambda *_a, **_k: (None, None)
    ca.nudge_extension = lambda *_a, **_k: (None, None)
    ca.bsk_candidates = lambda: []
    seen = []
    ca.fetch_bing_candidates = lambda *a, **k: seen.append(True) or ([], {}, [])

    sys.argv = ["collect_adapter.py", str(task_dir / "job.json"), str(result_file),
                "--allow-bing-fallback"]
    ca.main()

    assert seen == [True], "explicit opt-in must still allow the Bing path"
    with zipfile.ZipFile(result_file) as archive:
        report = json.loads(archive.read("manifest.json"))["execution_report"]
    assert any("Bing" in str(check.get("detail", "")) for check in report["source_checks"])
