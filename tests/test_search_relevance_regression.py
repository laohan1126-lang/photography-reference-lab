"""Regression for the 549b search-relevance failure.

The fixtures are sanitized from the saved task window (public card text/URLs);
no original images, browser profiles or private paths are committed. These are
text-routing tests, not visual identity or aesthetic acceptance.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import quote

from PIL import Image

from ref_lab.search_relevance import (classify_card, confirmed_count, exploration_limit,
                                      exploration_count)
from ref_lab.verified_collection import deterministic_plan, query_steps
from tools import collect_verified as worker

FIXTURES = Path(__file__).parent / "fixtures" / "search-relevance-20261020"
PROJECT = {"character": "西木野真姬", "work": "Love Live!", "costume": "", "brief": ""}


def load(name):
    return json.loads((FIXTURES / name).read_text("utf8"))


def test_original_549b_queries_reproduce_chinese_only_plan():
    # These are the actual queries saved in 549b's search-summary/name-plan.
    original = [
        ("xiaohongshu", "西木野真姬 cos 摄影"),
        ("pinterest", "西木野真姬 cosplay photography"),
    ]
    assert original == [
        ("xiaohongshu", "西木野真姬 cos 摄影"),
        ("pinterest", "西木野真姬 cosplay photography"),
    ]
    # The old deterministic plan also had no Maki/Nishikino/Japanese variant.
    old_names = ["西木野真姬", "西木野真姬 Love Live!"]
    assert not any("Maki" in name or "真姫" in name for name in old_names)


def test_new_plan_uses_trusted_multilingual_aliases_and_records_source():
    plan = deterministic_plan(PROJECT)
    assert "Maki Nishikino" in plan.names
    assert "西木野真姫" in plan.names
    sources = {record["source"] for record in plan.name_records}
    assert "canonical_preset" in sources
    steps = query_steps(PROJECT, plan, ["xiaohongshu", "pinterest"])
    pinterest = [step for step in steps if step["source"] == "pinterest"]
    xhs = [step for step in steps if step["source"] == "xiaohongshu"]
    assert any("Maki Nishikino" in step["query"] for step in pinterest)
    assert any("西木野真姫" in step["query"] for step in xhs)
    assert all(step.get("used_name") and step.get("name_source") for step in steps)
    custom = deterministic_plan(PROJECT, user_aliases=["Maki-custom"])
    assert any(record["name"] == "Maki-custom" and record["source"] == "user_input"
               for record in custom.name_records)
    # Work is a separate context term; it must never be the "English name".
    for step in steps:
        assert step["used_name"] != f"西木野真姬 {PROJECT['work']}"


def test_saved_pinterest_cards_are_unconfirmed_and_cannot_fill_target():
    cards = load("pinterest-cards.json")["cards"]
    assert [card["asset_sha"][:8] for card in cards[:4]] == [
        "fe431b30", "f57c08d3", "2850d634", "e0a17384"]
    plan = deterministic_plan(PROJECT)
    results = [classify_card(card, names=plan.name_records,
                             work_terms=[PROJECT["work"]]) for card in cards[:4]]
    assert [item["tier"] for item in results] == ["unconfirmed"] * 4
    rows = [{"asset_sha": str(index) * 64, "relevance": item}
            for index, item in enumerate(results)]
    assert confirmed_count(rows) == 0
    assert exploration_count(rows) == 4
    assert exploration_limit(4) == 1
    # Four generic downloads are not a reached target; only one may be explored.
    assert len(rows) > exploration_limit(4)


def test_saved_xhs_cards_keep_possible_maki_posts_as_unconfirmed_or_named():
    cards = load("xhs-cards.json")["cards"]
    plan = deterministic_plan(PROJECT)
    tiers = [classify_card(card, names=plan.name_records,
                           work_terms=[PROJECT["work"]])["tier"] for card in cards]
    assert tiers.count("target_named") >= 3       # 小真姬 / maki cards
    assert tiers.count("unconfirmed") >= 5        # empty/generic text remains explorable
    assert "other_character" not in tiers


def test_explicit_other_character_is_not_a_target_candidate():
    result = classify_card({"text": "別キャラの有馬かな cosplay"},
                           names=[{"name": "西木野真姬", "language": "zh"}],
                           other_terms=["有馬かな"])
    assert result["tier"] == "other_character"
    assert result["name_hits"] == []


def _fake_photo(folder: Path, seed: int) -> dict:
    path = folder / "images" / f"seed-{seed}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (320, 480), (40 + seed, 80, 120)).save(path, format="PNG")
    raw = path.read_bytes()
    return {"asset_sha": hashlib.sha256(raw).hexdigest(), "original_path": str(path.resolve()),
            "page_url": f"https://www.pinterest.com/pin/{seed}/",
            "image_url": f"https://i.pinimg.com/736x/seed-{seed}.jpg",
            "source_text": "", "width": 320, "height": 480}


def test_four_generic_pins_do_not_reach_target_or_lie_about_completion(tmp_path):
    cards = load("pinterest-cards.json")["cards"][:4]
    images = []

    class Browser:
        def __init__(self, folder): self.folder = folder
        def start(self): pass
        def close(self): pass
        def search(self, step):
            return {"url": "https://www.pinterest.com/search/pins/?q=" + quote(step["query"]),
                    "search": step["query"], "visibleMain": "", "login_required": False,
                    "challenge": False, "cards": cards}
        def receive(self, card, step):
            row = _fake_photo(self.folder, len(images) + 1)
            images.append(row)
            return [row]

    class Agent:
        producer = "synthetic-relevance"
        model = "synthetic"
        candidate_calls = 0
        vision_cli_calls = 0
        references = []
        deadline = float("inf")
        def __init__(self): self.candidate_limit = 10
        def plan(self, project): raise AssertionError("search-only must not call the name model")

    job = {"id": "549b-regression", "project_snapshot": PROJECT, "target_count": 4,
           "preferred_sources": ["pinterest"], "notes": ""}
    summary, _ = worker.collect(job, Agent(), Browser(tmp_path), tmp_path, search_only=True)
    assert summary["target_reached"] is False
    assert summary["stop_reason"] == "relevance_unconfirmed"
    assert summary["status"] == "partial"
    assert summary["counts"]["target_confirmed"] == 0
    assert summary["counts"]["exploration"] == 1
    assert summary["counts"]["found"] == 1
    assert summary["model_calls"] == 0 and summary["tokens"] == 0
    received = json.loads((tmp_path / "received.json").read_text("utf8"))
    assert len(received) == 1
    assert received[0]["relevance"]["label"] == "角色相关性未确认"


def test_continue_search_keeps_existing_original_and_adds_without_recounting(tmp_path):
    runs = []

    class Browser:
        def __init__(self, folder): self.folder = folder
        def start(self): pass
        def close(self): pass
        def search(self, step):
            run = len(runs)
            return {"url": "https://www.pinterest.com/search/pins/?q=" + quote(step["query"]),
                    "search": step["query"], "visibleMain": "", "login_required": False,
                    "challenge": False,
                    "cards": [{"page": f"https://www.pinterest.com/pin/{run + 1}/",
                               "text": "西木野真姬 cosplay"}]}
        def receive(self, card, step):
            row = _fake_photo(self.folder, len(runs) + 1)
            runs.append(row)
            return [row]

    class Agent:
        producer = "synthetic-continue"
        model = "synthetic"
        candidate_calls = 0
        vision_cli_calls = 0
        references = []
        deadline = float("inf")
        def __init__(self): self.candidate_limit = 10
        def plan(self, project): raise AssertionError("search-only must not call the name model")

    base = {"id": "continue-regression", "project_snapshot": PROJECT, "target_count": 1,
            "preferred_sources": ["pinterest"], "notes": "", "search_extra_target": 1}
    first, _ = worker.collect({**base, "search_extra_target": 0}, Agent(), Browser(tmp_path),
                              tmp_path, search_only=True)
    assert first["status"] == "completed" and len(runs) == 1
    first_sha = runs[0]["asset_sha"]
    second, _ = worker.collect(base, Agent(), Browser(tmp_path), tmp_path, search_only=True)
    assert second["target_reached"] is True
    assert second["counts"]["found"] == 2
    assert second["counts"]["target_confirmed"] == 2
    received = json.loads((tmp_path / "received.json").read_text("utf8"))
    assert {row["asset_sha"] for row in received} == {first_sha, runs[1]["asset_sha"]}
    assert len(received) == 2


class FakeSortBrowser(worker.Browser):
    supports_sort = True

    def __init__(self):
        self.folder = Path(".")
        self.session = "fake"
        self.active = ["综合"]
        self.clicks = []

    def snapshot(self):
        return {"url": "https://www.xiaohongshu.com/search_result?keyword=x",
                "search": "x", "visibleMain": "", "login_required": False,
                "challenge": False, "cards": [{"page": "https://www.xiaohongshu.com/explore/" + "a" * 24}]}

    def command(self, *args, **kwargs):
        if args[0] == "evaluate":
            script = args[-1]
            if script == worker.XHS_SORT_JS:
                return json.dumps({"ok": True, "value": {
                    "trigger": "body>div>span", "dismiss": None,
                    "comprehensive": "body>div>div:nth-child(1)",
                    "latest": "body>div>div:nth-child(2)",
                    "active": self.active, "selected": "最新" in self.active,
                    "selected_comprehensive": "综合" in self.active}})
            return json.dumps({"ok": True, "value": self.snapshot()})
        if args[0] == "click":
            selector = args[args.index("--selector") + 1]
            self.clicks.append(selector)
            self.active = ["综合"] if selector.endswith("1)") else ["最新"]
        return "{}"


def test_xhs_prefers_comprehensive_and_only_uses_latest_when_requested():
    browser = FakeSortBrowser()
    step = {"source": "xiaohongshu", "query": "西木野真姬 cos 摄影"}
    snapshot = browser.search(step, sort="relevance")
    assert snapshot["sort_state"] == "comprehensive"
    assert all(not click.endswith("2)") for click in browser.clicks)
    browser2 = FakeSortBrowser()
    snapshot2 = browser2.search(step, sort="latest")
    assert snapshot2["sort_state"] == "latest"
    assert any(click.endswith("2)") for click in browser2.clicks)
